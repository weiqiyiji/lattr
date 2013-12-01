#!/usr/bin/env python
# coding=utf-8

import unittest

from lattr.parser import HTMLCleaner, Document


class HTMLCleanerTestCase(unittest.TestCase):
    BROKEN_JAVASCRIPT = '<html><script></script ></html>'
    DOUBLE_DOUBLE_QUOTED_ATTRIBUTES = '<div id="test""></div>'
    UNCLOSED_TAGS = '<div<div>'
    UNCLOSED_ATTRIBUTE_VALUES = '<div id="7 class="test">'

    def setUp(self):
        self.cleaner = HTMLCleaner()

    def test_clean_broken_javascript_tag(self):
        cleaned = self.cleaner.clean(self.BROKEN_JAVASCRIPT)
        self.assertEqual('<html></html>', cleaned)

    def test_clean_double_quoted_attributes(self):
        cleaned = self.cleaner.clean(self.DOUBLE_DOUBLE_QUOTED_ATTRIBUTES)
        self.assertEqual('<div id="test"></div>', cleaned)

    def test_clean_unclosed_tags(self):
        cleaned = self.cleaner.clean(self.UNCLOSED_TAGS)
        self.assertEqual('<div><div>', cleaned)

    def test_unclosed_attribute_values(self):
        cleaned = self.cleaner.clean(self.UNCLOSED_ATTRIBUTE_VALUES)
        self.assertEqual('<div id="7" class="test">', cleaned)


class DocumentTestCase(unittest.TestCase):

    def test_parse_title(self):
        doc = Document('<html><title>test_title</title></html>')
        doc.parse()
        self.assertEqual('test_title', doc.title)

    def test_parse_title_from_id(self):
        doc = Document('''
        <html>
          <title>test_title</title>
          <body>
            <div id="title">div_title</div>
          </body>
        </html>''')
        doc.parse()
        self.assertEqual('div_title', doc.title)

    def test_title_from_maintitle(self):
        doc = Document('''
        <html>
          <title>Main - sub</title>
        </html>
        ''')
        doc.parse()
        self.assertEqual('Main', doc.title)

    def test_title_from_h1(self):
        doc = Document('''
        <html>
          <title>Short title</title>
          <body><h1>real title</h1></body>
        </html>
        ''')
        doc.parse()
        self.assertEqual('real title', doc.title)
