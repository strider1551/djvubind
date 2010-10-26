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

import glob
import os
import shutil
import sys

from . import utils

def enc_bitonal(filenames,  encoder='minidjvu',  encoder_opts=''):
    """
    Encode a list of bitonal image filenames into a djvu file.  Returns the filename of the
    newly created djvu file.
    """

    # Specify filenames that will be used.
    tempfile = 'enc_temp.djvu'
    outfile = 'enc_bitonal_out.djvu'
    if os.path.isfile(tempfile) or os.path.isfile(outfile):
        msg = 'wrn: encode.enc_bitonal(): One or more temporary filenames ("{0}" and "{1}") already exist and will be overwritten.'.format(tempfile, outfile)
        print(msg, file=sys.stderr)

    # Create a list of commands to execute to encode the files.
    if encoder == 'minidjvu':
        # Minidjvu has to worry about the length of the command since all the filenames are
        # listed.
        cmds = utils.split_cmd('minidjvu {0}'.format(encoder_opts), filenames, tempfile)
    elif encoder == 'cjb2':
        cmds = []
        for filename in filenames:
            cmds.append('cjb2 {0} "{1}" "{2}"'.format(encoder_opts, filename, tempfile))
    else:
        msg = 'err: encode.enc_bitonal(): The requested encoder ({0}) is not supported.'.format(encoder)
        print(msg, file=sys.stderr)
        sys.exit(1)

    # Execute each command, adding each result into a single, multipage djvu.
    for cmd in cmds:
        utils.execute(cmd)
        if (not os.path.isfile(outfile)):
            shutil.move(tempfile, outfile)
        else:
            utils.execute('djvm -i "{0}" "{1}"'.format(outfile, tempfile))
            os.remove(tempfile)

    # Check that the outfile has been created.
    if not os.path.isfile(outfile):
        msg = 'err: encode.enc_bitonal(): No encode errors, but "{0}" does not exist!'.format(outfile)
        print(msg, file=sys.stderr)
        sys.exit(1)

    return outfile

def enc_color(filenames, encoder='csepdjvu', encoder_opts=''):
    """
    Encode a list of color image filenames into a djvu file.  Returns the filename of the
    newly created djvu file.
    """

    # Specify filenames that will be used.
    outfile = 'enc_color_out.djvu'
    if os.path.isfile(outfile):
        msg = 'wrn: encode.enc_bitonal(): One or more temporary filenames ("{0}") already exist and will be overwritten.'.format(outfile)
        print(msg, file=sys.stderr)

    if encoder == 'csepdjvu':
        for filename in filenames:
            # Separate the bitonal text (scantailor's mixed mode) from everything else.
            utils.execute('convert -opaque black "{0}" "temp_graphics.tif"'.format(filename))
            utils.execute('convert +opaque black "{0}" "temp_textual.tif"'.format(filename))

            # Encode the bitonal image.  Note that at the moment, there is no way to pass
            # custom options to cjb2.
            bitonal = enc_bitonal(["temp_textual.tif"], 'cjb2')

            # Encode with color with bitonal via csepdjvu
            utils.execute('ddjvu -format=rle -v "{0}" "temp_textual.rle"'.format(bitonal))
            utils.execute('convert temp_graphics.tif temp_graphics.ppm')
            with open('temp_merge.mix', 'wb') as mix:
                with open('temp_textual.rle', 'rb') as rle:
                    buffer = rle.read(1024)
                    while buffer:
                        mix.write(buffer)
                        buffer = rle.read(1024)
                with open('temp_graphics.ppm', 'rb') as ppm:
                    buffer = ppm.read(1024)
                    while buffer:
                        mix.write(buffer)
                        buffer = ppm.read(1024)
            utils.execute('csepdjvu {0} "temp_merge.mix" "temp_final.djvu"'.format(encoder_opts))

            if (not os.path.isfile(outfile)):
                shutil.move('temp_final.djvu', outfile)
            else:
                utils.execute('djvm -i {0} "temp_final.djvu"'.format(outfile))

            # Clean up
            for tempfile in glob.glob('temp_*'):
                os.remove(tempfile)
            os.remove(bitonal)
    else:
        msg = 'err: encode.enc_color(): The requested encoder ({0}) is not supported.'.format(encoder)
        print(msg, file=sys.stderr)
        sys.exit(1)

    # Check that the outfile has been created.
    if not os.path.isfile(outfile):
        msg = 'err: encode.enc_color(): No encode errors, but "{0}" does not exist!'.format(outfile)
        print(msg, file=sys.stderr)
        sys.exit(1)

    return outfile

