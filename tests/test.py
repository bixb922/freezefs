# (c) 2023 Hermann Paul von Borries
# MIT License


# Test path: /./folder /folder/../folder /..

import sys
import os
import unittest
import time
import errno
import gc
import shutil # mpremote mip install shutil (standard from micropython-lib)

PYTHON = sys.implementation.name
if PYTHON == "cpython":
    from pathlib import Path
else:
    Path = lambda *args : "".join( args )

referencefolder = "testfiles"
testfolder = "fz"

test_folders = [ "sub1", "sub2", "sub1/sub2", "sub1/sub2/sub3" ]

def iter_both_test_folders():
    for folder in test_folders:
        yield Path( referencefolder + "/" + folder ), Path( testfolder + "/" + folder )

# txt files are ascii, bin are binary, uni are unicode
test_files = [
    ("file1.txt", 100),
    ("file2.txt", 0),
    ("file3.bin", 100),
    ("file4.bin", 0),
    ("file5.txt", 1), 
    ("file6.uni", 10), # Size of unicode files is in characters, not bytes
    ("file7.uni", 100), # Size of unicode files is in characters, not bytes
    ("file8.uni", 1000), # Size of unicode files is in characters, not bytes
    ("file9.uni", 10000), # Size of unicode files is in characters, not bytes
    ("sub1/file1.txt", 10),
    ("sub1/file2.txt", 20),
    ("sub1/sub2/file1.txt", 13),
    ("sub1/sub2/file2.txt", 11 ),
    ("sub1/sub2/file3.txt", 21 ),
    ("sub1/sub2/sub3/file4.txt", 77 )
]

        
def iter_both_test_files( filetype=None ):
    for f, length in test_files:
        if filetype == None or f.endswith( "." + filetype ):
            yield Path( referencefolder + "/" + f ), Path( testfolder + "/" + f )


# Old fashioned pseudorandom generator to generate
# same test data on PC and microcontroller
rand = 11
m = 2**31-1
a = 1664525
c = 1013904223
def getrand(n):
    global rand
    rand += (a*rand+c)%m
    return rand%n


# Some characters for testing
unicodes = "aáéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑ" + chr(0x1f600) + chr(0x1f603) + chr(0x1f604)
asciis = "".join( chr(x) for x in range(0,127) ) + "\r" + "\n" + "\t"

def write_str( filename, length, alphabet ):
    # Don't use newline to mirror Micropython
    if PYTHON == "cpython":
        fileopen = lambda fn : open( filename, "wt", encoding="utf-8", newline="" )
    else:
        fileopen = lambda fn : open( filename, "wt" )
    with fileopen( filename ) as file:
        for _ in range(length):
            p = getrand( len(alphabet) )
            s = alphabet[p:p+1]
            file.write( s )

def write_text( filename, length ):
    write_str( filename, length, asciis ) 

def write_bin( filename, length ):
    with open( filename, "wb" ) as file:
        for _ in range(length):
            b = bytearray(1)
            b[0] = getrand( 255 ) 
            file.write( b )

       
def write_uni( filename, length ):
    if length <= 10:
        write_str( filename, length, unicodes )
    else:
        write_str( filename, length, asciis + unicodes )

def make_testfiles( ): 
    try:
        shutil.rmtree( referencefolder )
    except:
        pass
    # This has to run both on PC/Python and MicroPython
    # Create folders
    for f in [""] + test_folders:
        if f == "":
            filename = referencefolder
        else:
            filename = referencefolder + "/" + f
        print("make_testfiles: Create folder", filename )
        try:
            os.mkdir( Path( filename ) )
        except Exception as e:
            print(f"make_testfiles: Could not create folder {filename}, {e}" )
            # Ignore errors, sometimes delete folder fails on Windows
     
    # Write files
    for f, length in test_files:
        filename = Path( referencefolder + "/" + f )
        if ".txt" in f:
            write_text( filename, length )
        elif ".bin" in f:
            write_bin( filename, length )
        elif ".uni" in f:
            write_uni( filename, length )
    print("make_testfiles: Test files created in folder ", referencefolder)

    
