#! /usr/bin/env python3

#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
"""
Perform OCR operations using various engines.
"""

import difflib
import os
import re
import shutil
import sys

from html.parser import HTMLParser

from . import utils


class BoundingBox(object):
    """
    A rectangular portion of an image that contains something of value, such as
    text or a collection of smaller bounding boxes.

        Attributes:
            * perimeter (dictionary): xmax, xmin, ymax, ymin - integer values for the coordinates of the box.
            * children (list): Either other bounding boxes or single character strings of each letter in the word.
    """

    def __init__(self):
        self.perimeter = {'xmax':0, 'xmin':1000000000, 'ymax':0, 'ymin':1000000000}
        self.children = []

    def add_element(self, box):
        """
        Adds a smaller BoundingBox.

            Arguments:
                * box (BoundingBox):
        """

        if box.perimeter['xmin'] < self.perimeter['xmin']:
            self.perimeter['xmin'] = box.perimeter['xmin']
        if box.perimeter['ymin'] < self.perimeter['ymin']:
            self.perimeter['ymin'] = box.perimeter['ymin']
        if box.perimeter['xmax'] > self.perimeter['xmax']:
            self.perimeter['xmax'] = box.perimeter['xmax']
        if box.perimeter['ymax'] > self.perimeter['ymax']:
            self.perimeter['ymax'] = box.perimeter['ymax']
        self.children.append(box)

        return None

    def sanity_check(self):
        """
        Verifies that the x/y min values are not greater than the x/y max values.

            Raises:
                * ValueError: A min is greater than a max.  Either there was bad input nothing was added to the bounding box.
        """

        if (self.perimeter['xmin'] > self.perimeter['xmax']) or (self.perimeter['ymin'] > self.perimeter['ymax']):
            raise ValueError('Boxing information is impossible (x/y min exceed x/y max).')
        return None


class djvuWordBox(BoundingBox):
    """
    BoundingBox of a single word.  See :py:meth:`~djvubind.ocr.BoundingBox`
    """

    def __init__(self):
        BoundingBox.__init__(self)

    def add_character(self, boxing):
        """
        Adds a character to the BoundingBox.

            Arguments:
                * boxing (dictionary): char, xmax, xmin, ymax, ymin.
        """

        if boxing['xmin'] < self.perimeter['xmin']:
            self.perimeter['xmin'] = boxing['xmin']
        if boxing['ymin'] < self.perimeter['ymin']:
            self.perimeter['ymin'] = boxing['ymin']
        if boxing['xmax'] > self.perimeter['xmax']:
            self.perimeter['xmax'] = boxing['xmax']
        if boxing['ymax'] > self.perimeter['ymax']:
            self.perimeter['ymax'] = boxing['ymax']
        self.children.append(boxing['char'])

        return None

    def encode(self):
        self.sanity_check()
        return '(word {0} {1} {2} {3} "{4}")'.format(self.perimeter['xmin'], self.perimeter['ymin'], self.perimeter['xmax'], self.perimeter['ymax'], ''.join(self.children))

class djvuLineBox(BoundingBox):
    """
    BoundingBox of a single line.  See :py:meth:`~djvubind.ocr.BoundingBox`
    """

    def __init__(self):
        BoundingBox.__init__(self)

    def encode(self):
        self.sanity_check()
        line = '(line {0} {1} {2} {3}'.format(self.perimeter['xmin'], self.perimeter['ymin'], self.perimeter['xmax'], self.perimeter['ymax'])
        words = '\n    '.join([x.encode() for x in self.children])
        return line+'\n    '+words+')'


class djvuPageBox(BoundingBox):
    """
    BoundingBox of a single page.  See :py:meth:`~djvubind.ocr.BoundingBox`
    """

    def __init__(self):
        BoundingBox.__init__(self)

    def encode(self):
        self.sanity_check()
        page = '(page {0} {1} {2} {3}'.format(self.perimeter['xmin'], self.perimeter['ymin'], self.perimeter['xmax'], self.perimeter['ymax'])
        lines = '\n  '.join([x.encode() for x in self.children])
        return page+'\n  '+lines+')'


class hocrParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.boxing = []
        self.version = '0.8.0'
        self.data = ''

    def parse(self, data):
        self.data = data
        if "class='ocr_cinfo'" in self.data:
            self.version = '1.0.0'
        self.feed(data)
        return None

    def handle_starttag(self, tag, attrs):
        if self.version == '0.8.0':
            if (tag == 'br') or (tag == 'p'):
                if (len(self.boxing) > 0):
                    self.boxing.append('newline')
            elif (tag == 'span'):
                # Get the whole element (<span title="bbox n n n n">x</span>), not just the tag.
                element = {}
                element['start'] = self.data.find(self.get_starttag_text())
                element['end'] = self.data.find('>', element['start'])
                element['end'] = self.data.find('>', element['end']+1)
                element['end'] = element['end'] + 1
                element['text'] = self.data[element['start']:element['end']]
                pos = element['text'].find('>') + 1
                element['char'] = element['text'][pos:pos+1]

                # Figure out the boxing information from the title attribute.
                attrs = dict(attrs)['title']
                attrs = attrs.split()[1:]
                positions = {'xmin':int(attrs[0]), 'ymin':int(attrs[1]), 'xmax':int(attrs[2]), 'ymax':int(attrs[3])}
                positions['char'] = element['char']

                # Escape special characters
                subst = {'"': '\\"', "'":"\\'", '\\': '\\\\'}
                if positions['char'] in subst.keys():
                    positions['char'] = subst[positions['char']]
                self.boxing.append(positions)

                # A word break is indicated by a space after the </span> tag.
                if (self.data[element['end']:element['end']+1] == ' '):
                    self.boxing.append('space')
        elif self.version == '1.0.0':
            if (tag == 'br') or (tag == 'p'):
                if (len(self.boxing) > 0):
                    self.boxing.append('newline')
            elif (tag == 'span') and (('class', 'ocr_line') in attrs):
                # Get the whole element, not just the tag.
                element = {}
                element['complete'] = re.search('{0}(.*?)</span>'.format(self.get_starttag_text()), self.data).group(0)
                if "<span class='ocr_cinfo'" not in element['complete']:
                    return None
                element['text'] = re.search('">(.*)<span', element['complete']).group(1)
                element['text'] = re.sub('<[\w\/\.]*>', '', element['text'])
                element['text'] = utils.replace_html_codes(element['text'])
                element['positions'] = re.search('title="x_bboxes (.*) ">', element['complete']).group(1)
                element['positions'] = [int(item) for item in element['positions'].split()]

                i = 0
                for char in element['text']:
                    if element['positions'][i:i+4] == []:
                        continue
                    section = element['positions'][i:i+4]
                    positions = {'char':char, 'xmin':section[0], 'ymin':section[1], 'xmax':section[2], 'ymax':section[3]}
                    i = i+4

                    # A word break is indicated by a space (go figure).
                    if (char == ' '):
                        self.boxing.append('space')
                        continue

                    # Escape special characters
                    subst = {'"': '\\"', "'":"\\'", '\\': '\\\\'}
                    if positions['char'] in subst.keys():
                        positions['char'] = subst[positions['char']]
                    self.boxing.append(positions)

        return None


class Cuneiform(object):
    """
    Everything needed to work with the Cuneiform OCR engine.
    """

    def __init__(self, options):
        if not utils.is_executable('cuneiform'):
            raise OSError('Cuneiform is either not installed or not in the configured path.')

        self.options = options

    def analyze(self, filename):
        """
        Performs OCR analysis on the image and returns a djvuPageBox object.
        """

        status = utils.simple_exec('cuneiform -f hocr -o "{0}.hocr" {1} "{0}"'.format(filename, self.options))
        if status != 0:
            if status == -6:
                # Cuneiform seems to have a buffer flow on every other image, and even more without the --singlecolumn option.
                msg = '\nwrn: cuneiform encountered a buffer overflow on "{0}".'.format(os.path.split(filename)[1])
                msg = utils.color(msg, 'red')
                print(msg, file=sys.stderr)
            else:
                # Cuneiform crashes on blank images (exit status 1, message about failing to detect something).
                # They do not consider this behavior a bug. See https://bugs.launchpad.net/cuneiform-linux/+bug/445357
                # Also, it seems that <=cuneiform-0.7.0 can only process bmp images.
                msg = 'wrn: cuneiform crashed on "{0}".'.format(os.path.split(filename)[1])
                msg = utils.color(msg, 'red')
                print(msg, file=sys.stderr)
            return []

        with open('{0}.hocr'.format(filename), 'r', encoding='utf8') as handle:
            text = handle.read()

        # Clean up excess files.
        basename = os.path.split(filename)[1]
        basename = basename.split('.')[:-1]
        basename = '.'.join(basename)
        if os.path.isdir(basename+'_files'):
            shutil.rmtree(basename+'_files')
        os.remove(filename+'.hocr')

        parser = hocrParser()
        parser.parse(text)

        # Cuneiform hocr inverts the y-axis compared to what djvu expects.  The total height of the
        # image is needed to invert the values.
        height = int(utils.execute('identify -format %H "{0}"'.format(filename), capture=True))
        for entry in parser.boxing:
            if entry not in ['space', 'newline']:
                ymin, ymax = entry['ymin'], entry['ymax']
                entry['ymin'] = height - ymax
                entry['ymax'] = height - ymin

        return parser.boxing


