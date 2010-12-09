import os
import uuid
import time
import logging
from cloudboot.exceptions import APIUsageException
from cloudboot.persistantance import CloudBootDB
from cloudboot.services import BootTopLevel

__author__ = 'bresnaha'

def config_get_or_none(parser, s, v):
    try:
        x = parser.get(s, v)
        return x
    except:
        return None


class CloudBoot(object):
    """
        This class is the top level boot description. It holds the parent Multilevel boot object which contains a set
        of many pollables.  The object also contains a way to get variable information from every service created.
        A service cannot be created without this object.  This object holds a dictionary of all services which is
        used for querying dependencies
    """
    
    def __init__(self, db_dir, config_file=None, db_name=None, log=logging):

        if db_name == None and config_file == None:
            raise APIUsageException("Cloud boot must have a db_name or a config file to load")
        if not os.path.exists(db_dir):
            raise APIUsageException("Path to the give db does not exist: %s" % (db_name))

        if db_name == None:
            db_name = str(uuid.uuid4()).split("-")[0]

        db_path = "/%s/cloudboot-%s.db" % (db_dir, db_name)
        if config_file == None:
            if not os.path.exists(db_path):
                raise APIUsageException("Path to the db does not exist %s.  New dbs must be given a config file" % (db_path))

        self._log = log
        self._started = False
        self.run_name = db_name
        dburl = "sqlite://%s" % (db_path)

        self._db = CloudBootDB(dburl)

        if config_file != None:
            self._bo = self._db.load_from_conf(config_file)
        else:
            self._bo = self._db.load_from_db()

        self._levels = []
        self._boot_top = BootTopLevel(log=log)
        for level in self._bo.levels:
            level_list = []
            for s in level.services:
                svc = self._boot_top.new_service(s, self._db)
                level_list.append(svc)

            self._boot_top.add_level(level_list)
            self._levels.append(level_list)


    # return a booting service for inspection by the user
    def get_service(self, svc_name):
        svc_dict = self._boot_top.get_services()
        return CloudService(svc_dict[svc_name])

    # get a list of all the services in the given level
    def get_level(self, level_ndx):
        svc_list = self._levels[level_ndx]
        cs_list = [CloudService(svc) for svc in svc_list]
        return cs_list

    def get_level_count(self):
        return len(self._levels)

    # poll the entire boot config until complete
    def block_until_complete(self, callback=None, poll_period=0.1):
        if not self._started:
            raise APIUsageException("Boot plan must be started first.")

        done = False
        while not done:
            time.sleep(poll_period)
            done = self.poll(callback)

    # poll one pass at the boot plan.
    def poll(self, callback=None):
        if not self._started:
            raise APIUsageException("Boot plan must be started first.")
        rc = self._boot_top.poll(callback=callback)
        if rc:
            self._bo.status = 1
            self._db.db_commit()

    def start(self):
        self._boot_top.start()
        self._started = True


class CloudService(object):

    def __init__(self, svc):
        """This should only be called by the CloudBoot object"""
        self._svc = svc
        self.name = svc.name

    def get_attr_from_bag(self, name):
        self._svc.get_dep(name)
    # need various methods for monitoring state. values from attr bag and from db

