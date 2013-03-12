#!/usr/bin/env python
# vim: sw=4:ts=4:sts=4:fdm=indent:fdl=0:
# -*- coding: UTF8 -*-
#
# A sword KJV indexed search module web app.
# Copyright (C) 2013 Josiah Gordon <josiahg@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from os.path import join, dirname
from bottle import run, debug, jinja2_template as template
from bottle import request, response, redirect, static_file, Bottle
from string import printable as string_printable
from html import escape as html_escape
from time import strftime
import json
import re

import sword_search
from sword_search import build_highlight_regx, highlight_search_terms
import errors


# Global variables

# Seperates tags and there attributes and text into groups.
tag_regx = re.compile(r'''
            <(?P<tag>
            [Ss]eg|[Nn]ote|[Ww]|[Mm]ilestone|[Ff]oreign|
            [Tt]itle|trans[cC]hange|divine[nN]ame|
            scrip[Rr]ef|[Qq])
            (?P<attr>[^>]*)(?:(?P<end>/>)|>
            (?P<text>[\w\W]*?)
            </(?P=tag)>)
            ''', re.X)

# Seperates tag attributes into the attribute name and its value.
attr_regx = re.compile(r'''\s*(?P<name>[^=]+)="(?P<value>[^"]+)\s*"''')

title_regx = re.compile(r'''
            <(?P<tag>[Tt]itle)(?P<attr>[^>]*)>
            (?P<text>[\w\W]*?)
            </(?P=tag)>
            ''', re.X)

# Extracts the language from a StrongsReal uri.
strongs_regx = re.compile(r'''
        sword://StrongsReal(H|G)(ebrew|reek)/(\d+?)
        ''', re.I | re.X)

# Extracts the languages from a strongs number.
strongs_lang_regx = re.compile(r'((H|G)\d+)', re.I)

# Regex for formatting morphology definitions.
morph_regx = re.compile(r'''
        (?:<(?P<italic>hi)      # The opening highlight
        [^>]+?>                 # Tag attributes
        ([^<]+)                 # Tag text
        </(?P=italic)>          # Tag end
        ([^><]+)                # Break after text
        <(?P<break>lb)/>)       # Break tag
        ''', re.I | re.X)

added_regx = re.compile(r'''
        <transChange\s+type="added">
        ([^<]+)
        </transChange>
        ''', re.I | re.X)

# Splits a search query into quoted groups and non-quoted words.
search_regx = re.compile(r'''(?:"(?P<quoted>[^"]+)"|(?P<unquoted>[^\s"]+))''')

# Find paragraph markers.
paragraph_regx = re.compile(r'''marker="[^"]+"''')

# Split a reference into book, chapter, and verse groups.
# ref_regx = re.compile(r'''(?P<book>\d*\D+)(?P<chap>\d*):?(?P<verse>\d*)''')
ref_regx = re.compile(r'''
    (?P<book>\d?[^\d-]+)
    \s*
    (?P<chap>[\d,-]*)
    :
    (?P<verse>[\d,-]*)
    ''', re.X)

# The main bottle app.
bible_app = Bottle()
bible_app.error_handler = errors.handler

project_root = dirname(__file__)


