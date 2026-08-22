@echo off
setlocal

cd /d "%~dp0"

set "PYTHON=.venv\Scripts\python.exe"
set "OUT_DIR=dist-nuitka-onefile"
set "DIST_DIR=dist"
set "APP_NAME=LinSoTracker"
set "APP_VERSION="
set "WINDOWS_VERSION="

rem A venv launcher may still exist while pointing to a Python installation that
rem was moved or upgraded. Run it once instead of checking the file only.
"%PYTHON%" -c "import sys" >nul 2>&1
if errorlevel 1 call :repair_venv
if errorlevel 1 goto error

"%PYTHON%" -c "import sys" >nul 2>&1
if errorlevel 1 (
    echo Python virtual environment is still unusable: %PYTHON%
    goto error
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

:repair_venv
echo Python virtual environment is missing or points to an unavailable Python.
echo Recreating .venv with an installed Python...

rem Prefer the regular Python 3.14 build required by this project.
where py >nul 2>&1
if not errorlevel 1 (
    py -3.14 -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        py -3.14 -m venv --clear .venv
        if errorlevel 1 exit /b 1
        exit /b 0
    )
)

rem Fall back to the first usable python available on PATH.
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        python -m venv --clear .venv
        if errorlevel 1 exit /b 1
        exit /b 0
    )
)

echo No usable Python installation was found.
exit /b 1

:error
echo.
echo Build failed.
pause
exit /b 1
