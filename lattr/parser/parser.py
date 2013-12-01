#!/usr/bin/env python
# coding=utf-8

import re
import sys
import math
from collections import deque as queue
from argparse import ArgumentParser

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

def _dbg(msg):
    print >>sys.stderr, msg


def _class_name(node):
    if 'class' in node.attrs:
        class_name = node['class']
        if isinstance(class_name, basestring):
            return class_name
        return ' '.join(class_name)
    return ''


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


RE_UNLIKELY_CANDIDATES = re.compile(
    'combx|comment|community|disqus|extra|foot|'
    'header|menu|remark|rss|shoutbox|sidebar|'
    'sponsor|ad-break|agegate|pagination|pager|'
    'popup|tweet|twitter', re.I)
RE_POSITIVE_TAG = re.compile(
    'article|body|content|entry|hentry|post|text', re.I)
RE_NEGATIVE_TAG = re.compile(
    'combx|comment|contact|foot|footer|footnote|'
    'link|media|meta|promo|related|scroll|shoutbox|sponsor|tags|widget', re.I)


class HTMLCleaner(object):
    def clean(self, html):
        for replacement in defined_replacements:
            html = replacement.apply(html)
        return html


class _HashableNode(object):
    def __init__(self, node):
        assert isinstance(node, Tag)
        self.node = node
        self._hash = None

    @property
    def hash(self):
        if not self._hash:
            reverse_path = []
            node = self.node
            while node:
                node_id = (node.name, tuple(node.attrs), node.string)
                reverse_path.append(node_id)
                node = node.parent
            self._hash = abs(hash(tuple(reverse_path)))
        return self._hash

    def __repr__(self):
        return '<%s@%s %s[id=%s,class=%s]>' % (
            self.__class__.__name__,
            self.hash,
            self.node.name,
            self.node.attrs.get('id') or '',
            _class_name(self.node))

    def __hash__(self):
        return self.hash

    def __eq__(self, other):
        return self.hash == other.hash