def tag_func(match):
    """ Modify the verse text to italicize, uppercase and extract headings.

    """

    # Get a dictionary of the matched text each key is one of the labels
    # in the regex.
    match_dict = match.groupdict()

    # Set the text to '' empty string if it is None.
    if not match_dict['text']:
        match_dict['text'] = ''

    # Get the most used values out of the dictionary.
    tag = match_dict.get('tag', '').lower()
    attr = match_dict.get('attr', '')
    text = match_dict.get('text', '')

    # Use another regex to get a dictionary of all the name=value pairs
    # in the attributes of this tag.
    attr_dict = dict(attr_regx.findall(attr.lower()))

    # Depending on the tag return an appropriate replacement.
    if 'transchange' in tag:
        if attr_dict.get('type', '') == 'added':
            return '<span class="added-text">%s</span>' % text
    if 'divinename' in tag:
        return '<span class="divine-name">%s</span>' % text
    if 'title' in tag:
        text = tag_regx.sub(tag_func, text)
        return '<span class="title-text">%s</span> ' % text
    if 'foreign' in tag:
        if 'n' in attr_dict:
            match_dict.update(attr_dict)
            foreign_str = '<span class="foreign-text">{n}</span> {text}'
            return foreign_str.format(**match_dict)
    if 'milestone' in tag:
        if 'marker' in attr_dict:
            match_dict.update(attr_dict)
            marker = '<span class="paragraph-marker">{marker}</span> {text}'
            return marker.format(**match_dict)
    if 'w' == tag:
        word_span = '<span class="word" '
        lemma_str = 'data-lemma="{lemma}" '
        morph_str = 'data-morph="{morph}"'
        close_span = '>{text}</span>'

        attr_dict = dict(attr_regx.findall(attr))
        if 'lemma' in attr_dict:
            word_span += lemma_str
        if 'morph' in attr_dict:
            word_span += morph_str
        word_span += close_span
        match_dict.update(attr_dict)
        match_dict['text'] = tag_regx.sub(tag_func, match_dict['text'])
        return word_span.format(**match_dict)
    if 'seg' == tag:
        seg_span = '<span class="seg">%s</span>'
        return seg_span % tag_regx.sub(tag_func, match_dict['text'])
    if 'note' == tag:
        note_span = '<span class="note">{text}</span>'
        return note_span.format(**match_dict)
    if 'scripref' == tag:
        passage_href = 'href="/biblesearch/lookup?verse_refs=%s">%s</a>'
        passage_a = '<a class="verseref verselist" ' + passage_href
        passage_str = attr_dict.get('passage', '')
        ref_list = []
        last_book = ''
        for book, chapter, verse in ref_regx.findall(passage_str.strip()):
            book = book.strip()
            if not book:
                book = last_book
            last_book = book
            # Attempt to fix the book name to destinguish between Judges
            # and Jude.
            if book.lower() == 'jud':
                book = 'Judg'
                text = text.replace('Jud ', 'Judg ')
            ref_list.append('%s+%s:%s' % (book, chapter, verse))
        refs = ';'.join(ref_list)

        return passage_a % (refs, text)
    if 'q' == tag:
        q_span = '<span class="red-quote">%s</span>'
        match_dict['text'] = tag_regx.sub(tag_func, match_dict['text'])
        return q_span % match_dict['text']


def build_verselist(verse_refs: str) -> str:
    """ Build the verse list html from a string of verse references.

    """

    sorted_verse_list = make_valid(verse_refs)

    # Generate the result html.
    return template('verselist', output=sorted_verse_list,
                    count=len(sorted_verse_list))


def make_valid(verse_refs: str) -> list:
    """ Converts a string of verse references into a sorted list of valid
    references.

    """

    # Get a set of valid verse references asked for.
    verse_refs = sword_search.parse_verse_range(verse_refs)

    # Get a sorted list of the verse set, because it is faster to
    # lookup verses from a sorted list than from a randomized one.
    return sorted(verse_refs, key=sword_search.sort_key)


def find_paragraph(verse_refs: list, inclusive: bool=True,
                   default: str='') -> str:
    """ Find the first verse with a paragraph marker in the verse_refs list.

    """

    last_ref = start_ref = default

    for ref, verse_text in sword_search.VerseTextIter(iter(verse_refs),
                                                      strongs=True,
                                                      morph=True,
                                                      render='raw'):
        ref_match = ref_regx.search(ref)
        last_match = ref_regx.search(last_ref)

        # Assume paragraphs don't cross into other books.
        if last_ref and ref_match:
            book = ref_match.groupdict().get('book', '').strip()
            last_book = last_match.groupdict().get('book', '').strip()
            if last_book != book:
                return last_ref

        # Check for a paragraph in the verse text.
        if paragraph_regx.search(verse_text):
            return ref if inclusive else last_ref

        # Keep track of the last references, so the start of the next
        # paragraph or book is not returned.
        last_ref = ref

    # The default if no paragraph was found.
    return ref if inclusive else last_ref