class Encoder:
    """
    An intelligent djvu super-encoder that can work with numerous djvu encoders.
    """

    def __init__(self, opts):
        self.opts = opts

        self.dep_check()

    def _c44(self, infile, outfile, dpi):
        """
        Encode files with c44.
        """

        cmd = 'c44 -dpi {0} {1} "{2}" "{3}"'.format(dpi, self.opts['cjb2_options'], infile, outfile)
        utils.execute(cmd)

        # Check that the outfile has been created.
        if not os.path.isfile(outfile):
            msg = 'err: encode.enc_bitonal(): No encode errors, but "{0}" does not exist!'.format(outfile)
            print(msg, file=sys.stderr)
            sys.exit(1)

        return None

    def _cjb2(self, infile, outfile, dpi):
        """
        Encode files with cjb2.
        """

        cmd = 'cjb2 -dpi {0} {1} "{2}" "{3}"'.format(dpi, self.opts['cjb2_options'], infile, outfile)
        utils.execute(cmd)

        # Check that the outfile has been created.
        if not os.path.isfile(outfile):
            msg = 'err: encode.enc_bitonal(): No encode errors, but "{0}" does not exist!'.format(outfile)
            print(msg, file=sys.stderr)
            sys.exit(1)

        return None

    def _csepdjvu(self, infile, outfile, dpi):
        """
        Encode files with cpaldjvu.
        """

        # Separate the bitonal text (scantailor's mixed mode) from everything else.
        utils.execute('convert -opaque black "{0}" "temp_graphics.tif"'.format(infile))
        utils.execute('convert +opaque black "{0}" "temp_textual.tif"'.format(infile))

        # Encode the bitonal image.
        self._cjb2('temp_textual.tif', 'enc_bitonal_out.djvu', dpi)

        # Encode with color with bitonal via csepdjvu
        utils.execute('ddjvu -format=rle -v "enc_bitonal_out.djvu" "temp_textual.rle"')
        utils.execute('convert temp_graphics.tif temp_graphics.ppm')
        with open('temp_merge.mix', 'wb') as mix:
            with open('temp_textual.rle', 'rb') as rle:
                buffer = rle.read(1024)
                while buffer:
                    mix.write(buffer)
                    buffer = rle.read(1024)
            with open('temp_graphics.ppm', 'rb') as ppm:
                buffer = ppm.read(1024)
                while buffer:
                    mix.write(buffer)
                    buffer = ppm.read(1024)
        utils.execute('csepdjvu -d {0} {1} "temp_merge.mix" "temp_final.djvu"'.format(dpi, self.opts['csepdjvu_options']))

        if (not os.path.isfile(outfile)):
            shutil.move('temp_final.djvu', outfile)
        else:
            utils.execute('djvm -i {0} "temp_final.djvu"'.format(outfile))

        # Clean up
        for tempfile in glob.glob('temp_*'):
            os.remove(tempfile)
        os.remove('enc_bitonal_out.djvu')

        return None

    def _minidjvu(self, infiles, outfile, dpi):
        """
        Encode files with minidjvu.
        N.B., minidjvu is the only encoder function that expects a list a filenames
        and not a string with a single filename.  This is because minidjvu gains
        better compression with a shared dictionary across multiple images.
        """

        # Specify filenames that will be used.
        tempfile = 'enc_temp.djvu'

        # Minidjvu has to worry about the length of the command since all the filenames are
        # listed.
        cmds = utils.split_cmd('minidjvu -d {0} {1}'.format(dpi, self.opts['minidjvu_options']), infiles, tempfile)

        # Execute each command, adding each result into a single, multipage djvu.
        for cmd in cmds:
            utils.execute(cmd)
            self.djvu_insert(tempfile, outfile)

        return None

    def dep_check(self):
        """
        Check for ocr engine availability.
        """

        if not utils.is_executable(self.opts['bitonal_encoder']):
            msg = 'err: encoder "{0}" is not installed.'.format(engine)
            print(msg, file=sys.stderr)
            sys.exit(1)
        if not utils.is_executable(self.opts['color_encoder']):
            msg = 'err: encoder "{0}" is not installed.'.format(engine)
            print(msg, file=sys.stderr)
            sys.exit(1)

        return None

    def djvu_insert(self, infile, djvufile, page_num=None):
        if (not os.path.isfile(djvufile)):
            shutil.copy(infile, djvufile)
        elif page_num is None:
            utils.execute('djvm -i "{0}" "{1}"'.format(djvufile, infile))
        else:
            utils.execute('djvm -i "{0}" "{1}" {2}'.format(djvufile, infile, int(page_num)))

    def enc_book(self, book, outfile):
        """
        Encode pages, metadata, etc. contained within a organizer.Book() class.
        """

        tempfile = 'temp.djvu'

        # Encode bitonal images first, mainly because of minidjvu needing to do
        # them all at once.
        if self.opts['bitonal_encoder'] == 'minidjvu':
            bitonals = []
            for page in book.pages:
                if page.bitonal:
                    filepath = os.path.split(page.path)[1]
                    bitonals.append(filepath)
            if len(bitonals) > 0:
                if self.opts['bitonal_encoder'] == 'minidjvu':
                    self._minidjvu(bitonals, tempfile, book.dpi)
                    self.djvu_insert(tempfile, outfile)
                    os.remove(tempfile)
        elif self.opts['bitonal_encoder'] == 'cjb2':
            for page in book.pages:
                if page.bitonal:
                    self._cjb2(page.path, tempfile, page.dpi)
                    self.djvu_insert(tempfile, outfile)
                    os.remove(tempfile)

        # Encode and insert non-bitonal
        if self.opts['color_encoder'] == 'csepdjvu':
            for page in book.pages:
                if not page.bitonal:
                    page_number = book.pages.index(page) + 1
                    self._csepdjvu(page.path, tempfile, page.dpi)
                    self.djvu_insert(tempfile, outfile, page_number)
                    os.remove(tempfile)

        # Add ocr data
        if self.opts['ocr']:
            for page in book.pages:
                handle = open('ocr.txt', 'w', encoding="utf8")
                handle.write(page.text)
                handle.close()
                page_number = book.pages.index(page) + 1
                utils.simple_exec('djvused -e "select {0}; remove-txt; set-txt \'ocr.txt\'; save" "{1}"'.format(page_number, outfile))
                os.remove('ocr.txt')

        # Insert front/back covers, metadata, and bookmarks
        if book.suppliments['cover_front'] is not None:
            dpi = int(utils.execute('identify -ping -format %x "{0}"'.format(book.suppliments['cover_front']), capture=True).decode('ascii').split(' ')[0])
            self._c44(book.suppliments['cover_front'], tempfile, dpi)
            self.djvu_insert(tempfile, outfile, 1)
        if book.suppliments['cover_back'] is not None:
            dpi = int(utils.execute('identify -ping -format %x "{0}"'.format(book.suppliments['cover_back']), capture=True).decode('ascii').split(' ')[0])
            self._c44(book.suppliments['cover_back'], tempfile, dpi)
            self.djvu_insert(tempfile, outfile, -1)
        if book.suppliments['metadata'] is not None:
            utils.simple_exec('djvused -e "set-meta {0}; save" "{1}"'.format(book.suppliments['metadata'], outfile))
        if book.suppliments['bookmarks'] is not None:
            utils.simple_exec('djvused -e "set-outline {0}; save" "{1}"'.format(book.suppliments['bookmarks'], outfile))

        os.remove(tempfile)

        return None
