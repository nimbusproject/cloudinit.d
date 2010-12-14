# this file contains a set of classes that are 'pollable' objects.
"""
This file contains a set of classes called 'pollables'.  A pollable is an object with a start(), cancel()
and poll() method.  It encapsulates some set of asyncronous functionality that is started and monitored
for completion.  The poll() method returns either true or false depending on whether or not the object
has completed its objective.

Pollables are combined later into bootlevels.  Each bootlevel consisists of N > 1 pollables.  when all
pollables are complete, that bootlevel is complete and the next bootlevel can be run.

The SVCContainer class in the services.py file is another type of pollable.  It is customized to use three
internal pollables of specific purpose.
"""
from boto.exception import EC2ResponseError
import logging
from select import select
import subprocess
import time
import thread
import datetime
from cloudboot.exceptions import TimeoutException, IaaSException, APIUsageException, ProcessException, MultilevelException
import cloudboot

__author__ = 'bresnaha'


class Pollable(object):

    def __init__(self, timeout=0):
        self._timeout = timeout

    def start(self):
        self._start_time = datetime.datetime.now()

    def poll(self):
        if self._timeout == 0:
            return False
        now = datetime.datetime.now()
        diff = now - self._timeout
        if diff.second > self._timeout:
            raise TimeoutException("pollable %s timedout at %d seconds" % (str(self), self._timeout))
        return False


class InstanceHostnamePollable(Pollable):
    """
    Async poll a IaaS service via boto.  Once the VM has an associated hostname, the Pollable object is considered
    ready.
    """

    def __init__(self, instance, log=logging, timeout=600):
        Pollable.__init__(self, timeout)
        self._instance = instance
        self._poll_error_count = 0
        self._log = log
        self._state = "pending"
        self._done = False
        self.exception = None
        self._thread = None

    def start(self):
        Pollable.start(self)
        self._thread = thread.start_new_thread(self._thread_poll, (0.1,))        

    def poll(self):
        if self.exception:
            raise self.exception
        if self._done:
            return True

        # check time out here
        Pollable.poll(self)
        if self._state == "running":
            self._done = True
            self._thread.join()
            return True
        if self._state != "pending":
            self.exception = IaaSException("The current state is %s.  Never reached state running" % (self._instance.state))
            raise self.exception
        return False

    def cancel(self):
        self._done = True
        if self._thread:
            self._thread.join()

    def get_instance(self):
        return self._instance

    def get_hostname(self):
        return self._instance.public_dns_name

    def _thread_poll(self, poll_period=0.1):

        while not self._done:
            try:
                self._state = self._instance.update()
                if self._state != "pending":
                    self._done = True
                else:
                    time.sleep(poll_period)
            except EC2ResponseError, ecex:
                # We allow this error to occur once.  It takes ec2 some time
                # to be sure of the instance id
                if self._poll_error_count > 0:
                    # if we poll too quick sometimes aws cannot find the id
                    self.exception = IaaSException(ecex)
                    self._log.error(ecex)
                    self._done = True
                self._poll_error_count = self._poll_error_count + 1                
            except Exception, ex:
                self.exception = IaaSException(ex)
                self._done = True


