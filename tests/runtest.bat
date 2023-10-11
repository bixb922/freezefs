rem create testfiles folder with testfiles locally
test.py
rem create freezeFS file to mount and test
python ..\freezefs testfiles frozenfiles_mount.py --target /fz --on-import mount
mpremote cp frozenfiles_mount.py : 
mpremote run test.py
