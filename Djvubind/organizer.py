#! /usr/bin/env python

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

import Djvubind.utils

class Book:
    def __init__(self):
        self.pages = []
        self.cover = {}
        self.cover["front"] = None
        self.cover["back"] = None
        self.metadata = None
        self.bookmarks = None

    def insert_page(self, path):
        self.pages.append(Page(path))
        return None

class Page:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.bitonal = self.is_bitonal(self.path)
        self.dpi = self.get_dpi(self.path)

    def get_dpi(self, path):
        dpi = Djvubind.utils.execute("identify -format '%x' {0} | awk '{{print $1}}'".format(path), capture=True)
        return int(dpi)

    def is_bitonal(self, path):
        if (Djvubind.utils.execute('identify -format %z "{0}"'.format(path), capture=True) != b'1\n'):
            return False
        else:
            return True
