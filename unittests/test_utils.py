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

class FunctColor(unittest.TestCase):
    """
    Tests for utils.color()
    """

    def test_01AddColor(self):
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

    def test_02BadColor(self):
        """
        Checks that no modification is made with an unsupported color.
        """
        text = 'Some text here.'
        out = djvubind.utils.color(text, 'mauve')
        self.assertEqual(text, out)

if __name__ == "__main__":
    unittest.main()
