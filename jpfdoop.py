#!/usr/bin/env python

# The main JPF-Doop program file. It is used to run JPF-Doop to
# generate unit tests.

import os, sys, shutil
import argparse
import ConfigParser
import time
import sets
import math
from collections import deque


from symbolize_tests import *
from generate_jpf_files import *
from command import *
from report import *

have_to_finish_by = None

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
    def __init__(self, unit_tests_name, unit_tests_directory, classlist_filename, timelimit, paths, randoop_only, dont_terminate = False, use_concrete_values = False):
        self.unit_tests_name = unit_tests_name
        self.unit_tests_directory = unit_tests_directory
        self.classlist_filename = classlist_filename
        self.unit_tests_timelimit = timelimit
        self.paths = paths
        self.dont_terminate = dont_terminate
        self.use_concrete_values = use_concrete_values
        self.randoop_only = randoop_only


    def run(self):

        # Remove previous unit tests
        
        shutil.rmtree(self.unit_tests_directory, ignore_errors = True)
        try:
            os.makedirs(self.unit_tests_directory)
        except:
            pass

        # Invoke Randoop. Check if it should use concrete values

        if not self.use_concrete_values:
            additional_params = ""
        else:
            additional_params = " --literals-file=concrete-values.txt --literals-level=ALL"

        additional_params += " --forbid-null=false --small-tests=true --testsperfile=1 --check-object-contracts=false"

        if self.dont_terminate:
            command = Command(args = "java $JVM_FLAGS -ea -cp " + ":".join([self.paths.lib_randoop, self.paths.lib_junit, self.paths.sut_compilation_dir]) + " randoop.main.Main gentests --classlist=" + self.classlist_filename + " --junit-output-dir=" + self.unit_tests_directory + " --junit-classname=" + self.unit_tests_name + " --timelimit=%s" % self.unit_tests_timelimit + additional_params)
            command.run()
        else:
            command = CommandWithTimeout(args = "java $JVM_FLAGS -ea -cp " + ":".join([self.paths.lib_randoop, self.paths.lib_junit, self.paths.sut_compilation_dir]) + " randoop.main.Main gentests --classlist=" + self.classlist_filename + " --junit-output-dir=" + self.unit_tests_directory + " --junit-classname=" + self.unit_tests_name + " --timelimit=%s" % self.unit_tests_timelimit + additional_params)
            command.run(timeout = int(int(self.unit_tests_timelimit) * 1.1 + 10))


