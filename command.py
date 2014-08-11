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
