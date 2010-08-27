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
import shutil
import sys

import Djvubind.ocr
import Djvubind.utils

class Book:
    def __init__(self):
        self.pages = []
        self.dpi = None

    def insert_page(self, path):
        self.pages.append(Page(path))
        return None

    def analyze(self, no_ocr=False):
        for index in range(len(self.pages)):
            position = (float(index)/len(self.pages))*100
            print('  {0:.2f}%   {1}   [   ] Initializing.                '.format(position, os.path.split(self.pages[index].path)[1]), end='\r')
            print('  {0:.2f}%   {1}   [   ] Checking if image is bitonal.'.format(position, os.path.split(self.pages[index].path)[1]), end='\r')
            self.pages[index].is_bitonal()

            print('  {0:.2f}%   {1}   [+  ] Finding image dpi.           '.format(position, os.path.split(self.pages[index].path)[1]), end='\r')
            self.pages[index].get_dpi()
            if (self.dpi is not None) and (self.pages[index].dpi != self.dpi):
                print("wrn: organizer.Book.insert_page(): page dpi is different from the previous page.  If you encounter problems with minidjvu, this is probably why.", file=sys.stderr)
                print("wrn: {0}".format(path))
            self.dpi = self.pages[index].dpi

            if no_ocr:
                print('  {0:.2f}%   {1}   [++ ] Skipping OCR.                '.format(position, os.path.split(self.pages[index].path)[1]), end='\r')
            else:
                print('  {0:.2f}%   {1}   [++ ] Running OCR.                 '.format(position, os.path.split(self.pages[index].path)[1]), end='\r')
                self.pages[index].ocr()

            print('                                                     '.format(position, os.path.split(self.pages[index].path)[1]), end='\r')

class Page:
    def __init__(self, path):
        self.path = os.path.abspath(path)

        self.bitonal = None
        self.dpi = 0
        self.text = ''

    def get_dpi(self):
        dpi = Djvubind.utils.execute("identify -format '%x' {0} | awk '{{print $1}}'".format(self.path), capture=True)
        self.dpi = int(dpi)
        return None

    def is_bitonal(self):
        if (Djvubind.utils.execute("identify -verbose {0} | grep 'Base type' | awk '{{print $3}}'".format(self.path), capture=True) != b'Bilevel\n'):
            self.bitonal = False
        else:
            if (Djvubind.utils.execute('identify -format %z "{0}"'.format(self.path), capture=True) != b'1\n'):
                print("msg: Bitonal image but with a depth of 8 instead of 1.  Modifying image depth.")
                Djvubind.utils.execute("mogrify -colors 2 '{0}'".format(self.path))
            self.bitonal = True
        return None

    def ocr(self):
        if self.path.split('.')[-1] in ['jpg', 'jpeg']:
            Djvubind.utils.execute('convert "{0}" "{0}.tif"'.format(self.path))
            self.text = Djvubind.ocr.get_text(self.path+'.tif')
            os.remove(self.path+'.tif')
        elif self.path.split('.')[-1] == 'tiff':
            shutil.copy2(self.path, self.path+'.tif')
            self.text = Djvubind.ocr.get_text(self.path+'.tif')
            os.remove(self.path+'.tif')
        elif self.path.split('.')[-1] == 'tif':
            self.text = Djvubind.ocr.get_text(self.path)
        else:
            self.text =  ''

        return None
