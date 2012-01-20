Installation
================

Dependencies
------------
Required Dependencies
    * DjVuLibre
    * ImageMagick
    * Python 3
Recommended Dependencies
    * cuneiform
    * minidjvu
    * tesseract

N.B.: If neither tesseract nor cuneiform are installed, you must always execute djvubind with the ``--no-ocr`` option.


Linux and Mac  Source Installation
--------------------------
Installation is not strictly necessary, since djvubind can be executed from an unpacked source archive.  However, installation is recommended for easier operation.  The process is typical of python programs that use distutils::

    python ./setup.py --dry-run install
    python ./setup.py install

You can also use ``--help`` for more details on installation options.  If you are running a Debian based distribution, you may be interested in ``--install-layout=deb``.

Linux Package Installation
--------------------------

Gentoo
^^^^^^
An ebuild is provided for each release and made available on the `download page <https://code.google.com/p/djvubind/downloads/list>`_.  If an experienced ebuild writer sees a problem with the ebuild, feel free to file an issue on the tracker.

Debian-based
^^^^^^^^^^^^
A debian package is provided for each release and made available on the `download page <https://code.google.com/p/djvubind/downloads/list>`_.  These packages are made and tested in an Ubuntu machine, but should be simple enough to work with any debian based distro.  If an experienced debian package manager sees a problem with the package, feel free to file an issue on the tracker.

Windows Installation
--------------------
Djvubind is known to work on the Windows platform but is not officially supported, meaning that installation and use is not as simple as most Window users expect.  These instructions are for a Windows XP machine, but will probably work in later versions.  Windows will not be officially supported unless a developer with Windows experience joins the project.

#. Install dependencies and note the path to their installation (e.g. "C:\\Program Files\\Python3")
#. Unzip djvubind to a location of preference (e.g. "C:\\Program Files\\djvubind")
#. Copy the configuration file ("docs\\config") to the user's Application Data folder ("C:\\Documents and Settings\\your-username-here\\Application Data\\djvubind\\config")
#. Modify the win_path variable of the user config file so that it matches the paths to your installed dependencies.
