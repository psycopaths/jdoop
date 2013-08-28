#!/usr/bin/env python

# The main JPF-Doop program file. It is used to run JPF-Doop to
# generate unit tests.

import os, sys, shutil
import argparse
import ConfigParser

from symbolize_tests import *
from generate_jpf_files import *
from command import *
from report import *

class ClassList:
    def __init__(self, filename):
        self.filename = filename
        self.list_of_classes = None

    def get_all_java_source_files(self, base, rootdir):
        """Finds all java files in a given directory tree and returns a list of such files"""

        if not self.list_of_classes == None:
            return self.list_of_classes

        ret = []
        
        for dirpath, dirnames, filenames in os.walk(os.path.join(base, rootdir)):
            for name in filenames:
                if name.endswith('.java'):
                    # No need to worry about abstract classes nor
                    # interfaces because Randoop will take care of
                    # that

                    # Check if this is a meta-package
                    if not name.startswith('package-info'):
                        ret.append(dirpath[len(os.path.normpath(base)) + 1:].replace("/", ".") + "." + name[:-len(".java")])

        self.list_of_classes = ret

        return ret

    def write_list_of_classes(self, root, rel_path):
        """Writes to a file a list of classes to be tested by JPFDoop"""

        with open(self.filename, 'w') as f:
            f.write("\n".join(self.get_all_java_source_files(root, rel_path)) + "\n")
        

class UnitTests:
    def __init__(self, name = "Randoop1Test", directory = "tests-round-1", randooped_package_name = "randooped"):
        self.directory = directory
        self.name = name
        self.randooped_package_name = randooped_package_name

class Paths:
    def __init__(self):
        pass

class RandoopRun:
    def __init__(self, unit_tests_name, unit_tests_directory, classlist_filename, timelimit, paths, use_concrete_values = False):
        self.unit_tests_name = unit_tests_name
        self.unit_tests_directory = unit_tests_directory
        self.classlist_filename = classlist_filename
        self.unit_tests_timelimit = timelimit
        self.paths = paths
        self.use_concrete_values = use_concrete_values

    def run(self):

        # Remove previous unit tests
        
        shutil.rmtree(self.unit_tests_directory, ignore_errors = True)
        try:
            os.makedirs(self.unit_tests_directory)
        except:
            pass

        # Invoke Randoop. Check if it should use concrete values

        if not self.use_concrete_values:
            concrete_values_str = ""
        else:
            concrete_values_str = " --literals-file=concrete-values.txt --literals-level=ALL"

        command = Command(args = "java $JVM_FLAGS -ea -cp " + ":".join([self.paths.lib_randoop, self.paths.lib_junit, self.paths.sut_compilation_dir]) + " randoop.main.Main gentests --classlist=" + self.classlist_filename + " --junit-output-dir=" + self.unit_tests_directory + " --junit-classname=" + self.unit_tests_name + " --timelimit=%s" % self.unit_tests_timelimit +  " --forbid-null=false --small-tests=true --testsperfile=1" + concrete_values_str)

        command.run()

