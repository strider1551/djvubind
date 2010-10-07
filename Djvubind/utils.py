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
import subprocess
import sys

def color(text, color):
    """Change the text color by adding ANSI escape sequences."""
    colors = {}
    colors['pink'] = '\033[95m'
    colors['blue'] = '\033[94m'
    colors['green'] = '\033[92m'
    colors['yellow'] = '\033[93m'
    colors['red'] = '\033[91m'
    end = '\033[0m'

    if color in colors.keys():
        text = colors[color] + text + end

    return text

def separate_cmd(cmd):
    """
    Convert a subprocess command string into a list, intelligently handling arguments
    enclosed in single or double quotes.
    """

    cmd = list(cmd)
    buffer = ''
    out = []
    switch = [False, '']

    for x in range(len(cmd)):
        char = cmd[x]
        if char == ' ' and not switch[0]:
            out.append(buffer)
            buffer = ''
        # Be wary of a single/double quote that is part of a filename and not part of an
        # enclosing pair
        elif (char == '"' or char == "'") and not switch[0]:
            if (char in cmd[x+1:]) and (buffer == ''):
                switch[0] = True
                switch[1] = char
            else:
                buffer = buffer + char
        elif char == switch[1] and switch[0]:
            out.append(buffer)
            buffer = ''
            switch[0] = False
        else:
            buffer = buffer + char
    out.append(buffer)

    # Just in case there were multiple spaces.
    while '' in out:
        out.remove('')

    return out

def simple_exec(cmd):
    cmd = separate_cmd(cmd)
    with open('/dev/null', 'w') as void:
        sub = subprocess.Popen(cmd, shell=False, stdout=void, stderr=void)
        return int(sub.wait())

def execute(cmd, capture=False):
    """Execute a command line process."""
    #print('>>> {0}'.format(cmd))
    if capture:
        s = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    else:
        s = subprocess.Popen(cmd, shell=True)
    status = s.wait()


    if (cmd.startswith('cuneiform')) and (status == 134):
        return status
    elif (cmd.startswith('cuneiform')) and (status == 1):
        # Cuneiform crashes on blank images.  Still need to raise an error since it may crash
        # for other reasons, but ocr.py by default just writes a blank file if cuneiform fails.
        sys.exit(1)
    elif status != 0:
        print('err: utils.execute(): command exited with bad status.\ncmd = {0}\nexit status = {1}'.format(cmd, status), file=sys.stderr)
        sys.exit(1)

    if capture:
        text = s.stdout.read()
        del(s)
        return text
    else:
        del(s)
        return status

def list_files(dir='.', filter=None, extension=None):
    """Find all files in a given directory that match criteria."""
    tmp = os.listdir(dir)
    contents = []
    for path in tmp:
        if os.path.isfile(path):
            contents.append(path)
    contents.sort()

    if filter is not None:
        remove = []
        for file in contents:
            if filter not in file:
                remove.append(file)
        for file in remove:
            contents.remove(file)

    if extension is not None:
        remove = []
        for file in contents:
            ext = file.split('.')[-1]
            if extension.lower() != ext.lower():
                remove.append(file)
        for file in remove:
            contents.remove(file)

    return contents

def is_executable(command):
    """Checks if a given command is available.  Handy for dependency checks on external commands."""
    for path in os.environ['PATH'].split(':'):
        path = os.path.join(path, command)
        if (os.access(path, os.X_OK)) and (not os.path.isdir(path)):
            return True

    return False
