# (c) 2023 Hermann Paul von Borries
# MIT License

import os
import errno
from io import BytesIO, StringIO
from collections import OrderedDict

# The filelist of the generated .py is a list of ( filename, direntry ) tuples.
# direntry in turn is:
#   For a folder:
#       None
#   For a file:
#      ( data, is unicode, original size in bytes )
#

# The root / is not stored in the filelist.
_DIRENTRY_DATA = 0
_DIRENTRY_TEXT = 1
_DIRENTRY_SIZE = 2

# The filelist is converted to filedict = OrderedDict( filelist ). The order
# is relevant for ilistdir (no sort necessary) and for deploy (folders
# are created before the files are copied). 


def get_basename( filename ):
    return filename.split("/")[-1]

def get_folder( filename ):
    basename = get_basename( filename )
    folder = filename[0:-len(basename)-1]
    if folder == "":
        folder = "/"
    return folder
   
class VfsFrozen:
    # see https://github.com/micropython/micropython/blob/master/tools/mpremote/mpremote/pyboardextended.py 
    # for file system.
    def __init__( self, direntries ):
        self.filedict = OrderedDict( direntries )
        self.path = "/"
    
    def _to_absolute_filename( self, filename ):
        f = filename
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
        filename = "".join( "/" + p for p in parts )
        filename = filename.replace("//", "/")
        return filename
        
    def _find_file( self, filename ):
        filename = self._to_absolute_filename( filename )
        if filename == "/":
            # The root is a folder. filedict doesn't have 
            # the root.
            return None
        if filename in self.filedict:
            # Return the file directory entry (dir_entry)
            return self.filedict[filename]
        else:
            raise OSError( errno.ENOENT )
             
    def open( self, filename, mode, buffering=None ):
        if mode not in ("r", "rb", "rt"):
            # Validate mode before opening file
            raise OSError( errno.EINVAL )
            
        dir_entry = self._find_file( filename )
        if dir_entry is None: 
            # This is a folder or the root.
            if filename == "/":
                raise OSError( errno.EPERM )
            raise OSError(errno.EISDIR)
            
        data = dir_entry[_DIRENTRY_DATA] 
        # data can be a str constant or a bytes constant.
        # BytesIO and StringIO accept both.
        if mode == "rb":
            return BytesIO( data )
        else:
            return StringIO( data )
        
    def chdir( self, path ):
        newdir = self._to_absolute_filename( path )
        direntry = self._find_file( newdir )
        if direntry is None:
            # It's a folder
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
            if get_folder( filename ) == abspath:
                basename = get_basename( filename )
                if dir_entry is not None:
                    yield ( basename, 0x8000, 0,  dir_entry[_DIRENTRY_SIZE] )
                else:
                    yield ( basename, 0x4000, 0, 0 )
                                         
    def stat( self, filename ): 
        dir_entry = self._find_file( filename )
        if dir_entry is None:
            return (0x4000, 0,0,0,0,0, 0, 0,0,0)
        else:
            return (0x8000, 0,0,0,0,0, dir_entry[_DIRENTRY_SIZE]  , 0,0,0)
        
    
    def statvfs( self, *args ):
        # statvfs returns:
        # block size, fragment size, blocks, 
        # free blocks, available blocks, files,
        # free inodes1, free_inodes2, mount flags=readonly
        # maximum filename length
        # Return block size of 1 byte = allocation unit
        # No free space. One "inode" per file or folder. 
        # Mount flags: readonly
        # Max filename size 255 (checked in freeze2py)
        sum_size = sum( d[_DIRENTRY_SIZE] for d in self.filedict.values() if d is not None )
        return (1,1,sum_size,  0,0,len( self.filedict ),  0,0,1, 255)
    
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



# Module level functions: mount_fs(), umount_fs() and deploy_fs()
# These are called from the generated .py module.
def _verbose_print( silent, function, *args ):
    if silent:
        return
    print( __name__, function + ":", *args )

def _file_exists( file ): 
    try:
        os.stat( file )
        return True
    except:
        return False
        
# Implement functionality of the frozen files module.
def mount_fs( direntries, mount_point, silent ):
    if _file_exists( mount_point ):
        raise OSError( errno.EEXIST )
        
    fs = VfsFrozen( direntries )
    os.mount( fs, mount_point, readonly=True )
    
    _verbose_print( silent, "mount", f"mounted filesystem at {mount_point}." )

def umount_fs( mount_point, silent ):
    if mount_point:
        os.umount( mount_point )
        _verbose_print( silent, "umount", f"{mount_point} unmounted." )
        
def deploy_fs( direntries, target, silent ):
    # Test if target already exists, this means "already copied before".
    files_in_target = 0
    try:
        files_in_target = len( os.listdir( target ) )
    except OSError:
        pass
    if files_in_target:
        _verbose_print( silent, "deploy",  f"Target {target} not empty, no files copied." )
        return

    # Create parent folders of the target folder and 
    # the target folder, if not yet created
    path = ""
    for p in target.split("/"):
        path += "/" + p
        if path == "/":
            # In case of target=/ don't try to create the root.
            continue
        try:
            os.mkdir( path )
            _verbose_print( silent, "deploy",  f"folder {target} created." )
        except OSError:
            _verbose_print( silent, "deploy",  f"folder {target} does already exist." )
            pass

    # Don't mount the frozen file system,
    # access file data through the internal file structure.
    for filename, direntry in direntries:
        dest = target + filename
        if direntry:
            # Copy file
            try:
                with open( dest, "wb") as file:
                    file.write( direntry[_DIRENTRY_DATA] )
            except Exception as e:
                _verbose_print( silent, "deploy",  f"Could not copy file {dest}, {e}" )
                raise
            _verbose_print( silent, "deploy",  f"file {dest} copied." )
        else:
            # Create folder (subfolders of the target folder)
            # Since the filelist is ordered by filename, parent folders
            # get created before their subfolders.
            try:
                os.mkdir( dest )
            except Exception as e:
                _verbose_print( silent, "deploy",  f"Could not create folder {dest}, {e}" )
                raise
            _verbose_print( silent, "deploy",  f"Folder {dest} created" )