class TestFiles(unittest.TestCase):

    def compare_lists( self, list1, list2 ):
        # With infinite memory, this could compare tuple( list1 ) with tuple( list2 )
        self.assertEqual( len(list1), len(list2) )
        for i, p in enumerate( list1 ):
            self.assertEqual( p, list2[i] )
         
         
    def check_testfile_size( self, folder ):
        for f, defsize in test_files:
            if ".uni" in f:
                # File size of unicode files is in characters, not bytes
                # can't compare here
                continue
            filename = "/" + folder + "/" + f
            filename = filename.replace("//", "/")
            try:
                size = os.stat( filename )[6]
            except OSError:
                break
            self.assertEqual( defsize, size )

    def test_full_read_binary( self ):
        for filename1, filename2 in iter_both_test_files( "bin" ):
            with open( filename1, "rb" ) as file1:
                c1 = file1.read()
            with open( filename2, "rb") as file2:
                c2 = file2.read()
            self.assertEqual( c1, c2 )

    def test_full_read_text( self ):
        for filename1, filename2 in iter_both_test_files( "txt" ):
            with open( filename1, "r" ) as file1:
                c1 = file1.read()
            with open( filename2, "r" ) as file2:
                c2 = file2.read()
            
            self.assertEqual( c1, c2 )

    def test_full_try_binary_as_text( self ):
        for filename1, filename2 in iter_both_test_files( "bin" ):
            if os.stat( filename1 )[6] == 0 and os.stat( filename2 )[6] == 0:
            # Length 0, will not raise error
                continue
            # Reading binary file as text should raise UnicodeError
            with self.assertRaises( UnicodeError ):
                with open( filename1, "r" ) as file1:
                    c1 = file1.read()
            with self.assertRaises( UnicodeError ):
                with open( filename2, "r") as file2:
                    c2 = file2.read()
           

    def test_full_read_0( self ):
        for file1, file2 in iter_both_test_files( "txt" ):
            with open( file1, "r" ) as file:
                c1 = file.read(0)
                d1 = file.read(10)
                e1 = file.read(0)
                f1 = file.read(20)
            with open( file2, "r" ) as file:
                c2 = file.read(0)
                d2 = file.read(10)
                e2 = file.read(0)
                f2 = file.read(20)
            
            self.assertEqual( c1, c2 )
            self.assertEqual( d1, d2 )
            self.assertEqual( e1, e2 )
            self.assertEqual( f1, f2 )

    
    def test_read_entire_text( self ):
        print("")
        for filetype in ("txt", "uni"):
            for filename1, filename2 in iter_both_test_files( filetype ):
                
                with open( filename1, "r") as file1:
                    gc.collect()
                    data1 = file1.read()
                    print(f"test_read_entire_text {filename1=} {len(data1)=} characters")
                with open( filename2, "r") as file2:
                    gc.collect()
                    data2 = file2.read()
                    print(f"test_read_entire_text {filename2=} {len(data2)=} characters")
                self.assertEqual( data1, data2 )
                data1 = None
                data2 = None
                gc.collect()
                
    def test_read_text( self ):
        for filetype in ("txt", "uni"):
            for length in ( 1, 10, 100, 1000 ):
                print(f"Test read text with read({length})" )
                for filename1, filename2 in iter_both_test_files( filetype ):
                    file1 = open( filename1, "r" )
                    file2 = open( filename2, "r" )
                    while True:
                        data1 = file1.read( length )
                        data2 = file2.read( length )
                        self.assertEqual( data1, data2 )
                        if not data1:
                            break
                    file1.close()
                    file2.close()


    def test_readline( self ):
        for filetype in ("txt", "uni"):
            for filename1, filename2 in iter_both_test_files( filetype ):
                for mode in ("r", "rb"):
                    file1 = open( filename1, mode )
                    file2 = open( filename2, mode )
                    while True:
                        data1 = file1.readline()
                        data2 = file2.readline()
                        self.assertEqual( data1, data2 )
                        if not data1:
                            break
                    file1.close()
                    file2.close()

               

    def test_readline3( self ):
        for filetype in ("txt", "uni"):
            for file1, file2 in iter_both_test_files( filetype ):
                with open( file1, "r" ) as file:
                    parts1 = [ _ for _ in file ]
                with open( file2, "r") as file:
                    parts2 = [ _ for _ in file ]
                self.compare_lists( parts1, parts2 )


    def test_read_binary( self ):
        for length in ( 1, 10, 100, 1000 ):
            print(f"Test read binary with read({length})" )
            for filename1, filename2 in iter_both_test_files( "bin" ):
                file1 = open( filename1, "rb" )
                file2 = open( filename2, "rb" )
                while True:
                    data1 = file1.read( length )
                    data2 = file2.read( length )
                    self.assertEqual( data1, data2 )
                    if not data2:
                        break
                file1.close()
                file2.close()
 
    def test_listdir( self ):
        for rf, tf in iter_both_test_folders():
            files1 = os.listdir( "/" + rf )
            files2 = os.listdir( "/" + tf )
            self.assertEqual( tuple(files1), tuple(files2) )
    
    def test_chdir( self ):
        for fol in test_folders:
            os.chdir( "/" + referencefolder + "/" + fol )
            files1 = os.listdir( "" )
            os.chdir( "/" + testfolder + "/" + fol )
            files2 = os.listdir( "" )
            self.assertEqual( tuple( files1 ), tuple( files2 ) )

        # chdir with ending /
        os.chdir( "/" + referencefolder + "/sub1/"  )
        self.assertEqual( "/" + referencefolder + "/sub1", os.getcwd() )
        os.stat( "file9.uni" )
        files1 = os.listdir( "" )
        
        
        os.chdir( "/" + testfolder + "/sub1/" )
        self.assertEqual( "/" + testfolder + "/sub1", os.getcwd() )
        os.stat( "file9.uni" )
        files2 = os.listdir( "" )
  
        self.assertEqual( tuple( files1 ), tuple( files2 ) )

        
        # Bad chdir: to nonexistent folder
        for folder in ( referencefolder, testfolder ):
            with self.assertRaises( OSError ):
                os.chdir("/" + folder + "/nonexistent")

        # Bad chdir: to file
        for folder in ( referencefolder, testfolder ):
            with self.assertRaises( OSError ):
                os.chdir("/" + folder + "/file1.txt")

        # chdir to relative path
        for folder in ( referencefolder, testfolder ):
            newdir = "/" + folder
            os.chdir( newdir )
            self.assertEqual( mewdir, os.getcwd() )
            newdir += "sub1"
            os.chdir( "sub1" )
            self.assertEqual( mewdir, os.getcwd() )
            newdir += "sub2"
            os.chdir( "sub2" )
            self.assertEqual( mewdir, os.getcwd() )

        os.chdir(rf + "/sub1/sub2/.." )
        files1 = os.listdir()
        os.chdir( tf + "/sub1/sub2/.." )
        files2 = os.listdir()
        self.assertEqual(files1, files2 )
        
        os.chdir(rf + "/sub1/sub2/." )
        files1 = os.listdir()
        os.chdir( tf + "/sub1/sub2/." )
        files2 = os.listdir()
        self.assertEqual(files1, files2 )

        os.chdir(rf + "/sub1/./sub2/.." )
        files1 = os.listdir()
        os.chdir( tf + "/sub1/./sub2/.." )
        files2 = os.listdir()
        self.assertEqual(files1, files2 )
        
        os.chdir(rf + "/,/sub1/sub2/.." )
        files1 = os.listdir()
        os.chdir( tf + "/./sub1/sub2/.." )
        files2 = os.listdir()
        self.assertEqual(files1, files2 )

        
        os.chdir("/")
        

    def test_ilistdir( self ):
        for rf, tf in iter_both_test_folders():
            files1 = [ _ for _ in os.listdir( "/" + rf ) ]
            files2 = [ _ for _ in os.listdir( "/" + tf ) ]
            self.assertEqual( tuple(files1), tuple(files2) )

        
    def test_stat( self ):
        for filename, length in test_files:
            file1 = "/" + testfolder + "/" + filename
            file2 = "/" + referencefolder + "/" + filename
            stat1 = os.stat( file1 )[0:6]
            stat2 = os.stat( file2 )[0:6]
        self.assertEqual( stat1, stat2 )

        stat1 = os.stat( testfolder )[0:6]
        stat2 = os.stat( referencefolder )[0:6]
        self.assertEqual( stat1, stat2 )
    
    def test_parent_dir( self ):
        rf = "/" + referencefolder
        tf = "/" + testfolder
        stat1 = os.stat( rf + "/sub1/sub2/../file1.txt" )
        stat2 = os.stat( tf + "/sub1/sub2/../file1.txt" )
        self.assertEqual( stat1[0:6], stat2[0:6] )
        
        os.chdir( rf + "/sub1/../sub1/sub2")
        p1 = os.getcwd().replace( rf, "/<root>")
        os.chdir( tf + "/sub1/../sub1/sub2")
        p2 = os.getcwd().replace( tf, "/<root>")
        self.assertEqual( p1, p2 )
        
        with self.assertRaises( OSError ):
            os.chdir( tf + "/.." )


        os.chdir("/")
        
    def test_stat_folder( self ):
        for filename in test_folders:
            file1 = "/" + testfolder + "/" + filename
            file2 = "/" + referencefolder + "/" + filename
            stat1 = os.stat( file1 )[0:6]
            stat2 = os.stat( file2 )[0:6]
        self.assertEqual( stat1, stat2 )

    def test_chdir( self ):
        tf = "/" + testfolder
        rf = "/" + referencefolder
        os.chdir( tf )
        self.assertEqual( os.getcwd(), tf )
        files1 = os.listdir("")
        files2 = os.listdir( rf )
        self.assertEqual( tuple( files1 ), tuple( files2 ) )

        os.chdir("sub1")
        self.assertEqual( os.getcwd(), tf +"/sub1")
        files1 = os.listdir("")
        files2 = os.listdir( rf + "/sub1" )
        self.assertEqual( tuple( files1 ), tuple( files2 ) )

        os.chdir( tf +"/sub1")
        self.assertEqual( os.getcwd(), tf + "/sub1")
        files1 = os.listdir("")
        files2 = os.listdir( rf  + "/sub1" )
        self.assertEqual( tuple( files1 ), tuple( files2 ) )
        
        os.chdir("sub2")
        self.assertEqual( os.getcwd(), "/fz/sub1/sub2")
        files1 = os.listdir("")
        files2 = os.listdir( rf  + "/sub1/sub2" )
        self.assertEqual( tuple( files1 ), tuple( files2 ) )

        os.chdir("sub3")
        self.assertEqual( os.getcwd(), "/fz/sub1/sub2/sub3")
        files1 = os.listdir("")
        files2 = os.listdir( rf  + "/sub1/sub2/sub3" )
        self.assertEqual( tuple( files1 ), tuple( files2 ) )
        
        os.chdir( "/fz" )
        self.assertEqual( os.getcwd(), "/fz")
        files1 = os.listdir("")
        files2 = os.listdir( "/" + referencefolder  )
        self.assertEqual( tuple( files1 ), tuple( files2 ) )
        
        os.chdir("/")
    
    def test_remove( self ):
        with self.assertRaises( OSError ):
            os.remove( testfolder +"/file1.txt")
    
    def test_write_not_allowed( self ):
        file1 = testfolder +"/file1.txt"
        with self.assertRaises( OSError ):
            open( file1, "w")
        with self.assertRaises( OSError ):
            open( file1, "wb")
        with self.assertRaises( OSError ):
            open( file1, "r+")
        with self.assertRaises( OSError ):
            open( file1, "a")
            
        with self.assertRaises( OSError ):
            os.rename( file1, testfolder + "/a.a")
            
        with self.assertRaises( OSError ):
            os.remove( file1 )
            

    def test_seek_binary( self ):
        # Test seek/tell on binary files
        file1 = open( referencefolder + "/file3.bin" ,"rb")
        file2 = open( testfolder + "/file3.bin", "rb" )
        for i in [1,51,2,92]:
            file1.seek(i)
            file2.seek(i)
            self.assertEqual( file1.tell(), file2.tell() )
            c1 = file1.read(1)
            c2 = file2.read(1)
            self.assertEqual( c1, c2 )

        for i in [1,51,-29,33]:
            file1.seek(i,1)
            file2.seek(i,1)
            self.assertEqual( file1.tell(), file2.tell() )
            c1 = file1.read(1)
            c2 = file2.read(1)
            self.assertEqual( c1, c2 )

        file1.seek(i,2)
        file2.seek(i,2)
        self.assertEqual( file1.tell(), file2.tell() )
        c1 = file1.read(1)
        c2 = file2.read(1)
        self.assertEqual( c1, c2 )
 
    def test_flush( self ):
        file1 = open( "/" + referencefolder + "/file3.bin" ,"rb")
        file2 = open( "/" + testfolder + "/file3.bin", "rb" )
        self.assertEqual( file1.flush(), file2.flush() )
     
    def test_statvfs( self ):
        t = os.statvfs( "/" + testfolder )
        self.assertEqual( (1, 1, 13578, 0, 0, 19, 0, 0, 1, 255), t )


 
