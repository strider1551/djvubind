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
#       Foundation, Inc.

import os
import pickle
import sys
import unittest

# Adjust the python path to use live code and not an installed version
loc = os.path.realpath(__file__)
loc = os.path.dirname(loc)
loc = os.path.join(loc+'/', '../djvubind')
loc = os.path.normpath(loc)
sys.path.insert(0, os.path.dirname(loc))

import djvubind.ocr
import djvubind.utils

# Move into the directory of the unittests
os.chdir(os.path.dirname(os.path.realpath(__file__)))

class Ocr(unittest.TestCase):
    """
    Tests for djvubind/ocr.py
    """


    def test_01_impossible_bounding_box(self):
        box = djvubind.ocr.BoundingBox()
        self.assertRaises(ValueError, box.sanity_check)

    def test_02_translate_check(self):
        with open('data/Ocr.translate_check_in.pickle', 'rb') as data:
            data_in = pickle.load(data)
        with open('data/Ocr.translate_check_out.pickle', 'rb') as data:
            data_out = pickle.load(data)
        self.assertEqual(data_out, djvubind.ocr.translate(data_in))

    def test_03_non_supported_engine(self):
        self.assertRaises(ValueError, djvubind.ocr.engine, 'fake-engine')

    def test_04_hocr_parser(self):
        """
        Checks whether the parser gives the same output that was given in the
        past.  Checks for each supported version of cuneiform hocr output.
        """

        for filename in djvubind.utils.list_files('data/', 'cuneiform_in'):
            version = filename.split('_')[-1]

            handle = open(filename, 'r', encoding='utf8')
            infile = handle.read()
            handle.close()
            handle = open('data/cuneiform_out_'+version, 'r', encoding='utf8')
            outfile = handle.read()
            handle.close()

            parser = djvubind.ocr.hocrParser()
            parser.parse(infile)

            self.assertEqual(outfile, str(parser.boxing))


class Utils(unittest.TestCase):
    """
    Tests for djvubind/utils.py
    """

    def test_01_add_color(self):
        """
        Checks for addition of proper ansi escape sequences.  If the platform
        is windows, the original text should be returned with no ansi sequences.
        """

        colors = {'pink': '\033[95mpink\033[0m',
                  'blue': '\033[94mblue\033[0m',
                  'green': '\033[92mgreen\033[0m',
                  'yellow': '\033[93myellow\033[0m',
                  'red': '\033[91mred\033[0m'}
        for color in colors.keys():
            out = djvubind.utils.color(color, color)
            if sys.platform.startswith('win'):
                self.assertEqual(color, out)
            else:
                self.assertEqual(colors[color], out)

    def test_02_add_bad_color(self):
        """
        Checks that no modification is made with an unsupported color.
        """
        text = 'Some text here.'
        out = djvubind.utils.color(text, 'mauve')
        self.assertEqual(text, out)

    def test_03_arabic_to_roman_samples(self):
        """
        Checks for the correct conversion of some sample numbers.
        """
        numbers = {'vi':6, 'x':10, 'iv':4, 'xlix':49}
        for roman in numbers.keys():
            out = djvubind.utils.arabic_to_roman(numbers[roman])
            self.assertEqual(roman, out)

    def test_04_arabic_to_roman_non_integer(self):
        """
        Checks that a TypeError is raised for non-integer arguments.
        """
        self.assertRaises(TypeError, djvubind.utils.arabic_to_roman, '5')

if __name__ == "__main__":
    unittest.main()
