# (c) 2023 Hermann Paul von Borries
# MIT License

import os
import errno
from io import BytesIO
from collections import OrderedDict

# The filelist of the generated .py is a list of ( filename, direntry ) tuples.
# direntry in turn is:
#   For a folder:
#       None
#   For a file:
#      ( data, utf-8 width )
#      data is the file data (bytes data type)
#      utf-8 width is 4 for binary files, 1 to 4 for UTF-8 files with
#      the maximum length of a UTF-8 sequence for a character. This is used
#      to optimize the use of the decode buffer.

# The root / is not stored in the filelist.
_DIRENTRY_DATA = 0
_DIRENTRY_UTF8_WIDTH = 1

# The filelist is converted to filedict = OrderedDict( filelist ). The order
# is relevant for ilistdir (no sort necessary) and for deploy (folders
# are created before the files are copied). 


# A buffer is allocated for files opened in read mode when
# a file.read(size) with size>0 is done. This buffer is used to decode
# UTF-8 sequences to Micropython strings.
# For file.read() without size, file.readline(), file.readlines() no buffer is allocated.
# If the buffer is small, file.read(size) needs to concatenate many small strings
# to get the result. If the buffer is too large, memory is wasted. 
_decode_buffer_size = 400
def set_decode_buffer_size( n ):
    global _decode_buffer_size
    if n < 16:
        return
    _decode_buffer_size = n

def get_basename( filename ):
    return filename.split("/")[-1]

def get_folder( filename ):
    basename = get_basename( filename )
    folder = filename[0:-len(basename)]
    return folder
   
# Count "size" unicode characters in buffer and
# return how many UTF-8 bytes in the buffer that is
# and how many unicode characters were found.  
@micropython.viper
def count_unicode_chars(buffer:ptr8, buffer_len:int, size:int ):

    byte_pos = 0
    chars = 0
    while True:
        c = buffer[byte_pos]
        if   0b00000000 <= c <= 0b01111111: # ASCII
            char_len = 1
        elif 0b11000000 <= c <= 0b11011111: # Start of a 2 byte UTF-8 sequence
            char_len = 2
        elif 0b11100000 <= c <= 0b11101111: # Start of a 3 byte UTF-8 sequence
            char_len = 3
        elif 0b11110000 <= c <= 0b11110111: # Start of a 4 byte UTF-8 sequence
            char_len = 4
        else:
            # Skipping by char_len should ensure we never see 
            # a UTF-8 continuation character, except with a malformed UTF-8
            # file.
            raise UnicodeError
        byte_pos += char_len
        chars += 1
        if chars >= size or byte_pos >= buffer_len:
            break
    return byte_pos, chars     
    
class VfsFrozen:
    # see https://github.com/micropython/micropython/blob/master/tools/mpremote/mpremote/pyboardextended.py 
    # for implmentation of a file system.
    def __init__( self, *args ):
        direntries, self.sum_size, self.files_folders = args
        self.filedict = OrderedDict( direntries )
        self.path = "/"
    
    def _to_absolute_filename( self, filename ):
        if not filename.startswith( "/" ) :
            filename = self.path + filename
        return filename.replace("//", "/")
        
    def _to_absolute_folder( self, filename ):
        # Internal folder names always end with /
        filename = self._to_absolute_filename( filename ) + "/"
        return filename.replace( "//", "/")
        
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
        if mode == "rb":
            return BytesIO_readonly( data )
        else:
            return StringIO_bytes( data, dir_entry[_DIRENTRY_UTF8_WIDTH])
        
    def chdir( self, path ):
        self.path = self._to_absolute_folder( path )
        
    def getcwd( self ):
        if self.path != "/" and self.path.endswith( "/" ):
            return self.path[0:-1]
        return self.path
        
    def ilistdir( self, path ):
        path = self._to_absolute_folder( path )
        for filename, dir_entry in self.filedict.items():
            if get_folder( filename ) == path:
                basename = get_basename( filename )
                if dir_entry is not None:
                    yield ( basename, 0x8000, 0,  len( dir_entry[_DIRENTRY_DATA] ) )
                else:
                    yield ( basename, 0x4000, 0, 0 )
                                         
    def stat( self, filename ): 
        dir_entry = self._find_file( filename )
        if dir_entry is None:
            return (0x4000, 0,0,0,0,0, 0, 0,0,0)
        else:
            return (0x8000, 0,0,0,0,0, len( dir_entry[_DIRENTRY_DATA] )  , 0,0,0)
        
    
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

