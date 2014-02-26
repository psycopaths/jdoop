#!/usr/bin/env python

# This is a script that was used for testing JPF-Doop against Randoop
# for our submission to the JPF Workshop 2013

import os, sys, shutil
import argparse
import time

from command import *
from xml_report_parser import *

def create_config_file(base_dir, package_dir, config_file_path):
    try:
        print "Creating dir: " + os.path.dirname(config_file_path)
        os.makedirs(os.path.dirname(config_file_path))
    except Exception, err:
        if not "[Errno 17]" in str(err):
            print str(err)
            sys.exit(1)

    print config_file_path

    with open(config_file_path, 'w') as f:
        f.write("[jpfdoop]\n")
        f.write("jpf-core = /users/projects/jpf/jpf-core\n")
        f.write("jpf-jdart = /users/projects/jpf/jpf-jdart\n")
        f.write("[sut]\n")
        f.write("compilation-directory = " + os.path.join(base_dir, package_dir, "build", "classes") + "\n")
        f.write("dependency-directory = " + os.path.join(base_dir, package_dir, "lib") + "\n")
        # f.write("compilation-directory = /proj/JPF-Doop/projects/sf110/30_bpmail/build/classes/ch/bluepenguin/email/aop/\n")
        f.write("[tests]\n")
        f.write("compilation-directory = build/tests\n")
        f.write("[lib]\n")
        f.write("junit = lib/junit4.jar\n")
        f.write("randoop = lib/randoop.jar\n")
        f.write("jacoco = lib/jacocoant.jar\n")

    print ""
    os.system("cat " + config_file_path)
    print ""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generates unit tests with Randoop only or with JPF-Doop.')
    parser.add_argument('--tool-name', nargs='+', default='all', help='A list of tools that should be tested. Valid options are all, Randoop, Iterative, and Baseline')
    parser.add_argument('--package-list', default='package-list.txt', help='A file name with a package per line to be tested')
    parser.add_argument('--iterations', nargs='+', required=True, help='List of iterations (e.g., between 1 and 5) that should be executed. Provide "all" if all iterations from 1 to 5 should be executed')
    parser.add_argument('--timelimit', default=120, type=int, help='Timelimit in seconds in which the tool should finish its execution')
    parser.add_argument('--generate-report', default=False, action="store_true", help='If compilation and code coverage report generation should be executed')
    parser.add_argument('--emulab', default=False, action="store_true", help='If the experiments are carried out on a machine in Emulab')
    params = parser.parse_args()

    if params.tool_name == ["all"] or params.tool_name == "all":
        tools = ["JPF-Doop", "Randoop"]
    else:
        tools = params.tool_name[:]

    packages = []
    with open(params.package_list, 'r') as f:
        for line_nl in f:
            (package_dir, package_name) = line_nl[:-1].split(" ")
            packages.append({'dir' : package_dir, 'name' : package_name})
            print packages[-1]

    if params.iterations == ["all"]:
        iterations = [i for i in range(1, 6)]
    else:
        iterations = [int(i) for i in params.iterations]

    log_filename = "execution.log"
    
    if params.emulab:
        results_base_dir = "/scratch/JPF-Doop/experiment-results/sf110"
    else:
        results_base_dir = "testing/sf110"

    benchmark_base_dir = "/scratch/JPF-Doop/projects/sf110"

    time_snapshot = time.strftime('%Y-%m-%d_%H-%M-%S')

    for package in packages:

        config_file = os.path.join(results_base_dir, package['dir'], "jpfdoop.ini")
        create_config_file(benchmark_base_dir, package['dir'], config_file)

        for tool in tools:

            print "Package being analyzed: %s, tool used: %s\n" % (package['name'], tool)

            tool_param = " --randoop-only --generate-report"

            if tool == "Randoop":
                tool_param = " --randoop-only"

            if params.generate_report:
                tool_param += " --generate-report"

            for iteration in iterations:
                # Clean up anything left from before
                command = Command(args = "./clean.sh")
                command.run()

                print "Calling JPF-Doop with:"
                print "python jpfdoop.py --configuration-file " + config_file + " --root " + os.path.join(benchmark_base_dir, package['dir']) + " --package-name " + package['name'] + " --timelimit " + str(params.timelimit) + tool_param + " 2>&1 | tee " + log_filename

                os.system("python jpfdoop.py --configuration-file " + config_file + " --root " + os.path.join(benchmark_base_dir, package['dir']) + " --package-name " + package['name'] + " --timelimit " + str(params.timelimit) + tool_param + " 2>&1 | tee " + log_filename)

                path = os.path.join(results_base_dir, package['name'], tool, "run-%02d" % iteration)
                os.makedirs(path)

                parser = xml_report_parser("jacoco-site/report.xml")
                branch = parser.branch_coverage()
                instruction = parser.instruction_coverage()
                
                summary_report_path_branch = os.path.join(results_base_dir, package['name'], tool + '-branch-' + time_snapshot + '.log')
                with open(summary_report_path_branch, 'a') as f:
                    f.write("%d %d %d\n" % (iteration, branch['covered'], branch['total']))

                summary_report_path_instruction = os.path.join(results_base_dir, package['name'], tool + '-instruction-' + time_snapshot + '.log')
                with open(summary_report_path_instruction, 'a') as f:
                    f.write("%d %d %d\n" % (iteration, instruction['covered'], instruction['total']))
                
                # Create a directory structure and move results to appropriate places
                
                # Move the following files and dirs to the respective directory:
                # - jacoco-site/
                # - randooped*/
                # - tests-round-*/
                # - concrete-values.txt
                # - execution.log
                # - classlist.txt
                try:
                    shutil.move("jacoco-site", path)
                except:
                    pass
                try:
                    command = Command(args = "mv randooped* " + path)
                    command.run()
                except:
                    pass
                try:
                    command = Command(args = "mv tests-round-* " + path)
                    command.run()
                except:
                    pass
                try:
                    shutil.move("concrete-values.txt", path)
                except:
                    pass
                try:
                    shutil.move(log_filename, path)
                except:
                    pass
                try:
                    shutil.move("classlist.txt", path)
                except:
                    pass
