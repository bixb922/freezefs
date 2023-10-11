# (c) 2023 Hermann Paul von Borries
# MIT License
# MicroPython VFS mount driver for freezefs
import os
import errno
from io import BytesIO, StringIO
from collections import OrderedDict
import sys

def _get_basename( filename ):
    return filename.split("/")[-1]

def _get_folder( filename ):
    basename = _get_basename( filename )
    folder = filename[0:-len(basename)-1]
    if folder == "":
        folder = "/"
    return folder

 
class VfsFrozen:
    # File system for frozen files. Implements mount, listdir, stat, open etc
    # Actual read, readinto, seek, are done by BytesIO and StringIO
    def __init__( self, direntries, sum_size, files_folders ):       
        # direntries is (filename, ( data, compressed, size ) for files
        #               (filename, None) for folders
        self.filedict = OrderedDict( direntries )
        self.sum_size = sum_size
        self.files_folders = files_folders
        self.path = "/"
    
    def _to_absolute_filename( self, filename ):
        if not filename.startswith( "/" ) :
            filename = self.path + "/" + filename
        if filename.endswith("/") and filename != "/":
            filename = filename[0:-1]
        filename = filename.replace("//", "/")

        # Solve ".."
        parts = filename.split("/")
        i = -1
        while ".." in parts:
            i = parts.index("..")
            if i > 1:
                del parts[i]
                del parts[i-1]
            else:
                # Can't access /..
                raise OSError( errno.EPERM )
        # Solve ./file or /folder/./file
        while "." in parts:
            i = parts.index(".")
            del parts[i]
        filename = "".join( "/" + p for p in parts ).replace( "//", "/" )
        return filename
        
    def _find_file( self, filename ):
        filename = self._to_absolute_filename( filename )
        if filename == "/":
            # The root is a folder. filedict doesn't have 
            # the root. Return folder direntry for the root.
            return None
        if filename in self.filedict:
            # Return the file directory entry (dir_entry)
            return self.filedict[filename]
        else:
            raise OSError( errno.ENOENT )

    def open( self, filename, mode, buffering=None ):
        # Validate mode before opening file
        for c in mode:
            # Modes may be "r"/"rt"/"tr" or "rb"/"br"
            if c not in "rbt":
                raise OSError( errno.EINVAL )
            
        dir_entry = self._find_file( filename )
        if dir_entry is None: 
            # This is a folder or the root of this file system
            if filename == "/":
                raise OSError( errno.EPERM )
            raise OSError(errno.EISDIR)
            
        data = dir_entry[0] # data 
        if not dir_entry[1]: # compressed
            if "b" in mode:
                return BytesIO( data )
            else:
                return StringIO( data )
        else:
            # Compressed file - late import of deflate library
            from deflate import DeflateIO, AUTO
            uncompressed_stream = DeflateIO( BytesIO( data ),
                            AUTO, 0, True )
            if "b" in mode:
                return uncompressed_stream
            else:
                # This requires to buffer the entire file...
                # Only useful if enough RAM is available.
                return StringIO( uncompressed_stream.read() )
        
    def chdir( self, path ):
        newdir = self._to_absolute_filename( path )
        dir_entry = self._find_file( newdir )
        if dir_entry is None:
            # ok, it's a folder
            self.path = newdir
            return
        raise OSError( -2 )
        
    def getcwd( self ):
        if self.path != "/" and self.path.endswith( "/" ):
            return self.path[0:-1]
        return self.path
        
    def ilistdir( self, path ):
        abspath = self._to_absolute_filename( path ) 
        # Test if folder exists, if not raise OSError ENOENT
        self._find_file( abspath )
        # Find all files
        for filename, dir_entry in self.filedict.items():
            if _get_folder( filename ) == abspath:
                basename = _get_basename( filename )
                if dir_entry is not None:
                    yield ( basename, 0x8000, 0,  dir_entry[2] )
                else:
                    yield ( basename, 0x4000, 0, 0 )
                                         
    def stat( self, filename ): 
        dir_entry = self._find_file( filename )
        if dir_entry is None:
            return (0x4000, 0,0,0,0,0, 0, 0,0,0)
        else:
            return (0x8000, 0,0,0,0,0, dir_entry[2], 0,0,0)
        
    
    def statvfs( self, *args ):
        # statvfs returns:
        # block size, fragment size, blocks, 
        # free blocks, available blocks, files,
        # free inodes1, free_inodes2, mount flags=readonly
        # maximum filename length
        # Return block size of 1 byte = allocation unit
        # No free space. One "inode" per file or folder. 
        # Mount flags: readonly
        # Max filename size 255 (checked in freezeFS)
        #sum_size = sum( d[2] for d in self.filedict.values() if d is not None )
        return (1,1,self.sum_size,  0,0,self.files_folders,  0,0,1, 255)
    
    def mount( self, readonly, x ):
        self.path = "/"
        
    def remove( self, filename ):
        raise OSError( errno.EPERM )
    
    def mkdir( self, *args ):
        raise OSError( errno.EPERM )

    def rename( self, oldfname, newfname ):
        raise OSError( errno.EPERM )
        
    def umount( self ):
        # No specific cleanup necessary on umount.
        pass

def mount_fs( frozen_module_name, target, silent ):
    module = __import__( frozen_module_name )
    
    if target is None:
        raise ValueError("No target specified")

    # Check target doesn't exist
    file_exists = False
    try:
        os.stat( target )
        file_exists = True
    except:
        pass  
    if file_exists:
        raise OSError( errno.EEXIST )
    
    if not silent:
        print( f"mounting {__name__} at {target}." )
        
    os.mount( VfsFrozen( module.direntries, module.sum_size, module.files_folders ), target, readonly=True )
    return True
