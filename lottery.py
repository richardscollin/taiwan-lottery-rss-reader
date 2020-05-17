#!/usr/bin/env python3
from html.parser import HTMLParser
import click
import feedparser
import json
import re
import sys

class SummaryParser(HTMLParser):
    drawing_mapping = { "特別獎": "special",
            "特獎": "grand",
            "頭獎": "regular",
            "增開六獎": "additional",
            }

    def __init__(self):
        super().__init__()
        self.drawing_info = {}

    def clear(self):
        self.drawing_info = {}

    def handle_data(self, data):
        (drawing_type, numbers) = data.split("：", 2)
        numbers = numbers.split("、")
        self.drawing_info[self.drawing_mapping[drawing_type]] = numbers


"""
Assumes argument string looks like:
'101年09月、10'

**Warning; watch out for parsing values as octal

Will return two date strings that look like:
'2020/01/01' '2020/03/01'
Where the end date day is not included in the range
"""

def parseRocDate(s):
    (roc_year, start_month, end_month) = re.split("年|月、", s)
    start = "{}-{}-01".format(1911 + int(roc_year), start_month)

    end_month = int(end_month, 10) + 1
    end_year = 1911 + int(roc_year)
    if end_month == 13:
        end_year += 1
        end_month = 1

    end = "{}-{:02d}-01".format(end_year, end_month)

    return {"start": start, "end": end}


@click.command()
@click.argument('database_file', type=click.Path(exists=False))
def main(database_file):
    old_modified = None

    try:
        with open(database_file) as f:
            old_data = json.load(f)
            old_modified = old_data.get("modified", None)
    except (AttributeError,FileNotFoundError) as e:
        pass
    except json.JSONDecodeError as e:
        print(e.msg)
        sys.exit(1)
    
    data = feedparser.parse('http://invoice.etax.nat.gov.tw/invoice.xml', modified=old_modified)


    """
             {'link': '',
              'links': [{'rel': 'alternate', 'type': 'text/html'}],
              'published': '2012-11-25 13:12:14.17',
              'published_parsed': time.struct_time(tm_year=2012, tm_mon=11, tm_mday=25, tm_hour=13, tm_min=12, tm_sec=14, tm_wday=6, tm_yday=330, tm_isdst=0),
              'summary': '<p>特別獎：15719324</p><p>特獎：11661657</p><p>頭獎：64718986、49313179、29736314</p><p>增開六獎：843、927</p>',
              'summary_detail': {'base': 'http://invoice.etax.nat.gov.tw/invoice.xml',
                                 'language': None,
                                 'type': 'text/html',
                                 'value': '<p>特別獎：15719324</p><p>特獎：11661657</p><p>頭獎：64718986、49313179、29736314</p><p>增開六獎：843、927</p>'},
              'title': '101年09月、10',
              'title_detail': {'base': 'http://invoice.etax.nat.gov.tw/invoice.xml',
                               'language': None,
                               'type': 'text/plain',
                               'value': '101年09月、10'}},

"""

    entries = data['entries']

    filtered = []
    for entry in entries:
        add = {}
        add['title'] = entry['title_detail']['value']
        add['summary'] = entry['summary_detail']['value']
        filtered.append(add)
        

    drawings = []

    parser = SummaryParser()
    for entry in filtered:
        parser.feed(entry['summary'])

        drawing_data = parser.drawing_info
        date_info = parseRocDate(entry['title'])
        drawing_data.update(date_info)
        parser.clear()

        drawings.append(drawing_data)

    if data.modified != old_modified:
        print("INFO: Updating json database. Last-Modified: {}".format(data.modified))
        print("Last drawing: {}".format(json.dumps(drawings[0], indent=4)))
        results = {"modified": data.modified, "drawings": drawings }
        with open(database_file, "w") as f:
            json.dump(results, f)
    else:
        print("INFO: Using cached database. Last-Modified: {}".format(data.modified))


if __name__ == '__main__':
    main()
