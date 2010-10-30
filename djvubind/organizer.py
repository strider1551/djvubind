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
import signal
import time
import threading
import queue

from . import ocr
from . import utils

def signal_handler(signal, frame):
    print('You pressed Ctrl-C!')
    sys.exit(0)

class QueueRunner(threading.Thread):
    def __init__(self, q, pagecount, engine, no_ocr=False, ocr_options={}):
        threading.Thread.__init__(self)
        self.queue = q
        self.no_ocr = no_ocr
        self.engine = engine
        self.ocr_options = ocr_options
        self.pagecount = pagecount

        self.quit = False

    def run(self):
        while not self.quit:
            try:
                # Process the page
                page = self.queue.get()
                page.is_bitonal()
                page.get_dpi()
                if not self.no_ocr:
                    page.ocr(self.engine, self.ocr_options)

                # Report completion percentage.
                # N.b., this is perfect, since queue.qsize() isn't completely reliable in a threaded
                # environment, but it will do well enough to give the user and idea of where we are.
                position = ( (self.pagecount - self.queue.qsize()) / self.pagecount ) * 100
                print('  {0:.2f}% completed.       '.format(position), end='\r')
            except queue.Empty:
                self.quit = True
            finally:
                self.queue.task_done()

class Book:
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
                print("wrn: organizer.Book.analyze(): page dpi is different from the previous page.  If you encounter problems with minidjvu, this is probably why.", file=sys.stderr)
            self.dpi = page.dpi

        return None

    def insert_page(self, path):
        self.pages.append(Page(path))
        return None

    def analyze(self, ocr_engine, no_ocr=False, ocr_options={}):
        # Create queu and populate with pages to process
        q = queue.Queue()
        for i in self.pages:
            q.put(i)

        # Detect number of available cpus
        ncpus = utils.cpu_count()
        if not isinstance(ncpus, int) or ncpus <= 0:
            ncpus = 1
        print('  Spawning {0} processing threads.'.format(ncpus))
        print('  {0:.2f}% completed.       '.format(0), end='\r')

        # Create threads to process the pages in queue
        for i in range(ncpus):
            p = QueueRunner(q, len(self.pages), ocr_engine, no_ocr, ocr_options)
            p.daemon = True
            p.start()

        # Wait for everything to digest.  Note that we don't simply call q.join()
        # because it blocks, preventing something like ctrl-c from killing the
        # program.
        while not q.empty():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                print('')
                sys.exit(1)
        q.join()

        # Figure out the book's dpi
        for page in self.pages:
            if (self.dpi is not None) and (page.dpi != self.dpi):
                print("wrn: {0}".format(page.path))
                print("wrn: organizer.Book.analyze(): page dpi is different from the previous page.  If you encounter problems with minidjvu, this is probably why.", file=sys.stderr)
            self.dpi = page.dpi

        return None

class Page:
    def __init__(self, path):
        self.path = os.path.abspath(path)

        self.bitonal = None
        self.dpi = 0
        self.text = ''

    def get_dpi(self):
        dpi = utils.execute('identify -ping -format %x "{0}"'.format(self.path), capture=True).decode('ascii').split(' ')[0]
        self.dpi = int(dpi)
        return None

    def is_bitonal(self):
        if utils.execute('identify -ping "{0}"'.format(self.path), capture=True).decode('ascii').find('Bilevel') == -1:
            self.bitonal = False
        else:
            if (utils.execute('identify -ping -format %z "{0}"'.format(self.path), capture=True).decode('ascii') != ('1' + os.linesep)):
                print("msg: {0}: Bitonal image but with a depth greater than 1.  Modifying image depth.".format(os.path.split(self.path)[1]))
                utils.execute('mogrify -colors 2 "{0}"'.format(self.path))
            self.bitonal = True
        return None

    def ocr(self, engine, ocr_options):
        # Note: This should really be moved to ocr.py, now that we have multiple ocr
        # engines which probably don't have the same filename/filetype requirements as
        # tesseract.
        if self.path.split('.')[-1] in ['jpg', 'jpeg']:
            utils.execute('convert "{0}" "{0}.tif"'.format(self.path))
            self.text = ocr.ocr(self.path+'.tif', engine, ocr_options)
            os.remove(self.path+'.tif')
        elif self.path.split('.')[-1] == 'tiff':
            shutil.copy2(self.path, self.path+'.tif')
            self.text = ocr.ocr(self.path+'.tif', engine, ocr_options)
            os.remove(self.path+'.tif')
        elif self.path.split('.')[-1] == 'tif':
            self.text = ocr.ocr(self.path, engine, ocr_options)
        else:
            self.text =  ''

        return None