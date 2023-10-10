# freezefs: Create self-extracting compressed or self-mounting archives for MicroPython 

## Purpose

freezefs saves a file structure with subfolders and builds an self-extractable or self-mountable archive in a .py file, optionally with compression, to be frozen as bytecode or extracted.

There are several ways to use freezefs:
* Freeze the archive as frozen bytecode in a MicroPython image. Import the archive and it gets mounted as a read-only file system. The files continue to reside in the frozen image. 
* Freeze the compressed archive as frozen bytecode in a MicroPython image. Import the archive once to extract the file structure to the flash file system. The purpose is to aid initial deployment of read/write files.
* Run a compressed .py archive with ```mpremote run```. The files get extracted to the microprocessor. This is a easy way to install many files at once, and it is quite fast.
* Install a compressed .py archive with ```mpremote mip install``` and then import the file to extract all files. This aids in installing complete systems over-the-air (OTA). The file should be compiled with mpy-cross, to get all the gain from compression.

Overall, it simplifies deploying text and binary files, such as MicroPython code, html pages, json data files, etc.


## Description
freezefs  is a utility program that runs on a PC and converts an arbitrary folder, subfolder and file structure into a Python source file. The files can be compressed. The generated Python file can then be frozen as bytecode into a MicroPython image, installed with mip on a microcontroller.

The archive file can be either mounted as a Virtual File System or extracted. 

The files can be compressed or be left uncompressed.

The drivers for mounting or extracting are included in the same generated Python file, making the output file a self-mounting or self-extracting archive file.

## Feedback
Please report any problem or ask for support in the issues section. If it works for you, please star the repository.

## Installation

Install the software with ```pip install freezefs```


## An example: freeze a files to a MicroPython image and mount file system
Suppose you have the following folders, files and subfolders on your PC and want to freeze that together with your MicroPython programs in a MicroPython image:

```
myfolder
    |
    +---index.html
    +---tunes.html
    +---favicon.ico
    +---css
    |    |
    |    +---mystyles.css
    |    +---normalize.css
    |
    +---images
         |
         +---myimage.jpg
```
The following command will archive the complete structure to the myfolder.py file:
```
python -m freezefs  myfolder frozen_myfolder.py --target=/myfolder --on-import=mount
```
The frozen_myfolder.py will now contain all the files and folders, together with the code to mount this as a read only file system. To mount on the microcontroller, add this line to _boot.py, boot.py or main.py:
```
import frozen_myfolder
```


When booting up the microcontroller, and once ```import frozen_myfolder``` has been executed, the above file structure is automatically mounted (using ```os.mount()``` internally) at /myfolder, and the files and folders will appear under ```/myfolder``` on the microcontroller as read only files. The files are not copied to ```/myfolder```, but remain in the MicroPython image on flash. They now can be accessed with MicroPython statements such as ```open( "/myfolder/index.html", "r"), read(), readline(), open in "rb" or "r" mode, os.listdir("/myfolder")``` etc. If the import is in ```boot.py``` or ```_boot.py```, the files are also visible with ```mpremote ls```. The RAM overhead is low, and access speed is similar to regular flash files.

## Another example: create a self-extractable file archive
Use:
```
python -m freezefs  myfolder frozen_myfolder.py --target=/myfolder --on-import=extract --compress
```

The frozen_myfolder.py will now contain all the files and folders compressed with zlib, together with the code to extract the files to the flash file system at ```/```. Optionally compile with ```mpy-cross frozen_myfolder.py``` to reduce file size. Have your code ```import frozen_myfolder```. This will decompress and extract (copy) the complete folder and subfolders to flash memory. On the next import, the files won't be overwritten (see ```--overwrite``` option).

Importing or running the file, for example ```mpremote run frozen_myfolder``` will also extract all files. Since this is quite fast, this is aids deploying software.

If you import a self-extracting archive, you should use:
```
__import__("frozen_myfolder")
```
This will free the used RAM memory of the import on the next garbage collection. 

## freezefs utility

