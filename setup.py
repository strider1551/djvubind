#! /usr/bin/env python

from distutils.core import setup

setup (name='djvubind',
      version='0.0.1',
      description='Creates djvu files with positional ocr, metadata, and bookmarks.',
      author='Adam Zajac',
      author_email='strider1551@gmail.com',
      url='',
      license='GPL-3',
      py_modules=['Djvubind/__init__'],
      #data_files=[('share/man/man1', ['docs/lib2mp3.1.gz']),
      #            ('bin', ['lib2mp3'])]
)
