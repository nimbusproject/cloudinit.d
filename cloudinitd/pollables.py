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
import select
import subprocess
import time
from threading import Thread
import datetime
from cloudinitd.exceptions import TimeoutException, IaaSException, APIUsageException, ProcessException, MultilevelException, PollableException
import cloudinitd
import traceback
import os
from cloudinitd.cb_iaas import *
import socket





class Pollable(object):

    def __init__(self, timeout=0, done_cb=None):
        self._timeout = timeout
        self._exception = None
        self._done_cb = done_cb
        self._end_time = None
        self._start_time = None

    def get_exception(self):
        return self._exception

    def start(self):
        self._start_time = datetime.datetime.now()

    def _execute_done_cb(self):
        self._end_time = datetime.datetime.now()
        if not self._done_cb:
            return
        self._done_cb(self)

    def pre_start(self):
        pass

    def poll(self):
        if self._timeout == 0:
            return False
        now = datetime.datetime.now()
        diff = now - self._start_time
        if diff.seconds > self._timeout:
            self._exception = TimeoutException("pollable %s timedout at %d seconds" % (str(self), self._timeout))
            raise self._exception
        return False

    def get_runtime(self):
        if not self._end_time:
            return None
        return self._end_time - self._start_time

class NullPollable(Pollable):

    def __init__(self, log=logging):
        Pollable.__init__(self)

    def start(self):
        Pollable.start(self)

    def poll(self):
        return True

class HostnameCheckThread(Thread):
    def __init__(self, host_poller):
        Thread.__init__(self)
        self.host_poller = host_poller

    def run(self):
        self.host_poller._thread_poll()

class InstanceTerminatePollable(Pollable):

    def __init__(self, instance, log=logging, timeout=600, done_cb=None):
        Pollable.__init__(self, timeout, done_cb=done_cb)
        self._instance = instance
        self._log = log
        self._started = False
        self._done = False
        self.exception = None
        self._thread = None

    def start(self):
        Pollable.start(self)
        self._started = True
        self._instance.terminate()

    def poll(self):
        if not self._started:
            raise APIUsageException("You must first start the pollable object")
        self._execute_done_cb()
        return True

    def cancel(self):
        pass


class PortPollable(Pollable):

    def __init__(self, host, port, retry_count=256, log=logging, timeout=600, done_cb=None):
        Pollable.__init__(self, timeout, done_cb=done_cb)
        self._log = log
        self._started = False
        self._done = False
        self.exception = None
        self._thread = None
        self._host = host
        self._port = port
        self._poll_error_count = 0
        self._retry_count = retry_count
        self._time_delay = datetime.timedelta(seconds=3                 )
        self._last_run = None

    def start(self):
        Pollable.start(self)
        self._started = True

    def poll(self):
        if not self._started:
            raise APIUsageException("You must first start the pollable object")

        if 'CLOUDINITD_TESTENV' in os.environ:
            return True

        Pollable.poll(self)

        now = datetime.datetime.now()
        if self._last_run:
            if now - self._last_run < self._time_delay:
                return False
        self._last_run = now

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10.0)
            cloudinitd.log(self._log, logging.DEBUG, "Attempting to connect to %s:%d" % (self._host, self._port))
            s.connect((self._host, self._port))
            self._execute_done_cb()
            return True
        except Exception, ex:
            self._poll_error_count = self._poll_error_count + 1
            if self._poll_error_count > self._retry_count:
                cloudinitd.log(self._log, logging.ERROR, "safety error count exceeded" + str(ex), tb=traceback)
                raise
            cloudinitd.log(self._log, logging.INFO, "Retry %d for %s:%d" % (self._poll_error_count, self._host, self._port))

            return False

    def cancel(self):
        pass



