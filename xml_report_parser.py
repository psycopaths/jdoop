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
