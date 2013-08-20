# Introduction

# Generating code coverage reports

JPF-Doop has a script that generates a code coverage report for JUnit
tests. The script is `report.py`, and it has a few dependencies:

- [Python](http://python.org), version 2.7
- [Apache Ant](https://ant.apache.org/),
- [JUnit](http://junit.org/),
- [Jacoco](http://www.eclemma.org/jacoco/), a code coverage library
  for Java,
- the `command.py` script from this repository; put it into the same
  directory where `report.py` is, and
- the `jacoco.xml` Ant build file from this repository; also keep it
  in the same directory where `report.py` is.

The JUnit and JaCoCo libraries are `.jar` files, and can be put into a
`lib/` directory.

To get help on how to run the code coverage script from the command
line, type:

`python report.py --help`

The script takes 6 mandatory arguments. For example, if you have JUnit
tests for the `org.apache.commons.collections` package, you have given
these unit tests a base name `MyTest` and their source files are in a
`my-tests/` directory, source Java files of the package are in an
`src/` directory and the package class files are in a `build/`
directory, the JUnit library is in the `lib/` directory, and your
JUnit tests are compiled to the `build/tests` directory, then run the
following command to get a code coverage report:

`python report.py --jacocopath lib/jacocoant.jar --unittests MyTest --sourcepath src/ --buildpath build/ --packagepath org/apache/commons/collections --classpath lib/junit4.jar:build/:build/tests:my-tests/`

The script will generate a code coverage report in two formats - HTML
and XML. Both can be found in a `jacoco-site/` directory.
