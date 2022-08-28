call activate LinSoTracker

set TCL_LIBRARY=C:\Users\LinSo\.conda\envs\LinSoTracker\Library\lib\tcl8.6
set TK_LIBRARY=C:\Users\LinSo\.conda\envs\LinSoTracker\Library\lib\tcl8.6

python -m nuitka --onefile --standalone --windows-icon-from-ico="icon.ico"  --enable-plugin=tk-inter --windows-disable-console "LinSoTracker.py"

call conda deactivate