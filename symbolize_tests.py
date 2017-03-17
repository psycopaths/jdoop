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


import re
import sys, os, errno, fileinput
import argparse

class Callable:
    def __init__(self, anycallable):
        self.__call__ = anycallable

class Literal:
    def represents_int(s):
        if s == "":
            return False
        try:
            if s[0] == "(":
                int(s[1:-1])
            else:
                int(s)
            return True
        except ValueError:
            return False

    def represents_long(s):
        if s == "":
            return False

        expr = s

        if s[0] == "(" and s[-1] == ")":
            expr = s[1:-1]
        if expr[-1] == "l" or expr[-1] == "L":
            expr = expr[:-1]

        try:
            long(expr)
            return True
        except ValueError:
            return False

    def represents_float(s):
        if s == "":
            return False

        expr = s

        if s[0] == "(" and s[-1] == ")":
            expr = s[1:-1]
        if expr[-1] == "f" or expr[-1] == "F":
            expr = expr[:-1]

        try:
            float(expr)
            return True
        except ValueError:
            return False

    def represents_double(s):
        if s == "":
            return False

        expr = s

        if s[0] == "(" and s[-1] == ")":
            expr = s[1:-1]
        if re.search("^Double\.", s):
            return True
        if expr[-1] == "d" or expr[-1] == "D":
            expr = expr[:-1]

        try:
            float(expr)
            return True
        except ValueError:
            return False

    def represents_boolean(s):
        return s == "true" or s == "false"

    def represents_string(s):
        if s == "":
            return False

        return s[0] == '"' and s[-1] == '"'

    def represents_primitive(s):
        # JDart does not support symbolic strings currently

        # return (Literal.represents_int(s) or Literal.represents_long(s)
        #         or Literal.represents_float(s) or Literal.represents_double(s)
        #         or Literal.represents_boolean(s) or Literal.represents_string(s))

        return (Literal.represents_int(s) or Literal.represents_long(s) or 
                Literal.represents_float(s) or Literal.represents_double(s) or
                Literal.represents_boolean(s))

    def extract_cast_prefix(s):

        # Keeps track of whether we are in a string literal
        in_double_quotes = False

        stack = []
        last = -1
        i = 0
        length = len(s)

        while i < length:

            if in_double_quotes:
                if s[i] == "\\":
                    i += 1

                elif s[i] == '"':
                    in_double_quotes = False
                
                i += 1
                continue

            if s[i] == '\"':
                in_double_quotes = True
                i += 1
                continue
            
            if s[i] == '(':
                stack.append(i)
            elif s[i] == ')':
                l = stack[-1]
                subs = s[l + 1:i]
                if Literal.represents_primitive(subs):
                    # If I use the commented part, the whole string s
                    # becomes the prefix

                    # return s[:i+1]

                    return s[:l]

                stack.pop()
                last = i

            i += 1

        return s[:last + 1]

    represents_int = Callable(represents_int)
    represents_float = Callable(represents_float)
    represents_double = Callable(represents_double)
    represents_boolean = Callable(represents_boolean)
    represents_string = Callable(represents_string)
    represents_long = Callable(represents_long)
    represents_primitive = Callable(represents_primitive)
    extract_cast_prefix = Callable(extract_cast_prefix)

