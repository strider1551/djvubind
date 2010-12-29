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
                element['positions'] = re.search('title="x_bboxes (.*) ">', element['complete']).group(1)
                element['positions'] = [int(item) for item in element['positions'].split()]

                i = 0
                for char in element['text']:
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


class boxfileParser():

    def __init__(self):
        self.boxing = []
        self.image = ''

    def parse_box(self, boxfile):
        """
        Parse the tesseract positional information.
        """
        data = []

        for line in boxfile.split('\n'):
            if (line == ''):
                continue
            line = line.split()
            if len(line) != 5 and len(line) != 6: # Tesseract 3 box file has 6 columns
                print('err: ocr.boxfileParser.parse_box(): The format of the boxfile is not what was expected.', file=sys.stderr)
                sys.exit(1)

            data.append({'char':line[0], 'xmin':int(line[1]), 'ymin':int(line[2]), 'xmax':int(line[3]), 'ymax':int(line[4])})

        return data

    def resolve(self, boxdata, text):
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

    def parse(self, boxfile, text):
        boxfile = self.parse_box(boxfile)
        boxfile = self.resolve(boxfile, text)
        textfile = [text[x:x+1] for x in range(len(text))]
        warning_count = 0

        for x in range(len(textfile)):
            char = textfile[x]
            if (len(boxfile) == 0):
                break

            if (char == '\n'):
                if (len(self.boxing) > 0) and (self.boxing[-1] != 'newline'):
                    self.boxing.append('newline')
                continue
            elif (char == ' '):
                if (len(self.boxing) > 0) and (self.boxing[-1] != 'space'):
                    self.boxing.append('space')
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
                            msg = 'wrn: tesseract produced a significant mismatch between textual data and character position data on "{0}".  This may result in partial ocr content for this page.'.format(os.path.split(self.image)[1])
                            msg = utils.color(msg, 'red')
                            print(msg, file=sys.stderr)
                    continue
                if (char in ['"', '\\']):
                    boxfile.pop(0)
                    continue
                self.boxing.append(boxfile.pop(0))

        return None


class djvuWordBox:
    def __init__(self):
        self.xmax = 0
        self.xmin = 100000
        self.ymax = 0
        self.ymin = 100000
        self.word = ''

    def add_char(self, boxing):
        if boxing['xmin'] < self.xmin:
            self.xmin = boxing['xmin']
        if boxing['ymin'] < self.ymin:
            self.ymin = boxing['ymin']
        if boxing['xmax'] > self.xmax:
            self.xmax = boxing['xmax']
        if boxing['ymax'] > self.ymax:
            self.ymax = boxing['ymax']
        self.word = self.word + boxing['char']
        return None

    def encode(self):
        if (self.xmin > self.xmax) or (self.ymin > self.ymax):
            print('err: ocr.djvuWordBox(): Boxing information is impossible (x/y min exceed x/y max).')
            sys.exit(1)
        return '(word {0} {1} {2} {3} "{4}")'.format(self.xmin, self.ymin, self.xmax, self.ymax, self.word)


class djvuLineBox:
    def __init__(self):
        self.xmax = 0
        self.xmin = 100000
        self.ymax = 0
        self.ymin = 100000
        self.words = []

    def add_word(self, word_box):
        if word_box.xmin < self.xmin:
            self.xmin = word_box.xmin
        if word_box.ymin < self.ymin:
            self.ymin = word_box.ymin
        if word_box.xmax > self.xmax:
            self.xmax = word_box.xmax
        if word_box.ymax > self.ymax:
            self.ymax = word_box.ymax
        self.words.append(word_box)

    def encode(self):
        if (self.xmin > self.xmax) or (self.ymin > self.ymax):
            print('err: ocr.djvuLineBox(): Boxing information is impossible (x/y min exceed x/y max).')
            sys.exit(1)
        line = '(line {0} {1} {2} {3}'.format(self.xmin, self.ymin, self.xmax, self.ymax)
        words = '\n    '.join([x.encode() for x in self.words])
        return line+'\n    '+words+')'


class djvuPageBox:
    def __init__(self):
        self.xmax = 0
        self.xmin = 100000
        self.ymax = 0
        self.ymin = 100000
        self.lines = []

    def add_line(self, line_box):
        if line_box.xmin < self.xmin:
            self.xmin = line_box.xmin
        if line_box.ymin < self.ymin:
            self.ymin = line_box.ymin
        if line_box.xmax > self.xmax:
            self.xmax = line_box.xmax
        if line_box.ymax > self.ymax:
            self.ymax = line_box.ymax
        self.lines.append(line_box)

    def encode(self):
        if (self.xmin > self.xmax) or (self.ymin > self.ymax):
            print('err: ocr.djvuPageBox(): Boxing information is impossible (x/y min exceed x/y max).')
            sys.exit(1)
        page = '(page {0} {1} {2} {3}'.format(self.xmin, self.ymin, self.xmax, self.ymax)
        lines = '\n  '.join([x.encode() for x in self.lines])
        return page+'\n  '+lines+')'


