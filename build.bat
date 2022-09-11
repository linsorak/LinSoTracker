call activate LinSoTracker

rmdir /s /q "dist"
rmdir /s /q "_pycache_"
rmdir /s /q "build"
del "LinSoTracker.spec"

pyinstaller "LinSoTracker.py" --clean --onefile --version-file "properties.rc" --icon "icon.ico"

robocopy "templates" "dist/templates" /E
copy tracker.data dist\tracker.data /Y

call conda deactivate