class InstanceHostnamePollable(Pollable):
    """
    Async poll a IaaS service via boto.  Once the VM has an associated hostname, the Pollable object is considered
    ready.
    """

    def __init__(self, svc=None, log=logging, timeout=600, done_cb=None, instance=None):
        Pollable.__init__(self, timeout, done_cb=done_cb)
        self._svc = svc
        self._instance = instance
        self._poll_error_count = 0
        self._max_id_error_count = 1
        self._log = log
        self._done = False
        self.exception = None
        self._thread = None
        self._ok_states = ["networking", "pending", "scheduling", "spawning", "launching"]


    def pre_start(self):
        if not self._instance:
            iaas_con = iaas_get_con(self._svc)
            self._instance = iaas_con.run_instance()
            # it might be awkward to call back into service here, not sure how i feel
            if self._svc:
                # this is for historical records in the database
                self._svc.new_iaas_instance(self._instance)


    def start(self):
        self.pre_start()
        Pollable.start(self)
        self._update()
        self._thread = HostnameCheckThread(self)
        self._thread.start()

    def poll(self):
        if self.exception:
            raise self.exception
        if self._done:
            return True

        # check time out here
        Pollable.poll(self)
        # cache the state at tis time on the local call stack, should be thread safe
        state = self._instance.get_state()
        cloudinitd.log(self._log, logging.DEBUG, "Current iaas state in poll for %s is %s" % (self.get_instance_id(), state))
        if state == "running":
            self._done = True
            self._thread.join()
            self._execute_done_cb()
            return True
        if state not in self._ok_states:
            msg = "The current state is %s.  Never reached state running" % (state)
            cloudinitd.log(self._log, logging.DEBUG, msg, tb=traceback)
            self.exception = IaaSException(msg)
            raise self.exception
        return False

    def cancel(self):
        self._done = True
        if self._instance:
            self._instance.cancel()
        if self._thread:
            self._thread.join(3.0)

    def get_instance_id(self):
        return self._instance.get_id()

    def get_instance(self):
        return self._instance

    def get_hostname(self):
        return self._instance.get_hostname()

    def get_status(self):
        return self._instance.get_state()

    def _update(self):
        try:
            self._instance.update()
        except EC2ResponseError, ecex:
            # We allow this error to occur once.  It takes ec2 some time
            # to be sure of the instance id
            if self._poll_error_count > self._max_id_error_count:
                # if we poll too quick sometimes aws cannot find the id
                cloudinitd.log(self._log, logging.ERROR, "safety error count exceeded" + str(ecex), tb=traceback)
                raise
            self._poll_error_count = self._poll_error_count + 1

    def _thread_poll(self, poll_period=1.0):
        done = False
        while not self._done and not done:
            try:
                if self._instance.get_state() not in self._ok_states:
                    cloudinitd.log(self._log, logging.DEBUG, "%s polling thread done" % (self.get_instance_id()))
                    done = True
                # because update is called in start we will sleep first
                else:
                    time.sleep(poll_period)
                    self._update()
                    cloudinitd.log(self._log, logging.DEBUG, "Current iaas state in thread for %s is %s" % (self.get_instance_id(), self._instance.get_state()))
            except Exception, ex:
                cloudinitd.log(self._log, logging.ERROR, str(ex), tb=traceback)
                self.exception = IaaSException(ex)
                done = True

