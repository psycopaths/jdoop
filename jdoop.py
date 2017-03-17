#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2017 Marko Dimjašević
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

# The main JDoop program file. It is used to run JDoop to generate
# unit tests.

import os, sys, shutil
import argparse
import ConfigParser
import time
import sets
import math
from collections import deque
import re


from symbolize_tests import *
from generate_jpf_files import *
from command import *
from report import *

have_to_finish_by = None

class ClassList:
    def __init__(self, filename):
        self.filename = filename
        self.list_of_classes = None


    def get_all_java_source_files(self, base):
        """Finds all java files in a given directory tree and returns a list of such files"""

        if not self.list_of_classes == None:
            return self.list_of_classes

        ret = []
        
        for dirpath, dirnames, filenames in os.walk(base):
            for name in filenames:
                if name.endswith('.java'):
                    # No need to worry about abstract classes nor
                    # interfaces because Randoop will take care of
                    # that

                    # Check if this is a meta-package
                    if not name.startswith('package-info'):
                        classname = name[:-len(".java")]
                        package_name = dirpath[len(os.path.normpath(base)) + 1:].replace("/", ".")
                        if package_name == "":
                            fqdn = classname
                        else:
                            fqdn = package_name + "." + classname
                        ret.append(fqdn)

        self.list_of_classes = ret

        return ret


    def write_list_of_classes(self, root):
        """Writes to a file a list of classes to be tested by JDoop"""

        with open(self.filename, 'w') as f:
            f.write("\n".join(self.get_all_java_source_files(root)) + "\n")
        

class UnitTests:
    def __init__(self, name = "Randoop1Test", directory = "tests-round-1", randooped_package_name = "randooped", index_lo = 0, index_hi = 500):
        self.directory = directory
        self.name = name
        self.randooped_package_name = randooped_package_name
        self.index_lo = index_lo
        self.index_hi = index_hi

class Paths:
    def __init__(self):
        pass


class RandoopRun:
    def __init__(self, unit_tests_name, unit_tests_directory, classlist_filename, timelimit, paths, randoop_only, dont_terminate = False, use_concrete_values = False, seed = 0, dependencies_classpath = None):
        self.unit_tests_name = unit_tests_name
        self.unit_tests_directory = unit_tests_directory
        self.classlist_filename = classlist_filename
        self.unit_tests_timelimit = timelimit
        self.paths = paths
        self.dont_terminate = dont_terminate
        self.use_concrete_values = use_concrete_values
        self.randoop_only = randoop_only
        self.seed = seed
        self.dependencies_classpath = dependencies_classpath


    def run(self):

        # Remove previous unit tests
        
        shutil.rmtree(self.unit_tests_directory, ignore_errors = True)
        try:
            os.makedirs(self.unit_tests_directory)
        except:
            pass

        # Invoke Randoop. Check if it should use concrete values

        additional_params = ""
        if self.use_concrete_values and os.path.exists("concrete-values.txt") == True:
            additional_params = " --literals-file=concrete-values.txt --literals-level=ALL"

        additional_params += " --forbid-null=false --small-tests=true --testsperfile=1 --ignore-flaky-tests"
        additional_params += " --randomseed=%i" % self.seed

        cp = ""
        if self.dependencies_classpath != None:
            cp = self.dependencies_classpath + ":"
        cp += ":".join([self.paths.sut_compilation_dir, self.paths.lib_junit, self.paths.lib_hamcrest, self.paths.lib_randoop])

        if self.dont_terminate:
            command_str = "java $JVM_FLAGS -ea -cp " + cp + " randoop.main.Main gentests --classlist=" + self.classlist_filename + " --junit-output-dir=" + self.unit_tests_directory + " --regression-test-basename=" + self.unit_tests_name + " --timelimit=%s" % self.unit_tests_timelimit + additional_params
            print "Starting Randoop: " + command_str
            command = Command(args = command_str)
            command.run()
        else:
            command_str = "java $JVM_FLAGS -ea -cp " + cp + " randoop.main.Main gentests --classlist=" + self.classlist_filename + " --junit-output-dir=" + self.unit_tests_directory + " --regression-test-basename=" + self.unit_tests_name + " --timelimit=%s" % self.unit_tests_timelimit + additional_params
            print "Starting Randoop: " + command_str
            command = CommandWithTimeout(args = command_str)
            command.run(timeout = int(int(self.unit_tests_timelimit) * 1.1 + 10))