def get_paragraph(verse_ref: str) -> str:
    """ Finds and returns the paragraph that verse_ref belongs to.

    """

    # Get verses on either side to try and find the entire paragraph.
    verse_list = sword_search.add_context([verse_ref], 200)
    sorted_verse_list = sorted(verse_list, key=sword_search.sort_key)

    # Get the index of this verse.
    verse_index = sorted_verse_list.index(verse_ref)

    # Get the first half including the current reference.
    first_half = reversed(sorted_verse_list[:verse_index + 1])

    # Get the second half not including the current reference.
    last_half = sorted_verse_list[verse_index + 1:]

    # Find the start of the paragraph by searching backwards from the
    # target reference.
    start_ref = find_paragraph(first_half, inclusive=True, default=verse_ref)

    # Search forwards to find the end of the paragraph (start of the
    # next paragraph).
    end_ref = find_paragraph(last_half, inclusive=False, default=verse_ref)

    # Make it a range.
    return '%s-%s' % (start_ref, end_ref)


def lookup_verses(verse_refs, search_terms: str='', context=0):
    """ Looks up the verses in verse_refs, highlights the search_terms, and
    returns a list of verses adding context verses on either side of each.

    """

    # Get a set of valid verse references asked for.
    verse_refs = sword_search.parse_verse_range(verse_refs)

    # Add the context.
    verse_list = sword_search.add_context(verse_refs, context)

    # Get a sorted list of the verse set, because it is faster to lookup
    # verses from a sorted list than from a randomized one.
    verse_list = sorted(verse_list, key=sword_search.sort_key)

    # Get all the strongs numbers out of the search terms.
    strongs_list = re.findall(r'(?i)((?:H|G)\d+)', search_terms)

    # Remove strongs numbers from search_terms.
    search_terms = re.sub(r'(?i)(H|G)\d+', '', search_terms).strip()

    # Split the search terms in to '"' quoted groups.
    terms_list = [''.join(i) for i in search_regx.findall(search_terms)]
    terms_list = [i for i in terms_list if not i.startswith('!')]

    # The results list.
    results_list = []

    # Highlight colors.
    highlight_text = '<span class="query-highlight">\\1</span>'

    # Build dictionary of verse references and text.
    for ref, verse_text in sword_search.VerseTextIter(iter(verse_list),
                                                      strongs=True, morph=True,
                                                      render='raw'):
        # Highlight only in the verses found during the search, not in
        # any of the context verses.
        if ref in verse_refs:
            # Build a regular expression that can be used to highlight
            # the search query in the output text.
            reel = build_highlight_regx(terms_list, False,
                                        color_tag='</?span[^>]*>',
                                        extra_tag='</span>')
            # Apply the highlight regex to highlight the verse text.
            verse_text = highlight_search_terms(verse_text, reel,
                                                highlight_text,
                                                color_tag='</?span[^>]*>')

        # Setup the verse text for highlighting and put the headings,
        # notes, and paragraph markers in.
        verse_text = tag_regx.sub(tag_func, verse_text)

        if results_list:
            last_ref = results_list[-1]['verseref']
            last_book, _ = last_ref.rsplit(' ', 1)
            cur_book, _ = ref.rsplit(' ', 1)

            # Put a break between books.
            if cur_book != last_book:
                results_list.append({
                    "highlight": False,
                    "verseref": '',
                    "versetext": '',
                })

        # Build a list of the results.
        results_list.append({
            "highlight": ref in verse_refs,
            "verseref": ref,
            "versetext": verse_text,
        })

    # Return the list of results and the list of strongs numbers in the
    # search query.
    return results_list


