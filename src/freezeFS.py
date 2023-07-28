# (c) 2023 Hermann Paul von Borries
# MIT License
import argparse
from pathlib import Path, PurePosixPath
from glob import glob
import os
import sys
import time

MAX_FILENAME_LEN = 255


def get_max_utf8_bytes_char( s ):
    # Get length of longest UTF-8 sequence in s
    # This is used to allocate a buffer for file.read( size )
    # when in text mode.
    if len(s) == 0:
        return 1
    bits = max( ord(c).bit_length() for c in s )
    if bits <= 7:
        return 1
    elif bits <= 11:
        return 2
    elif bits <= 16:
        return 3
    else:
        return 4


def get_utf8_width( pc_filepath ):       
    # Discover longest utf-8 sequence in the file (if UTf-8)
    try:
        with open( pc_filepath, "r", encoding="UTF-8") as file:
            s = file.read()
        return get_max_utf8_bytes_char( s )
    except UnicodeError:
        # Probably this is a binary file (or a malformed UTF-8 file)
        # If None were returned, a non-unicode file will generate
        # a UnicodeError on open.
        # As 4 is returned, file.open will succeed, but a later
        # read() will return UnicodeError. 4 means that 4 byte UTF-8
        # sequences may be expected.
        return 4
 
def write_data(  pc_infolder, pc_outfile, target, on_import, silent ):
    files = []
    # With Python 3.13 on we could use follow_symlinks=True on Windows
    # Add root
    var = 0
    # Use glob, rglob does not follow symlinks
    for p in glob( "**", root_dir=pc_infolder, recursive=True ):
        pc_path = Path( p )
        # Make a list with variable name, filepath and the 
        # Micropython path
        #mp_path = "/" + pc_path.relative_to( pc_infolder ).as_posix()
        mp_path = "/" + pc_path.as_posix()
        if len( mp_path ) > MAX_FILENAME_LEN:
            raise ValueError(f"File name longer than {MAX_FILENAME_LEN}: {mp_path} ")
        fileinfo =  ( pc_infolder / pc_path, mp_path, var )
        files.append( fileinfo )
        var += 1
    files_to_python( files, pc_outfile, target, on_import )
    return True
    
def files_to_python( files, pc_outfile, target, on_import ): 
    files.sort( key=lambda x: x[1])         
    with open( pc_outfile, "w", encoding="utf-8") as file:
        sum_size = 0
        number_of_files = 0
        number_of_folders = 0
        
        for pc_path, mp_path, var in files:            
            if pc_path.is_file():
                file.write(f"# {mp_path}\n" ) 
                pythonized = file_to_py( pc_path )
                file.write(f"_f{var} = const(\n{pythonized})\n")

        file.write("_direntries = const((")
        for pc_path, mp_path, var in files:            
            if pc_path.is_file():
                uw = get_utf8_width( pc_path )
                size = pc_path.stat().st_size
                direntry = f"( _f{var}, {uw} )"
                sum_size += size 
                number_of_files += 1
                print(f"Appended file {pc_path}->{mp_path}, {size} bytes" )
            else:
                direntry = "None"
                size = 0
                number_of_folders += 1
                print(f"Appended folder {pc_path}->{mp_path}")
            file.write(f" ( '{mp_path}',  {direntry} ),\n" )
        file.write("))\n\n" )

        t = time.localtime()        
        file.write(f"DATE_FROZEN = const('{t[0]}/{t[1]:02d}/{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}')\n")
        file.write(f"last_mount_point = None\n" )
        
        file.write(f"def mount( mount_point='{target}' ):\n" )
        nf = number_of_files+number_of_folders
        file.write( "    from vfsfrozen import mount_fs\n" )
        file.write( "    global last_mount_point\n" )
        file.write(f"    last_mount_point = mount_fs( _direntries, mount_point, {sum_size}, {nf}, {silent})\n" )
        file.write(f"def deploy( target='{target}'):\n" )
        file.write( "    from vfsfrozen import deploy_fs\n" )
        file.write(f"    deploy_fs( _direntries, target, {silent} )\n" )
        file.write( "def umount():\n" )
        file.write( "    from vfsfrozen import umount_fs\n" )
        file.write( "    global last_mount_point\n" )
        file.write(f"    last_mount_point = umount_fs( last_mount_point, {silent} )\n" ) 
        if on_import == "mount":
            file.write( "mount()\n" )
        elif on_import == "deploy":
            file.write( "deploy()\n" )
            
        print(f"Sum of file sizes {sum_size} bytes, {number_of_files} files {number_of_folders} folders" ) 

def file_to_py( pc_path ):
    pythonized = ""
    size = pc_path.stat().st_size
    if size == 0:
        return pythonized + "  b''"
 
    with open( pc_path, "rb") as file:
        while True:
            chunk = file.read(16)
            if len(chunk) == 0:
                break
            pythonized += f"  {str(chunk)}\\\n"
        file.close()
    
    # Last item without \ and \n
    return pythonized[0:-2]
  

DESC = """freezeFS.py
Utility to convert a folder and its subfolders to a single Python source.
The output file can be then frozen in a Micropython image together with
vfsfrozen.py and mounted as a readonly file system.
With the --on_import mount option, the file system will be mounted on import (this is the default).
With the --on_import deploy option, the content will be copied the first time to flash. If the target folder already exists, no file is copied nor modified. The file system is not mounted.

Examples:
freezeFS.py input_folder frozenfolder.py
freezeFS.py input_folder frozenfolder.py --target=/myfiles --on_import mount
freezeFS.py input_folder frozenfolder.py --target=/myfiles --on_import deploy
"""
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                __file__, 
                description=DESC,
                formatter_class = argparse.RawDescriptionHelpFormatter)
    parser.add_argument('infolder', type=str, help='Input folder path')
    parser.add_argument('outfile', type=str,
                        help='Path and name of output file. Must have .py extension.')
    parser.add_argument("--target", "-t", type=str,
                        dest="target",
                        help="For mount: Mount point. For deploy: destination folder. Default value is the name of the output file. Example: --target /myfiles. Must start with /")
    parser.add_argument("--on_import", "-o", type=str,
                        dest="on_import",
                        choices=["mount", "deploy", "no_action"],
                        default="mount",
                        help="Action when importing output module. Default is mount.")
    parser.add_argument("--silent", "-s", 
                        dest="silent", default=False,
                        action="store_true",
                        help="Supress messages printed when mounting/copying files.")
  

    args = parser.parse_args()
    pc_infolder = Path( args.infolder )
    pc_outfile = Path( args.outfile )
    module_name = pc_outfile.name[0:-len(pc_outfile.suffix)]
    target = args.target
    on_import = args.on_import 
    silent = args.silent
    
    if not pc_infolder.is_dir():
        quit("Input folder does not exist, or is not a folder")

    if not pc_outfile.suffix.lower() == '.py':
        quit('Output filename must have a .py extension.')
    
    if target:
        if not target.startswith("/"):
            target = "/" + target
        if target.endswith("/") and target != "/":
            target = target[0:-1]
    else:
        target = "/" + module_name

    print(f'Writing Python file {pc_outfile}.')
    
    if not write_data( pc_infolder, pc_outfile, target, on_import, silent ):
        sys.exit(1)

    print(pc_outfile, 'written successfully.')
    if on_import == "mount":
        print(f"On import the file system will be mounted at {target}." )
   
    elif on_import == "deploy":
        print(f"On import the file system will be deployed (copied if empty) to {target}." )
    
  

  

