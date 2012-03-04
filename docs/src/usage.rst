Usage
=====

.. note::
    Windows users will probably have neither python nor djvubind in their path, so execution would be something similar to: ``"C:\Program Files\Python31\python.exe" "C:\Program Files\djvubind\bin\djvubind"``.  This should be done from a command line terminal (Start->Run, and enter "cmd").

A full listing of options can be found with ``djvubind --help``. Additional information on usage may also be found in the manpage.

Project Files
-------------
Djvubind expects to either be run from the directory containing all of your image files, or to be passed that directory as an argument. The images must have an extension of .tif or .tiff. They will be added to the file in a sorted order.

.. note::
    Support for the Netpbm format (.pnm, .pbm, .pgm, .ppm) is `a planned feature <https://code.google.com/p/djvubind/issues/detail?id=31&colspec=ID%20Type%20Status%20Priority%20Milestone%20Reporter%20Summary>`_ for the future. At this point, djvubind **will** process files with the .pnm and .pbm extensions, but no promises that it will work! If you do use those extensions and encounter a problem, please report it.

Front/Back Covers
^^^^^^^^^^^^^^^^^

If "cover_front.jpg" or "cover_back.jpg" exist in the directory, they will be added as the first or last page in the file, as appropriate. These images will not be scanned for OCR. Alternate filenames to use can be specified with ``--cover-front`` and ``--cover-back``.

Bookmarks
^^^^^^^^^

If a file named "bookmarks" exists in the directory, it will be passed to djvused to create bookmarks in the file. It should be in the format accepted by ``djvused -e 'set-outline'``. For example: ::

    (bookmarks
      ("Cover" "#1" )
      ("Contents" "#7" )
    )

An alternative filename may be used with ``--bookmarks``.

Metadata
^^^^^^^^

If a file named "metadata" exists in the directory, it will be passed to djvused to add metadata to the file. It should be in the format accepted by ``djvused -e 'set-meta'``. For example: ::

    author "John Smith"
    title "Creating Quality Documents"

An alternative filename may be used with ``--metadata``.

Titles (or renaming pages)
--------------------------

Most published books number the frontmatter with roman numerals, and the rest of the book in arabic numerals, such that "1" is the first page of chapter one, but perhaps the twentieth physical page in the book. Additionally, some pages may be numbered differently (such as photo pages) or not at all. To facilitate following this standard digitally, you may take advantage of the various options for titles.

``--title-start=<filename>`` will specify the page to start counting as "1". Any pages which come before this in the file will be titled with roman numerals.

``--title-exclude=<filename>:<string>`` will skip that page in the numbering sequence and instead title it with the specified string. Please note that you cannot use the same title twice, and that this is a limitation of ``djvused`` (if not DjVu itself).

``--title-uppercase`` will make the roman numerals uppercase.

An example: suppose your directory contains the following: page_000.tif, page_001.tif, page002.tif, page_003.tif, page_004.tif ::

    command: djvubind --title-start=page_002.tif
    titles:  i, ii, 1, 2, 3

    command: djvubind --title-start=page_002.tif --titles-exclude=page_003.tif:blank
    titles:  i, ii, 1, blank, 2