class Document(object):

    MAXIMUM_TITLE_LENGTH = 150
    MINIMUM_TITLE_LENGTH = 15
    NODE_TO_SCORE_MIN_LENGHT = 25

    def __init__(self, html):
        if not html:
            raise RuntimeError('No html document specified for parser!')
        self.html = html
        self._soup = BeautifulSoup(html, 'lxml')
        self.title = None
        self.main_content = None

    def parse(self):
        # Remove these tags first
        self._remove_tags('script')
        # TODO(jiluo): Remove css sheets
        # TODO(jiluo): Add body to body_cache
        # TODO(jiluo): Find next page link

        self._prepare_document()
        self.title = self._parse_title()
        self.main_content = self._grab_main_content()

    def _remove_tags(self, *tags):
        for tag in tags:
            for node in self._soup.find_all(tag):
                node.extract()

    def _walk_nodes(self, root):
        pending = queue()
        pending.append(root)
        while len(pending):
            node = pending.popleft()
            if isinstance(node, Tag):
                for child in node.children:
                    pending.append(child)
                yield node

    def _prepare_document(self):
        if not self._soup.body:
            self._soup.html.append(self._soup.new_tag('body'))

        self._soup.body.id = 'lattrBody'
        # TODO(jiluo): Turn all double br's into p's
        # TODO(jiluo): Note, this is pretty costly as far as processing goes.
        #              Maybe optimize later
        # TODO(jiluo): Turn all relative urls into absolute urls
        for node in self._walk_nodes(self._soup.html):
            if not node.name:
                node.extract()
                continue
            id = node.attrs.get('id') or ''
            class_name = _class_name(node) or ''
            unlikely_match_string = '%s%s' % (id, class_name)
            if RE_UNLIKELY_CANDIDATES.search(unlikely_match_string):
                node.extract()
                _dbg('Remove unlikely candidate - ' + unlikely_match_string)

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
        return current_title

    def _score_node(self, node):
        content_score = self._class_weight(node)
        if node.name == 'div':
            content_score += 5
        elif node.name in ('pre', 'td', 'blockquote'):
            content_score += 3
        elif node.name in ('address', 'ol', 'ul', 'dl', 'dd', 'dt', 'li', 'form'):
            content_score -= 3
        elif node.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'th'):
            content_score -= 5
        return content_score

    def _class_weight(self, node):
        weight = 0
        class_name = _class_name(node)
        if class_name:
            if RE_POSITIVE_TAG.search(class_name):
                weight += 25
            if RE_NEGATIVE_TAG.search(class_name):
                weight -= 25
        id = node.attrs.get('id')
        if id:
            if RE_POSITIVE_TAG.search(id):
                weight += 25
            if RE_NEGATIVE_TAG.search(id):
                weight -= 25
        if node.name == 'article':
            weight += 50
        return weight

    def _grab_main_content(self):
        scores = {}
        for node in self._walk_nodes(self._soup.html):
            if node.name not in ('p', 'td', 'pre', 'div'):
                continue
            inner_text = node.text
            if len(inner_text) < self.NODE_TO_SCORE_MIN_LENGHT:
                continue
            parent_node = node.parent
            if not parent_node or not parent_node.name:
                continue
            parent_node_key = _HashableNode(parent_node)
            if parent_node_key not in scores:
                scores[parent_node_key] = self._score_node(parent_node)
            grand_parent_node = parent_node.parent
            grand_parent_node_key = None
            if (grand_parent_node and
                grand_parent_node.name and
                grand_parent_node not in scores):
                grand_parent_node_key = _HashableNode(grand_parent_node)
                scores[grand_parent_node_key] = self._score_node(grand_parent_node)

            # Add a point for the paragraph itself as a base.
            content_score = 1

            # Add points for any commas within this paragraph
            content_score += inner_text.count(',')

            # For every 100 characters in this paragraph, add another point.
            # Up to 3 points.
            content_score += min(math.floor(len(inner_text) / 100), 3)

            # Add the score to the parent. The grandparent gets half.
            scores[parent_node_key] = scores[parent_node_key] + content_score
            if grand_parent_node_key:
                scores[grand_parent_node_key] += content_score / 2

        # After we've calculated scores, loop through all of the possible
        # candidate nodes we found and find the one with the highest score.
        top_candidate_key = self._find_top_candidate(scores)
        top_candidate = top_candidate_key.node

        # Now that we have the top candidate, look through its siblings
        # for content that might also be related.
        # Things like preambles, content split by ads that we removed, etc.
        sibling_score_threshold = max(10, scores[top_candidate_key] * 0.2)

        top_candidate_class_name = _class_name(top_candidate)
        if top_candidate.name == 'body':
            output = top_candidate
        else:
            output = self._soup.new_tag('div')
            output.append(top_candidate)
        for sibling in top_candidate.next_siblings:
            if isinstance(sibling, NavigableString): continue
            append = False
            content_bonus = 0
            if (top_candidate_class_name and
                _class_name(sibling) == top_candidate_class_name):
                content_bonus = content_bonus + scores[top_candidate_key] * 0.2
            sibling_key = _HashableNode(sibling)
            if (sibling in scores and
                (scores[sibling_key] + content_bonus) >= sibling_score_threshold):
                append = True
            if append:
                output.append(sibling)
        if not output:
            output.append(top_candidate)
        return output

    def _find_top_candidate(self, scores):
        top_candidate = None
        for candidate, score in scores.iteritems():
            scores[candidate] *= (1 - self._link_density(candidate.node))
            _dbg('Candidate: %s with score %d' % (candidate, scores[candidate]))
            if not top_candidate or scores[candidate] > scores[top_candidate]:
                top_candidate = candidate
        if not top_candidate:
            top_candidate = _HashableNode(self._soup.body)
            scores[top_candidate] = 0
        _dbg('top_candidate %s with score %d' % (top_candidate,
                                                 scores[top_candidate]))
        return top_candidate

    def _link_density(self, node):
        '''Get the density of links as a percentage of the content.
        This is the amount of text that is inside a link
        divided by the total text in the node.
        '''
        links = node.find_all('a')
        if links:
            link_length = reduce(lambda accum, x: accum + len(x.text), links, 0.0)
            return link_length / len(node.text)
        return 0


def _wrap_content(title, content_node, wrap):
    if wrap:
        doc = BeautifulSoup(
            '''
            <html>
                <head>
                    <title><title/>
                </head>
                <body></body>
            </html>''')
        doc.title.append(doc.new_string(title))
        doc.body.append(content_node)
        return doc
    else:
        return content_node


def _read_html(args):
    if args.url:
        return requests.get(args.url).text

    if args.file:
        if args.file == '-':
            return sys.stdin.read()
        else:
            with open(args.file, 'rb') as fp:
                return fp.read()
    return ''


def _define_options():
    arg_parser = ArgumentParser()
    group = arg_parser.add_mutually_exclusive_group()
    group.add_argument('-f', '--file', dest='file',
                       help=('html file to parse, '
                             'if file is "-", means read from stdin'))
    group.add_argument('-u', '--url', dest='url',
                       help='use URL instead of a local file')
    arg_parser.add_argument('-o', '--output', dest='output',
                            help='write main content to output file')
    arg_parser.add_argument('-w', dest='wrap_content', action='store_true',
                            help='wrap the main content in <html> tag')
    return arg_parser


def main():
    arg_parser = _define_options()
    args = arg_parser.parse_args()
    if not (args.file or args.url):
        arg_parser.print_help()
        exit(1)

    doc = Document(_read_html(args))
    doc.parse()
    print 'Title: %s' % doc.title

    main_content = str(_wrap_content(doc.title,
                                     doc.main_content,
                                     args.wrap_content))
    if args.output:
        with open(args.output, 'wb') as fp:
            fp.write(main_content)
    else:
        print 'Main content: %s' % main_content


if __name__ == '__main__':
    main()
