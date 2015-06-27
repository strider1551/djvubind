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
import sys
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

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


class TestUtils(unittest.TestCase):
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

    def test_05_counter(self):
        """
        Sanity check for utils.counter()
        """

        counter = djvubind.utils.counter(start=1, roman=True)
        self.assertEqual(next(counter), "i")
        self.assertEqual(next(counter), "ii")

        counter = djvubind.utils.counter(start=1)
        self.assertEqual(next(counter), "1")
        self.assertEqual(next(counter), "2")

        counter = djvubind.utils.counter(start=1, incriment=2)
        self.assertEqual(next(counter), "1")
        self.assertEqual(next(counter), "3")

        counter = djvubind.utils.counter(start=1, end=3)
        self.assertEqual(next(counter), "1")
        self.assertEqual(next(counter), "2")
        self.assertEqual(next(counter), "3")
        with self.assertRaises(StopIteration):
            next(counter)

    def test_06_contents(self):
        """
        Sanity check for utils.list_files()
        """

        with mock.patch('os.listdir') as mocked_listdir, \
             mock.patch('os.path.isfile') as mocked_isfile:
            mocked_listdir.return_value = ['test.tif', 'test.jpg', 'test.sh', 'test', 'skip', 'skip.jpg']
            mocked_isfile.return_value = True

            tmp = djvubind.utils.list_files()
            self.assertEqual(tmp, ['./skip', './skip.jpg', './test', './test.jpg', './test.sh', './test.tif'])
            tmp = djvubind.utils.list_files(contains="test")
            self.assertEqual(tmp, ['./test', './test.jpg', './test.sh', './test.tif'])
            tmp = djvubind.utils.list_files(extension="tif")
            self.assertEqual(tmp, ['./test.tif'])
            tmp = djvubind.utils.list_files(contains="test", extension="jpg")
            self.assertEqual(tmp, ['./test.jpg'])

if __name__ == '__main__':
    unittest.main()
