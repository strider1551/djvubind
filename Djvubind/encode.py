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

import Djvubind.utils

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
        cmds = Djvubind.utils.split_cmd('minidjvu {0}'.format(encoder_opts), filenames, tempfile)
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
        Djvubind.utils.execute(cmd)
        if (not os.path.isfile(outfile)):
            shutil.move(tempfile, outfile)
        else:
            Djvubind.utils.execute('djvm -i "{0}" "{1}"'.format(outfile, tempfile))
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
            Djvubind.utils.execute('convert -opaque black "{0}" "temp_graphics.tif"'.format(filename))
            Djvubind.utils.execute('convert +opaque black "{0}" "temp_textual.tif"'.format(filename))

            # Encode the bitonal image.  Note that at the moment, there is no way to pass
            # custom options to cjb2.
            bitonal = enc_bitonal(["temp_textual.tif"], 'cjb2')

            # Encode with color with bitonal via csepdjvu
            Djvubind.utils.execute('ddjvu -format=rle -v "{0}" "temp_textual.rle"'.format(bitonal))
            Djvubind.utils.execute('convert temp_graphics.tif temp_graphics.ppm')
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
            Djvubind.utils.execute('csepdjvu {0} "temp_merge.mix" "temp_final.djvu"'.format(encoder_opts))

            if (not os.path.isfile(outfile)):
                shutil.move('temp_final.djvu', outfile)
            else:
                Djvubind.utils.execute('djvm -i {0} "temp_final.djvu"'.format(outfile))

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
