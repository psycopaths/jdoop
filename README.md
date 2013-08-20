# Introduction

To be added soon.

# Generating code coverage reports

JPF-Doop has a script that generates a code coverage report for JUnit
tests. The script is `report.py`, and it has a few dependencies. First
of all, clone this repository. In addition, the following is needed:

- [Python](http://python.org), version 2.7
- [Apache Ant](https://ant.apache.org/),

To get help on how to run the code coverage script from the command
line, type:

`python report.py --help`

The script takes 6 arguments, where the `--jacocopath` argument is
optional. For example, if you have JUnit tests for the
`org.apache.commons.collections` package, you have given these unit
tests a base name `MyTest` and their source files are in a `my-tests/`
directory, source Java files of the package are in an `src/` directory
and the package class files are in a `build/` directory, and your
JUnit tests are compiled to the `build/tests` directory, then run the
following command to get a code coverage report:

`python report.py --unittests MyTest --sourcepath src/ --buildpath build/ --packagepath org/apache/commons/collections --classpath build/:build/tests:my-tests/`

The script will generate a code coverage report in two formats - HTML
and XML. Both can be found in a `jacoco-site/` directory.
