import os
import sys
from optparse import OptionParser

class bootOpts(object):

    def __init__(self, long, short, description, default, vals=None, range=None, flag=None, count=False, long_help=False):
        self.long = "--" + long.replace('_', '-')
        self.dest = long
        self.short = "-" + short
        self.vals = vals
        self.default = default
        self.flag = flag
        self.range = range
        self.description = description
        self.count = count
        self.long_help = long_help

    def validate(self, options):

        try:
            val = getattr(options, self.dest)
        except:
            emsg = self.get_error_msg()
            raise Exception(emsg)

        if val == None:
            return
        if self.flag != None:
            return
        if self.range != None:
            if len(self.range) == 2:
                if float(val) == -1.0:
                    if float(self.range[0]) != -1.0 and float(self.range[1]) != -1.0:
                        raise Exception("you specified a value out of range")
 
                    else:
                        return

                if (float(val) < float(self.range[0]) and float(self.range[0]) != -1.0) or (float(val) > float(self.range[1]) and float(self.range[1]) != -1.0):
                    emsg = self.get_error_msg()
                    raise Exception(emsg)
            return

        if self.vals != None:
            for v in self.vals:
                if val == v:
                    return

            emsg = self.get_error_msg()
            raise Exception(emsg)

    def get_description(self):
        if self.range != None:
            msg = self.description + " : between %s - %s" % (self.range[0], self.range[1])
            return msg

        if self.vals != None:
            msg = self.description + " : {"
            delim = ""
            for v in self.vals:
                msg = msg + delim + str(v)
                delim = " | "
            msg = msg + "}"

            return msg

        return self.description

    def add_opt(self, parser):
        if self.flag != None:
            if self.default:
                a = "store_false"
            else:
                a = "store_true"
            parser.add_option(self.short, self.long, dest=self.dest, default=self.default,
                action=a,
                help=self.get_description())
            return

        if self.count:
            parser.add_option(self.short, self.long, dest=self.dest,
                default=self.default,
                action="count",
                help=self.get_description())
            return

        parser.add_option(self.short, self.long, dest=self.dest,
            default=self.default, type="string",
            help=self.get_description())