class JDoop:
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

        self.dependencies_classpath = None

        self.darted_count = 0


    def read_config_file(self, params):
        config_file_name = params.configuration_file
        if config_file_name.find(os.sep) == -1:
            scriptPath = os.path.realpath(__file__)
            config_file_name = os.path.join(os.path.dirname(scriptPath), config_file_name)
        config = ConfigParser.RawConfigParser()
        config.read(config_file_name)

        if params.jpf_core_path == None:
            try:
                self.jpf_core_path = str(config.get('jdoop', 'jpf-core'))
            except Exception, err:
                sys.exit("A path to the jpf-core module wasn't provided!")
        else:
            self.jpf_core_path = params.jpf_core_path

        if params.jdart_path == None:
            try:
                self.jdart_path = str(config.get('jdoop', 'jdart'))
            except Exception, err:
                sys.exit("A path to the jdart module wasn't provided!")
        else:
            self.jdart_path = params.jdart_path

        if params.sut_compilation == None:
            try:
                self.paths.sut_compilation_dir = str(config.get('sut', 'compilation-directory'))
            except Exception, err:
                sys.exit("A directory where class files of the package being tested can be found wasn't provided!")
        else:
            self.paths.sut_compilation_dir = params.sut_compilation

        if params.test_compilation == None:
            try:
                self.paths.tests_compilation_dir = str(config.get('tests', 'compilation-directory'))
            except Exception, err:
                sys.exit("A directory where generated JUnit tests should be compiled to wasn't provided!")
        else:
            self.paths.tests_compilation_dir = params.test_compilation
        self.paths.tests_compilation_dir = os.path.abspath(self.paths.tests_compilation_dir)

        if params.junit_path == None:
            try:
                self.paths.lib_junit = str(config.get('lib', 'junit'))
            except Exception, err:
                sys.exit("Path to the JUnit jar archive wasn't provided!")
        else:
            self.paths.lib_junit = params.junit_path

        if params.hamcrest_path == None:
            try:
                self.paths.lib_junit = str(config.get('lib', 'hamcrest'))
            except Exception, err:
                sys.exit("Path to the Hamcrest jar archive wasn't provided!")
        else:
            self.paths.lib_hamcrest = params.hamcrest_path

        if params.randoop_path == None:
            try:
                self.paths.lib_randoop = str(config.get('lib', 'randoop'))
            except Exception, err:
                sys.exit("Path to the Randoop jar archive wasn't provided!")
        else:
            self.paths.lib_randoop = params.randoop_path

        if params.jacoco_path == None:
            try:
                self.paths.lib_jacoco = str(config.get('lib', 'jacoco'))
            except Exception, err:
                sys.exit("Path to the JaCoCo jar archive wasn't provided!")
        else:
            self.paths.lib_jacoco = params.jacoco_path


    def run_randoop(self, unit_tests, classlist, timelimit, dont_terminate = False, use_concrete_values = False, seed = 0):
        """Invokes Randoop"""

        if self.randoop_only:
            seed = 0
        randoop_run = RandoopRun(unit_tests.name, unit_tests.directory, classlist.filename, str(timelimit), self.paths, self.randoop_only, dont_terminate, use_concrete_values, seed, self.dependencies_classpath)
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
                    if re.search(".*[0-9]+\.class", line.lstrip()):
                        calls_in_total += 1
        except:
            return []

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
            classes = ",\n".join(
                ["%s%i.class" % (unit_tests.name, j) for j in range(
                    n_calls * i, min(n_calls * (i + 1), calls_in_total))])
            with open(os.path.join(unit_tests.directory, class_name + ".java"), 'w') as f:
                # Put a proper class name into the template
                f.write(suite_template.substitute(classes=classes, classname=class_name))

            ret_list.append(UnitTests(
                class_name,
                unit_tests.directory,
                unit_tests.randooped_package_name,
                n_calls * i,
                min(n_calls * (i + 1), calls_in_total)))

        return ret_list


    def compile_tests(self, unit_tests):
        """Compiles unit tests generated by Randoop"""

        try:
            os.makedirs(self.paths.tests_compilation_dir)
        except:
            pass

        cp = ""
        if self.dependencies_classpath != None:
            cp += self.dependencies_classpath + ":"
        cp += ":".join([
            self.paths.sut_compilation_dir,
            self.paths.lib_junit,
            self.paths.lib_hamcrest,
            self.paths.tests_compilation_dir])

        for unit_tests_suite in unit_tests:
            suite_base_name = unit_tests_suite.name[:unit_tests_suite.name.find("_e")]
            source_unit_file_paths = [
                "%s/%s%i.java" % (unit_tests_suite.directory, suite_base_name,
                                  j) for j in range(unit_tests_suite.index_lo,
                                                    unit_tests_suite.index_hi)]

            compile_tests_command = Command(args = (
                "javac -g -d " + self.paths.tests_compilation_dir +
                " -classpath " + cp + " " + " ".join(source_unit_file_paths) +
                " " + "%s/%s.java" % (unit_tests_suite.directory,
                                      unit_tests_suite.name)))
            compile_tests_command.run()

    def compile_symbolic_tests(self, root_dir, unit_tests):
        """Compiles JDart-modified symbolic unit tests"""

        try:
            os.makedirs(self.paths.tests_compilation_dir)
        except:
            pass
        cp = ""
        if self.dependencies_classpath != None:
            cp = self.dependencies_classpath + ":"
        cp += ":".join([
            self.paths.sut_compilation_dir,
            self.paths.lib_junit,
            self.paths.lib_hamcrest,
            os.path.join(self.jdart_path, "build"),
            os.path.join(self.jdart_path, "build/annotations/"),
            self.paths.tests_compilation_dir])

        compile_tests_command = Command(args = "javac -g -d " + self.paths.tests_compilation_dir + " -classpath " + cp + " " + os.path.join("./", unit_tests.randooped_package_name +  "/*java"))
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

        classpath = ""
        if self.dependencies_classpath != None:
            classpath = self.dependencies_classpath + ","
        classpath += ",".join([
            self.paths.tests_compilation_dir,
            self.paths.lib_junit,
            self.paths.lib_hamcrest,
            self.paths.sut_compilation_dir])

        classes_to_analyze = []

        for unit_test_index in unit_test_indices:
            # Something is wrong here with this classes-to-analyze. Or
            # maybe not... probably whenever there is a new unit test,
            # it just gets appended to the file. Check that

            class_name = 'test' + str(unit_test_index) + 'Class'

            symbolic_unit_tests = SymbolicUnitTests(
                unit_tests.randooped_package_name,
                os.path.join(unit_tests.directory,
                             unit_tests.name + str(unit_test_index) +'.java'),
                [class_name])
            symbolic_unit_tests.generate_symbolized_unit_tests()

            if symbolic_unit_tests.wrote_test_case == False:
                continue

            # Generate a JPF configuration file (.jpf) for this
            # symbolic test case driver
            whole_path = os.path.join(
                unit_tests.randooped_package_name.replace(".", os.sep),
                class_name + ".java")
            f = GenerateConfFile(
                unit_tests.randooped_package_name,
                classpath,
                "darted%i" % self.darted_count,
                "darted",
                symbolic_unit_tests.sym_var_list)
            f.generate_jpf_conf_file(
                whole_path,
                whole_path.replace(".java", ".jpf"))

            classes_to_analyze.append(class_name)
            self.darted_count += 1

        with open(os.path.join(
                unit_tests.randooped_package_name,
                "classes-to-analyze"), 'w') as f:
            f.write("\n".join(classes_to_analyze))


    def run_jdart(self, unit_tests, root_dir, classlist, timelimit, concrete_values_file_name = 'concrete-values.txt', template_filename = 'randoop-format.template'):
        """Calls JDart on the symbolized unit tests and collects concrete values used in the concolic execution"""

        from string import Template

        # Write down the time when the method started executing and
        # add timelimit to it. That's the time when the method has to
        # terminate
        finish_time = time.time() + timelimit

        concrete_values_iteration = sets.Set()
        concrete_values_iteration_stats = []

        global_before_size = len(self.concrete_values_all_runs)

        class_file = os.path.join(unit_tests.randooped_package_name, "classes-to-analyze")
        if os.path.exists(class_file) != True:
            return

        with open(class_file) as f:
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
            f.write(randoop_template.substitute(classname = classlist.get_all_java_source_files(root_dir)[0], values = "\n".join(self.concrete_values_all_runs)))


    def collect_darted_suites(self):
        """"Finds all test suites generated by JDart"""

        import re

        ret_list = []
        for i in range(self.darted_count):
            suite_name = "TestsTest1" # This seems to be JDart's default
            package_name = "darted%i" % i
            directory = os.path.join("darted", package_name)
            if os.path.exists(os.path.join(directory, suite_name + ".java")):
                index_lo = 10
                index_hi = 11
                test_case_file_name = "TestsTest10.java"

                ret_list.append(UnitTests(
                    suite_name,
                    directory,
                    package_name,
                    index_lo,
                    index_hi
                ))

        return ret_list

    def jdart_suites_to_junit4(self, darted_suites, template_filename = 'suite_header.template'):
        """Turns tests generated by JDart from JUnit version 3 to version 4"""

        from string import Template

        for suite in darted_suites:
            suite_file_path = os.path.join(
                suite.directory,
                "%s.java" % suite.name
            )
            try:
                os.remove(suite_file_path)
            except OSError, e:
                pass

            # Assumption: there is only one test case file generated
            # by JDart and it has the same name as the suite plus 0 in
            # the end. Probably this assumption will do for the time
            # being.
            list_of_test_case_classes = ["%s%i" % (suite.name, i) for i in range(1)]

            with open(suite_file_path, 'w') as f:
                f.write("package %s;\n\n" % suite.randooped_package_name)
                f.write("import org.junit.runner.RunWith;\n")
                f.write("import org.junit.runners.Suite;\n")
                f.write("import org.junit.runners.Suite.SuiteClasses;\n\n")
                f.write("@RunWith(Suite.class)\n")
                f.write("@SuiteClasses({\n")
                f.write(",\n".join(["%s.%s.class" % (suite.randooped_package_name, tc_class) for tc_class in list_of_test_case_classes]))
                f.write("\n})\n")
                f.write("public class %s { }\n" % suite.name)

            for tc_class in list_of_test_case_classes:
                tc_class_path = os.path.join(suite.directory, "%s.java" % tc_class)
                with open(tc_class_path) as f:
                    input_lines = f.readlines()
                try:
                    os.remove(tc_class_path)
                except OSError, e:
                    pass

                output_lines = []
                included_imports = False
                to_skip = 0
                for line in input_lines:
                    if to_skip > 0:
                        to_skip -= 1
                        continue

                    if "import" in line:
                        if not included_imports:
                            output_lines.extend("import org.junit.FixMethodOrder;\n")
                            output_lines.extend("import org.junit.Test;\n")
                            output_lines.extend("import org.junit.runners.MethodSorters;\n")
                            included_imports = True
                        continue

                    if "public class" in line:
                        output_lines.extend("@FixMethodOrder(MethodSorters.NAME_ASCENDING)\n")
                        output_lines.extend("public class %s {\n" % tc_class)
                        continue

                    if "public void" in line:
                        method_name_and_params = line.lstrip().split(' ')[2]
                        output_lines.extend("  @Test\n")
                        output_lines.extend("  public void %s throws Throwable {\n" % method_name_and_params)
                        continue

                    if "// step 0" in line:
                        to_skip = 3
                        continue

                    if "obj." in line:
                        output_lines.extend("      try {\n")
                        output_lines.extend(line)
                        output_lines.extend("      } catch (java.lang.Exception e) { }\n")
                        continue

                    output_lines.extend(line)

                with open(tc_class_path, 'w') as tc_file:
                    tc_file.write("".join(output_lines))

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

        start_time = time.time()
        self.clock[clock_label] = [start_time, None]


    def stop_clock(self, clock_label):

        assert clock_label in self.clock, "No started clock with a label %s!" % clock_label

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
        """Prints statistics on execution times for various components of JDoop"""

        print ""

        for c in jdoop.clock.iterkeys():
            jdoop.print_clock(c)

    def determine_timelimit(self, identifier, execution_number = None):
        """Determine how much time can and should be spent for a particular task given a global time limit and time left"""

        # Write down the current time
        current_time = time.time()

        if identifier == "Randoop":
            minimum_time = 45 # seconds

            if execution_number == 1:
                default_time = 20 # seconds

                if self.randoop_only:
                    return int(math.ceil(have_to_finish_by - current_time))

            # If we are in the baseline mode, let Randoop run for the
            # remaining time
            elif execution_number == 2 and self.baseline:
                return int(math.ceil(have_to_finish_by - current_time))

            else:
                default_time = 300 # seconds

            if have_to_finish_by - current_time < minimum_time or have_to_finish_by - current_time < default_time:
                # Let's say it doesn't make sense to run Randoop for
                # less than 3 seconds
                return max(int(have_to_finish_by - current_time - 5), 3)

            elif have_to_finish_by - current_time < 2 * minimum_time and not execution_number == 1:
                return int(have_to_finish_by - current_time)
            else:
                return default_time
        if identifier == "JDart":
            short_running_time = 20 # seconds
            normal_running_time = 90 # seconds
            minimum_time = normal_running_time + 10 # seconds
            
            if have_to_finish_by - current_time < minimum_time:
                if have_to_finish_by - current_time < short_running_time:
                    return 0
                return short_running_time
            else:
                return normal_running_time

        return 42

        
