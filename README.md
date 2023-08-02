# freezeFS: Freeze file structures into MicroPython images to mount or deploy 
## Purpose

freezeFS is a utility that freezes file structures into a MicroPython image. It converts folders into Python source files and mounts them as read-only Virtual File Systems on microcontrollers. This allows  standard access to the files with low RAM usage. It also offers the option to copy files for initial deployment. Overall, it simplifies deploying text and binary files with a MicroPython image.

## Description
freezeFS.py  is a utility program that runs on a PC and converts an arbitrary folder, subfolder and file structure into a Python source file. The generated Python file can then be frozen as bytecode into a MicroPython image together with the Virtual File System driver vfsfrozen.py.

When the generated Python file is imported, the file structure is mounted with os.mount() as a read only Virtual File System, which can be accessed on the microcontroller with regular file operations such as open in  "r" or "rb" mode, read, readinto, readline, seek, tell, close, listdir, ilistidr, stat. 

If the deploy option is used, the files and folders of the frozen files are copied to the standard flash file system.  This enables installing configuration and data files when booting the MicroPython image the first time.

An important topic is that opening files in "r" mode requires to buffer the file in RAM. However, many libraries such as web servers and json support reading text modes in "rb" mode, and no overhead is incurred. 

## Feedback
Please leave feedback in the issues section. If it works for you, please star the repository.

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

When booting up the microcontroller, and once ```import myfolder``` has been executed, the above file structure is mounted (using ```os.mount()``` internally) at /myfolder, and the files and folders will appear under /myfolder on the microcontroller as read only files. The files are not copied to /myfolder, but remain in the MicroPython image on flash.

## Try out the example
To try out the example, create myfolder with your files and subfolders, and run:
```
python freezeFS.py myfolder myfolder.py
Writing Python file myfolder.py.
Writing Python file myfolder.py.
Appended folder myfolder\css->/css
Appended file myfolder\css\mystyles.css->/css/mystyles.css, 14050 bytes
Appended file myfolder\css\normalize.css->/css/normalize.css, 7870 bytes
Appended file myfolder\favicon.ico->/favicon.ico, 1150 bytes
Appended folder myfolder\images->/images
Appended file myfolder\images\myimage.jpg->/images/myimage.jpg, 17337 bytes
Appended file myfolder\index.html->/index.html, 7475 bytes
Appended file myfolder\tunes.html->/tunes.html, 5671 bytes
Sum of file sizes 53553 bytes, 6 files 2 folders
myfolder.py written successfully.
On import the file system will be mounted at /myfolder.
% mpremote cp vfsfrozen.py :
% mpremote cp myfolder.py :
% mpremote
>>>import myfolder
vfsfrozen mount: mounted filesystem at /myfolder
>>> os.listdir("/myfolder")
['file1.txt', 'mysubfolder']
>>> os.listdir("/myfolder/mysubfolder")
['css', 'favicon.ico', 'images', 'index.html', 'tunes.html']
>>> x=open("/myfolder/index.html")
>>> x.readline()
'<!DOCTYPE html>\r\n'
>>> x.readline()
'\r\n'
>>> x.readline()
'<head>\r\n'
>>> x.readline()
'\t<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\r\n'
>>> x.close()
>>> os.stat("/myfolder/index.html")
(32768, 0, 0, 0, 0, 0, 7475, 0, 0, 0)
os.stat("/myfolder/images")
(16384, 0, 0, 0, 0, 0, 0, 0, 0, 0)
>>> os.listdir("/myfolder/images")
>>> z=open("/myfolder/images/myimage.jpg", "rb")
>>> z.read(10)
b'\xff\xd8\xff\xe0\x00\x10JFIF'
>>> z.close()
```
If you add ```import myfolder``` to ```boot.py``` then you can inspect the mounted the file system with mpremote:
```
% mpremote ls myfolder
ls :myfolder
           0 css/
        1150 favicon.ico
           0 images/
        7475 index.html
        5671 tunes.html
% mpremote ls myfolder/css
ls :myfolder/css
       14050 mystyles.css
        7870 normalize.css
```
In this test case, the file system gets created in RAM instead of flash, so all files are now loaded to RAM. When freezing myfolder.py with the MicroPython image, the file data resides in flash and uses no RAM. However, the functionality can be tested easily this way.

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
  --silent, -s          Suppress messages when mounting/copying files.
