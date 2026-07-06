@echo off
setlocal

cd /d "%~dp0"

set "PYTHON=.venv\Scripts\python.exe"
set "OUT_DIR=dist-nuitka-onefile"
set "DIST_DIR=dist"
set "APP_NAME=LinSoTracker"
set "APP_VERSION="
set "WINDOWS_VERSION="

if not exist "%PYTHON%" (
    echo Python virtual environment not found: %PYTHON%
    echo Creating it with the first python found on PATH...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 goto error
)

if exist "%OUT_DIR%" rmdir /s /q "%OUT_DIR%"
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"
if exist "%APP_NAME%.build" rmdir /s /q "%APP_NAME%.build"
if exist "%APP_NAME%.dist" rmdir /s /q "%APP_NAME%.dist"
if exist "%APP_NAME%.onefile-build" rmdir /s /q "%APP_NAME%.onefile-build"

echo Installing/updating Nuitka build dependencies...
"%PYTHON%" -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 goto error
"%PYTHON%" -m pip install --upgrade -r requirements.txt
if %ERRORLEVEL% NEQ 0 goto error
"%PYTHON%" -m pip install --upgrade --force-reinstall "https://github.com/Nuitka/Nuitka/archive/develop.zip"
if %ERRORLEVEL% NEQ 0 goto error

echo Synchronizing version from CoreService.py...
for /f "usebackq delims=" %%v in (`"%PYTHON%" Tools\sync_version.py --print-version`) do set "APP_VERSION=%%v"
if "%APP_VERSION%"=="" goto error
for /f "usebackq delims=" %%v in (`"%PYTHON%" Tools\sync_version.py --print-windows-version`) do set "WINDOWS_VERSION=%%v"
if "%WINDOWS_VERSION%"=="" goto error
"%PYTHON%" Tools\sync_version.py
if %ERRORLEVEL% NEQ 0 goto error

echo Building %APP_NAME% onefile executable with Nuitka...
"%PYTHON%" -m nuitka ^
    --mode=onefile ^
    --assume-yes-for-downloads ^
    --enable-plugin=tk-inter ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=icon.ico ^
    --output-dir="%OUT_DIR%" ^
    --output-filename="%APP_NAME%.exe" ^
    --include-package-data=pygame_gui ^
    --product-name="%APP_NAME%" ^
    --file-description="%APP_NAME%" ^
    --product-version="%WINDOWS_VERSION%" ^
    --file-version="%WINDOWS_VERSION%" ^
    LinSoTracker.py
if %ERRORLEVEL% NEQ 0 goto error

echo Copying external runtime files next to the executable...
if exist "tracker.data" copy tracker.data "%OUT_DIR%\tracker.data" /Y
if %ERRORLEVEL% GEQ 8 goto error

if exist "templates" robocopy "templates" "%OUT_DIR%\templates" /E /NFL /NDL /NJH /NJS /NC /NS /NP
if %ERRORLEVEL% GEQ 8 goto error

set "PACKAGE_NAME=%APP_NAME%-%APP_VERSION%-win"
set "PACKAGE_ZIP=%DIST_DIR%\%PACKAGE_NAME%.zip"

echo Packaging %PACKAGE_NAME%...
if not exist "%OUT_DIR%\%APP_NAME%.exe" (
    echo Missing packaged executable: %OUT_DIR%\%APP_NAME%.exe
    goto error
)
if not exist "%OUT_DIR%\tracker.data" (
    echo Missing packaged data file: %OUT_DIR%\tracker.data
    goto error
)
if not exist "%OUT_DIR%\templates" (
    echo Missing packaged templates directory: %OUT_DIR%\templates
    goto error
)
if exist "%PACKAGE_ZIP%" del /q "%PACKAGE_ZIP%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%OUT_DIR%\LinSoTracker.exe','%OUT_DIR%\tracker.data','%OUT_DIR%\templates' -DestinationPath '%PACKAGE_ZIP%' -Force"
if %ERRORLEVEL% NEQ 0 goto error

echo.
echo Build complete:
echo %CD%\%OUT_DIR%\%APP_NAME%.exe
echo %CD%\%PACKAGE_ZIP%
echo.
pause
exit /b 0

:error
echo.
echo Build failed.
pause
exit /b 1
