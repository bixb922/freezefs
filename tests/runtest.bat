rem create testfiles folder with testfiles locally
test.py
rem create freezeFS file to mount and test
python ..\freezefs testfiles frozenfiles_mount.py --target /fz --on-import mount
mpy-cross frozenfiles_mount.py
mpremote cp frozenfiles_mount.mpy : 
mpremote run test.py
