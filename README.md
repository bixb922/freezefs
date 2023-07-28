# freezeFS: Freeze file structures into MicroPython images to mount or deploy files 
## Purpose

freezeFS is a utility that freezes file structures into a MicroPython image. It converts folders into Python source files and mounts them as read-only Virtual File Systems on microcontrollers. This allows  standard access to the files with low RAM usage. It also offers the option to copy files for initial deployment. Overall, it simplifies deploying text and binary files with a MicroPython image.

## Description
freezeFS.py  is a utility program that runs on a PC and converts an arbitrary folder, subfolder and file structure into a Python source file. The generated Python file can then be frozen as bytecode into a MicroPython image together with the Virtual File System driver vfsfrozen.py.

When the generated Python file is imported, the file structure is mounted with os.mount() as a read only Virtual File System, which can be accessed on the microcontroller with regular file operations such as open in  "r" or "rb" mode, read, readinto, readline, seek, tell, close, listdir, ilistidr, stat. 

If the deploy option is used, the files and folders of the frozen files are copied to flash.  This enables initializing configuration and data files when booting the MicroPython image the first time.

## Installation
The software is implemented in two files: freezeFS.py for the PC and vfsfrozen.py for the microcontroller.

Copy freezeFS.py  to a folder of your choice on your PC.

Copy vfsfrozen.py to the microcontroller, or better, freeze vfsfrozen.py together with the generated .py files.

## An example
Suppose you have the following folder on your PC:

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
The following command will freeze the complete structure to the myfolder.py file:
```
freezeFS.py  myfolder myfolder.py 
```
To make the file structure depicted visible on the microcontroller, you will have to write a boot.py file (or modify your main.py file) to include the line:
```
import myfolder
```
The next step is to include myfolder.py the manifest.py used for freezing the MicroPython image, as well as vfsfrozen.py, which is the file system manager of this utility.

When booting up the microcontroller, and once ```import myfolder``` has been executed, the above file structure is mounted (using os.mount() internally) at /myfolder, and the files and folders will appear under /myfolder on the microcontroller as read only files. The files are not copied to /myfolder, but remain in the MicroPython image on flash.

To try out the example, create myfolder with your files and subfolders, and run:
```
python freezeFS.py myfolder myfolder.py
% mpremote cp vfsfrozen.py :
Writing Python file myfolder.py.
Appended file myfolder\file1.txt->/file1.txt, 100 bytes
Appended folder myfolder\mysubfolder->/mysubfolder
Appended file myfolder\mysubfolder\file20.txt->/mysubfolder/file20.txt, 10 bytes
Appended file myfolder\mysubfolder\file30.txt->/mysubfolder/file30.txt, 20 bytes
Sum of file sizes 130 bytes, 3 files 1 folders
myfolder.py written successfully.
On import the file system will be mounted at /myfolder.
% mpremote cp myfolder.py :
% mpremote
>>>import myfolder.py
vfsfrozen mount: mounted filesystem at /myfolder
>>> os.listdir("/myfolder")
['file1.txt', 'mysubfolder']
>>> os.listdir("/myfolder/mysubfolder")
['file20.txt', 'file30.txt']
>>> x=open("/myfolder/file1.txt")
>>> x.read()
'Hello, this is a text file. Unicode está soportado. '
>>> x.close()
```
os.listdir should now show the frozen files and folders. open("/myfolder/myfile.data") will open that file. 

In this test case, the file system gets created in RAM instead of flash, so all files are now loaded to RAM. When freezing myfolder.py with the MicroPython image, the file data resides in flash and uses no RAM. Other than that, you can test the functionality.

## freezeFS.py  utility

You run this program on your PC to freeze a folder and its content (files and subfolders) to a .py file. 

To freeze several folders, either put those in a parent folder and freeze the parent folder, or repeat the freezeFS.py  command for each folder, generating one output module for each folder. 

