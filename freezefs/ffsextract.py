# (c) 2023 Hermann Paul von Borries
# MIT License
# freezefs file extract driver for MicroPython

import os
import errno
import sys

class _VerbosePrint:
    def __init__( self, module_name, function, silent ):
        self.silent = silent
        self.prefix = f"{module_name}.{function}"

    def print( self, *args ):
        if not self.silent:
            print( self.prefix, *args )

def _file_exists( filename ):
    try:
        open( filename ).close()
        return True
    except:
        return False
 

def _extract_file( dir_entry, destination ):
    
    from io import BytesIO
    data = dir_entry[0]
    if not data:
        return
    # Process in small chunks to reduce memory use
    buffer = bytearray(256)
    stream = BytesIO( data )
    if dir_entry[1]:
        # This is a compressed file
        # Import here, so this is imported only when needed
        from deflate import DeflateIO, AUTO
        stream = DeflateIO( stream, AUTO, 0, True )
    with open( destination, "wb" ) as outfile:
        while True:
            n = stream.readinto( buffer )
            if n == 0:
                break
            outfile.write( memoryview( buffer )[0:n] )
    stream.close()

def _create_folder( folder, vp ):   
    path = ""
    # Create parent folders first, then the specified folder
    for p in folder.split("/"):
        path += "/" + p
        path = path.replace("//", "/" )
        try:
            os.mkdir( path )
            vp.print( f"folder {path} created." )
        except Exception as e:
            if type(e) is not OSError or e.errno != errno.EEXIST:
                vp.print( f"folder {path} not created: ", e )
     
def _extract_all( direntries, target, overwrite, vp ):
    _create_folder( target, vp )
    
    # Don't mount the frozen file system,
    # access file data through the internal file structure.
    for filename, dir_entry in direntries:
        # get destination filename
        dest = (target + filename).replace("//", "/")
        if dir_entry:
            # Copy file
            try:
                if overwrite == "never" and _file_exists( dest ):
                    vp.print( f"file {dest} exists, not extracted." )
                else:
                    vp.print(  f"extracting file {dest}." )
                    _extract_file( dir_entry, dest )
            except Exception as e:
                vp.print( f"file {dest} not copied: {e}." )
                raise
        else:
            # Create folder (and it's parent folders if not created yet)
            # This relies on directory entries being sorted, so
            # the dir_entry for the folder comes up before the files it contains.
            _create_folder( dest, vp )
 
   
# Called from the generated (frozen) .py module
def extract_fs( module_name, target, overwrite, silent ):
    
    # Delete this module from list of loaded modules to help
    # free the memory after use. Calling program must use __import__
    # __main__ is not in sys.modules[]
    module = __import__( module_name )
    if module_name != "__main__":
        del sys.modules[ module_name ]
    
    vp = _VerbosePrint( module_name, "extract", silent )

    vp.print( f"extracting files to {target}." )
    _extract_all( direntries, target, overwrite, vp )
            
    return 