def do_search(search_terms: str='', min_range: str="Genesis",
              max_range: str="Revelation"):
    """ Performs a search for the terms in search_terms in the range
    min_range-max_range.

    Returns a sorted list of references.

    """

    # Make a valid range string.
    range_str = "%s-%s" % (min_range, max_range)

    # Split the search terms in to '"' quoted groups.
    terms_list = [''.join(i) for i in search_regx.findall(search_terms)]

    # Get a set of verse references that match the search criteria.
    bible_search = sword_search.Search(multiword=True)
    verse_set = bible_search.mixed_search(terms_list, range_str=range_str)

    # Build the return list of dictionaries.
    sorted_verse_list = sorted(verse_set, key=sword_search.sort_key)

    # Verse list cookie.
    response.set_cookie('search_terms', json.dumps(search_terms),
                        path='/biblesearch')

    return sorted_verse_list


def build_search_page(verse_list: str='', verses: str='',
                      strongs_morph: str='', context: int=0, min_range:
                      str="Genesis", max_range: str="Revelation", verse_ref:
                      str="Genesis 1:1", devotional_date: str="today",
                      search_terms: str=""):
    """ Build the search page and return a dictionary.

    """

    drop_list = [
        {
            'name': 'context_dropdown',
            'id': 'dcontext',
            'href': '#',
            'label': 'Context',
            'value': context
        },
        {
            'name': 'range_dropdown',
            'id': 'drange',
            'href': '#',
            'label': 'Range',
            'min_range': min_range,
            'max_range': max_range
        },
        {
            'name': 'lookup_dropdown',
            'id': 'dlookup',
            'href': '#',
            'label': 'Reference',
            'reference': verse_ref
        },
        {
            'name': 'devotional_dropdown',
            'id': 'ddevotional',
            'href': '#',
            'label': 'Devotional',
            'date': devotional_date
        },
    ]

    dropdowns = '\n'.join([template(i['name'], **i) for i in drop_list])

    return template('biblesearch', verse_list=verse_list, verses=verses,
                    strongs_morph=strongs_morph, dropdowns=dropdowns,
                    search_terms=html_escape(search_terms))


def build_page(reference_list: list=[], search_terms: str='', context: int=0):
    """ Build a webpage of the verses in reference list with the words and
    phrases in search_terms highlighted.  A context is added to each verse.

    """

    # Get cookie data to use in the page.
    min_range = json.loads(request.get_cookie('min_range', '"Genesis"'))
    max_range = json.loads(request.get_cookie('max_range', '"Revelation"'))
    verse_ref = json.loads(request.get_cookie('reference', '"Genesis 1:1"'))
    devotional_date = json.loads(request.get_cookie('devotional', '"today"'))

    if not search_terms:
        search_terms = json.loads(request.get_cookie('search_terms', '""'))

    if not reference_list and search_terms:
        reference_list = do_search(search_terms, min_range=min_range,
                                   max_range=max_range)

    if not context:
        context = json.loads(request.get_cookie('context', '0'))

    verses = lookup_verses(reference_list, search_terms, context)
    verses_html = template('verses', output=verses)

    # Build the result page.
    search_page_dict = {
        'verse_list': build_verselist(','.join(reference_list)),
        'verses': verses_html,
        'context': context,
        'min_range': min_range,
        'max_range': max_range,
        'verse_ref': verse_ref,
        'devotional_date': devotional_date,
        'search_terms': search_terms
    }

    return build_search_page(**search_page_dict)


# Handle static files
# @bible_app.route('/<path>')
@bible_app.route('/assets/<path:path>')
def handle_static(path):
    """ Serve up static file

    """

    # Return the requested static file.
    return static_file(path, join(project_root, "assets"))


@bible_app.route("/biblesearch/context")
def context():
    """ Set the context cookie and refresh the page.

    """

    context = request.query.get('context', 0, type=int)
    response.set_cookie('context', json.dumps(context), path='/biblesearch')

    return build_page(context=context)


@bible_app.route("/biblesearch/range")
def range():
    """ Set the range cookie and refresh the page.

    """

    # Get the new range.
    min_range = request.query.get('min', "Genesis").strip()
    max_range = request.query.get('max', "Revelation").strip()

    # Set the range cookies.
    response.set_cookie('min_range', json.dumps(min_range),
                        path='/biblesearch')
    response.set_cookie('max_range', json.dumps(max_range),
                        path='/biblesearch')

    # Re-search using the new range.
    search_terms = json.loads(request.get_cookie('search_terms', '""'))
    sorted_verse_list = do_search(search_terms, min_range, max_range)

    # Return the built page.
    return build_page(sorted_verse_list, search_terms)


