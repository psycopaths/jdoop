#!/usr/bin/env python
# -*- coding: utf-8 -*-

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


from command import *

class Report:
    def __init__(self, jacoco_path, unit_tests_list, package_path, classpath, source_dir, build_dir):
        self.jacoco_path = jacoco_path
        self.unit_tests_list = unit_tests_list
        self.package_path = package_path
        self.classpath = classpath
        self.source_dir = source_dir
        self.build_dir = build_dir
    
    def run_testing(self, ut_list = None):

        if ut_list == None:
            ut_list = self.unit_tests_list

        # Execute unit tests
        for uts in ut_list:
            code_coverage_command = Command(args = "ant -f jacoco.xml -Darg0=%s -Darg1=%s -Darg2=%s -Darg3=%s -Darg4=%s -Darg5=%s test" % (self.jacoco_path, uts, self.classpath, self.package_path, self.source_dir, self.build_dir))
            code_coverage_command.run()

    def run_code_coverage(self):
        """Runs JaCoCo on all unit tests from the list and generates a code coverage report"""

        self.run_testing(ut_list = self.unit_tests_list[:-1])

        # Run tests for the last unit test set and generate a report
        report_command = Command(args = "ant -f jacoco.xml -Darg0=%s -Darg1=%s -Darg2=%s -Darg3=%s -Darg4=%s -Darg5=%s report" % (self.jacoco_path, self.unit_tests_list[-1], self.classpath, self.package_path, self.source_dir, self.build_dir))
        report_command.run()



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generates a JaCoCo code coverage report for given unit tests.')
    parser.add_argument('--jacocopath', default=os.path.normcase("lib/jacocoant.jar"), help='Path to the JaCoCo jar file')
    parser.add_argument('--unittests', nargs='+', help='A list of base names of JUnit files (e.g. RandoopTest) that should be run in order to determine code coverage')
    parser.add_argument('--classpath', default=".", help='Classpath is a Java classpath, where paths are separated by the : symbol')
    parser.add_argument('--packagepath', required=True, help='Path of a package, i.e. if a package name is org.example, put org/example here')
    parser.add_argument('--sourcepath', nargs='+', help='Root directory where package sources can be found')
    parser.add_argument('--buildpath', required=True, help='Root directory where package class files can be found')
    params = parser.parse_args()

    for src in params.sourcepath:
        report = Report(params.jacocopath, params.unittests, params.packagepath, ":".join([params.classpath, "lib/junit4.jar"]), src, params.buildpath)
        report.run_code_coverage()