def timing_tests():
    print("\nTiming tests. /testfolder is on the standard file system, /fz is the VfsFrozen file system running in RAM.\n" )  
    class HowLong:
        def __init__( self, name ):
            self.name = name
        def __enter__( self ):
            self.t0 = time.ticks_ms()
            return self
        def __exit__( self, exception_type, exception_value, traceback ):
            print(self.name, time.ticks_diff( time.ticks_ms(), self.t0 ))

    size = os.stat( referencefolder + "/file9.uni" )[6]
    
    for mode in ("r", "rb"):
        for i in (1,10,100,1000):
            for folder in (referencefolder, testfolder ) :
                filename = folder + "/file9.uni"
                size = os.stat( filename )[6]
                with HowLong(f"Timed file.read({i:4d})  for {filename:19s}, size={size} bytes, mode={mode:2s}, msec="):
                    with open( filename, mode ) as file:
                        s = ""
                        while True:
                            r = file.read(i)
                            if len(r) == 0:
                                break
               

    for folder in (referencefolder, testfolder ) :
        filename = folder + "/file9.uni"
        with HowLong(f"Timed file.readline()  for {filename:19s}, size={size} bytes, mode=rb, msec="):
            with open( filename, "rb") as file:
                while True:
                    line = file.readline()
                    if len(line) == 0:
                        break



 
if __name__ == "__main__":
    if PYTHON == "cpython":
        make_testfiles()
        sys.exit()
    gc.collect()
    # Collect frequently
    gc.threshold( gc.mem_free()//2)
    make_testfiles()
    
    import frozenfiles_mount
    
    unittest.main()
    
    # Run without unittest:
    #t = TestFiles() 
    #t.test_chdir()
    
    timing_tests()
    