class PopenExecutablePollable(Pollable):
    """
    This Object will asynchornously for/exec a program and collect all of its stderr/out.  The program is allowed to fail
    by returning an exit code of != 0 allowed_errors number of times.
    """

    def __init__(self, cmd, allowed_errors=1024, log=logging, timeout=600):
        Pollable.__init__(self, timeout)
        self.cmd = cmd
        self._stderr = ""
        self._stdout = ""
        self._error_count = 0
        self._allowed_errors = allowed_errors
        self._log = log
        self._started = False
        self._p = None
        self._exception = None

    def _get_stderr(self):
        """Get and reset the current stderr buffer from any (and all) execed programs.  Good for logging"""
        s = self._stderr_str
        self._stderr_str = ""
        return s

    def _get_stdout(self):
        """Get and reset the current stdout buffer from any (and all) execed programs.  Good for logging"""
        s = self._stdout_str
        self._stdout_str = ""
        return s

    def start(self):
        Pollable.start(self)
        self._run()
        self._started = True

    def poll(self):
        if self._exception:
            raise self._exception
        if not self._started:
            raise APIUsageException("You must call start before calling poll.")        
        if self._done:
            return True
        # check timeout here
        try:
            Pollable.poll(self)
            return self._poll()
        except TimeoutException, toex:
            self._exception = toex
            raise
        except Exception, ex:
            self._exception = ProcessException(ex, self._stdout_str, self._stderr_str)
            raise self._exception

    def cancel(self):
        if not self._done:
            return
        # kill it and set the error count to past the max so that it is not retried
        self._p.terminate()
        self._error_count = self._allowed_errors

    def _poll(self):
        """pool to see of the process has completed.  If incomplete None is returned.  Otherwise the latest return code is sent"""

        rc = self._poll_process()
        if rc == None:
            return False
        if rc != 0:
            self._error_count = self._error_count + 1
            if self._error_count < self._allowed_errors:
                raise ProcessException("Process exceeded the allowed number of failures: %s" % (self._cmd))
            self._run()
            return False
        self._final_rc = rc
        self._done = True
        return True

    def _poll_process(self, poll_period=0.1):
        eof = self._read_output(self._p, poll_period)
        if not eof:
            return None
        rc = self._p.poll()
        return rc

    def _read_output(self, p, poll_period):
        selectors = []
        if not self._stdout_eof:
            selectors.append(p.stdout)
        if not self._stderr_eof:
            selectors.append(p.stderr)

        (rlist,wlist,elist) = select.select(selectors, [], [], poll_period)
        for f in rlist:
            line = f.readline()
            if f == p.stdout:
                # we assume there will be a full line or eof
                # not the fastest str concat, but this is small
                self._stdout_str = self._stdout_str + line
                if line == "":
                    self._stdout_eof = True
            else:
                self._stderr_str = self._stderr_str + line
                if line == "":
                    self._stderr_eof = True

        return self._stderr_eof and self._stdout_eof

    def _run(self):
        self._log.debug(self._cmd)
        self._p = subprocess.Popen(self._cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)


class MultiLevelPollable(Pollable):
    """
    This pollable object monitors a set of pollable levels.  Each level is a list of pollable objects.   When all
    pollables in a list are complete, the next level is polled.  When all levels are completed this pollable is
    considered complete
    """
    def __init__(self, log=logging, timeout=0, callback=None):
        Pollable.__init__(self, timeout)
        self.levels = []
        self.level_ndx = -1
        self._log = log
        self.starting_state = 1
        self.transition_state = 2
        self.complete_state = 3
        self._timeout = timeout
        self.exception = None
        self._done = False
        self._level_error_ex = []
        self._level_error_polls = []
        self._callback = callback

    def get_level(self):
        return self.level_ndx + 1

    def start(self):
        Pollable.start(self)        
        if self.level_ndx >= 0:
            return
        self.level_ndx = 0
        if len(self.levels) == 0:
            return
        if self._callback:
            self._callback(self, cloudboot.callback_action_started, self.level_ndx)
        for p in self.levels[self.level_ndx]:
            p.start()

    def poll(self):
        if self.exception:
            raise self.exception
        if self.level_ndx < 0:
            raise APIUsageException("You must call start before calling poll.")
        if self.level_ndx == len(self.levels):
            return True
        Pollable.poll(self)

        # allow everything in the level to complete before raising the exception
        level = self.levels[self.level_ndx]
        done = True
        for p in level:
            if p not in self._level_error_polls:
                try:
                    rc = p.poll()
                    if not rc:
                        done = False
                except Exception, ex:
                    self._level_error_ex.append(ex)
                    self._level_error_polls.append(p)

        if done:
            # see if the level had an error
            if len(self._level_error_polls) > 0:
                self.exception = MultilevelException(self._level_error_ex, self._level_error_polls, self.level_ndx)
                raise self.exception

            self.level_ndx = self.level_ndx + 1
            if self.level_ndx == len(self.levels):
                self._execute_cb(cloudboot.callback_action_complete, self.level_ndx - 1)
                self._done = True
                return True
            if self._callback:
                self._execute_cb(cloudboot.callback_action_complete, self.level_ndx - 1)
                self._execute_cb(cloudboot.callback_action_started, self.level_ndx)

            for p in self.levels[self.level_ndx]:
                p.start()
        return False

    def _execute_cb(self, action, lvl):
        if not self._callback:
            return
        self._callback(self, action, lvl)
            
    def cancel(self):
        """
        Simply call cancel on all the objects this one owns
        """
        for level in self.level_ndx:
            for p in level:
                p.cancel()        

    def add_level(self, pollable_list):
        if self.level_ndx >= 0:
            raise APIUsageException("You cannot add a level after starting the poller")
        self.levels.append(pollable_list)