class JPFDoop:
    def __init__(self):
        pass
        self.paths = Paths()
        self.clock = {}
        self.concrete_values_temporary_file = 'concrete-values-jdart.txt'

        self.concrete_values_all_runs = sets.Set()
        self.concrete_values_all_runs_stats = []

        self.concrete_values_iterations_stats = []

        self.compilation_threads = deque()

        self.randoop_only = False
        self.baseline = False


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


    def run_randoop(self, unit_tests, classlist, timelimit, dont_terminate = False, use_concrete_values = False):
        """Invokes Randoop"""

        randoop_run = RandoopRun(unit_tests.name, unit_tests.directory, classlist.filename, str(timelimit), self.paths, self.randoop_only, dont_terminate, use_concrete_values)
        randoop_run.run()


    def check_and_split_up_suite(self, unit_tests, n_calls = 500, template_filename = 'suite_header.template'):
        """Splits up the main unit test suite class into several classes with up to n_calls unit test calls"""

        import math
        from string import Template

        calls_in_total = 0
        suite_path = os.path.join(unit_tests.directory, unit_tests.name + ".java")

        try:
            with open(suite_path, 'r') as f:
                for line in f:
                    if line.lstrip().startswith('result.addTest'):
                        calls_in_total += 1
        except:
            return []

        # Maybe no splitting needs to be done if there are not too
        # many unit tests
        # if calls_in_total < n_calls:
        #     return [unit_tests]

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
                    f.write("    try {\n      result.addTest(new TestSuite(" + unit_tests.name + str(j) + ".class));\n    } catch (Exception e) {\n    }\n")
                
                f.write("    return result;\n  }\n\n}\n")

            ret_list.append(UnitTests(class_name, unit_tests.directory, unit_tests.randooped_package_name))

        return ret_list


    def compile_tests(self, unit_tests):
        """Compiles unit tests generated by Randoop"""

        try:
            os.makedirs(self.paths.tests_compilation_dir)
        except:
            pass

        for unit_tests_suite in unit_tests:
            compile_tests_command = Command(args = "javac -g -d " + self.paths.tests_compilation_dir + " -classpath " + ":".join([self.paths.sut_compilation_dir, self.paths.lib_junit]) + " " + unit_tests_suite.directory + "/*java")
            compile_tests_command.run()

        # if self.randoop_only:
        #     for unit_tests_suite in unit_tests:
        #         compile_tests_command = Command(args = "javac -g -d " + self.paths.tests_compilation_dir + " -classpath " + ":".join([self.paths.sut_compilation_dir, self.paths.lib_junit]) + " " + unit_tests_suite.directory + "/*java")
        #         compile_tests_command.run()
        # else:
        #     for unit_tests_suite in unit_tests:
        #         compile_tests_command = CommandWithTimeout(args = "javac -g -d " + self.paths.tests_compilation_dir + " -classpath " + ":".join([self.paths.sut_compilation_dir, self.paths.lib_junit]) + " " + unit_tests_suite.directory + "/*java")
        #         self.compilation_threads.append([compile_tests_command, unit_tests_suite.name])
        #         compile_tests_command.run_without_joining()

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


    def run_jdart(self, unit_tests, root_dir, classlist, path, timelimit, concrete_values_file_name = 'concrete-values.txt', template_filename = 'randoop-format.template'):
        """Calls JDart on the symbolized unit tests and collects concrete values used in the concolic execution"""

        from string import Template

        # Write down the time when the method started executing and
        # add timelimit to it. That's the time when the method has to
        # terminate
        finish_time = time.time() + timelimit

        concrete_values_iteration = sets.Set()
        concrete_values_iteration_stats = []

        global_before_size = len(self.concrete_values_all_runs)

        with open(os.path.join(unit_tests.randooped_package_name, "classes-to-analyze")) as f:
            for line_nl in f:
                # Write down the current time
                current_time = time.time()
                # Exit if we already reached the timelimit
                if current_time >= finish_time:
                    break

                class_name = line_nl[:-1]

                whole_path = os.path.join(unit_tests.randooped_package_name, class_name + ".jpf")

                # Remove any previously written values
                try:
                    os.remove(self.concrete_values_temporary_file)
                except:
                    pass

                jdart = CommandWithTimeout(args=os.path.join(self.jpf_core_path, "bin/jpf") + " " + whole_path)
                timeout = max(min(10, math.ceil(finish_time - time.time())), 1)
                jdart.run(timeout)

                collected_values = sets.Set()
                try:
                    with open(self.concrete_values_temporary_file, 'r') as f:
                        for line in f:
                            if ":" in line:
                              collected_values.add(line[:-1])
                except:
                    pass

                print "Collected values: " + str(collected_values)
                print "Global set before adding these values: " + str(self.concrete_values_all_runs)

                # Measure a contribution of the just read values to
                # the global set concrete_values_all_runs
                before_size = len(self.concrete_values_all_runs)
                self.concrete_values_all_runs.update(collected_values)
                after_size  = len(self.concrete_values_all_runs)

                print "Global set after adding these values:  " + str(self.concrete_values_all_runs)

                # Insert size of the collected_values set and its
                # contribution to the global set
                # concrete_values_all_runs
                self.concrete_values_all_runs_stats.append([len(collected_values), after_size - before_size, unit_tests.name])

                # Measure a contribution of the just read values to
                # the local set concrete_values_iteration
                before_size = len(concrete_values_iteration)
                concrete_values_iteration.update(collected_values)
                after_size  = len(concrete_values_iteration)

                # Insert size of the collected_values set and its
                # contribution to the global set concrete_values
                concrete_values_iteration_stats.append([len(collected_values), after_size - before_size])

        # Collect information on contribution of this iteration to
        # overall concrete values
        self.concrete_values_all_runs.update(concrete_values_iteration)
        
        # If there is a boolean value, make sure both boolean values are in
        if "boolean:true" in self.concrete_values_all_runs or "boolean:false" in self.concrete_values_all_runs:
            self.concrete_values_all_runs.add("boolean:true")
            self.concrete_values_all_runs.add("boolean:false")

        global_after_size = len(self.concrete_values_all_runs)
        self.concrete_values_iterations_stats.append([len(concrete_values_iteration), global_after_size - global_before_size, unit_tests.name])

        # Read a template for the Randoop format from the file
        randoop_template_str = ''
        with open(template_filename, 'r') as f:
            randoop_template_str = f.read()

        randoop_template = Template(randoop_template_str)

        # Write unique concrete values back to the concrete values file
        with open(concrete_values_file_name, 'w') as f:
            f.write(randoop_template.substitute(classname = classlist.get_all_java_source_files(root_dir, path)[0], values = "\n".join(self.concrete_values_all_runs)))


    def run_code_coverage(self, unit_tests_list, package_path):
        """Runs JaCoCo on all unit tests from the list and generates a code coverage report"""

        # Run tests for all unit test sets but the last one
        for uts in unit_tests_list[:-1]:
            code_coverage_command = Command(args = "ant -f jacoco.xml -Darg0=%s -Darg1=%s test" % (uts.name, package_path))
            code_coverage_command.run()

        # Run tests for the last unit test set and generate a report
        report_command = Command(args = "ant -f jacoco.xml -Darg0=%s -Darg1=%s report" % (unit_tests_list[-1].name, package_path))
        report_command.run()


    def start_clock(self, clock_label):

        assert not clock_label in self.clock, "A clock with label %s was already started!" % clock_label
        # if clock_label in self.clock:
        #     raise Exception()

        start_time = time.time()
        self.clock[clock_label] = [start_time, None]


    def stop_clock(self, clock_label):

        assert clock_label in self.clock, "No started clock with a label %s!" % clock_label

        # if not clock_label in self.clock:
        #     raise Exception("Clock %s wasn't even started!" % clock_label)

        [start_time, previous_end_time] = self.clock[clock_label]

        assert previous_end_time == None, "Clock %s was already stopped!" % clock_label
        
        end_time = time.time()
        self.clock[clock_label] = [start_time, end_time]


    def get_clock_starting_time(self, clock_label):
        
        assert clock_label in self.clock, "No clock with a label %s!" % clock_label
        
        return self.clock[clock_label][0]


    def total_clock_time(self, clock_label):

        assert clock_label in self.clock, "No clock with a label %s!" % clock_label

        [start_time, end_time] = self.clock[clock_label]
        assert not end_time == None, "Clock %s wasn't stopped during the program execution!" % clock_label

        return end_time - start_time


    def print_clock(self, clock_label):
        
        print "%s: %.2lf" % (clock_label, self.total_clock_time(clock_label))

    def print_stats(self):
        """Prints statistics on execution times for various components of JPF-Doop"""

        print ""

        for c in jpfdoop.clock.iterkeys():
            jpfdoop.print_clock(c)

    def determine_timelimit(self, identifier, execution_number = None):
        """Determine how much time can and should be spent for a particular task given a global time limit and time left"""

        # Write down the current time
        current_time = time.time()

        if identifier == "Randoop":
            randoop_scale_factor = 1.1 # A scale-down factor because Randoop always takes longer
            minimum_time = 45 # seconds

            if execution_number == 1:
                default_time = 20 # seconds

                if self.randoop_only:
                    return int(math.ceil(have_to_finish_by - current_time))

            # If we are in the baseline mode, let Randoop run for the
            # remaining time
            elif execution_number == 2 and self.baseline:
                return int(math.ceil(have_to_finish_by - current_time))

            elif execution_number == 4:
                # This is a Randoop execution by which most of the
                # concrete values would be generated on average, so we
                # will give much more time to Randoop than usual
                default_time = 180 # seconds
            else:
                default_time = 45 # seconds

            if have_to_finish_by - current_time < minimum_time or have_to_finish_by - current_time < default_time:
                # Let's say it doesn't make sense to run Randoop for
                # less than 3 seconds
                return max(int((have_to_finish_by - current_time) / randoop_scale_factor), 3)

            elif have_to_finish_by - current_time < 2 * minimum_time and not execution_number == 1:
                return int((have_to_finish_by - current_time) / randoop_scale_factor)
            else:
                return int(default_time / randoop_scale_factor)
        if identifier == "JDart":
            short_running_time = 20 # seconds
            normal_running_time = 45 # seconds
            minimum_time = normal_running_time + 10 # seconds
            
            if have_to_finish_by - current_time < minimum_time:
                if have_to_finish_by - current_time < short_running_time:
                    return 0
                return short_running_time
            else:
                return normal_running_time

        return 42

        