freezeFS.py --help will show the command format and options.
```
positional arguments:
  infolder              Input folder path
  outfile               Path and name of output file. Must have .py extension.

options:
  -h, --help            show this help message and exit
  --target TARGET, -t TARGET
                        For mount: Mount point. For deploy: destination folder. Default value is the name
                        of the output file. Example: --target /myfiles. Must start with /
  --on_import {mount,deploy,no_action}, -o {mount,deploy,no_action}
                        Action when importing output module. Default is mount.
  --silent, -s          Supress messages when mounting/copying files.
```


### freezeFS.py  with --on_import mount (default)
WIth this option, the outfile.py module mounts its file system on import to the mount point (virtual folder) specified by --target. If no target specified, the virtual folder name is the name of the output file.

The files in the mounted folder on the microcontroller are read-only. 

### freezeFS.py  with --on_import deploy
This functionality is supports the initial deployment of read-write data files to the flash file system. If you want to distribute or setup a complete system on a frozen MicroPython image, this option allows to deploy configuration and data files to be copied to the microcontroller's file system the first time the system boots.

With this option, the folder is not mounted but copied once to the file system at the specified target. Your application can now read and modify these files.

The next time the system boots up, this software checks whether the target folder is empty. If not empty, it exits without modifying the files.

To copy the content of the frozen file system, use the --on_import=deploy option on the PC and then ```import``` the .py with the frozen files in your main.py or boot.py. Preferably, the import should be in frozen code, for example in _boot.py. 

The deploy option will automatically create the folders and subfolders specified in --target.

deploy does not mount the file system to do the file copy. However you can mount the file system at any point to access and retrieve files.

## An example for deploy
Suppose need several folders with files on the microcontroller:
```
root folder /
    |
    +---main.py
    +---config.json

Data folder with read/write data
    +---data
    |    +---data files that will be updated

Static folder and subfolders for web server
    +---static
    +    +--- html files
    +    +--- image
    +    +      +--- image files
    +    +--- css
    +    +      +---- css files

Media folder with binary files (read only)
    +---media
    +    +---- binary media files to be read
```
You would have to create 4 folders on the PC (root with main.py and config.py, data, static media) and you could freeze with these commands:
```
freezeFS.py root frozen_root.py --target=/ --on_import=deploy
freezeFS.py data frozen_data.py --target=data --on_import=deploy
freezeFS.py static frozen_static.py --target=static --on_import=mount
freezeFS.py  media frozen_media.py --target=media --on_import=mount
```
The next step is to add frozen_root.py, frozen_data.py, frozen_static.py, frozen_media.py and vfsfrozen.py to the mainfest.py. Then you add these statements to _boot.py:
```
import frozen_root
import frozen_data
import frozen_static
import frozen_media
```
Then you would have to compile and create the MicroPython image (for example, a .bin file) and write that to the microcontroller's flash.

On the first boot, main.py, config.py will be copied to flash. The data folder will be created and it's content copied to flash. At /static and at /media, read only file systems with the files will be mounted.

The import statements may be left in _boot.py. Since now the root folder and the data folder have files, vfsfrozen.py will not modify those further.


### freezeFS.py  --target
For ```--on_import mount```, this is the mount point on the file system of the microcontroller.


For ```--on_import deploy```, this is the destination folder on the file system of the microcontroller.


### freezeFS.py  --silent
By default, mount, deploy and umount functions print the progress. If you want to suppress those messages, freeze the files with --silent.

If an exception occurs during mount, deploy and umount, the exception will be raised independently of the --silent option.


## The frozen .py file

The output file of the freezeFS.py  utility is a module with the frozen file system. This module contains a const with all the file data. MicroPython will access the file data directly in flash. The generated  .py file also has the mount, umount and deploy functions. 