class Tesseract(object):
    """
    Everything needed to work with the Tesseract OCR engine.
    """

    def __init__(self, options):
        if not utils.is_executable('tesseract'):
            raise OSError('Tesseract is either not installed or not in the configured path.')

        self.options = options

    def _correct_boxfile(self, boxdata, text):
        """
        Reconciles Tesseract's boxfile data with it's plain text data.

        The Tesseract boxfile does not include information like spacing, which is kinda important
        since we want to know where one word ends and the next begins.  The plain textfile will
        give that information, but sometimes its content does not exactly match the boxfile.  So we
        do our best to merge those two pieces of data together and "fix" the boxfile to match the
        textfile.
        """

        # Convert the boxing information into a plain text string with no bounding information.
        boxtext = ''
        for entry in boxdata:
            boxtext = boxtext + entry['char']
        # Remove spacing and newlines from the readable text because the boxing data doesn't have those.
        text = text.replace(' ', '')
        text = text.replace('\n', '')

        # Figure out what changes are needed, but don't do them immediately since it would
        # change the boxdata index and screw up the next action.
        diff = difflib.SequenceMatcher(None, boxtext, text)
        queu = []
        for action, a_start, a_end, b_start, b_end in diff.get_opcodes():
            entry = boxdata[a_start]
            item = {'action':action, 'target':entry, 'boxtext':boxtext[a_start:a_end], 'text':text[b_start:b_end]}
            queu.append(item)

        # Make necessary changes
        for change in queu:
            if (change['action'] == 'replace'):
                if (len(change['boxtext']) == 1) and (len(change['text']) == 1):
                    index = boxdata.index(change['target'])
                    boxdata[index]['char'] = change['text']
                elif (len(change['boxtext']) > 1) and (len(change['text']) == 1):
                    # Combine the boxing data
                    index = boxdata.index(change['target'])
                    new = {'char':'', 'xmin':0, 'ymin':0, 'xmax':0, 'ymax':0}
                    new['char'] = change['text']
                    new['xmin'] = min([x['xmin'] for x in boxdata[index:index+len(change['boxtext'])]])
                    new['ymin'] = min([x['ymin'] for x in boxdata[index:index+len(change['boxtext'])]])
                    new['xmax'] = min([x['xmax'] for x in boxdata[index:index+len(change['boxtext'])]])
                    new['ymax'] = min([x['ymax'] for x in boxdata[index:index+len(change['boxtext'])]])
                    del(boxdata[index:index+len(change['boxtext'])])
                    boxdata.insert(index, new)
                elif (len(change['boxtext']) == 1) and (len(change['text']) > 1):
                    # Use the same boxing data.  Will djvused complain that character
                    # boxes overlap?
                    index = boxdata.index(change['target'])
                    del(boxdata[index])
                    i = 0
                    for char in list(change['text']):
                        new = {'char':char, 'xmin':change['target']['xmin'], 'ymin':change['target']['ymin'], 'xmax':change['target']['xmax'], 'ymax':change['target']['ymax']}
                        boxdata.insert(index+i, new)
                        i = i + 1
                elif (len(change['boxtext']) > 1) and (len(change['text']) > 1):
                    if (len(change['boxtext']) == len(change['text'])):
                        index = boxdata.index(change['target'])
                        for char in list(change['text']):
                            boxdata[index]['char'] = char
                            index = index + 1
                    else:
                        # Delete the boxdata and replace with the plain text data
                        index = boxdata.index(change['target'])
                        deletions = boxdata[index:index+len(change['boxtext'])]
                        for target in deletions:
                            boxdata.remove(target)

                        i = 0
                        for char in list(change['text']):
                            new = {'char':char, 'xmin':change['target']['xmin'], 'ymin':change['target']['ymin'], 'xmax':change['target']['xmax'], 'ymax':change['target']['ymax']}
                            boxdata.insert(index+i, new)
                            i = i + 1
            elif (change['action'] == 'delete'):
                index = boxdata.index(change['target'])
                deletions = boxdata[index:index+len(change['boxtext'])]
                for target in deletions:
                    boxdata.remove(target)
            elif (change['action'] == 'insert'):
                # *Don't* use the boundaries of previous and next characters to guess at a boundary
                # box.  Things would be ugly if the next character happened to be on a new line.
                # Just duplicate the boundaries of the previous character
                index = boxdata.index(change['target'])
                i = 0
                for char in list(change['text']):
                    new = {'char':char, 'xmin':change['target']['xmin'], 'ymin':change['target']['ymin'], 'xmax':change['target']['xmax'], 'ymax':change['target']['ymax']}
                    boxdata.insert(index+i, new)
                    i = i + 1

        return boxdata

    def analyze(self, filename):
        """
        Performs OCR analysis on the image and returns a djvuPageBox object.
        """

        basename = os.path.split(filename)[1].split('.')[0]
        tesseractpath = utils.get_executable_path('tesseract')

        utils.execute('{0} "{1}" "{2}_box" {3} batch makebox'.format(tesseractpath, filename, basename, self.options))
        utils.execute('{0} "{1}" "{2}_txt" {3} batch'.format(tesseractpath, filename, basename, self.options))

        # tesseract-3.00 changed the .txt extension to .box so check which file was created.
        if os.path.exists(basename + '_box.txt'):
            boxfilename = basename + '_box.txt'
        else:
            boxfilename = basename + '_box.box'

        with open(boxfilename, 'r', encoding='utf8') as handle:
            boxfile = handle.read()
        with open(basename+'_txt.txt', 'r', encoding='utf8') as handle:
            text = handle.read()

        os.remove(boxfilename)
        os.remove(basename+'_txt.txt')

        data = []
        for line in boxfile.split('\n'):
            if (line == ''):
                continue
            line = line.split()
            if len(line) != 5 and len(line) != 6: # Tesseract 3 box file has 6 columns
                print('err: ocr.boxfileParser.parse_box(): The format of the boxfile is not what was expected.', file=sys.stderr)
                sys.exit(1)
            data.append({'char':line[0], 'xmin':int(line[1]), 'ymin':int(line[2]), 'xmax':int(line[3]), 'ymax':int(line[4])})
        boxfile = data

        boxfile = self._correct_boxfile(boxfile, text)
        textfile = [text[x:x+1] for x in range(len(text))]
        warning_count = 0

        boxing = []
        for x in range(len(textfile)):
            char = textfile[x]
            if (len(boxfile) == 0):
                break

            if (char == '\n'):
                if (len(boxing) > 0) and (boxing[-1] != 'newline'):
                    boxing.append('newline')
                continue
            elif (char == ' '):
                if (len(boxing) > 0) and (boxing[-1] != 'space'):
                    boxing.append('space')
                continue
            else:
                if (char != boxfile[0]['char']):
                    if (len(boxfile) >= 2) and (x+3 <= len(textfile)):
                        # Maybe this character isn't certain (e/o/c) and we should skip to the next character in both files.
                        if (textfile[x+1] == boxfile[1]['char']):
                            boxfile.pop(0)
                        # Maybe the boxfile inserted an extra character.
                        elif (textfile[x] == boxfile[1]['char']):
                            pass
                        elif (warning_count == 0):
                            warning_count = warning_count +1
                            msg = 'wrn: tesseract produced a significant mismatch between textual data and character position data on "{0}".  This may result in partial ocr content for this page.'.format(os.path.split(filename)[1])
                            msg = utils.color(msg, 'red')
                            print(msg, file=sys.stderr)
                    continue
                if (char in ['"', '\\']):
                    boxfile.pop(0)
                    continue
                boxing.append(boxfile.pop(0))

        return boxing


def engine(ocr_engine, options=''):
    """
    Provides an abstract factory to load the proper ocr engine class.  Any options
    would be the string equivalent to what could be used in a command line execution.
    """

    if ocr_engine == 'tesseract':
        return Tesseract(options)
    elif ocr_engine == 'cuneiform':
        return Cuneiform(options)
    else:
        raise ValueError('The requested ocr engine ({0}) is not supported.'.format(ocr_engine))

def translate(boxing):
    """
    Translate djvubind's internal boxing information into a djvused format.

    .. warning::
       This function will eventually migrater to djvubind.encode
    """

    page = djvuPageBox()
    line = djvuLineBox()
    word = djvuWordBox()
    for entry in boxing:
        if entry == 'newline':
            if (line.children != []):
                if (word.children != []):
                    line.add_element(word)
                page.add_element(line)
            line = djvuLineBox()
            word = djvuWordBox()
        elif entry == 'space':
            if (word.children != []):
                line.add_element(word)
            word = djvuWordBox()
        else:
            word.add_character(entry)
    if (word.children != []):
        line.add_element(word)
    if (line.children != []):
        page.add_element(line)

    if (page.children != []):
        return page.encode()
    else:
        return ''