if __name__ == "__main__":

    jdoop = JDoop()
    jdoop.start_clock("program")

    parser = argparse.ArgumentParser(description='Generates unit tests with Randoop only or with JDoop.')
    parser.add_argument('--root', required=True, help='source files root directory')
    parser.add_argument('--classlist', default='classlist.txt', help='Name of a file to write a file list to')
    parser.add_argument('--timelimit', default=120, type=int, help='Timelimit in seconds in which JDoop should finish its execution')
    parser.add_argument('--configuration-file', default='jdoop.ini', help='A configuration file with settings for JDoop')
    parser.add_argument('--randoop-only', default=False, action="store_true", help='The tool should run Randoop only')
    parser.add_argument('--baseline', default=False, action="store_true", help='The tool should run in the baseline mode')
    parser.add_argument('--classpath', default=None, help='A classpath to dependencies of tested classes')
    parser.add_argument('--generate-report', default=False, action="store_true", help='The tool should generate a code coverage report once it finishes its execution')
    parser.add_argument('--jpf-core-path', help='Path to the jpf-core module')
    parser.add_argument('--jdart-path', help='Path to the jdart module')
    parser.add_argument('--sut-compilation', help='Directory where class files of the package being tested can be found')
    parser.add_argument('--test-compilation', help='Directory where generated JUnit tests should be compiled to')
    parser.add_argument('--junit-path', help='Path to the JUnit jar archive')
    parser.add_argument('--hamcrest-path', help='Path to the Hamcrest jar archive')
    parser.add_argument('--randoop-path', help='Path to the Randoop jar archive')
    parser.add_argument('--jacoco-path', help='Path to the JaCoCo jar archive')
    params = parser.parse_args()

    have_to_finish_by = jdoop.get_clock_starting_time("program") + params.timelimit

    # The path on the file system of this very script
    scriptPath = os.path.realpath(__file__)
    scriptDir = os.path.dirname(scriptPath)

    jdoop.read_config_file(params)
    jdoop.randoop_only = params.randoop_only
    jdoop.baseline = params.baseline
    jdoop.dependencies_classpath = params.classpath

    # Create a list of classes to be tested
    classlist = ClassList(params.classlist)
    classlist.write_list_of_classes(params.root)

    unit_tests = UnitTests(name = "Regression1Test", directory = "tests-round-1", randooped_package_name = "randooped1")

    # Determine how much time should be given to the first run of
    # Randoop
    timelimit = jdoop.determine_timelimit("Randoop", 1)

    # Invoke Randoop to generate unit tests
    init_seed = 10
    jdoop.start_clock("Randoop #1")
    jdoop.run_randoop(unit_tests, classlist, timelimit, dont_terminate = True, seed = init_seed)
    jdoop.stop_clock("Randoop #1")

    # Split up the main unit test suite class if needed. With 1 unit
    # test per class, there are too many calls from the main class to
    # fit into the 64K bytecode size limit
    #
    new_unit_tests = jdoop.check_and_split_up_suite(unit_tests, template_filename = os.path.join(scriptDir, "suite_header.template"))

    # Start creating a list of unit tests
    unit_tests_list = new_unit_tests[:]

    # A classpath variable needed for code coverage reports
    classpath = ":".join([jdoop.paths.lib_junit, jdoop.paths.lib_hamcrest, jdoop.paths.sut_compilation_dir, jdoop.paths.tests_compilation_dir])
    if jdoop.dependencies_classpath != None:
        classpath += ":" + jdoop.dependencies_classpath

    i = 1
    # Instead of using True for an infinite loop, in this way I am
    # avoiding of Randoop going in the loop for a brief minimum 3
    # seconds
    while not params.randoop_only:

        i += 1

        # Symbolize unit tests
        jdoop.start_clock("Symbolization of unit tests #%d" % (i-1))
        # TODO: Vary number of unit tests to select based on
        # previous performance
        jdoop.symbolize_unit_tests(unit_tests, count = 1000)
        jdoop.stop_clock("Symbolization of unit tests #%d" % (i-1))

        # Compile symbolized unit tests
        jdoop.start_clock("Compilation of symbolic unit tests #%d" % (i-1))
        jdoop.compile_symbolic_tests(params.root, unit_tests)
        jdoop.stop_clock("Compilation of symbolic unit tests #%d" % (i-1))

        # Run JDart on symbolized unit tests
        timelimit = jdoop.determine_timelimit("JDart")

        if os.path.exists(classlist.filename) != True:
            classlist.write_list_of_classes(params.root)

        jdoop.start_clock("Global run of JDart #%d" % (i-1))
        jdoop.run_jdart(unit_tests, params.root, classlist, timelimit, template_filename = os.path.join(scriptDir, "randoop-format.template"))
        jdoop.stop_clock("Global run of JDart #%d" % (i-1))

        # Run Randoop
        timelimit = jdoop.determine_timelimit("Randoop", i)
        if timelimit > 3:
            unit_tests = UnitTests(name = "Regression%dTest" % i, directory = "tests-round-%d" % i, randooped_package_name = "randooped%d" % i)

            # In case the system under test deleted the list of
            # classes, re-create it
            if os.path.exists(classlist.filename) != True:
                classlist.write_list_of_classes(params.root)

            jdoop.start_clock("Randoop #%d" % i)
            if params.randoop_only:
                jdoop.run_randoop(unit_tests, classlist, timelimit, dont_terminate = True, seed = init_seed + i)
            else:
                jdoop.run_randoop(unit_tests, classlist, timelimit, dont_terminate = True, use_concrete_values = True, seed = init_seed + i)
            jdoop.stop_clock("Randoop #%d" % i)

            # Split up the main unit test suite class if needed. With 1 unit
            # test per class, there are too many calls from the main class to
            # fit into the 64K bytecode size limit
            #
            new_unit_tests = jdoop.check_and_split_up_suite(unit_tests, template_filename = os.path.join(scriptDir, "suite_header.template"))

            unit_tests_list.extend(new_unit_tests)

        # Check if we're out of time and break out of the loop if so
        if time.time() >= have_to_finish_by - 3:
            break

        # If we are in the baseline mode, no further iterations should
        # be performed
        if jdoop.baseline:
            break

    darted_suites = []
    if jdoop.darted_count > 0:
        darted_suites = jdoop.collect_darted_suites()
        jdoop.jdart_suites_to_junit4(darted_suites)

    jdoop.stop_clock("program")

    if params.generate_report:
        jdoop.start_clock("Compilation of unit tests")
        jdoop.compile_tests(unit_tests_list)
        jdoop.compile_tests(darted_suites)
        jdoop.stop_clock("Compilation of unit tests")

    # A work-around for the code below that runs JaCoCo reports:
    # combine the package name and the suite name
    for i in range(len(darted_suites)):
        darted_suites[i].name = "%s.%s" % (
            darted_suites[i].randooped_package_name, darted_suites[i].name)
    unit_tests_list.extend(darted_suites)

    if params.generate_report:
        # Run all tests and let JaCoCo measure coverage
        jdoop.start_clock("Code coverage report")

        for unit_tests_suite in unit_tests_list[:-1]:
            report = Report(jdoop.paths.lib_jacoco, [unit_tests_suite.name], classpath, params.root, jdoop.paths.sut_compilation_dir)
            report.run_testing()

        # Run code coverage for the last one and generate a report
        report = Report(jdoop.paths.lib_jacoco, [unit_tests_list[-1].name], classpath, params.root, jdoop.paths.sut_compilation_dir)
        report.run_code_coverage()

        jdoop.stop_clock("Code coverage report")

    # Print execution time statistics
    jdoop.print_stats()

    # Print statistics on concrete values
    if not params.randoop_only:
        # Print statistics about concrete values
        print ""
        print "Concrete values stats\n"

        print "Contribution of each JDart execution"
        for s in jdoop.concrete_values_all_runs_stats:
            print "Set size: %4d, contribution: %4d, unit tests name: %s" % (s[0], s[1], s[2])

        print "\nContribution of each iteration"
        for s in jdoop.concrete_values_iterations_stats:
            print "Set size: %4d, contribution: %4d, unit tests name: %s" % (s[0], s[1], s[2])