Sample output when importing a generated output .py module, with --on_import=mount
```
>>> import frozenfiles
vfsfrozen mount: mounted filesystem at /fz.
>>>import frozenfiles
>>> frozenfiles.deploy()
vfsfrozen deploy: folder found at /fz, no files copied.
>>> frozenfiles.umount()
vfsfrozen umount: /fz unmounted.
>>> frozenfiles.deploy()
vfsfrozen deploy: folder /fz created.
vfsfrozen deploy: file /fz/file1.txt copied.
vfsfrozen deploy: file /fz/file2.txt copied.
vfsfrozen deploy: file /fz/file3.bin copied.
vfsfrozen deploy: Folder /fz/sub1 created
vfsfrozen deploy: file /fz/sub1/file1.txt copied.
vfsfrozen deploy: file /fz/sub1/file2.txt copied.
vfsfrozen deploy: Folder /fz/sub1/sub2 created
vfsfrozen deploy: file /fz/sub1/sub2/file2.txt copied.
```
Note that the second ```import frozenfiles``` does not attempt to mount again. This is a result of how Python works: initialization code is called for the first import after boot only.

The generated .py module exposes the following functions: mount(), umount(), deploy(). These are the same that are called on import, and are provided to be called manually in case of freezing with on_import=no_action. 

* ```mount( mount_point )``` If not mounted, this function will mount the file system on the specified mount point. This option allows to mount/dismount manually. If mount_point is omiitted, the mount_point specified by the --target option of the freezeFS.py  command is used.

* ```umount() ``` This will dismount the virtual file system.

* ```deploy( target )``` if the target folder is empty, all files in the frozen module will be copiedto the folder specified by target. The folder and it's subfolder will be created.

* The DATE_FROZEN attribute has the date/time when the file structure was frozen.

## The VFS module (vfsfrozen.py)

This is the module that implements the Virtual File System. You have to install it on your microcontroller by copying the vfsfrozen.py file to your root folder or the /lib folder, or better freeze via manifest.py to the MicroPython image.

This module implements mount, umount, chdir, getcwd, ilistdir, listdir, stat, open, close, read, readinto, readline, readlines, the iterator for reading lines and the decoding of UTF-8 text files to MicroPython strings.

statvfs returns block size of 1. The file system size is the sum of all file sizes, without overhead. Mode flag is 1 (read only). The maximum file length is set to 255.

open will only accept modes "r", "rt" and "rb". As usual, "r" will decode UTF-8 to strings, and "rb" will return bytes (bytearray).

file.open with modes "r+w", "a", etc. raises an OSError, since the file system frozen into the MicroPython image is read only.

remove, mkdir and rename will raise an OSError( errno.EPERM ).

ilistdir will show file type (0x4000 for folders, 0x8000 for files as usual) and file size. Unused fields returned by ilistdir are set to zero.

If file.read(size) with size>0 is used, a 400 byte buffer for UTF-8 decoding is allocated for that file, and data is read to
the buffer for decoding UTF-8 to MicroPython strings.You can use FreezeFS.set_decode_buffer_size( n ) to change that value. "n" must be > 16 bytes.

## Unit tests

The /test folder on github has unit tests. 
To run the tests on the microcontroller use these commands:
```
mpremote mip install unittest
test.py
freezeFS.py  testfiles frozenfiles.py --target /fz --on_import mount
mpremote cp vfsfrozen.py :
mpremote cp frozenfiles.py : 
mpremote run test.py
```
test.py will create and populate the testfiles folder on the PC. The files are frozen into frozenfiles.py. The tests compare behaviour of file operations of the freezeFS file system and the standard file system. 

## Performance

File operations are comparable or a somewhat faster than littlevfs2 on my ESP32-S3 with PSRAM. The only operation that is slower is file.read(size) for a file opened with "r" and the size parameter less than about 10 characters. file.read(1) is about double the time of littlevfs2. All other operations like read(), readline(), readlines(), open(), close(), os.listdir(), os.ilistdir(), os.statvfs(), os.stat() take similar or less time of littlevfs2.

## Dependencies
These standard MicroPython libraries are needed: os, io.BytesIO, collections.OrderedDict and errno. 

Python 3.10 or later must be installed on the PC.

The code is Python only. No C/C++ code. There are no processor or board specific dependencies.

## Compatibility
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