class OCR:
    """
    An intelligent ocr process that can work with numerous ocr engines.
    """

    def __init__(self, opts):
        self.opts = opts

        self.dep_check()

    def _cuneiform(self, filename):
        """"
        Process the filename with cuneiform.
        """

        status = utils.simple_exec('cuneiform -f hocr -o "{0}.hocr" {1} "{0}"'.format(filename, self.opts['cuneiform_options']))
        if status != 0:
            if status == -6:
                # Cuneiform seems to have a buffer flow on every other image, and even more without the --singlecolumn option.
                msg = '\nwrn: cuneiform encountered a buffer overflow on "{0}".  Ocr on this image will be done with tesseract.'.format(os.path.split(filename)[1])
                msg = utils.color(msg, 'red')
                print(msg, file=sys.stderr)
            else:
                # Cuneiform crashes on blank images (exit status 1, message about failing to detect something).
                # They do not consider this behavior a bug. See https://bugs.launchpad.net/cuneiform-linux/+bug/445357
                # Also, it seems that <=cuneiform-0.7.0 can only process bmp images.
                msg = 'wrn: cuneiform crashed on "{0}".  Ocr on this image will be done with tesseract.'.format(os.path.split(filename)[1])
                msg = utils.color(msg, 'red')
                print(msg, file=sys.stderr)
            return self._tesseract(filename)

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

    def _tesseract(self, filename):
        """
        Process the filename with tesseract.
        """

        basename = os.path.split(filename)[1].split('.')[0]
        tesseractpath = utils.get_executable_path('tesseract')

        status_a = utils.simple_exec('{0} "{1}" "{2}_box" {3} batch makebox'.format(tesseractpath, filename, basename, self.opts['tesseract_options']))
        status_b = utils.simple_exec('{0} "{1}" "{2}_txt" {3} batch'.format(tesseractpath, filename, basename, self.opts['tesseract_options']))
        if (status_a != 0) or (status_b != 0):
            msg = 'wrn: Tesseract failed on "{0}".  There will be no ocr for this page.'.format(os.path.split(filename)[1])
            msg = utils.color(msg, 'red')
            print(msg, file=sys.stderr)
            return []

        # tesseract-3.00 changed the .txt extension to .box so check which file was created.
        if os.path.exists(basename + '_box.txt'):
            boxfilename = basename + '_box.txt'
        else:
            boxfilename = basename + '_box.box'

        with open(boxfilename, 'r', encoding='utf8') as handle:
            boxfile = handle.read()
        with open(basename+'_txt.txt', 'r', encoding='utf8') as handle:
            textfile = handle.read()

        os.remove(boxfilename)
        os.remove(basename+'_txt.txt')

        parser = boxfileParser()
        parser.image = filename
        parser.parse(boxfile, textfile)

        return parser.boxing

    def analyze_image(self, filename):
        """
        Retrieve boxing information.  This should return a list of each character
        and it's information in dictionary form, or 'newline' or 'space'. E.g.:
        [{char:'a', 'xmin':12, 'ymin':50, 'xmax':15, 'ymax':53}, 'space', ...]
        """

        if self.opts['ocr_engine'] == 'tesseract':
            boxing = self._tesseract(filename)
        elif self.opts['ocr_engine'] == 'cuneiform':
            boxing = self._cuneiform(filename)
        else:
            msg = 'wrn: ocr engine "{0}" is not supported.'.format(self.opts['ocr_engine'])
            print(msg, file=sys.stderr)
            sys.exit(1)

        return boxing

    def dep_check(self):
        """
        Check for ocr engine availability.
        """

        engine = self.opts['ocr_engine']

        if not utils.is_executable(engine):
            msg = 'wrn: ocr engine "{0}" is not installed. Tesseract will be used instead.'.format(engine)
            msg = utils.color(msg, 'red')
            print(msg, file=sys.stderr)
            self.opts['ocr_engine'] = 'tesseract'
        if (engine != 'tesseract') and (not utils.is_executable('tesseract')):
            msg = 'err: ocr engine "{0}" is not installed.  Tesseract is a mandatory dependency.'.format('tesseract')
            print(msg, file=sys.stderr)
            sys.exit(1)

        return None

    def translate(self, boxing):
        """
        Translate djvubind's internal boxing information into a djvused format.
        """

        page = djvuPageBox()
        line = djvuLineBox()
        word = djvuWordBox()
        for entry in boxing:
            if entry == 'newline':
                if (line.words != []):
                    if (word.word != ''):
                        line.add_word(word)
                    page.add_line(line)
                line = djvuLineBox()
                word = djvuWordBox()
            elif entry == 'space':
                if (word.word != ''):
                    line.add_word(word)
                word = djvuWordBox()
            else:
                word.add_char(entry)
        if (word.word != ''):
            line.add_word(word)
        if (line.words != []):
            page.add_line(line)

        if (page.lines != []):
            return page.encode()
        else:
            return ''
