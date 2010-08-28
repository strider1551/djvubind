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
import string
import sys

import Djvubind.utils

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
