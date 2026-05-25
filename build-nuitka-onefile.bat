@echo off
setlocal

cd /d "%~dp0"

set "PYTHON=.venv\Scripts\python.exe"
set "OUT_DIR=dist-nuitka-onefile"
set "APP_NAME=LinSoTracker"
set "APP_VERSION="

if not exist "%PYTHON%" (
    echo Python virtual environment not found: %PYTHON%
    echo Create it first, or edit PYTHON in this script.
    pause
    exit /b 1
)

if exist "%OUT_DIR%" rmdir /s /q "%OUT_DIR%"
if exist "%APP_NAME%.build" rmdir /s /q "%APP_NAME%.build"
if exist "%APP_NAME%.dist" rmdir /s /q "%APP_NAME%.dist"
if exist "%APP_NAME%.onefile-build" rmdir /s /q "%APP_NAME%.onefile-build"

echo Installing/updating Nuitka build dependencies...
"%PYTHON%" -m pip install --upgrade nuitka ordered-set zstandard
if %ERRORLEVEL% NEQ 0 goto error

echo Synchronizing version from CoreService.py...
for /f "usebackq delims=" %%v in (`"%PYTHON%" Tools\sync_version.py --print-version`) do set "APP_VERSION=%%v"
if "%APP_VERSION%"=="" goto error
"%PYTHON%" Tools\sync_version.py
if %ERRORLEVEL% NEQ 0 goto error

set "DEV_FILE_OPTION="
if exist ".dev" set "DEV_FILE_OPTION=--include-data-file=.dev=.dev"

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
    --include-package-data=pygame_menu ^
    %DEV_FILE_OPTION% ^
    --product-name="%APP_NAME%" ^
    --file-description="%APP_NAME%" ^
    --product-version="%APP_VERSION%" ^
    --file-version="%APP_VERSION%" ^
    LinSoTracker.py
if %ERRORLEVEL% NEQ 0 goto error

echo Copying external runtime files next to the executable...
if exist "tracker.data" copy tracker.data "%OUT_DIR%\tracker.data" /Y
if %ERRORLEVEL% GEQ 8 goto error

if exist ".dev" copy .dev "%OUT_DIR%\.dev" /Y
if %ERRORLEVEL% GEQ 8 goto error

if exist "templates" robocopy "templates" "%OUT_DIR%\templates" /E /NFL /NDL /NJH /NJS /NC /NS /NP
if %ERRORLEVEL% GEQ 8 goto error

if exist "default_saves" robocopy "default_saves" "%OUT_DIR%\default_saves" /E /NFL /NDL /NJH /NJS /NC /NS /NP
if %ERRORLEVEL% GEQ 8 goto error

if exist "devtemplates" robocopy "devtemplates" "%OUT_DIR%\devtemplates" /E /NFL /NDL /NJH /NJS /NC /NS /NP
if %ERRORLEVEL% GEQ 8 goto error

echo.
echo Build complete:
echo %CD%\%OUT_DIR%\%APP_NAME%.exe
echo.
pause
exit /b 0

:error
echo.
echo Build failed.
pause
exit /b 1
