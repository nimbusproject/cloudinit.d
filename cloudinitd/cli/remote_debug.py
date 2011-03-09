import sys

# Changing "ENABLED" to True requires the presence of the library ("pycharm-debug.egg")
# as well as a socket opened (which happens when you activiate the 'Python remote' debug
# configuration in PyCharm on the specified host with the same port configured).

ENABLED = False

HOST = "localhost"
PORT = 51234

def connect_debugger_if_enabled():
    if not ENABLED:
        return

    try:
        from pydev import pydevd
    except ImportError, e:
        print >>sys.stderr, "Could not import remote debugging library: %s" % str(e)
        return

    pydevd.settrace(HOST, port=PORT, stdoutToServer=True, stderrToServer=True)
