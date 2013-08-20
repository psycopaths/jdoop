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
    def __init__(self, cmd, args = None):
        self.cmd = cmd
        self.process = None
        self.args = args

    def run(self, timeout):
        def target():
            # self.process = subprocess.Popen(args=self.args, executable=self.cmd, shell=True, preexec_fn=os.setsid)
            self.process = subprocess.Popen(args=self.args, shell=True, preexec_fn=os.setsid)
            self.process.communicate()

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            os.killpg(self.process.pid, signal.SIGTERM)
            thread.join()
            print 'Timeout Termination: ' + self.cmd + ' ' + self.args