You run this program on your PC to freeze a folder and its content (files and subfolders) to a .py file. 


```python -m freezefs --help``` will show the command format and options.

```
usage: python -m freezefs [-h] [--on-import {mount,extract}] [--target TARGET] [--overwrite {never,always}]
                          [--compress | --no-compress | -c] [--wbits WBITS] [--level LEVEL] [--silent]
                          infolder outfile

freezefs.py
freezefs saves a file structure with subfolders and builds an self-extractable or self-mountable archive in a .py file, optionally with compression, to be frozen as bytecode or extracted.

Examples:
freezefs.py input_folder frozenfiles.py --target=/myfiles --on_import mount
freezefs.py input_folder frozenfiles.py --target=/myfiles --on_import=extract --compress

positional arguments:
  infolder              Input folder path
  outfile               Path and name of output module. Must have .py extension.

options:
  -h, --help            show this help message and exit
  --on-import {mount,extract}, -oi {mount,extract}
                        Action when importing output module. Default is mount.
  --target TARGET, -t TARGET
                        For --on-import=mount: mount point. For --on-import=extract: destination folder.
                        Example: --target /myfiles. Must start with /
  --overwrite {never,always}, -ov {never,always}
                        always: on extract, all files are overwritten. never: on extract, no file is
                        overwritten, only new files are extracted. Default: never.
  --compress, --no-compress, -c
                        Compress files before writing to output .py. See python zlib compression. (default:
                        False)
  --wbits WBITS, -w WBITS
                        Compression window of 2**WBITS bytes. Between 9 and 14. Default is 10 (1024 bytes)
  --level LEVEL, -l LEVEL
                        Compression level. Between 0 (no compression) and 9 (best compression). Default is 9
  --silent, -s          Supress messages printed when mounting/copying files and while running this program.
```
### The infolder
The input folder and subfolders contain the files to be archived in the output .py file. 


### The output .py file
The outfile is overwritten with the MicroPython code with file contents (possibly compressed), file and folder names and the code to os.mount() or extract the files.


### freezefs with --on-import mount (default)

With this option, the output .py module mounts its file system on import at the mount point (virtual folder) specified by --target as read-only files. 

The purpose --on-import=mount option to enable mounting a file system frozen in bytecode in a MicroPython image. So the best use for this option is to put the .py output file or files into a manifest.py, generate the MicroPython image and load the image to a microcontroller. Add a import of the output .py file in the main.py or boot.py (or _boot.py) and the files get visible read only at the specified target.

 The files frozen in the MicroPython image use very little RAM overhead. The files read from flash. Only a file directory is loaded in RAM for lookup of files.

See below for --on-import with --compress.

#### Using --on-import=mount with --compress has some restrictions

It is possible to combine --on-import=mount with --compress and freeze as bytecode to a MicroPython image. The files are decompressed on the fly. Open in "rb" mode is very efficient. However open in "r" mode (open in text mode) and the complete file is loaded to RAM on after compressing, so this combination is only of use if enough RAM is available.

If you import an output .py file that is not frozen in a MicroPython image but resides on the standard flash file system, the import loads the complete .py file system to RAM. This needs as much RAM as each file. Access is very fast, but a lot of RAM may be needed.

### freezefs with --on-import=extract
This option is intended for use with --compress to deploy files to the regular flash file system.

When importing or running this .py file on a MicroPython system, the file system gets decompressed and extracted.

Also see --overwrite option.

With the --on-import=extract option, the folder is not mounted but copied to the file system at

### --on-import=extract with --overwrite=never
When extracting, each file that exists will be skipped. Only non-existing files will be extracted.



### --on-import=extract with --overwrite=always
When extracting, existing files will be overwritten.


### freezefs  --target
For ```--on-import=mount``` this is the mount point on the file system of the microcontroller.

For ```--on-import=export```, this is the destination folder on the file system of the microcontroller.

Must start with /, i.e. must be a root folder. ```--target=/myfolder/subfolder```  is a valid target.

