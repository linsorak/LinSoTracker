#/bin/zsh
rm -rf dist
pyinstaller --noconfirm --onefile --windowed --icon icon.ico LinSoTracker.py
mkdir dist/LinSoTracker-install
cd dist/LinSoTracker-install
ln -s /Applications Applications
cp -r ../LinSoTracker.app .
cd ../..