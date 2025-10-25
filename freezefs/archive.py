# (c) 2023 Hermann Paul von Borries
# MIT License
# freeze
import argparse
from pathlib import Path, PurePosixPath
from glob import glob
import os
import sys
import time
import zlib

MAX_FILENAME_LEN = 255
VERSION = 2 # Directory entries changed
silent = False
def _verbose_print( *args ):
    if silent:
        return
    print( *args )

varcounter = 0
class FileObject:
    def __init__( self, pc_infolder, path, request_compression, level, wbits ):
        global varcounter
        self.path = path 
        self.request_compression = request_compression
        self.level = level
        self.wbits = wbits
        
        self.mp_path = "/" + self.path.as_posix()
        if len( self.mp_path ) >= MAX_FILENAME_LEN:
            raise ValueError(f"File name too long {self.mp_path}")
        
        self.pc_path = pc_infolder / path
        
        # Assign a variable name and get the file data (raw or compressed)
        self.is_file = self.pc_path.is_file()
        if self.is_file:
            self.varname = f"_f{varcounter}"
            varcounter += 1
            self._get_data()
            
    def _get_data( self ):
        # get data, compress (if indicated)
        # assign self.size, self.compressed_size, self.compressed
        self.data = self._file_read( )
        self.size = len( self.data )
        self.compressed = False
        self.compressed_size = self.size
        if self.request_compression:
            compressed_data = self._zlib_compress( self.data )
            if len( compressed_data ) < self.size:
                # Use compression if compression gives some gain
                self.data = compressed_data
                self.compressed = True
                self.compressed_size = len( self.data )
    
    def _zlib_compress( self, original_data ):
        # This will create the zlib header (8 bytes) that contains level and wbits for deflate
        zco = zlib.compressobj( level=self.level, wbits=self.wbits )
        compressed_data = zco.compress( self.data )
        compressed_data += zco.flush()
        return compressed_data


    def get_pythonized( self ):
        pythonized = ""
        p = 0
        while True:
                chunk = self.data[p:p+16]
                pythonized += f"  {str(chunk)}\\\n"
                if len(chunk) == 0:
                    break
                p += 16
            
        # Last item without \ nor \n 
        return pythonized[0:-2]

    def _file_read( self ):
        with open( self.pc_path, "rb" ) as file:
            return file.read()
    
      
def to_python(  pc_infolder, pc_outfile,
                mc_target, on_import, overwrite,
                silent,
                request_compression, wbits, level ):
        
    # Get files
    files = []
    for path in glob(os.path.join(pc_infolder, "**"), recursive=True):
        rel_path = os.path.relpath(path, pc_infolder)
        fo = FileObject(pc_infolder, Path(rel_path), request_compression, level, wbits)
        files.append( fo )

    # Generate output        
    files.sort( key=lambda fo: fo.mp_path )         
    with open( pc_outfile, "w", encoding="utf-8") as outfile:
        _files_to_python( outfile, files, silent )
        _generate_appended_code( outfile,
                                 mc_target, on_import, overwrite,
                                 silent )
        
    # Print some statistics
    sum_size = sum( fo.size for fo in files if fo.is_file  )
    number_of_files = sum( 1 for fo in files if fo.is_file )
    number_of_folders = len( files ) - number_of_files
    _verbose_print(f"Sum of file sizes {sum_size} bytes, {number_of_files} files {number_of_folders} folders" ) 
    if request_compression and sum_size != 0:
        sum_compressed_size = sum( fo.compressed_size for fo in files if fo.is_file )
        r = sum_compressed_size/sum_size*100
        _verbose_print(f"Sum of compressed sizes {sum_compressed_size}, compressed/original={r:.1f}%")

    return True
    
def _files_to_python( outfile, files, silent ):
        
    # Generate one const for each file
    for fo in files:
        if fo.is_file:
            pythonized = fo.get_pythonized()
            c = ""
            if fo.compressed:
                c = f", compressed level={fo.level} wbits={fo.wbits} compressed size={fo.compressed_size}" 
            outfile.write(f"# {fo.mp_path} size={fo.size}{c}\n" ) 
            outfile.write(f"{fo.varname} = const(\n{pythonized})\n")
            
    # Generate the directory entries
    outfile.write("direntries = const((")
    for fo in files:            
        if fo.is_file:
            direntry = f"( {fo.varname}, {fo.compressed}, {fo.size} )"
            ratio = ""
            if fo.compressed:
                r = fo.compressed_size / fo.size * 100
                ratio = f", compressed/original={r:.0f}%" 
            _verbose_print(f"Appended file   {fo.pc_path} ({fo.size} bytes) as {fo.mp_path}{ratio}" )
        else:
            direntry = f"None"
            _verbose_print(f"Appended folder {fo.pc_path} as {fo.mp_path}")
        outfile.write(f" ( '{fo.mp_path}',  {direntry} ),\n" )
    outfile.write("))\n\n" )
    # Generate file info
    outfile.write(f"version = const({VERSION})\n")
    t = time.localtime()        
    outfile.write(f"date_frozen = const( '{t[0]}/{t[1]:02d}/{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}' )\n\n")
    sum_size = sum( fo.size for fo in files if fo.is_file )
    outfile.write(f"sum_size = const({sum_size})\n" )
    outfile.write(f"files_folders = const({len(files)})\n" )

