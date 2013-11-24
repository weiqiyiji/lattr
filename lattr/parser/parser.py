#!/usr/bin/env python
# coding=utf-8

import re
from bs4 import BeautifulSoup


class Replacement(object):
    def __init__(self, desc, regex, replacement):
        self.desc = desc
        self.regex = regex
        self.replacement = replacement

    def apply(self, content):
       return self.regex.sub(self.replacement, content)

    def dry_run(self, content):
        # useful for debugging:
        return '%s:%s' % (self.desc, str(self.regex.findall(content)))


defined_replacements = [
    Replacement('javascript',
                re.compile('<script.*?</script[^>]*>', re.DOTALL | re.IGNORECASE),
                replacement=''),
    Replacement('double double-quoted attributes',
                re.compile('(="[^"]+")"+'),
                '\\1'),
    Replacement('unclosed tags',
                re.compile('(<[a-zA-Z]+[^>]*)(<[a-zA-Z]+[^<>]*>)'),
                '\\1>\\2'),
    Replacement('unclosed (numerical) attribute values',
                re.compile('(<[^>]*[a-zA-Z]+\s*=\s*"[0-9]+)( [a-zA-Z]+="\w+"|/?>)'),
                '\\1"\\2')
]


class HTMLCleaner(object):
    def clean(self, html):
        for replacement in defined_replacements:
            html = replacement.apply(html)
        return html


class Document(object):

    MAXIMUM_TITLE_LENGTH = 150
    MINIMUM_TITLE_LENGTH = 15

    def __init__(self, html):
        if not html:
            raise RuntimeError('No html document specified for parser!')
        self.html = html
        self._soup = BeautifulSoup(html, 'lxml')
        self._title = None

    @property
    def title(self):
        if not self._title:
            self._parse_title()
        return self._title

    def parse(self):
        self._remove_tags('script', 'style')
        # TODO(jiluo): Add body to body_cache
        # TODO(jiluo): Find next page link

        self._prepare_document()
        self._parse_title()

        return str(self._soup)

    def _remove_tags(self, *tags):
        for tag in tags:
            for node in self._soup.find_all(tag):
                node.extract()

    def _prepare_document(self):
        if not self._soup.body:
            self._soup.html.append(self._soup.new_tag('body'))

        self._soup.body.id = 'lattrBody'
        # TODO(jiluo): Turn all double br's into p's
        # TODO(jiluo): Note, this is pretty costly as far as processing goes.
        #              Maybe optimize later

    def _parse_title(self):
        current_title = original_title = ''
        title_tag = self._soup.find(id='title')
        if title_tag:
            current_title = original_title = title_tag.text
        elif self._soup.title:
            current_title = original_title = self._soup.title.text

        if re.search(r' [\|\-] ', current_title):
            current_title = re.sub(r'(.*) [\|\-] .*', r'\1', original_title)
        elif (len(current_title) < self.MINIMUM_TITLE_LENGTH or
              len(current_title) > self.MAXIMUM_TITLE_LENGTH):
            h1tags = self._soup.find_all('h1')
            if h1tags and len(h1tags) == 1:
                current_title = h1tags[0].text

        self._title = current_title
