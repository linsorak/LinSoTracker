#/bin/bash

rm -rf dist build
pyinstaller --noconfirm --onefile --windowed --icon icon.ico -n LinSoTracker LinSoTracker.py
cp -r tracker.data templates dist
mv dist LinSoTracker-Linux
zip -r9 LinSoTracker-linux-x64.zip LinSoTracker-Linux