class PopenExecutablePollable(Pollable):
    """
    This Object will asynchornously for/exec a program and collect all of its stderr/out.  The program is allowed to fail
    by returning an exit code of != 0 allowed_errors number of times.
    """

    def __init__(self, cmd, allowed_errors=64, log=logging, timeout=600, callback=None, done_cb=None):
        Pollable.__init__(self, timeout, done_cb=done_cb)
        self._cmd = cmd
        self._stderr_str = ""
        self._stdout_str = ""
        self._stdout_eof = False
        self._stderr_eof = False
        self._error_count = 0
        self._allowed_errors = allowed_errors
        self._log = log
        self._started = False
        self._p = None
        self._exception = None
        self._done = False
        self._callback = callback
        self._time_delay = datetime.timedelta(seconds=10)
        self._last_run = None

    def get_stderr(self):
        """Get and reset the current stderr buffer from any (and all) execed programs.  Good for logging"""
        s = self._stderr_str
        return s

    def get_stdout(self):
        """Get and reset the current stdout buffer from any (and all) execed programs.  Good for logging"""
        s = self._stdout_str
        return s

    def get_output(self):
        return self.get_stderr() + os.linesep + self.get_stdout()

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
            cloudinitd.log(self._log, logging.ERROR, str(toex), tb=traceback)
            raise
        except Exception, ex:
            cloudinitd.log(self._log, logging.ERROR, str(ex), tb=traceback)
            self._exception = ProcessException(self, ex, self._stdout_str, self._stderr_str)
            raise self._exception

    def cancel(self):
        if self._done or not self._started:
            return
        # kill it and set the error count to past the max so that it is not retried
        self._p.terminate()
        self._error_count = self._allowed_errors

    def _execute_cb(self, action, msg):
        if not self._callback:
            return
        self._callback(self, action, msg)

    def _poll(self):
        """pool to see of the process has completed.  If incomplete None is returned.  Otherwise the latest return code is sent"""
        if self._last_run:
            now = datetime.datetime.now()
            if now - self._last_run < self._time_delay:
                return False
            self._last_run = None
            self._execute_cb(cloudinitd.callback_action_transition, "retrying the command")
            self._run()

        rc = self._poll_process()
        if rc is None:
            return False
        self._log.info("process return code %d" % (rc))
        if rc != 0:
            self._error_count = self._error_count + 1
            if self._error_count >= self._allowed_errors:
                ex = Exception("Process exceeded the allowed number of failures %d with %d: %s" % (self._allowed_errors, self._error_count, self._cmd))
                raise ProcessException(ex, self._stdout_str, self._stderr_str, rc)
            self._last_run = datetime.datetime.now()
            return False
        self._done = True
        self._execute_cb(cloudinitd.callback_action_complete, "Pollable complete")
        self._execute_done_cb()
        self._p = None
        return True

    def _poll_process(self, poll_period=0.1):
        eof = self._read_output(self._p, poll_period)
        if not eof:
            return None
        self._p.poll()
        return self._p.returncode

    def _read_output(self, p, poll_period):
        selectors = []
        if not self._stdout_eof:
            selectors.append(p.stdout)
        if not self._stderr_eof:
            selectors.append(p.stderr)

        (rlist,wlist,elist) = select.select(selectors, [], [], poll_period)
        if not rlist:
            p.poll()
            if p.returncode:
                self._stdout_eof = True
                self._stderr_eof = True

        for f in rlist:
            line = f.readline()

            if f == p.stdout:
                # we assume there will be a full line or eof
                # not the fastest str concat, but this is small
                self._stdout_str = self._stdout_str + line
                if not line:
                    self._stdout_eof = True
                else:
                    cloudinitd.log(self._log, logging.INFO, "stdout: %s" %(line))
            else:
                self._stderr_str = self._stderr_str + line
                if not line:
                    self._stderr_eof = True
                else:
                    cloudinitd.log(self._log, logging.INFO, "stderr: %s" %(line))

        return self._stderr_eof and self._stdout_eof

    def _run(self):
        cloudinitd.log(self._log, logging.DEBUG, "running the command %s" % (str(self._cmd)))
        self._p = subprocess.Popen(self._cmd, shell=True, stdin=open(os.devnull), stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)

    def get_command(self):
        return self._cmd