def _generate_appended_code( outfile,
                             mc_target, on_import,  overwrite, silent ):

        # Compute which drivers to include

        include_file = "ffs" + on_import + ".py"
        # Include driver            
        
        # Open driver files same folder where freezefs.py is
        f = Path( __file__ ).parent / include_file
        with open( f, "r" ) as file:
            while True:
                line = file.readline()
                if line == "":
                    break
                # Don't copy comments nor empty lnes
                s = line.strip(" ")
                if s.startswith("#") or s == "\n":
                    continue
                # Make indents one by one instead of by four
                line = line.replace("    ", " ")
                outfile.write( line )
        outfile.write("\n")
 
        if on_import == "mount":
            outfile.write(f"mount_fs( __name__, '{mc_target}', {silent} )")
        elif on_import == "extract":
            outfile.write(f"extract_fs( __name__, '{mc_target}', '{overwrite}', {silent} )")   


DESC = """freezefs.py
freezefs saves a file structure with subfolders and builds an self-extractable or self-mountable archive in a .py file, optionally with compression, to be frozen as bytecode or extracted.


Examples:
freezefs.py input_folder frozenfiles.py --target=/myfiles --on_import mount
freezefs.py input_folder frozenfiles.py --target=/myfiles --on_import=extract --compress

"""
def main():
    parser = argparse.ArgumentParser(
                "python -m freezefs", 
                description=DESC,
                formatter_class = argparse.RawDescriptionHelpFormatter)
    parser.add_argument('infolder', type=str, help='Input folder path')
    parser.add_argument('outfile', type=str,
                        help='Path and name of output module. Must have .py extension.')

    parser.add_argument("--on-import", "-oi", type=str,
                        dest="on_import",
                        choices=["mount", "extract"],
                        default="mount",
                        help="Action when importing output module. Default is mount.")

    parser.add_argument("--target", "-t", type=str,
                        dest="target",
                        help="For --on-import=mount: mount point."
                             " For --on-import=extract: destination folder."
                             " Default: the infolder."
                             " Example: --target /myfiles. Must start with /")
                             
    parser.add_argument("--overwrite", "-ov", type=str,
                        dest="overwrite",
                        choices=["never", "always"],
                        default="never",
                        help="always: on extract, all files are overwritten. never: on extract, no file is overwritten, only new files are extracted. Default: never. ")
                        
    # Compress parameters
    parser.add_argument("--compress", "-c",
                        dest="compress", default=False,
                        action=argparse.BooleanOptionalAction,
                        help="Compress files before writing to output .py. See python zlib compression." )

    parser.add_argument("--wbits", "-w",
                        type=int,
                        dest="wbits",
                        default=10,
                        help="Compression window of 2**WBITS bytes. Between 9 and 14."
                              " Default is 10 (1024 bytes)")
    parser.add_argument("--level", "-l",
                        type=int,
                        dest="level",
                        default=9,
                        help="Compression level. Between 0 (no compression) and 9 (best compression)."
                             " Default is 9" )
    parser.add_argument("--silent", "-s", 
                        dest="silent", default=False,
                        action="store_true",
                        help="Supress messages printed when mounting/copying files"
                              " and while running this program.")

    args = parser.parse_args()
    
    # Use pathlib paths to make code independent of operati
    pc_infolder = Path( args.infolder )
    pc_outfile = Path( args.outfile )


    
    if not pc_infolder.is_dir():
        quit("Input folder does not exist, or is not a folder")

    if not pc_outfile.suffix.lower() == '.py':
        quit('Output filename must have a .py extension.')

    if args.target:
        mc_target = PurePosixPath( args.target )
        if not args.target.startswith("/"):
            quit( "Target must start with /")

        if args.target.endswith("/") and args.target != "/":
            quit( "Target must not end with /")
    else:
        mc_target = PurePosixPath( "/" + pc_infolder.stem )
        print( f"Target set to {mc_target}" )
        
    if not ( 9 <= args.wbits <= 14 ):
        quit("--wbits must be between 9 and 14")
        
    if not( 0 <= args.level <= 9 ):
        quit("--level must be between 0 and 9" )
      

    if mc_target.stem == pc_outfile.stem:
        print(f"--target must be a different name than output file: {pc_outfile.stem}")
        sys.exit(1)

    _verbose_print(f'Writing Python file {pc_outfile}.') 
    if not to_python( pc_infolder, pc_outfile,
                      mc_target, args.on_import, args.overwrite,
                      args.silent,
                      args.compress, args.wbits, args.level ):
        sys.exit(1)


    module_name = pc_outfile.stem

    if args.on_import == "mount":
        _verbose_print(f"On import the file system will be mounted at {mc_target}." )
    elif args.on_import == "extract":
        if args.overwrite == "never":
            _verbose_print(f"On import the file system will be extracted to {mc_target} writing only files that don't exist." )
        else:
            _verbose_print(f"On import the file system will be extracted to {mc_target} overwriting all files." )

    if args.on_import == "mount" and args.compress:
        # This is the only combination that is heavy in RAM use.
        print("sWarning: --on-import=mount and --compress loads file in RAM when opening files in text 'r' mode. High RAM use." )
        
    _verbose_print(pc_outfile, 'written successfully.')
