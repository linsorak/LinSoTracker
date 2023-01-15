#/bin/zsh
dmg(){
  hdiutil create -fs HFS+ -srcfolder "$1" -volname "$2" "$2.dmg"
}

rm -rf dist
pyinstaller --noconfirm --onefile --windowed --icon icon.ico LinSoTracker.py
cp -r tracker.data templates dist/LinSoTracker.app/Contents/MacOS/.
mkdir dist/LinSoTracker-install
cd dist/LinSoTracker-install
ln -s /Applications Applications
cp -r ../LinSoTracker.app .
cd ../..
dmg ./dist/LinSoTracker-install "dist/LinSoTracker-$(arch)"