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

import glob
import os
import pickle
import sys
import tempfile
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

# Move into the directory of the unittests
os.chdir(os.path.dirname(os.path.realpath(__file__)))

class TestOcr(unittest.TestCase):
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

            # For some reason the reference files were saved as plain-text, not
            # as pickled objects.
            # Because dictionaries are unordered, a simple assertEqual won't
            # work. "Dirty" fix is to check the length of the strings, which
            # gives us imperfect confidence that nothing has fallen apart.
            self.assertEqual(len(outfile), len(str(parser.boxing)))

    def test_05_tesseract_versions(self):
        for version in glob.glob('/opt/tesseract*'):
            with self.subTest(version=version):
                executable = version + '/bin/tesseract'
                djvubind.utils.get_executable_path = mock.Mock(return_value=executable)
                test_image = os.path.abspath('data/test_image_001.tif')
                config = os.path.abspath('data/hocr')
                origin = os.getcwd()
                with tempfile.TemporaryDirectory() as tempdir, djvubind.utils.ChangeDirectory(tempdir):
                    os.chdir(tempdir)
                    engine = djvubind.ocr.Tesseract(config)
                    engine.analyze(test_image)
                    os.chdir(origin)

if __name__ == '__main__':
    unittest.main()
