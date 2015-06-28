# djvubind

| master | develop |
|--------|---------|
| [![Build Status](https://travis-ci.org/strider1551/djvubind.svg?branch=master)](https://travis-ci.org/strider1551/djvubind) | [![Build Status](https://travis-ci.org/strider1551/djvubind.svg?branch=develop)](https://travis-ci.org/strider1551/djvubind) |

## Dependencies

### Required

- [python-3.2 or greater](https://www.python.org/)
- [djvulibre](http://djvu.sourceforge.net/)
- [imagemagick](http://www.imagemagick.org/)
- [tesseract](https://code.google.com/p/tesseract-ocr/)

You could forgo having tesseract installed so long as you always use the `--no-ocr` option.

### Optional

- [minidjvu](http://minidjvu.sourceforge.net/)
- [cuneiform](http://cognitiveforms.com/products_and_services/cuneiform)

Minidjvu will get better compression on bitonal images than cjb2 (part of djvulibre) currently can. Some say that cuneiform is a better ocr engine, but in my experience it has issues with buffer overflows. I generally advise against using cuneiform. If you choose to use it anyway and it crashes, tesseract will take over for that image.

## Installation

Installation should be as simple as `./setup.py install` on Unix based systems. You can add `--dry-run` if you want to check what will happen before doing it, or just use `--help` for all the details on options. Those with debian based distros will probably be insterest in `--install-layout=deb`.

Installation is not necessary, since djvubind can run straight from the unpacked source. This is actually preferred in a Windows environment

N.b., at the moment most distributions are able to have python3 installed but do not use that version by default. If this is the case (and it probably is), explicitly call python3 when installing (e.g. `python3 ./setup.py install`)

## Usage

Run djvubind in a directory that contains the files that should combined into the djvu file. Only files with .tif or .tiff extension will be included in the file. Additionally, by default "bookmarks" and "metadata" files will be inserted if they are present; they should be in the format used by djvused for print-outline and print-meta. A front or back cover image can also be provided in jpeg or tiff formats.

### An example directory:
```
cover_front.jpg
cover_back.jpg
bookmarks
metadata
page_0001.tif
page_0002.tif
...
page_n.tif
```

### An example bookmarks file:

```
(bookmarks
 ("Cover" "#1" )
 ("Contents" "#7" )
)
```

Note the # symbol before the page number, and don't forget that if you have a cover image, that will be page 1, not your first page of text.

### An example metadata file:

```
author "John Smith"
title "Creating Quality Documents"
```
