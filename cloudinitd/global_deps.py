import ConfigParser
from cloudinitd.exceptions import ConfigException

g_var_objects = {}
g_global_obj = {}

class CidVarObject(object):

    def __init__(self):
        # using its own dict to avoid any conflicts in __dict__
        self.vars = {}

    def set_var(self, key, val):
        self.vars[key] = val

def set_global_var_file(path, rank):
    parser = ConfigParser.ConfigParser()
    parser.read(path)
    items = parser.items("globals")
    for (key, value) in items:
        set_global_var(key, value, rank)

def set_global_var(key, val, rank):
    global g_var_objects
    rank = int(rank)
    if rank not in g_var_objects:
        g_var_objects[rank] = CidVarObject()
    obj = g_var_objects[rank]
    obj.set_var(key, val)

def global_merge_down():
    global g_global_obj
    keys = g_var_objects.keys()
    keys.sort()

    global_obj = CidVarObject()
    for rank in keys:
        rank_obj = g_var_objects[rank]

        for key in rank_obj.vars:
            val = rank_obj.vars[key]
            global_obj.set_var(key, val)
    g_global_obj = global_obj


def get_global(key, default=None, raise_ex=False):
    if key not in g_global_obj.vars.keys():
        if raise_ex:
            raise ConfigException("The global variable %s is not set." % (key))
        return default
    return g_global_obj.vars[key]
