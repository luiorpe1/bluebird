#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bluebird HTML parser

Use this parser in your message reader controller to strip all
the HTML tags and leave its content as plain text

class:

BlueHTMLParser -- parse an HTML string and strip all tags

"""
import sys
if sys.version_info.major == 2:
    from HTMLParser import HTMLParser
else:
    from html.parser import HTMLParser


class BlueHTMLParser(HTMLParser):
    """Strips the HTML tags from a HTML formatted message"""

    _tag = None
    _attrs = None

    _data = None
    _linkcount = None
    _footnotes = None

    _ignoretags = ['html', 'meta', 'style', 'script']

    def __init__(self, strict=False):
        if not issubclass(BlueHTMLParser, object):  # Runnning Python 2
            HTMLParser.__init__(self)
        else:
            super(BlueHTMLParser, self).__init__(strict)

        self._data = []
        self._linkcount = 0
        self._footnotes = ['\n']

    def get_result(self):
        return ''.join(self._data + self._footnotes)

    def handle_starttag(self, tag, attrs):
        #print("Encountered an end tag :", tag)
        self._tag = tag
        self._attrs = dict(attrs)

        if tag == 'br':
            self._data.append('\n')
        elif tag == 'p':
            self._data.append('\n\n')
        elif tag == 'a':
            self._linkcount += 1

    def handle_endtag(self, tag):
        #print("Encountered an end tag :", tag)
        self._tag = tag
        self._attrs = None

    def handle_data(self, data):
        #print("Encountered some data  :", data)
        if data is None:
            #print('tag: ', self._tag, ' has data None')
            return

        if data == '\r\n':
            return
        #data = data.strip('\r\n')

        #print('tag: ', self._tag)
        if self._tag in self._ignoretags:
            return
        elif self._tag == 'a':
            if self._attrs is None:
                self._data.append(data)
            else:
                self._data.append('%s[%d]' % (data, self._linkcount))
                self._footnotes.append('[%d] %s: %s' %
                                      (self._linkcount,
                                       data,
                                       self._attrs['href']))
        else:
            self._data.append(data)

## =================================================================

if __name__ == '__main__':
    parser = BlueHTMLParser(strict=False)
    if len(sys.argv) <= 1:
        parser.feed('<html><head><title>Test</title></head>'
                    '<body><h1>Parse me!</h1></br>'
                    '<a href="www.test.com">test</a></body></html>')
    else:
        with open(sys.argv[1], 'r') as f:
            parser.feed(f.read())

    print(parser.get_result())
