# Copyright 2015 Marko Dimjašević
#
# This file is part of JDoop.
#
# JDoop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# JDoop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with JDoop.  If not, see <http://www.gnu.org/licenses/>.


import subprocess, threading
import os, signal

class Command:
    def __init__(self, args):
        self.process = None
        self.args = args

    def run(self):
        self.process = subprocess.Popen(args=self.args, shell=True)
        self.process.communicate()


class CommandWithTimeout:
    def __init__(self, args = None):
        self.process = None
        self.args = args
        self.thread = None

    def run_without_joining(self):
        def target():
            self.process = subprocess.Popen(args=self.args, shell=True, preexec_fn=os.setsid)
            self.process.communicate()

        self.thread = threading.Thread(target=target)
        self.thread.start()

    def join_thread(self, timeout = None):
        if timeout == None:
            self.thread.join()
        else:
            self.thread.join(timeout)
            if self.thread.is_alive():
                os.killpg(self.process.pid, signal.SIGTERM)
                self.thread.join()
                print 'Timeout Termination: ' + self.args

    def run(self, timeout = None):

        self.run_without_joining()
        self.join_thread(timeout)
