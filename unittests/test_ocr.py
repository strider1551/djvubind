#! /usr/bin/env python3

import os
import sys
import unittest

# Check if we are working in the source tree or from an installed package and
# adjust the python path accordingly
loc = os.path.realpath(__file__)
loc = os.path.dirname(loc)
loc = os.path.join(loc+'/', '../djvubind')
loc = os.path.normpath(loc)
if os.path.isdir(loc):
    sys.path.insert(0, os.path.dirname(loc))

import djvubind.utils
import djvubind.ocr

class CuneiformTest(unittest.TestCase):
    """
    Tests for cuneiform related functions and classes
    """

    def test_01HocrParser(self):
        """
        Checks whether the parser gives the same output that was given in the
        past.  Checks for each supported version of cuneiform hocr output.
        """

        for filename in djvubind.utils.list_files('files/', 'cuneiform_in'):
            version = filename.split('_')[-1]

            handle = open(filename, 'r', encoding='utf8')
            infile = handle.read()
            handle.close()
            handle = open('files/cuneiform_out_'+version, 'r', encoding='utf8')
            outfile = handle.read()
            handle.close()

            parser = djvubind.ocr.hocrParser()
            parser.parse(infile)

            self.assertEqual(outfile, str(parser.boxing))


class TesseractTest(unittest.TestCase):
    """
    Tests for tesseract related functions and classes
    """

    def test_01TesseractParser(self):
        """
        Checks whether the parser gives the same output that was given in the
        past.  Checks for each supported version of tesseract output.
        """
        for filename in djvubind.utils.list_files('files/', extension='box'):
            version = filename.split('_')[-1]
            version = version[:-4]

            handle = open(filename, 'r', encoding='utf8')
            infilebox = handle.read()
            handle.close()
            handle = open(filename[:-3]+'txt', 'r', encoding='utf8')
            infiletxt = handle.read()
            handle.close()
            handle = open('files/tesseract_out_'+version, 'r', encoding='utf8')
            outfile = handle.read()
            handle.close()

            parser = djvubind.ocr.boxfileParser()
            parser.parse(infilebox, infiletxt)

            self.assertEqual(str(outfile), str(parser.boxing))

if __name__ == "__main__":
    unittest.main()
