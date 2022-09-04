call activate LinSoTracker

@REM set TCL_LIBRARY=C:\Users\LinSo\.conda\envs\LinSoTracker\Library\lib\tcl8.6
@REM set TK_LIBRARY=C:\Users\LinSo\.conda\envs\LinSoTracker\Library\lib\tcl8.6

@REM https://www.youtube.com/watch?v=gxeRv-cuSas

pyinstaller --clean --onefile --windowed --version-file "properties.rc" --icon "icon.ico"  "LinSoTracker.py"
@REM pyinstaller --noconfirm --clean --onedir --windowed --version-file "properties.rc" --icon "icon.ico"  "LinSoTracker.py"

call conda deactivate