class MultiLevelPollable(Pollable):
    """
    This pollable object monitors a set of pollable levels.  Each level is a list of pollable objects.   When all
    pollables in a list are complete, the next level is polled.  When all levels are completed this pollable is
    considered complete
    """
    def __init__(self, log=logging, timeout=0, callback=None, continue_on_error=False):
        Pollable.__init__(self, timeout)
        self.levels = []
        self.level_times = []
        self.level_ndx = -1
        self._log = log
        self._timeout = timeout
        self.exception = None
        self._done = False
        self._level_error_ex = []
        self._all_level_error_exs = []
        self._exception_occurred = False
        self._continue_on_error = continue_on_error
        self._level_error_polls = []
        self._callback = callback
        self._reversed = False
        self.last_exception = None
        self._canceled = False
        self._current_level_start = None

    def get_level(self):
        return self.level_ndx + 1

    def _get_callback_level(self):
        if self._reversed:
            ndx = len(self.levels) - self.level_ndx - 1
        else:
            ndx = self.level_ndx
        return ndx

    def pre_start(self):
        for l in self.levels:
            for p in l:
                p.pre_start()

    def start(self):
        Pollable.start(self)
        if self.level_ndx >= 0:
            return

        self._current_level_start_time = datetime.datetime.now()
        self.level_ndx = 0
        if len(self.levels) == 0:
            return
        self._start()

    def _start(self):
        self._execute_cb(cloudinitd.callback_action_started, self._get_callback_level())
        for p in self.levels[self.level_ndx]:
            try:
                p.start()
            except Exception, ex:
                self._exception_occurred = True
                self.last_exception = PollableException(p, ex)
                self._level_error_ex.append(self.last_exception)
                self._level_error_polls.append(p)
                cloudinitd.log(self._log, logging.ERROR, "Multilevel poll error on start %s" % (str(ex)), traceback)

                if not self._continue_on_error:
                    self._execute_cb(cloudinitd.callback_action_error, self._get_callback_level())
                    self.exception = ex
                    raise


    def poll(self):
        if self.exception and not self._continue_on_error:
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
                    self._exception_occurred = True
                    self.last_exception = PollableException(p, ex)
                    self._level_error_ex.append(self.last_exception)
                    self._level_error_polls.append(p)
                    cloudinitd.log(self._log, logging.ERROR, "Multilevel poll error %s" % (str(ex)), traceback)

        if done:
            # see if the level had an error
            cb_action = cloudinitd.callback_action_complete
            if len(self._level_error_polls) > 0:
                cb_action = cloudinitd.callback_action_error
                exception = MultilevelException(self._level_error_ex, self._level_error_polls, self.level_ndx)
                self.last_exception = exception
                if not self._continue_on_error:
                    self._execute_cb(cloudinitd.callback_action_error, self._get_callback_level())
                    self.exception = exception
                    raise exception

                self._all_level_error_exs.append(self._level_error_ex)
                self._level_error_polls = []
                self._level_error_ex = []

            _current_level_end_time = datetime.datetime.now()
            self.level_times.append(_current_level_end_time - self._current_level_start_time)
            self._current_level_start_time = datetime.datetime.now()


            self._execute_cb(cb_action, self._get_callback_level())
            self.level_ndx = self.level_ndx + 1

            if self.level_ndx == len(self.levels):
                self._done = True
                return True
            self._execute_cb(cloudinitd.callback_action_started, self._get_callback_level())

            self._start()
        return False

    def _execute_cb(self, action, lvl):
        if not self._callback:
            return
        self._callback(self, action, lvl+1)

    def get_level_times(self):
        return self.level_times

    #def cancel(self):
    # table this for now
    #    """
    #    Simply call cancel on all the objects this one owns
    #    """
    #    for level in self.levels:
    #        for p in level:
    #            p.cancel()

    def add_level(self, pollable_list):
        if self.level_ndx >= 0:
            raise APIUsageException("You cannot add a level after starting the poller")
        self.levels.append(pollable_list)

    def reverse_order(self):
        self.levels.reverse()
        self._reversed = not self._reversed

    def cancel(self):
        if self._canceled:
            return

        for i in range(0, self.level_ndx):
            lvl = self.levels[i]
            for p in lvl:
                p.cancel()

        self._canceled = True


class ValidationPollable(Pollable):

    def __init__(self, svc, timeout=600, done_cb=None):
        Pollable.__init__(self, timeout, done_cb=done_cb)
        self._svc = svc


    def start(self):
        Pollable.start(self)
