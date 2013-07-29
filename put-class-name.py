#!/usr/bin/env python

import sys
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Replace the placeholder string with the appropriate package and class name.')
    parser.add_argument('--classname', required=True, help='fully-qualified name of a class')
    parser.add_argument('--concretevaluesfile', default='concrete-values-tmp.txt')
    params = parser.parse_args()

    result = open('concrete-values.txt', 'w')

    with open(params.concretevaluesfile, 'r') as f:
        for line in f:
            if line != "<This is a placeholder for the class name>\n":
                result.write(line)
            else:
                result.write(params.classname + "\n")

    result.close()
