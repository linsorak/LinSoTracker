#/bin/bash
rm -rf dist build
pip3 install Pillow
pyinstaller --noconfirm --onefile --windowed --icon icon.ico -w --hidden-import PIL LinSoTracker.py
cp -r tracker.data templates .dev dist/LinSoTracker.app/Contents/MacOS/.
mv dist LinSoTracker-macOS
zip -r9 ./LinSoTracker-macos-x64.zip LinSoTracker-macOS/LinSoTracker.app