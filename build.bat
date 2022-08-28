conda activate pygameDev
pyinstaller --noconfirm --onefile --windowed --icon "icon.ico" "LinSoTracker.py" --version-file "file_version_info.txt"
python -m nuitka --enable-plugin=tk-inter --onefile --windows-icon-from-ico="icon.ico" --version-file="file_version_info.txt" "LinSoTracker.py"