if __name__ == "__main__":

    jpfdoop = JPFDoop()
    jpfdoop.start_clock("program")

    parser = argparse.ArgumentParser(description='Generates unit tests with Randoop only or with JPF-Doop.')
    parser.add_argument('--package-name', required=True, help='A Java package with classes to analyze.')
    parser.add_argument('--root', required=True, help='source files root directory')
    parser.add_argument('--classlist', default='classlist.txt', help='Name of a file to write a file list to')
    parser.add_argument('--timelimit', default=120, type=int, help='Timelimit in seconds in which JPF-Doop should finish its execution')
    parser.add_argument('--configuration-file', default='jpfdoop.ini', help='A configuration file with settings for JPF-Doop')
    parser.add_argument('--randoop-only', default=False, action="store_true", help='The tool should run Randoop only')
    parser.add_argument('--baseline', default=False, action="store_true", help='The tool should run in the baseline mode')
    parser.add_argument('--generate-report', default=False, action="store_true", help='The tool should generate a code coverage report once it finishes its execution')
    params = parser.parse_args()

    have_to_finish_by = jpfdoop.get_clock_starting_time("program") + params.timelimit

    jpfdoop.read_config_file(params.configuration_file)
    jpfdoop.paths.package_path = os.path.normpath(params.package_name.replace(".", "/"))
    jpfdoop.randoop_only = params.randoop_only
    jpfdoop.baseline = params.baseline

    # Create a list of classes to be tested
    classlist = ClassList(params.classlist)
    classlist.write_list_of_classes(params.root, jpfdoop.paths.package_path)

    unit_tests = UnitTests(name = "Randoop1Test", directory = "tests-round-1", randooped_package_name = "randooped1")

    # Determine how much time should be given to the first run of
    # Randoop
    timelimit = jpfdoop.determine_timelimit("Randoop", 1)

    # Invoke Randoop to generate unit tests
    jpfdoop.start_clock("Randoop #1")
    jpfdoop.run_randoop(unit_tests, classlist, timelimit, dont_terminate = True)
    jpfdoop.stop_clock("Randoop #1")

    # Split up the main unit test suite class if needed. With 1 unit
    # test per class, there are too many calls from the main class to
    # fit into the 64K bytecode size limit
    #
    new_unit_tests = jpfdoop.check_and_split_up_suite(unit_tests)

    # Compile tests generated by Randoop
    # if params.generate_report and not params.randoop_only:
    #     jpfdoop.compile_tests(new_unit_tests)

    # Start creating a list of unit tests
    # unit_tests_list = [ut.name for ut in new_unit_tests]
    unit_tests_list = new_unit_tests[:]

    # A classpath variable needed for code coverage reports
    classpath = ":".join([jpfdoop.paths.lib_junit, jpfdoop.paths.sut_compilation_dir, jpfdoop.paths.tests_compilation_dir])

    i = 1
    # Instead of using True for an infinite loop, in this way I am
    # avoiding of Randoop going in the loop for a brief minimum 3
    # seconds
    while not params.randoop_only:

        i += 1

        if not params.randoop_only:
            # Symbolize unit tests
            jpfdoop.start_clock("Symbolization of unit tests #%d" % (i-1))
            # TODO: Vary number of unit tests to select based on
            # previous performance
            jpfdoop.symbolize_unit_tests(unit_tests, count = 30)
            jpfdoop.stop_clock("Symbolization of unit tests #%d" % (i-1))

            # Generate JPF configuration files
            jpfdoop.generate_jpf_conf(unit_tests, params.root)

            # Compile symbolized unit tests
            jpfdoop.start_clock("Compilation of symbolic unit tests #%d" % (i-1))
            jpfdoop.compile_symbolic_tests(params.root, unit_tests)
            jpfdoop.stop_clock("Compilation of symbolic unit tests #%d" % (i-1))

            # Run JDart on symbolized unit tests
            timelimit = jpfdoop.determine_timelimit("JDart")

            jpfdoop.start_clock("Global run of JDart #%d" % (i-1))
            jpfdoop.run_jdart(unit_tests, params.root, classlist, jpfdoop.paths.package_path, timelimit)
            jpfdoop.stop_clock("Global run of JDart #%d" % (i-1))

        unit_tests = UnitTests(name = "Randoop%dTest" % i, directory = "tests-round-%d" % i, randooped_package_name = "randooped%d" % i)

        # Run Randoop
        timelimit = jpfdoop.determine_timelimit("Randoop", i)
        jpfdoop.start_clock("Randoop #%d" % i)
        if params.randoop_only:
            jpfdoop.run_randoop(unit_tests, classlist, timelimit, dont_terminate = True)
        else:
            jpfdoop.run_randoop(unit_tests, classlist, timelimit, dont_terminate = True, use_concrete_values = True)
        jpfdoop.stop_clock("Randoop #%d" % i)

        # Split up the main unit test suite class if needed. With 1 unit
        # test per class, there are too many calls from the main class to
        # fit into the 64K bytecode size limit
        #
        new_unit_tests = jpfdoop.check_and_split_up_suite(unit_tests)

        # Compile tests generated by Randoop
        # if params.generate_report:
        #     jpfdoop.compile_tests(new_unit_tests)

        # unit_tests_list.extend([ut.name for ut in new_unit_tests])
        unit_tests_list.extend(new_unit_tests)

        # Check if we're out of time and break out of the loop if so
        if time.time() >= have_to_finish_by:
            break

        # If we are in the baseline mode, no further iterations should
        # be performed
        if jpfdoop.baseline:
            break

    jpfdoop.stop_clock("program")

    # if params.generate_report and not params.randoop_only:
    if params.generate_report:
        # jpfdoop.start_clock("Remaining unit test compilation")
        jpfdoop.start_clock("Compilation of unit tests")
        # while jpfdoop.compilation_threads:
        #     [cmd, name] = jpfdoop.compilation_threads.popleft()
        #     cmd.join_thread()
        # jpfdoop.stop_clock("Remaining unit test compilation")

        jpfdoop.compile_tests(unit_tests_list)
        jpfdoop.stop_clock("Compilation of unit tests")

    # if params.generate_report and params.randoop_only:
    #     jpfdoop.compile_tests(new_unit_tests)
        

    if params.generate_report:
        # Run all tests and let JaCoCo measure coverage
        jpfdoop.start_clock("Code coverage report")
        # for unit_tests_suite in unit_tests_list[:-1]:
        #     report = Report(jpfdoop.paths.lib_jacoco, [unit_tests_suite], os.path.normpath(jpfdoop.paths.package_path), classpath, params.root, jpfdoop.paths.sut_compilation_dir)
        #     report.run_testing()

        # # Run code coverage for the last one and generate a report
        # report = Report(jpfdoop.paths.lib_jacoco, [unit_tests_list[-1]], os.path.normpath(jpfdoop.paths.package_path), classpath, params.root, jpfdoop.paths.sut_compilation_dir)
        # report.run_code_coverage()

        for unit_tests_suite in unit_tests_list[:-1]:
            report = Report(jpfdoop.paths.lib_jacoco, [unit_tests_suite.name], os.path.normpath(jpfdoop.paths.package_path), classpath, params.root, jpfdoop.paths.sut_compilation_dir)
            report.run_testing()

        # Run code coverage for the last one and generate a report
        report = Report(jpfdoop.paths.lib_jacoco, [unit_tests_list[-1].name], os.path.normpath(jpfdoop.paths.package_path), classpath, params.root, jpfdoop.paths.sut_compilation_dir)
        report.run_code_coverage()

        jpfdoop.stop_clock("Code coverage report")

    # Print execution time statistics
    jpfdoop.print_stats()

    # Print statistics on concrete values
    if not params.randoop_only:
        # Print statistics about concrete values
        print ""
        print "Concrete values stats\n"

        print "Contribution of each JDart execution"
        for s in jpfdoop.concrete_values_all_runs_stats:
            print "Set size: %4d, contribution: %4d, unit tests name: %s" % (s[0], s[1], s[2])

        print "\nContribution of each iteration"
        for s in jpfdoop.concrete_values_iterations_stats:
            print "Set size: %4d, contribution: %4d, unit tests name: %s" % (s[0], s[1], s[2])
