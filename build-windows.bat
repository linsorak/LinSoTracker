@REM call activate LinSoTrackerRelease

rmdir /s /q "dist"
rmdir /s /q "_pycache_"
rmdir /s /q "build"
del "LinSoTracker.spec"

@REM Sync properties.rc (filevers/prodvers/FileVersion/ProductVersion) to self.version
python Tools\sync_version.py

pyinstaller --clean --onefile --version-file "properties.rc" --icon "icon.ico"  "LinSoTracker.py"

robocopy "templates" "dist/templates" /E
robocopy "devtemplates" "dist/devtemplates" /E
copy tracker.data dist\tracker.data /Y

ren dist LinSoTracker-Windows
7z a -tzip LinSoTracker-win-x64.zip LinSoTracker-Windows

@REM call conda deactivate