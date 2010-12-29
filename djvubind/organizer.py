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
"""
Data structures to organize collect and abstract information.
"""

import os
import sys

from . import utils

class Book:
    """
    Contains all information regarding the djvu ebook that will be produced.
    """

    def __init__(self):
        self.pages = []
        self.suppliments = {'cover_front':None,
                            'cover_back':None,
                            'metadata':None,
                            'bookmarks':None}
        self.dpi = None

    def get_dpi(self):
        """
        Sets the book's dpi based on the dpi of the individual pages.  Pretty much
        only used by minidjvu.
        """

        for page in self.pages:
            if (self.dpi is not None) and (page.dpi != self.dpi):
                print("wrn: {0}".format(page.path))
                print("wrn: organizer.Book.analyze(): Page dpi is different from the previous page.", file=sys.stderr)
                print("wrn: organizer.Book.analyze(): If you encounter problems with minidjvu, this is probably why.", file=sys.stderr)
            self.dpi = page.dpi

        return None

    def insert_page(self, path):
        """
        Add an image to the book.
        """

        self.pages.append(Page(path))
        return None

class Page:
    """
    Contains information relevant to a single page/image.
    """

    def __init__(self, path):
        self.path = os.path.abspath(path)

        self.bitonal = None
        self.dpi = 0
        self.text = ''

    def get_dpi(self):
        """
        Find the resolution of the image.
        """

        dpi = utils.execute('identify -ping -format %x "{0}"'.format(self.path), capture=True).decode('ascii').split(' ')[0]
        self.dpi = int(dpi)
        return None

    def is_bitonal(self):
        """
        Check if the image is bitonal.
        """

        if utils.execute('identify -ping "{0}"'.format(self.path), capture=True).decode('ascii').find('Bilevel') == -1:
            self.bitonal = False
        else:
            if (utils.execute('identify -ping -format %z "{0}"'.format(self.path), capture=True).decode('ascii') != ('1' + os.linesep)):
                print("msg: {0}: Bitonal image but with a depth greater than 1.  Modifying image depth.".format(os.path.split(self.path)[1]))
                utils.execute('mogrify -colors 2 "{0}"'.format(self.path))
            self.bitonal = True
        return None
