@REM call activate LinSoTrackerRelease

rmdir /s /q "dist"
rmdir /s /q "_pycache_"
rmdir /s /q "build"
del "LinSoTracker.spec"

@REM Sync properties.rc (filevers/prodvers/FileVersion/ProductVersion) to self.version
python Tools\sync_version.py

@REM --noconsole replaces the base64/exec ShowWindow trick that used to hide the
@REM console at runtime: that pattern is a textbook antivirus heuristic trigger.
pyinstaller --clean --onefile --noconsole --version-file "properties.rc" --icon "icon.ico"  "LinSoTracker.py"

robocopy "templates" "dist/templates" /E
copy tracker.data dist\tracker.data /Y

@REM updater.exe is a prebuilt binary that pyinstaller does not produce, and the
@REM "rmdir dist" above wipes it, so it must be copied back on every build.
copy bin\updater.exe dist\updater.exe /Y

del /q "LinSoTracker-win-x64.zip" 2>nul
pushd "dist"
7z a -tzip "..\LinSoTracker-win-x64.zip" "*"
popd

@REM call conda deactivate
