#/bin/bash
rm -rf dist build
pip3 install Pillow
pyinstaller --noconfirm --onefile --windowed --icon icon.ico -w --hidden-import PIL LinSoTracker.py
cp -r tracker.data templates dist/LinSoTracker.app/Contents/MacOS/.
# mkdir dist/LinSoTracker-install
# cd dist/LinSoTracker-install
# ln -s /Applications Applications
# cp -r ../LinSoTracker.app .
# cd ../..
# dmg ./dist/LinSoTracker-install "dist/LinSoTracker-$(arch)"
mv dist LinSoTracker-macOS
zip -r9 ./LinSoTracker-macos-x64.zip LinSoTracker-macOS/LinSoTracker.app