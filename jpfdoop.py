#!/usr/bin/env python

# The main JPF-Doop program file. It is used to run JPF-Doop to
# generate unit tests.

import subprocess, os, shutil, threading
import argparse

from symbolize_tests import *
from generate_jpf_files import *

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
            self.process = subprocess.Popen(args=self.args, executable=self.cmd, shell=True, preexec_fn=os.setsid)
            self.process.communicate()

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            os.killpg(self.process.pid, signal.SIGTERM)
            thread.join()
            print 'Timeout Termination: ' + self.cmd + ' ' + self.args

class ClassList:
    def get_all_java_source_files(self, base, rootdir):
        ret = []
        
        for dirpath, dirnames, filenames in os.walk(os.path.join(base, rootdir)):
            for name in filenames:
                if name.endswith('.java'):
                    # No need to worry about abstract class or
                    # interfaces because Randoop will take care of
                    # that
                    ret.append(dirpath[len(os.path.normpath(base)) + 1:].replace("/", ".") + "." + name[:-len(".java")])

        return ret

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generates unit tests with Randoop only or with JPF-Doop.')
    parser.add_argument('--packagename', required=True, help='A Java package with classes to analyze.')
    parser.add_argument('--path', required=True, help='path within the root directory to the source files')
    parser.add_argument('--root', default='src/examples/', help='source files root directory')
    parser.add_argument('--classlist', default='classlist.txt', help='Name of a file to write a file list to')
    params = parser.parse_args()
    classlist = ClassList()

    # Make a class list of classes to be tested

    with open(params.classlist, 'w') as f:
        f.write("\n".join(classlist.get_all_java_source_files(params.root, params.path)) + "\n")

    # Invoke Randoop to generate unit tests

    unit_tests_classlist = params.classlist
    unit_tests_directory = "tests-1st-round"

    # Remove previous unit tests

    shutil.rmtree(unit_tests_directory, ignore_errors = True)
    os.mkdir(unit_tests_directory)

    # Run Randoop

    unit_tests_name = "Randoop1Test"
    unit_tests_timelimit = 5
    unit_tests_number_upper_limit = 15
    randoop_command = Command(args = "java -ea -cp lib/randoop.jar:lib/junit4.jar:build/examples randoop.main.Main gentests --classlist=%s --junit-output-dir=%s --junit-classname=%s --timelimit=%d --outputlimitrandom=%d --forbid-null=false --small-tests=true" % (unit_tests_classlist, unit_tests_directory, unit_tests_name, unit_tests_timelimit, unit_tests_number_upper_limit))
    randoop_command.run()

    # Symbolize unit tests

    unit_tests = SymbolicUnitTests(params.packagename, "src/examples", "classes-to-analyze", '%s/%s%s' % (unit_tests_directory, unit_tests_name, '0.java'))
    unit_tests.generate_symbolized_unit_tests()
    
    # Generate JPF configuration files
    
    jpf_configuration_files = CoordinateConfFileGeneration(params.packagename, 'src/examples', 'classes-to-analyze')
    jpf_configuration_files.run()

    # Compile symbolized unit tests

    compile_tests_command = Command(args = "javac -g -d build/examples -cp build/:build/classes:build/annotations:build/examples/:build/tests:lib/junit4.jar src/examples/randooped/*java")
    compile_tests_command.run()

    # Run JDart
    # TODO Read a path to the jpf executable from a file

    jdart_path = "/home/marko/projects/jpf/jpf-core/bin/jpf"
    
    with open("src/examples/" + params.packagename + "/" + "classes-to-analyze") as f:
        for line_nl in f:
            class_name = line_nl[:-1]

            whole_path = "src/examples" + "/" + params.packagename + "/" + class_name + ".jpf"

            jdart = CommandWithTimeout(cmd=jdart_path, args=whole_path)
            jdart.run(timeout=20)
            
    put_class_name_command = Command(args = "python put-class-name.py  --classname org.apache.commons.collections.FastHashMap")
    put_class_name_command.run()

    unit_tests_directory2 = "tests-2nd-round"

    # Remove previous unit tests

    shutil.rmtree(unit_tests_directory2, ignore_errors = True)
    os.mkdir(unit_tests_directory2)

    # Run Randoop

    unit_tests_name = "Randoop2Test"
    unit_tests_timelimit = 10
    unit_tests_number_upper_limit = 100000000
    randoop_command = Command(args = "java -ea -cp lib/randoop.jar:lib/junit4.jar:build/examples randoop.main.Main gentests --classlist=%s --literals-file=concrete-values.txt --literals-level=ALL --junit-output-dir=%s --junit-classname=%s --timelimit=%d --outputlimitrandom=%d --forbid-null=false --small-tests=true" % (unit_tests_classlist, unit_tests_directory2, unit_tests_name, unit_tests_timelimit, unit_tests_number_upper_limit))
    randoop_command.run()
