#!/usr/bin/env python3

import configparser
import os

class ConfigLoader(object):
    CONFIG_FILE = "config.ini"
    CONFIG_FALLBACK = "config.ini.skel"

    def __init__(self):
        pass

    def load(self):
        config = configparser.ConfigParser()

        if (os.path.isfile(self.CONFIG_FILE)):
            try:
                config.read(self.CONFIG_FILE)
            except configparser.ParsingError as error:
                print(error)
                print("Please correct the errors and try again")
                sys.exit(1)
        else:
            print("Could not find %s; copying %s -> %s" % (
                self.CONFIG_FILE, self.CONFIG_FALLBACK, self.CONFIG_FILE
            ))
            shutil.copyfile(self.CONFIG_FALLBACK, self.CONFIG_FILE)
            print("Please edit this file before running again.")
            sys.exit(1)

        return config
