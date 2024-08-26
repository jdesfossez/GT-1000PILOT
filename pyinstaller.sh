#!/bin/bash

# MAC normal
#pyinstaller -n GT-1000PILOT --collect-all pygt1000 --collect-all gt1000pilot --add-data "logo.png:." --clean --onefile -i icon.icns --windowed --splash logo.png launch.py
# MAC debug
pyinstaller -n GT-1000PILOT-debug --collect-all pygt1000 --collect-all gt1000pilot --add-data "logo.png:." --clean --onefile -i icon.icns  launch.py



# for windows apparently:
#pyinstaller  -n GT-1000PILOT --collect-all pygt1000 --collect-all gt1000pilot --add-data "logo.png;." --clean --onefile launch.py
