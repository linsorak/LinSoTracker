call activate LinSoTracker

set TCL_LIBRARY=C:\Users\LinSo\.conda\envs\LinSoTracker\Library\lib\tcl8.6
set TK_LIBRARY=C:\Users\LinSo\.conda\envs\LinSoTracker\Library\lib\tcl8.6

pyinstaller --noconfirm --onefile --windowed --icon "icon.ico"  "LinSoTracker.py"

call conda deactivate