```


### freezeFS.py  with --on_import mount (default)
WIth this option, the outfile.py module mounts its file system on import to the mount point (virtual folder) specified by --target. If no target specified, the virtual folder name is the name of the output file.

The files in the mounted folder on the microcontroller are read-only. 

### freezeFS.py  with --on_import deploy
This functionality is supports the initial deployment of read-write data files to the flash file system. If you want to distribute or setup a complete system on a frozen MicroPython image, this option allows to deploy configuration and data files to be copied to the microcontroller's file system the first time the system boots.

With this option, the folder is not mounted but copied once to the file system at the specified target. Your application can now read and modify these files.

The next time the system boots up, this software checks whether the target folder is empty. If not empty, it exits without modifying the files.

To copy the content of the frozen file system, use the --on_import=deploy option on the PC and then ```import``` the .py with the frozen files in your ```main.py``` or ```boot.py```. Preferably, the import should be in frozen code, for example in ```_boot.py```. 

The deploy option will automatically create the folders and subfolders specified in --target.

deploy does not mount the file system to do the file copy. However you can mount the file system at any point to access and retrieve files.

With ```--on_import=deploy target=/``` you can deploy files to the root of the file system. For example, you can deploy main.py this way.

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

On the first boot, ```main.py```, ```config.py``` will be copied to flash. The data folder will be created and it's content copied to flash. At /static and at /media, read only file systems with the files will be mounted.

The import statements for deploying may be left in ```_boot.py```. Since now the root folder and the data folder have files, vfsfrozen.py will not modify those further.

If all folders content is erased, the next boot will deploy the files again. This can be used as a "factory reset".


### freezeFS.py  --target
For ```--on_import mount```, this is the mount point on the file system of the microcontroller.


For ```--on_import deploy```, this is the destination folder on the file system of the microcontroller.


### freezeFS.py  --silent
By default, mount, deploy and umount functions print the progress. If you want to suppress those messages, freeze the files with --silent.

If an exception occurs during mount, deploy and umount, the exception will be raised independently of the --silent option.


## The frozen .py file

The output file of the freezeFS.py  utility is a module with the frozen file system. This generated module contains const with all the file data. MicroPython will access the file data directly in flash. The generated  .py file also has the mount, umount and deploy functions. 

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
Note that the second ```import frozenfiles``` will not attempt to mount again. This is a result of how Python works: initialization code is called for the first import after boot only. A second try of frozenfiles.deploy() won't deploy again either, because the target folder is not empty anymore.

The generated .py module exposes the following functions: ```mount()```, ```umount()```, ```deploy()```. These are the same that are called by the on_import option, and are provided to be called manually in case of freezing with on_import=no_action. In all cases, the default value for mount_point, target and silent_mode are the parameters provided in the freezeFS command.

* ```mount( mount_point, silent_mode )``` If not mounted, this function will mount the file system on the specified mount point. This option allows to mount manually. If mount_point is omitted, the mount_point specified by the --target option of the freezeFS.py  command is used.

* ```umount( mount_point, silent_mode ) ``` This will dismount the virtual file system at the mount_point specified. You also can use os.umount(). The default value for mount_point is the mount point specified by the --target option of the freezeFS.py command.

* ```deploy( target, silent_mode )``` if the target folder is empty, all files in the frozen module will be copied to the folder specified by target. The folder and it's subfolder will be created.

* The get_date_frozen() function will return a string with date/time when the file structure was frozen.

* The get_version() function will return 1.

## The VFS module (vfsfrozen.py)

This is the module that implements the Virtual File System. You have to install it on your microcontroller by copying the vfsfrozen.py file to your root folder or the /lib folder, or better freeze via manifest.py to the MicroPython image.

This module implements ```os.mount```, ```os.umount```, ```os.chdir```, ```os.getcwd```, ```os.ilistdir```, ```os.listdir```, ```os.stat```, ```open```, ```close```, ```read```, ```readinto```, ```readline```, the iterator for reading lines and the decoding of UTF-8 format files to MicroPython strings.

```statvfs``` returns block size of 1. The file system size is the sum of all file sizes, without overhead. Mode flag is 1 (read only). The maximum file length is set to 255.

```open``` will only accept modes "r", "rt" and "rb". As usual, "r" will decode UTF-8 to strings, and "rb" will return bytes.

```open``` with modes "w", "wb", "a", etc. raises an OSError, since the file system frozen into the MicroPython image is read only.

```remove```, ```mkdir``` and ```rename``` will raise an OSError( errno.EPERM ).

```ilistdir``` will show file type (0x4000 for folders, 0x8000 for files as usual) and file size. Unused fields returned by ilistdir are set to zero.

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
Running test.py on the PC will create and populate the testfiles folder. The files are frozen into frozenfiles.py. The tests compare behaviour of file operations of the freezeFS file system and the standard file system. 

## Dependencies
These standard MicroPython libraries are needed: os, io.BytesIO, collections.OrderedDict and errno. 

Python 3.10 or later must be installed on the PC. Probably earlier versions of Python will work too.

The code is Python only. No C/C++ code. There are no processor or board specific dependencies.

# Version
Version number 1.

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



