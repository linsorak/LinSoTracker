conda activate pygameDev
pyinstaller --noconfirm --onefile --windowed --icon "icon.ico"  "LinSoTracker.py"
pyinstaller --noconfirm --onefile --console --icon "icon.ico"  "LinSoTracker.py"
pyinstaller --noconfirm --onefile --console --icon "favicon.ico"  "LinSoTracker.py"
python -m nuitka --onefile --enable-plugin=pyqt5 --enable-plugin=numpy --standalone --windows-icon-from-ico="icon.ico"  "LinSoTracker.py"