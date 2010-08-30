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

    def input(self, data):
        self.data = data

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

def parse_box(boxfile):
    """
    Parse the tesseract positional information into a two dimensional array.
    [[char, x_min, y_min, x_max, y_max], ...]
    """
    data = []

    try:
        with open(boxfile, 'r', encoding='utf8') as handle:
            for line in handle:
                line = line.split()
                if len(line) != 5:
                    print('err: ocr.parse_box(): The format of the boxfile is not what was expected.', file=sys.stderr)
                    sys.exit(1)
                data.append([line[0], int(line[1]), int(line[2]), int(line[3]), int(line[4])])
    except IOError:
        print('err: ocr.parse_box(): Problem with file input/output: "{0}"'.format(boxfile), file=sys.stderr)
        sys.exit(1)

    return data

def get_text(image):
    """
    Runs tesseract on the given image, then process the data into a format that djvu will understand.
    """
    if image[-4:] != '.tif':
        print('err: ocr.get_text(): tesseract is very picky and demands that the image carry a .tif extension.', file=sys.stderr)
        sys.exit(1)

    Djvubind.utils.execute('tesseract {0} page_box -l eng batch makebox &> /dev/null'.format(image))
    Djvubind.utils.execute('tesseract {0} page_txt -l eng batch &> /dev/null'.format(image))

    boxfile = parse_box('page_box.txt')

    try:
        with open('page_txt.txt', 'r', encoding='utf8') as handle:
            page_xn = 100000
            page_xx = 100000
            page_yn = 0
            page_yx = 0
            line_buff = ''

            for line in handle:
                line = line.strip()
                if line == '\n' or line == '':
                    continue
                line = line.strip()
                words = line.split()
                word_buff = ''
                for word in words:
                    word_xn = 100000
                    word_xx = 100000
                    word_yn = 0
                    word_yx = 0
                    for char in word:
                        if len(boxfile) == 0:
                            break
                        # Why exactly is it important that the character be printable?  I
                        # think this was a carry-over from the original perl script.  It
                        # stays for now, but *seriously* needs to be experimented with.
                        if char not in string.printable:
                            if char == boxfile[0][0]:
                                boxfile.pop()
                            continue
                        # How does it even happen that page_txt and page_box don't agree
                        # character for character... again, *seriously* needs to be
                        # investigated by manually comparing the files.
                        if char != boxfile[0][0]:
                            if len(boxfile) == 1:
                                break
                            if char == boxfile[1][0]:
                                #print('wrn: mismatch between ocr text and ocr position (fixed)')
                                boxfile.pop(0)
                            else:
                                pass
                                #print('wrn: significant mismatch between ocr text and ocr position')
                                #print('{0}, {1}, {2}'.format(word, char, boxfile[0][0]))
                        data = boxfile.pop(0)

                        if word_xn > data[1]:
                            word_xn = data[1]
                        if word_xx > data[2]:
                            word_xx = data[2]
                        if word_yn < data[3]:
                            word_yn = data[3]
                        if word_yx < data[4]:
                            word_yx = data[4]

                        if page_xn > data[1]:
                            page_xn = data[1]
                        if page_xx > data[2]:
                            page_xx = data[2]
                        if page_yn < data[3]:
                            page_yn = data[3]
                        if page_yx < data[4]:
                            page_yx = data[4]
                    # Bad things happen if the boundary box is screwed up
                    if (word_xn == 100000) and (word_yn == 0):
                        continue
                    word = word.replace('"', '')
                    word = word.replace("'", "")
                    word = word.replace('\\', '')
                    word_buff = '%s\n  (word %s %s %s %s "%s")' % (word_buff, word_xn, word_xx, word_yn, word_yx, word)
                # Bad things happen if the line has no words
                if (word_xn == 100000) and (word_yn == 0):
                    continue
                else:
                    line_buff = '%s\n (line %s %s %s %s\n%s)' % (line_buff, word_xn, word_xx, word_yn, word_yx, word_buff)
            page_buff = '(page %s %s %s %s\n%s)\n' % (page_xn, page_xx, page_yn, page_yx, line_buff)
    except IOError:
        print('err: ocr.get_text(): Problem with file input/output: "page_txt.txt"', file=sys.stderr)
        sys.exit(1)

    os.remove('page_box.txt')
    os.remove('page_txt.txt')

    return page_buff


def ocr(image, engine='tesseract'):
    page = djvuPageBox()

    if (engine == 'cuneiform'):
        try:
            status = Djvubind.utils.execute('cuneiform -f "hocr" -o "{0}.hocr" --singlecolumn "{0}" &> /dev/null'.format(image))
            if status == 134:
                # Cuneiform seems to have a buffer flow on every other image, and even more without the --singlecolumn option.
                msg = 'wrn: cuneiform encountered a buffer overflow on "{0}".  Ocr on this image will be done with tesseract.'.format(os.path.split(image)[1])
                msg = Djvubind.utils.color(msg, 'red')
                print(msg, file=sys.stderr)
                return ocr(image, engine='tesseract')
        except:
            # Cuneiform crashes on blank images (exit status 1, message about failing to detect something).
            # They do not consider this behavior a bug. See https://bugs.launchpad.net/cuneiform-linux/+bug/445357
            msg = 'wrn: cuneiform crashed on "{0}", which likely means the image is blank.  No ocr will be done.'.format(os.path.split(image)[1])
            msg = Djvubind.utils.color(msg, 'red')
            print(msg, file=sys.stderr)
            with open('{0}.hocr'.format(image), 'w', encoding='utf8') as handle:
                handle.write('')

        with open('{0}.hocr'.format(image), 'r', encoding='utf8') as handle:
            text = handle.read()

        parser = hocrParser()
        parser.input(text)
        parser.feed(text)

        # Cuneiform hocr inverts the y-axis compared to what djvu expects.  The total height of the
        # image is needed to invert the values.  Better to get it now once rather than in the loop
        # where it is used.
        height = int(Djvubind.utils.execute('identify -format %H "{0}"'.format(image), capture=True))

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
                # Invert the y-axis
                ymin, ymax = entry['ymin'], entry['ymax']
                entry['ymin'] = height - ymax
                entry['ymax'] = height - ymin
                word.add_char(entry)

        basename = os.path.split(image)[1].split('.')[0]
        if os.path.isdir(basename+'_files'):
            shutil.rmtree(basename+'_files')
        os.remove(image+'.hocr')

    elif (engine == 'tesseract'):
        # Run the old code for now.  In future, rework to use djvuPageBox
        return get_text(image)

    else:
        print('err: ocr.ocr(): Specified ocr engine is not supported.', file=sys.stderr)
        sys.exit(1)

    if (page.lines != []):
        return page.encode()
    else:
        return ''
