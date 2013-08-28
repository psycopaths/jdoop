# Introduction

JPF-Doop is a testing tool for Java libraries. It is based on the Java
PathFinder's concolic execution engine [jDART][0] and [Randoop][1], a
feedback-directed random testing engine.

# Setting up

After you've cloned the repository, you can configure various
parameters in `jpfdoop.ini`. Most importantly, change `jpf-core` and
`jpf-jdart` in the `jpfdoop` section so that they point to the main
directories of jpf-core and jpf-jdart, respectively. Do not use `~` as
a shorthand for your home directory.

# Usage

To run JPF-Doop, a few parameters need to be passed to it, including a
package name and where the package's source and class files are. Other
arguments are optional. For example, to test the
`org.apache.commons.collections` package from the Apache Commons
library from the [jpf-doop-examples][2] repository, assuming that
JPF-Doop and `jpf-doop-examples` are on the same directory hierarchy
level, run the following:

```
#!bash
$ python jpfdoop.py --package org.apache.commons.collections --root ../jpf-doop-examples/
```

A code coverage report will be generated and can be found in the
`jacoco-site/` directory.

For further instructions on how to use JPF-Doop, run:

```
#!bash
$ python jpfdoop.py --help
```

# Generating code coverage reports

JPF-Doop has a script that generates a code coverage report for JUnit
tests that can be used without JPF-Doop, i.e. unit tests can be
generated or obtained in some other way. The script is `report.py`,
and it has a few dependencies. First of all, clone this repository. In
addition, the following is needed:

- [Python][3], version 2.7,
- [Apache Ant][4].

To get help on how to run the code coverage script from the command
line, type:

```
#!bash
$ python report.py --help
```

The script takes 6 arguments, where the `--jacocopath` argument is
optional. There is an example package named `branching` in the
`report-examples/` directory. If you build the example in such a way
that `.class` files are in the same directory where respective `.java`
files are, this is how you would generate a code coverage report for
the example:

```
#!bash
$ python report.py --unittests TestBranching --classpath report-examples/:report-examples/branching/tests/ --sourcepath report-examples/ --packagepath branching --buildpath report-examples/
```

The `report.py` script will generate a code coverage report in two
formats - HTML and XML. Both can be found in a `jacoco-site/`
directory.

[0]: https://bitbucket.org/psycopaths/jpf-jdart
[1]: https://code.google.com/p/randoop/
[2]: https://bitbucket.org/psycopaths/jpf-doop-examples
[3]: http://python.org
[4]: https://ant.apache.org/