@bible_app.route("/biblesearch/search")
@bible_app.route("/biblesearch/search<ext>")
def search(ext: str=''):
    """ Search the bible and return a list of verses in the requested range.

    """

    # Get the search query and the min and max ranges.
    search_terms = request.query.get('search', '').strip()

    # Don't even search if there is nothing to search for.
    if not search_terms:
        return {'html': ''}

    # Get cookie values as fallbacks.
    min_range = json.loads(request.get_cookie('min_range', '"Genesis"'))
    max_range = json.loads(request.get_cookie('max_range', '"Revelation"'))

    # Get the other query strings.
    min_range = request.query.get('min_range', min_range).strip()
    max_range = request.query.get('max_range', max_range).strip()

    # Set the range cookies.
    response.set_cookie('min_range', json.dumps(min_range),
                        path='/biblesearch')
    response.set_cookie('max_range', json.dumps(max_range),
                        path='/biblesearch')

    # Get a list of verses.
    sorted_verse_list = do_search(search_terms, min_range, max_range)

    if ext == '.json':
        return {'references': sorted_verse_list}
    else:
        return build_page(sorted_verse_list, search_terms)


@bible_app.route("/biblesearch/references")
@bible_app.route("/biblesearch/references<ext>")
def references(ext: str=''):
    """ Returns and html verse list of the requested references.

    """

    verse_refs = request.query.get('verse_refs', '').strip()
    verse_refs = verse_refs.replace('+', ' ')

    if ext == '.json':
        return {'html': build_verselist(verse_refs)}
    else:
        return build_page(make_valid(verse_refs))


@bible_app.route("/biblesearch/paragraph")
@bible_app.route("/biblesearch/paragraph<ext>")
def paragraph(ext: str=''):
    """ Attempts to find the start and end of the paragraph and returns all
    those verses.

    """

    verse_refs = request.query.get('start', '').strip()
    verse_refs = ';'.join(i.strip() for i in verse_refs.split(','))

    if not verse_refs:
        return {'html': ''}

    verse_list = make_valid(verse_refs)

    # Build a paragraph for each verse in the list.
    verse_refs = [get_paragraph(i) for i in verse_list]

    if ext == '.json':
        return {'references': verse_refs}
    else:
        return build_page(make_valid(verse_refs))


@bible_app.route("/biblesearch/lookup")
@bible_app.route("/biblesearch/lookup<ext>")
def lookup(ext: str=''):
    """ Lookup the verse reference and return the verse text and the verse text
    for all the verses in the requested context.

    """

    # Get the search_terms cookie as a fallback
    search_terms = json.loads(request.get_cookie('search_terms', '""'))

    # Get the context cookie as a fallback.
    context = json.loads(request.get_cookie('context', '0'))

    # Get the search terms, verse references, and context.
    search_terms = request.query.get('terms', search_terms).strip()
    verse_refs = request.query.get('verse_refs', '').strip()
    context = request.query.get('context', context, type=int)

    verse_refs = verse_refs.replace('+', ' ')

    # Set the context cookie.
    response.set_cookie('context', json.dumps(context), path='/biblesearch')

    if ext == '.json':
        # Lookup the verses in verse_refs.
        lines = lookup_verses(verse_refs, search_terms, context)

        # Generate the result html.
        result_str = template('verses', output=lines)

        # Return json data to the javascript.
        return {'html': result_str}
    else:
        return build_page(make_valid(verse_refs), search_terms, context)