For ```--on-import=extract```, this can be ```--target=/``` to deploy files to the root folder, such as main.py.

If omitted, the last subfolder of the infolder is set as target, for example if the infolder is ```/myfolder/subfolder```, target will be set to ```/subfolder```.

### freezefs --compress
This option compresses the files when packing them into the output .py files and decompresses them using deflate on the microcontroller.

This option is best for use with --on-import=extract. It works with ```--on-import=mount```, but the RAM usage is high when opening text files with "r" mode.

### freezefs --compress, --wbits and --level options

 --wbits indicates the number of bytes used at any time for compressing (called the window size). The size of the window is 2\*\*WBITS, so --wbits=9 means windows size of 2\*\*9=512 bytes and --wbits=14 means 2\*\*14=16384 bytes. The higher the value, the better the compression, however, to decompress, up to 2\*\*WBITS bytes may needed on the microcontroller. 
 
 --level goes from 0 (no compression) to 9 (highest compression). Level 9 is a bit slower to decompress.
 
 See Python docs for zlib and MicroPython docs for deflate for more details. 
 

### freezefs  --silent
By default, mount and extract print the progress. If you want to suppress those messages, freeze the files with --silent.

If an exception occurs during mount or extract, the exception will be raised independently of the --silent option.

## The frozen .py output file

The output file of the freezefs  utility is a module with the frozen file system. This generated module contains consts with all the file data. MicroPython will access the file data directly in flash, if the .py file is frozen as bytecode in a MicroPython image. 

The code for extract or mount is included in the file. When compiled to .mpy files, this code is about 1800 bytes for mount or 1300 bytes for extract.


### The mounted virtual file system

freezefs implements a Virtual File System (VFS), included in the output file when using --on-import=mount

The VFS implements ```os.mount```, ```os.umount```, ```os.chdir```, ```os.getcwd```, ```os.ilistdir```, ```os.listdir```, ```os.stat```, ```open```, ```close```, ```read```, ```readinto```, ```readline```, the iterator for reading lines and the decoding of UTF-8 format files to MicroPython strings.

```statvfs``` returns block size of 1. The file system size is the sum of all file sizes, without overhead. Mode flag is 1 (read only). The maximum file length is set to 255.

```open``` will only accept modes "r", "rt" and "rb". As usual, "r" will decode UTF-8 to strings, and "rb" will return bytes.

```open``` with modes "w", "wb", "a", etc. raises an OSError, since the file system frozen into the MicroPython image is read only.

```remove```, ```mkdir``` and ```rename``` will raise an OSError( errno.EPERM ).

```ilistdir``` will show file type (0x4000 for folders, 0x8000 for files as usual) and file size. Unused fields returned by ilistdir are set to zero.

If ```--compress``` was used, the files are decompressed on open. ```read()```, ```readinto()```, ```readline()```, ```readlines()``` are available. However, ```seek()``` and ```tell()``` are not available. ```open(file,"rb")``` uses very little RAM. open(file,"r") will buffer the complete file in RAM.


## Unit tests

The /test folder on github has unit tests.


## Dependencies
These standard MicroPython libraries are needed: sys, os, io.BytesIO, io.StringIO, collections.OrderedDict and errno.  If --compress is used, deflate is needed. Deflate is present in MicroPython 1.20 or later.

Python 3.10 or later must be installed on the PC. Probably earlier versions of Python will work too.

The code is MicroPython/Python only. No C/C++ code. There are no processor or board specific dependencies.

#  Changes fron version 1 
Version number 2. If you are using version 1, please regenerate the output .py files with the new version of freezefs as they are incompatible.

Added --compress and --overwrite switches. Drivers for extracting and mounting are now included. freezefs is now pip installable.

## Compatibility with MicroPython/Python versions
Tested with MicroPython 1.20 and Python 3.10.7 and 3.11.4.

## Copyright and license
Source code and documentation Copyright (c) 2023 Hermann Paul von Borries.

This software and documentation is licensed according to the MIT license:

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.



