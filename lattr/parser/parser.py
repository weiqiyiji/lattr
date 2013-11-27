#!/usr/bin/env python
# coding=utf-8

import re
import math
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


RE_UNLIKELY_CANDIDATES = ('combx|comment|community|disqus|extra|foot|'
                          'header|menu|remark|rss|shoutbox|sidebar|'
                          'sponsor|ad-break|agegate|pagination|pager|'
                          'popup|tweet|twitter')


class Document(object):

    MAXIMUM_TITLE_LENGTH = 150
    MINIMUM_TITLE_LENGTH = 15
    NODE_TO_SCORE_MIN_LENGHT = 25

    def __init__(self, html):
        if not html:
            raise RuntimeError('No html document specified for parser!')
        self.html = html
        self._soup = BeautifulSoup(html, 'lxml')
        self._title = None
        self._main_content = None

    @property
    def title(self):
        if not self._title:
            self._parse_title()
        return self._title

    def parse(self):
        # Remove these tags first
        self._remove_tags('script', 'style')
        # TODO(jiluo): Add body to body_cache
        # TODO(jiluo): Find next page link

        self._prepare_document()
        self._parse_title()
        self._grab_main_content()

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

    def _grab_main_content(self):
        scores = {}
        for node in self._soup.descendants:
            if node.name not in ('p', 'td', 'pre', 'div'):
                continue
            inner_text = node.text
            if len(inner_text) < NODE_TO_SCORE_MIN_LENGHT):
                continue
            parent_node = node.parent
            if not parent_node or not parent_node.name:
                continue
            if parent_node not in scores:
                scores[candidates] = 0
            grand_parent_node = parent_node.parent
            if (grand_parent_node and
                grand_parent_node.name and
                grand_parent_node not in scores):
                scores[grand_parent_node] = 0

            # Add a point for the paragraph itself as a base.
            content_score = 1

            # Add points for any commas within this paragraph
            content_score = content_score + inner_text.count(',')

            # For every 100 characters in this paragraph, add another point.
            # Up to 3 points.
            content_score = min(math.floor(len(inner_text) / 100), 3)

            # Add the score to the parent. The grandparent gets half.
            scores[parent_node] = scores[parent_node] + content_score
            if grand_parent_node:
                scores[grand_parent_node] = scores[grand_parent_node] + content_score

        # After we've calculated scores, loop through all of the possible
        # candidate nodes we found and find the one with the highest score.
        top_candidate = self._find_top_candidate(scores)

        # Now that we have the top candidate, look through its siblings
        # for content that might also be related.
        # Things like preambles, content split by ads that we removed, etc.

    def _find_top_candidate(self, scores):
        top_candidate = None
        for candidate, score in scores.iteritems():
            scores[candidate] = score * (1 - self._link_density(candidate))
            if not top_candidate || scores[candidate] > scores[top_candidate]:
                top_candidate = candidate
        if not top_candidate:
            top_candidate = self._soup.body
        return top_candidate

    def _link_density(self, node):
        '''Get the density of links as a percentage of the content.
        This is the amount of text that is inside a link
        divided by the total text in the node.
        '''
        links = node.find_all('a')
        if links:
            link_length = reduce(lambda accum, x: accum = accum + len(x.text), 0)
            return link_length / len(node.text)
        return 0