@bible_app.route("/biblesearch/devotional")
@bible_app.route("/biblesearch/devotional<ext>")
def devotional(ext: str=''):
    """ Lookup the daily devotional.

    """

    # Get the search terms, verse references, and context.
    devotional_date = request.query.get('date', '').strip()

    # Record what devotional is being visited.
    response.set_cookie('devotional', json.dumps(devotional_date),
                        path='/biblesearch')

    # Lookup the specified daily devotional.
    if devotional_date.lower() == 'today':
        # Today is an alias for today's date.
        devotional_date = strftime('%m.%d')
    devotional_lookup = sword_search.Lookup('Daily')
    devotional_text = devotional_lookup.get_raw_text(devotional_date)

    # Make the verse lists at the end into links.
    devotional_text = tag_regx.sub(tag_func, devotional_text)

    # Return json data to the javascript.
    if ext == '.json':
        # Return json data to the javascript.
        return {'html': devotional_text}
    else:
        return build_search_page(verses=devotional_text)


@bible_app.route("/biblesearch/strongs")
@bible_app.route("/biblesearch/strongs<ext>")
def strongs(ext: str=''):
    """ Lookup the strongs/morph and return the appropriate text.

    """

    # Get the stripped query.
    strongs_nums = request.query.get('strongs', '').strip()
    morph_tags = request.query.get('morph', '').strip()

    # Don't even search if there is nothing to search for.
    if not strongs_nums and not morph_tags:
        return {'html': ''}

    # List of text to return.
    text_list = []

    # Lookup and convert strongs numbers.
    for strongs in strongs_nums.split():
        num, lang = strongs_lang_regx.findall(strongs)[0]

        # Figure out the language to use.
        language = 'Hebrew' if lang.upper() == 'H' else 'Greek'
        lookup = sword_search.Lookup(module_name='StrongsReal%s' % language)

        strongs_num = ('0' if lang == 'H' else '') + num[1:].lstrip('0')

        # Get the strongs definition.
        text = lookup.get_raw_text(strongs_num)

        # Fix strongs headings so their language can be detected by
        # the javascript.
        text_name = 'data-name="%s\\1"' % lang.upper()
        try:
            text = re.sub('name="([^"]+)"', text_name, text)
        except Exception as err:
            print("%s: (text: %s, text_name: %s, num: %s)" % (err, text, text_name, num))

        # Convert hrefs to lookup links, and append the converted
        # text to the return list.
        try:
            text = strongs_regx.sub('/biblesearch/strongs?strongs=\\1', text)
        except Exception as err:
            print("%s: (text: %s, num: %s)" % (err, text, num))

        text_list.append(text)
        text_list.append('<br/>')

    # Lookup and convert morph tags.
    for tag in morph_tags.split():
        morphtype, tag_name = tag.split(':')

        # Put the tag name as a heading.
        text_list.append('<br/><b>%s</b>' % tag_name)

        # Don't bother looking up hebrew morph tags.
        if morphtype.lower() != 'robinson':
            continue

        # Get the tag definition.
        lookup = sword_search.Lookup(module_name="Robinson")
        text = lookup.get_raw_text(tag_name.upper())

        # If the tag does not match the regular expression, just append
        # it to the text list.
        if not morph_regx.match(text):
            text_list.append(text)

        # Convert the raw tag text to valid html.
        for match in morph_regx.finditer(text):
            text_list.append('<i>{1}</i>{2}<br/>'.format(*match.groups()))

    strongs_morph_html = template('strongs', output=text_list)
    if ext == '.json':
        return {'html': strongs_morph_html}
    else:
        return build_search_page(strongs_morph=strongs_morph_html)


@bible_app.route("/biblesearch/books")
@bible_app.route("/biblesearch/books<ext>")
def books(ext: str=''):
    """ Search the census data and return a jsond dict of the results.

    """

    return {'array': sword_search.book_list}


# Handle the index page
@bible_app.route("/")
@bible_app.route("/<location>")
def index(location='biblesearch'):
    """ This "index" maps to the template index.html under the ./views/
    directory.

    """

    if location == 'biblesearch':
        if request.get_cookie('javascript'):
            print('javascript: yep')
            return build_search_page()
        else:
            print('javascript: nope')
            return build_page()

    return template(location)


if __name__ == "__main__":
    # Run under local testing server
    debug(True)
    run(bible_app, host="192.168.1.3", port=8080, reloader=True,
        server='tornado')
