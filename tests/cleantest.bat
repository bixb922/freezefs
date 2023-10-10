mpremote rm frozenfiles_mount.mpy
mpremote run "import shutil;shutil.rmtree('testfiles')"
del frozenfiles_mount.py
del frozenfiles_mount.mpy
del /S /Q testfiles
rmdir /S /Q testfiles