class StringIO_bytes():

    def __init__( self, data, utf8_width ):
        self.stream = BytesIO( data )
        self.utf8_width = utf8_width
        # UTF-8 decode buffer: allocate as late as possible
        self.buffer = None
        
    def __enter__( self ):
        return self
        
    def __exit__( self, exception_type, exception_value, traceback ):
        self.close()
        
    def close( self ):
        self.stream.close()
        
    @micropython.native
    def read( self, size=-1 ):
        # Read data and decode UTF-8 to Micropython string
        if size < 0:
            return self.stream.read().decode()

        if size == 0:
            return "" 
            
        # max_chars is the maximum unicode characters that can 
        # fit into self.buffer.
        if self.buffer is None:
            self.buffer = bytearray( _decode_buffer_size ) 
        max_chars = len(self.buffer) // self.utf8_width

        result = ""    
        remainder = size  
 
        while remainder > 0: 
            # Invariants: remainder is the remainder of unicode
            # characters to be read.
            # result is the accumulated decoded result.
            # len(result) <= size
            # self.stream.tell() always points to the start of a
            # valid UTF-8 character sequence.
            # origin is the start of the next UTF-8 character to be read
            
            # Read one bufferful of data.  The buffer size is
            # good for max_chars UTF-8 character sequences.
            origin = self.stream.tell()
            bytes_read = self.stream.readinto( self.buffer )
            
            if bytes_read == 0:
                break

            # Count unicode characters in the buffer. By limiting
            # the count to max_chars, we ensure counting never
            # stops at in the midst of a character.

            bytes_used, chars = count_unicode_chars( self.buffer, bytes_read, min( max_chars, remainder ) )
            # Now bytes_used and chars span the same data.

            # Reset the file pointer to point to the first unprocessed byte.
            self.stream.seek( origin + bytes_used )
            # At this point, the next byte of self.stream is always
            # a start of unicode sequence (except for UnicodeError)

            result += self.buffer[0:bytes_used].decode()
            remainder -= chars

        return result

    def readline( self ):
        return self.stream.readline().decode()     
    
    def readinto( self, buffer ):
        # No decoding, readinto for text files reads bytes e.g. bytearray
        return self.stream.readinto( buffer )
        
    def readlines( self ):
        return [ _ for _ in self ]
        
    def __iter__( self ):
        return self
              
    def __next__( self ):
        line = self.readline()
        if not line :
            raise StopIteration
        return line
            
    def seek( self, val, whence=0 ):
        return self.stream.seek( val, whence )
    
    def tell( self ):
        return self.stream.tell()
    
    def flush( self ):
        pass
       
class BytesIO_readonly( BytesIO ):
    def write( *args ):
        # Not allowed, the file is opened readonly
        raise OSError( errno.EPERM )
        
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
def mount_fs( direntries, mount_point, sum_size, files_folders, silent ):
    if _file_exists( mount_point ):
        raise OSError( errno.EEXIST )
        
    fs = VfsFrozen( direntries, sum_size, files_folders )
    os.mount( fs, mount_point )
    
    _verbose_print( silent, "mount", f"mounted filesystem at {mount_point}." )
    return mount_point

def umount_fs( mount_point, silent ):
    if mount_point:
        os.umount( mount_point )
        _verbose_print( silent, "umount", f"{mount_point} unmounted." )
    return None
        
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
    # access file data through
    # the internal file structure.
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
            # Create folder
            # Since the filelist is ordered by filename, parent folders
            # get created before their subfolders.
            try:
                os.mkdir( dest )
            except Exception as e:
                _verbose_print( silent, "deploy",  f"Could not create folder {dest}, {e}" )
                raise
            _verbose_print( silent, "deploy",  f"Folder {dest} created" )
