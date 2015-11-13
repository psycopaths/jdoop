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

# A class that extracts branch and instruction coverage from a JaCoCo
# code coverage XML report


import sys
from BeautifulSoup import BeautifulStoneSoup

class xml_report_parser:
    def __init__(self, filename):
        self.filename = filename
        self.counters = None
        self.soup = BeautifulStoneSoup(open(filename).read())

    def find_counter(self, type):
        if self.counters == None:
            # Check only last 6 counters because they are global
            # summaries for the whole package
            self.counters = self.soup.findAll('counter')[-6:]

        ret = dict()
        for counter in self.counters:
            counter_attrs = dict(counter.attrs)
            if counter_attrs[u'type'] == type:
                ret['covered'] = int(counter_attrs[u'covered'])
                ret['total'] = ret['covered'] + int(counter_attrs[u'missed'])
                break

        return ret

    def branch_coverage(self):
        return self.find_counter(u'BRANCH')

    def instruction_coverage(self):
        return self.find_counter(u'INSTRUCTION')

if __name__ == "__main__":
    parser = xml_report_parser(sys.argv[1])
    print parser.branch_coverage()
    print parser.instruction_coverage()