class SymbolicUnitTests:

    def __init__(self, package_name, input_file, class_names):
        self.output_file = None
        self.method_name = None
        self.class_name = class_names[0]

        self.input_file = input_file

        # assert that this is a valid package name
        # I'll revisit this latter
        # assert re.match("[a-zA-Z][a-zA-Z]*(\.[a-zA-Z][a-zA-Z]*)*", package_name)
        self.package_name = package_name
        
        self.path = package_name.replace(".", os.sep)

        try:
            os.makedirs(self.path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    def initialize_output_file(self):
        self.output_file = []
        self.output_file.append("// This is an automatically generated file")
        self.output_file.append("package " + self.package_name + ";\n")
        self.sym_var_list = []
        self.method_name = None
        self.method_def_pos = None
        self.wrote_test_case = False

    def finalize_and_write_output_file(self):

        if not re.search("sym_var", " ".join(self.output_file)):
            return

        rand_vals = {
            'int': '0', 'float': '0.0f', 'double': '0.0', 'boolean': 'false'
        }

        self.output_file[self.method_def_pos] = self.output_file[self.method_def_pos].replace(
            "()", "(" + ", ".join(self.sym_var_list) + ")"
        )
        self.output_file.append("  " + "public static void main(String[] args) throws Throwable {")

        self.output_file.append("    " + self.class_name + " tc0 = new " + self.class_name + "();")
        self.output_file.append("    " + "try {")
        self.output_file.append("      " + "tc0.%s(%s);" % (
            self.method_name,
            ', '.join([rand_vals[var.split(' ')[0]] for var in self.sym_var_list])))
        self.output_file.append("    " + "} catch (Exception e) {")
        self.output_file.append("    " + "}")
        self.output_file.append("  " + "}")

        self.output_file.append("}\n")

        with open(os.path.join(self.path, self.class_name + ".java"), 'w') as f:
            f.write("\n".join(self.output_file))

        self.wrote_test_case = True


    def find_parameter_parantheses(self, line):

        # Keeps track of whether we are in a string literal
        in_double_quotes = False

        stack = []
        left = -1
        right = -1
        i = 0
        length = len(line)

        while i < length:

            if in_double_quotes:
                if line[i] == "\\":
                    i += 1

                elif line[i] == '"':
                    in_double_quotes = False
                
                i += 1
                continue

            if line[i] == '\"':
                in_double_quotes = True
                i += 1
                continue

            if line[i] == '(':
                stack.append(i)
            elif line[i] == ')':
                if i == (len(line) - 2) and line[i + 1] == ";" and len(stack) == 1:
                    left = stack.pop()
                    right = i
                    break
                else:
                    stack.pop()

            i += 1

        return (left, right)

    # A method that splits a string into a list of
    # parameters. Parameters are delimited by a comma
    def split_into_parameters(self, s):

        list_of_parameters = []

        in_double_quotes = False

        length = len(s)
        i = 0

        start = 0
        in_word = False

        while i < length:

            if not in_word and s[i] != ',':
                start = i
                in_word = True

            if in_double_quotes:
                if s[i] == "\\":
                    i += 2
                    continue

                elif s[i] == '"':
                    in_double_quotes = False
                    in_word = False
                    list_of_parameters.append(s[start:i+1].lstrip().rstrip())
                    i += 1

                else:
                    i += 1

                continue

            if s[i] == '\"':
                in_double_quotes = True
                start = i
                in_word = True
                i += 1
                continue

            if s[i] == ',':
                if in_word:
                    list_of_parameters.append(s[start:i].lstrip().rstrip())
                    in_word = False
                
                i += 1
                continue

            i += 1

        if in_word:
            list_of_parameters.append(s[start:].lstrip().rstrip())

        return list_of_parameters

    def generate_symbolized_unit_tests(self):

        sym_variables_whitespace = None
        method_count = 0

        self.initialize_output_file()

        sym_var_counter = 0
        has_seen_class_name = False

        with open(self.input_file, 'r') as f:
            for line_nl in f:
                # Remove the newline character
                line = line_nl[:-1]
                whitespace = line[:len(line) - len(line.lstrip())]

                if re.search("public class", line):
                    continue

                if re.search("@Test", line.lstrip()):
                    continue

                # If this is a line that imports JUnit classes, a line
                # that defines a debugging variable, or the final line
                # that only has a closing bracket of the class, skip it
                if re.search("import ", line) or re.search("public static boolean debug = false;", line) or line[0:1] == '}' or re.search("if \(debug\)", line) or re.search("NAME_ASCENDING", line):
                    continue

                # Extract the leading whitespace in a line of the first
                # method definitinion, method name, and create the
                # single-method class name
                if re.search("public void", line):
                    if method_count != 0:
                        self.finalize_and_write_output_file()
                        self.initialize_output_file()

                    method_count += 1

                    if not sym_variables_whitespace:
                        sym_variables_whitespace = whitespace
                    # extract method name and store it for later usage
                    self.method_name = line.lstrip().split(" ")[2][:-2]
                    has_seen_class_name = True
                    self.output_file.append("public class " + self.class_name + " {\n")
                    self.output_file.append("  public static boolean debug = false;\n")

                # Avoid too many empty lines at the beginning of the file
                if line.lstrip() == "" and not has_seen_class_name:
                    continue

                # Skip JUnit assertion statements
                if (re.search(".*assertTrue\(", line.lstrip())
                    or re.search(".*assertNotNull\(", line.lstrip())
                    or re.search(".*assertNull\(", line.lstrip())
                    or re.search(".*org.junit.Assert.fail", line.lstrip())):
                    # self.output_file.append(line)
                    continue

                # Check if this is the null value assignment to a variable
                if re.search("null;$", line):
                    self.output_file.append(line)
                    continue

                # find the left and the right parameter paranthesis
                (lpar, rpar) = self.find_parameter_parantheses(line.rstrip())

                # This matches only method calls (both static and
                # non-static), and not constructors
                if ((re.search(".* = ", line.lstrip()) == None
                    or re.search("^.*\..*\(.*\) *;$", line.lstrip().rstrip()))
                    and not (re.search(".* = new ", line.lstrip()))):

                    non_interesting = True

                    # Check if this is a static method call. The least
                    # what we expect of a static method call is of form
                    # ClassName.methodName();
                    if re.search("^.*\..*\(.*\) *;$", line.lstrip().rstrip()):
                        non_interesting = False

                    # Check if this is a new variable declaration
                    elif re.search(".* = ", line):

                        non_interesting = False

                        # Check if it is a new array line
                        if re.search("= new", line) and lpar == -1 and rpar == -1:
                            non_interesting = True

                        # Check if it is a variable initialized to null
                        if re.search("= null;", line):
                            non_interesting = True

                    if non_interesting:
                        if re.search("public void", line):
                            self.method_def_pos = len(self.output_file)
                        self.output_file.append(line)
                        continue

                # Since we got this far, we must be in a method call line or a constructor call line

                # skip if there are no parameters, i.e. just print out the
                # line
                if lpar + 1 == rpar or (lpar == -1 and rpar == -1):
                    self.output_file.append(line)
                    continue

                parameters = self.split_into_parameters(line[lpar + 1:rpar])

                # Assume none of the parameters will be turned to symbolic,
                # i.e. that all of them are objects
                turned_to_symbolic = [None for i in range(len(parameters))]

                symbolic_name = "sym_var%d" % sym_var_counter

                for i in range(len(parameters)):

                    if parameters[i] == "":
                        continue

                    var_declaration = ""
                    is_symbolic = False

                    prefix = ""

                    if Literal.represents_primitive(parameters[i]):
                        suffix = parameters[i]
                    else:
                        prefix = Literal.extract_cast_prefix(parameters[i])
                        if len(prefix) > 0:
                            suffix = parameters[i][len(prefix):]
                        else:
                            suffix = parameters[i]

                    # Check if the current parameter is int, double, bool, or
                    # string. The order of testing is important
                    if Literal.represents_int(suffix):
                        is_symbolic = True
                        var_declaration = "int %s" % symbolic_name

                    # Z3 currently doesn't support longs
                    # elif Literal.represents_long(suffix):
                    #     is_symbolic = True
                    #     var_declaration = "public long %s = %s;" % (symbolic_name, suffix)

                    elif Literal.represents_float(suffix):
                        is_symbolic = True
                        var_declaration = "float %s" % symbolic_name

                    elif Literal.represents_double(suffix):
                        is_symbolic = True
                        var_declaration = "double %s" % symbolic_name

                    elif Literal.represents_boolean(suffix):
                        is_symbolic = True
                        var_declaration = "boolean %s" % symbolic_name

                    # Jdart does not support symbolic strings currently

                    # elif Literal.represents_string(suffix):
                    #     is_symbolic = True
                    #     var_declaration = "String %s" % symbolic_name

                    # If the parameter is made symbolic, create a new
                    # variable in the code by adding two additional code
                    # lines for that purpose
                    if is_symbolic:
                        turned_to_symbolic[i] = prefix + symbolic_name
                        self.sym_var_list.append(var_declaration)
                        sym_var_counter += 1

                        # Prepare the name for the next symbolic variable
                        symbolic_name = "sym_var%d" % sym_var_counter

                # copy everything up to the parameters to a new string
                new_line = line[:lpar + 1]

                # for each parameter, check if it's concrete or symbolic
                for i in range(len(parameters)):
                    if i != 0:
                        new_line += ", "

                    if not turned_to_symbolic[i]:
                        new_line += parameters[i]
                        continue

                    new_line += turned_to_symbolic[i]

                new_line += ");"

                self.output_file.append(new_line)

        # print out the last method's class
        self.finalize_and_write_output_file()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process JUnit tests generated by Randoop to make them fit for symbolic analysis by jDART.')
    parser.add_argument('--package', default='randooped')
    parser.add_argument('--root', default='./')
    parser.add_argument('--listfile', default='classes-to-analyze')
    parser.add_argument('--unit-tests-name', default='Randoop1Test')
    parser.add_argument('--unit-tests-directory', default='tests-round-1')
    params = parser.parse_args()

    asdf = '%s/%s%s' % (params.unit_tests_directory, params.unit_tests_name, '260.java')
    print asdf
    unit_tests = SymbolicUnitTests(params.package, "classes-to-analyze", asdf, ["test260Class"])
    # unit_tests = SymbolicUnitTests(params.package, params.root, params.listfile)
    unit_tests.generate_symbolized_unit_tests()
