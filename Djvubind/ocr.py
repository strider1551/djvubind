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

import difflib
import os
import shutil
import string
import sys

from html.parser import HTMLParser

import Djvubind.utils


class hocrParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.boxing = []

    def parse(self, data):
        self.data = data
        self.feed(data)
        return None

    def handle_starttag(self, tag, attrs):
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

            # Disregard punction.  Note that a single quote might be an apostrophy and not a quote.
            if element['char'] not in ['.', ',', '!', '?', ':', ';', '"']:
                self.boxing.append(positions)

            # A word break is indicated by a space after the </span> tag.
            if (self.data[element['end']:element['end']+1] == ' '):
                self.boxing.append('space')

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
            if len(line) != 5:
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
                    print('case 01')
                    index = boxdata.index(change['target'])
                    boxdata[index]['char'] = change['text']
                elif (len(change['boxtext']) > 1) and (len(change['text']) == 1):
                    # Combine the boxing data
                    print('case 02')
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
                    print('case 03')
                    index = boxdata.index(change['target'])
                    del(boxdata[index])
                    i = 0
                    for char in list(change['text']):
                        new = {'char':char, 'xmin':change['target']['xmin'], 'ymin':change['target']['ymin'], 'xmax':change['target']['xmax'], 'ymax':change['target']['ymax']}
                        boxdata.insert(index+i, new)
                        i = i + 1
                elif (len(change['boxtext']) > 1) and (len(change['text']) > 1):
                    if (len(change['boxtext']) == len(change['text'])):
                        print('case 04')
                        index = boxdata.index(change['target'])
                        for char in list(change['text']):
                            boxdata[index]['char'] = char
                            index = index + 1
                    else:
                        print('err: Djvubind.ocr.boxfileParser.resolve(): Complex replacement that shouldn\'t happen in real life.', file=sys.err)
                        pass
            elif (change['action'] == 'delete'):
                print('case 06')
                index = boxdata.index(change['target'])
                deletions = boxdata[index:index+len(change['boxtext'])]
                for target in deletions:
                    boxdata.remove(target)
            elif (change['action'] == 'insert'):
                # *Don't* use the boundaries of previous and next characters to guess at a boundary
                # box.  Things would be ugly if the next character happened to be on a new line.
                # Just duplicate the boundaries of the previous character
                print('case 07')
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
                            msg = Djvubind.utils.color(msg, 'red')
                            print(msg, file=sys.stderr)
                    continue
                if (char in ['.', ',', '!', '?', ':', ';', '"']):
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


def ocr(image, engine='tesseract', options={'tesseract':'-l eng', 'cuneiform':'--singlecolumn'}):
    if (engine == 'cuneiform'):
        status = Djvubind.utils.simple_exec('cuneiform -f hocr -o "{0}.hocr" {1} "{0}"'.format(image, options['cuneiform']))
        if status != 0:
            if status == -6:
                # Cuneiform seems to have a buffer flow on every other image, and even more without the --singlecolumn option.
                msg = '\nwrn: cuneiform encountered a buffer overflow on "{0}".  Ocr on this image will be done with tesseract.'.format(os.path.split(image)[1])
                msg = Djvubind.utils.color(msg, 'red')
                print(msg, file=sys.stderr)
            else:
                # Cuneiform crashes on blank images (exit status 1, message about failing to detect something).
                # They do not consider this behavior a bug. See https://bugs.launchpad.net/cuneiform-linux/+bug/445357
                # Also, it seems that <=cuneiform-0.7.0 can only process bmp images.
                msg = 'wrn: cuneiform crashed on "{0}".  Ocr on this image will be done with tesseract.'.format(os.path.split(image)[1])
                msg = Djvubind.utils.color(msg, 'red')
                print(msg, file=sys.stderr)
            return ocr(image, engine='tesseract')

        with open('{0}.hocr'.format(image), 'r', encoding='utf8') as handle:
            text = handle.read()

        # Sometimes filenames have multiple periods, especially when using tesseract
        # and 'image.tiff' was copied to 'image.tiff.tif'
        basename = os.path.split(image)[1]
        basename = basename.split('.')[:-1]
        basename = '.'.join(basename)
        if os.path.isdir(basename+'_files'):
            shutil.rmtree(basename+'_files')
        os.remove(image+'.hocr')

        parser = hocrParser()
        parser.parse(text)

        # Cuneiform hocr inverts the y-axis compared to what djvu expects.  The total height of the
        # image is needed to invert the values.  Better to get it now once rather than in the loop
        # where it is used.
        height = int(Djvubind.utils.execute('identify -format %H "{0}"'.format(image), capture=True))

    elif (engine == 'tesseract'):
        basename = os.path.split(image)[1].split('.')[0]
        status_a = Djvubind.utils.simple_exec('tesseract "{0}" "{1}_box" {2} batch makebox'.format(image, basename, options['tesseract']))
        status_b = Djvubind.utils.simple_exec('tesseract "{0}" "{1}_txt" {2} batch'.format(image, basename, options['tesseract']))
        if (status_a != 0) or (status_b != 0):
            msg = 'wrn: Tesseract failed on "{0}".  There will be no ocr for this page.'.format(os.path.split(image)[1])
            msg = Djvubind.utils.color(msg, 'red')
            print(msg, file=sys.stderr)
            return ''

        with open(basename+'_box.txt', 'r', encoding='utf8') as handle:
            boxfile = handle.read()
        with open(basename+'_txt.txt', 'r', encoding='utf8') as handle:
            textfile = handle.read()
        os.remove(basename+'_box.txt')
        os.remove(basename+'_txt.txt')

        parser = boxfileParser()
        parser.image = image
        parser.parse(boxfile, textfile)

    else:
        print('err: ocr.ocr(): Specified ocr engine is not supported.', file=sys.stderr)
        sys.exit(1)

    page = djvuPageBox()
    line = djvuLineBox()
    word = djvuWordBox()
    for entry in parser.boxing:
        if entry == 'newline':
            if (line.words != []):
                page.add_line(line)
            line = djvuLineBox()
            word = djvuWordBox()
        elif entry == 'space':
            if (word.word != ''):
                line.add_word(word)
            word = djvuWordBox()
        else:
            if (engine == 'cuneiform'):
                ymin, ymax = entry['ymin'], entry['ymax']
                entry['ymin'] = height - ymax
                entry['ymax'] = height - ymin
            word.add_char(entry)

    if (page.lines != []):
        return page.encode()
    else:
        return ''