class JPFDoop:
    def __init__(self):
        pass
        self.paths = Paths()

    def read_config_file(self, config_file_name):
        config = ConfigParser.RawConfigParser()
        config.read(config_file_name)

        sections = ['jpfdoop', 'sut', 'tests', 'lib']
        for section in sections:
            if not config.has_section(section):
                sys.exit("The configuration file does not have the [" + section + "] section!")

        try:
            self.jpf_core_path = str(config.get('jpfdoop', 'jpf-core'))
            self.jpf_jdart_path = str(config.get('jpfdoop', 'jpf-jdart'))
            self.paths.sut_compilation_dir = str(config.get('sut', 'compilation-directory'))
            self.paths.tests_compilation_dir = str(config.get('tests', 'compilation-directory'))
            self.paths.lib_junit = str(config.get('lib', 'junit'))
            self.paths.lib_randoop = str(config.get('lib', 'randoop'))
            self.paths.lib_jacoco = str(config.get('lib', 'jacoco'))
        except Exception, err:
            print str(err) + " in " + config_file_name
            sys.exit(1)

    def run_randoop(self, unit_tests, classlist, params, use_concrete_values = False):
        """Invokes Randoop"""

        randoop_run = RandoopRun(unit_tests.name, unit_tests.directory, classlist.filename, str(params.rtimelimit), self.paths, use_concrete_values)
        randoop_run.run()

    def check_and_split_up_suite(self, unit_tests, n_calls = 4500, template_filename = 'suite_header.template'):
        """Splits up the main unit test suite class into several classes with up to n_calls unit test calls"""

        import math
        from string import Template

        calls_in_total = 0
        suite_path = os.path.join(unit_tests.directory, unit_tests.name + ".java")

        with open(suite_path, 'r') as f:
            for line in f:
                if line.lstrip().startswith('result.addTest'):
                    calls_in_total += 1

        # Maybe no splitting needs to be done if there are not too
        # many unit tests
        if calls_in_total < n_calls:
            return [unit_tests]

        try:
            os.remove(suite_path)
        except:
            sys.exit('Unable to remove ' + suite_path)

        # Read a template for a unit test suite from the file
        suite_template_str = ''
        with open(template_filename, 'r') as f:
            suite_template_str = f.read()

        suite_template = Template(suite_template_str)

        # Split up the main suite file into ceil(calls_in_total / n_calls)
        # files

        ret_list = []

        # We assume that unit test classes that Randoop generated are
        # enumerated from 0 to (calls_in_total - 1)

        for i in range(int(math.ceil(float(calls_in_total) / n_calls))):
            class_name = unit_tests.name + "_e" + str(i)
            with open(os.path.join(unit_tests.directory, class_name + ".java"), 'w') as f:
                # Put a proper class name into the template
                f.write(suite_template.substitute(classname=class_name))

                # Write up to n_calls method calls
                for j in range(n_calls * i, min(n_calls * (i + 1), calls_in_total)):
                    f.write("    result.addTest(new TestSuite(" + unit_tests.name + str(j) + ".class));\n")
                
                f.write("    return result;\n  }\n\n}\n")

            ret_list.append(UnitTests(class_name, unit_tests.directory, unit_tests.randooped_package_name))

        return ret_list

    def compile_tests(self, unit_tests):
        """Compiles unit tests generated by Randoop"""

        try:
            os.makedirs(self.paths.tests_compilation_dir)
        except:
            pass

        compile_tests_command = Command(args = "javac -g -d " + self.paths.tests_compilation_dir + " -classpath " + ":".join([self.paths.sut_compilation_dir, self.paths.lib_junit]) + " " + unit_tests.directory + "/*java")
        compile_tests_command.run()

    def compile_symbolic_tests(self, root_dir, unit_tests):
        """Compiles JDart-modified symbolic unit tests"""

        try:
            os.makedirs(self.paths.tests_compilation_dir)
        except:
            pass

        compile_tests_command = Command(args = "javac -g -d " + self.paths.tests_compilation_dir + " -classpath " + ":".join([os.path.join(self.jpf_jdart_path, "build"), os.path.join(self.jpf_jdart_path, "build/annotations/"), self.paths.sut_compilation_dir, self.paths.tests_compilation_dir, self.paths.lib_junit]) + " " + os.path.join("./", unit_tests.randooped_package_name +  "/*java"))
        compile_tests_command.run()

    def select_unit_test_files(self, unit_tests, count):
        """Makes a random selection of JUnit tests that have to be symbolized for jDART"""

        import re, random

        dir_list = os.listdir(unit_tests.directory)

        prog = re.compile(unit_tests.name + "[0-9]+\.java")
        unit_tests_list = filter(prog.match, dir_list)

        # Now select only <count> of them

        if count > len(unit_tests_list):
            unit_tests_indices = [i for i in range(len(unit_tests_list))]
        else:
            unit_tests_indices = random.sample(range(len(unit_tests_list)), count)

        return unit_tests_indices

    def symbolize_unit_tests(self, unit_tests, count):
        """Replaces concrete method input values with symbolic variables in unit tests"""

        unit_test_indices = self.select_unit_test_files(unit_tests, count)

        # Remove the file with class names
        try:
            os.remove(os.path.join(unit_tests.randooped_package_name, "classes-to-analyze"))
        except OSError, e:
            pass

        for unit_test_index in unit_test_indices:
            # Something is wrong here with this classes-to-analyze. Or
            # maybe not... probably whenever there is a new unit test,
            # it just gets appended to the file. Check that

            symbolic_unit_tests = SymbolicUnitTests(unit_tests.randooped_package_name, "classes-to-analyze", os.path.join(unit_tests.directory, unit_tests.name + str(unit_test_index) +'.java'), ['test' + str(unit_test_index) + 'Class'])
            symbolic_unit_tests.generate_symbolized_unit_tests()

    def generate_jpf_conf(self, unit_tests, root_dir):
        """Generates JPF configuration files (.jpf) for JDart"""
        
        jpf_configuration_files = CoordinateConfFileGeneration(unit_tests.randooped_package_name, 'classes-to-analyze', ",".join([self.paths.tests_compilation_dir, self.paths.lib_junit]))
        jpf_configuration_files.run()

    def run_jdart(self, unit_tests, root_dir):
        """Calls JDart on the symbolized unit tests"""

        with open(os.path.join(unit_tests.randooped_package_name, "classes-to-analyze")) as f:
            for line_nl in f:
                class_name = line_nl[:-1]

                whole_path = os.path.join(unit_tests.randooped_package_name, class_name + ".jpf")

                jdart = CommandWithTimeout(cmd=os.path.join(self.jpf_core_path, "bin/jpf"), args=os.path.join(self.jpf_core_path, "bin/jpf") + " " + whole_path)
                jdart.run(timeout=20)

    def consolidate_concrete_values(self, classlist, root_dir, path, input_file_name = 'concrete-values-tmp.txt', output_file_name = 'concrete-values.txt', template_filename = 'randoop-format.template'):
        """Reorganizes the output file so that all concrete values are unique"""

        import sets
        from string import Template

        # Collect all values and put them into a set so that there is no value repead twice
        unique_values = sets.Set()

        for file_name in [input_file_name, output_file_name]:
            try:
                with open(file_name, 'r') as f:
                    for line in f:
                        if ":" in line:
                            unique_values.add(line[:-1])
            except:
                pass

        # If there is a boolean value, make sure both boolean values are in
        if "boolean:true" in unique_values or "boolean:false" in unique_values:
            unique_values.add("boolean:true")
            unique_values.add("boolean:false")

        # Read a template for the Randoop format from the file
        randoop_template_str = ''
        with open(template_filename, 'r') as f:
            randoop_template_str = f.read()

        randoop_template = Template(randoop_template_str)

        # Write those unique values back to the output file
        with open(output_file_name, 'w') as f:
            f.write(randoop_template.substitute(classname = classlist.get_all_java_source_files(root_dir, path)[0], values = "\n".join(unique_values)))

    def run_code_coverage(self, unit_tests_list, package_path):
        """Runs JaCoCo on all unit tests from the list and generates a code coverage report"""

        # Run tests for all unit test sets but the last one
        for uts in unit_tests_list[:-1]:
            code_coverage_command = Command(args = "ant -f jacoco.xml -Darg0=%s -Darg1=%s test" % (uts.name, package_path))
            code_coverage_command.run()

        # Run tests for the last unit test set and generate a report
        report_command = Command(args = "ant -f jacoco.xml -Darg0=%s -Darg1=%s report" % (unit_tests_list[-1].name, package_path))
        report_command.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generates unit tests with Randoop only or with JPF-Doop.')
    parser.add_argument('--packagename', required=True, help='A Java package with classes to analyze.')
    parser.add_argument('--root', default='src/examples/', help='source files root directory')
    parser.add_argument('--classlist', default='classlist.txt', help='Name of a file to write a file list to')
    parser.add_argument('--rtimelimit', default=30, help='Timelimit for a single run of Randoop')
    parser.add_argument('--runittests', default=20, type=int, help='Upper limit of number of unit tests Randoop will generate in a single run')
    parser.add_argument('--conffile', default='jpfdoop.ini', help="A configuration file with settings for JPF-Doop")
    params = parser.parse_args()

    jpfdoop = JPFDoop()
    jpfdoop.read_config_file(params.conffile)
    jpfdoop.paths.package_path = os.path.normpath(params.packagename.replace(".", "/"))

    # Create a list of classes to be tested
    classlist = ClassList(params.classlist)
    classlist.write_list_of_classes(params.root, jpfdoop.paths.package_path)

    unit_tests = UnitTests(name = "Randoop1Test", directory = "tests-round-1", randooped_package_name = "randooped1")

    # Invoke Randoop to generate unit tests
    jpfdoop.run_randoop(unit_tests, classlist, params)

    # Split up the main unit test suite class if needed. With 1 unit
    # test per class, there are too many calls from the main class to
    # fit into the 64K bytecode size limit
    #
    new_unit_tests = jpfdoop.check_and_split_up_suite(unit_tests)

    # Compile tests generated by Randoop
    for unit_tests_suite in new_unit_tests:
        jpfdoop.compile_tests(unit_tests_suite)

    # Start creating a list of unit tests
    unit_tests_list = [ut.name for ut in new_unit_tests]

    for i in range(2,5):

        # Symbolize unit tests
        jpfdoop.symbolize_unit_tests(unit_tests, params.runittests)

        # Generate JPF configuration files
        jpfdoop.generate_jpf_conf(unit_tests, params.root)

        # Compile symbolized unit tests
        jpfdoop.compile_symbolic_tests(params.root, unit_tests)

        # Run JDart on symbolized unit tests
        jpfdoop.run_jdart(unit_tests, params.root)

        # Replace a placeholder with a valid class name in the file with
        # concrete values
        jpfdoop.consolidate_concrete_values(classlist, params.root, jpfdoop.paths.package_path)

        unit_tests = UnitTests(name = "Randoop%dTest" % i, directory = "tests-round-%d" % i, randooped_package_name = "randooped%d" % i)

        # Run Randoop
        jpfdoop.run_randoop(unit_tests, classlist, params, use_concrete_values = True)

        # Split up the main unit test suite class if needed. With 1 unit
        # test per class, there are too many calls from the main class to
        # fit into the 64K bytecode size limit
        #
        new_unit_tests = jpfdoop.check_and_split_up_suite(unit_tests)

        # Compile tests generated by Randoop
        for unit_tests_suite in new_unit_tests:
            jpfdoop.compile_tests(unit_tests_suite)

        unit_tests_list.extend([ut.name for ut in new_unit_tests])

    # Generate a code coverage report
    classpath = ":".join([jpfdoop.paths.lib_junit, jpfdoop.paths.sut_compilation_dir, jpfdoop.paths.tests_compilation_dir])
    report = Report(jpfdoop.paths.lib_jacoco, unit_tests_list, os.path.normpath(jpfdoop.paths.package_path), classpath, params.root, jpfdoop.paths.sut_compilation_dir)
    report.run_code_coverage()
