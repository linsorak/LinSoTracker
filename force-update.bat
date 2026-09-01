@echo off
setlocal EnableExtensions EnableDelayedExpansion
title LinSoTracker - Force update

REM Forces a reinstall of the latest published build, whatever version is
REM currently installed.
REM
REM Place this file in the LinSoTracker folder, next to LinSoTracker.exe and
REM updater.exe, then double-click it. It uses updater.exe when present, and
REM falls back to a direct download otherwise.

cd /d "%~dp0."
set "INSTALL_DIR=%~dp0"
set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"
set "JSON_URL=http://linsotracker.com/tracker/update.json"
set "WORK_DIR=%TEMP%\LinSoTracker-force-update"

echo ============================================
echo   LinSoTracker - forced update
echo ============================================
echo Folder: %INSTALL_DIR%
echo.

if not exist "%INSTALL_DIR%\LinSoTracker.exe" goto :wrong_folder

tasklist /FI "IMAGENAME eq LinSoTracker.exe" 2>nul | find /i "LinSoTracker.exe" >nul
if not errorlevel 1 goto :still_running

REM ---- preferred path: hand over to the shipped updater -------------------
if not exist "%INSTALL_DIR%\updater.exe" goto :direct_download

echo Starting updater.exe ...
echo A progress window will open. Do not close it.
echo.
REM 0.0.0.0 is never the published version, so the updater always downloads.
"%INSTALL_DIR%\updater.exe" --current_version 0.0.0.0 --url_json "%JSON_URL%" --destination_path "%INSTALL_DIR%" --file_to_execute "%INSTALL_DIR%\LinSoTracker.exe"
if errorlevel 1 goto :updater_failed
echo Done.
exit /b 0

REM ---- fallback: no updater.exe in this folder ----------------------------
:direct_download
echo updater.exe is not in this folder - downloading directly.
echo.

where curl.exe >nul 2>&1
if errorlevel 1 goto :no_tools
where tar.exe >nul 2>&1
if errorlevel 1 goto :no_tools

rmdir /s /q "%WORK_DIR%" 2>nul
mkdir "%WORK_DIR%" 2>nul
if not exist "%WORK_DIR%" goto :fail_temp

echo [1/4] Reading the version manifest...
curl -s -L --fail -o "%WORK_DIR%\update.json" "%JSON_URL%"
if errorlevel 1 goto :no_network

REM "lastest_version" appears once for the application and once per official
REM template. The application one comes first, so only the first hit is kept.
set "LINE="
for /f "delims=" %%L in ('findstr /i "lastest_version" "%WORK_DIR%\update.json"') do if not defined LINE set "LINE=%%L"
if not defined LINE goto :bad_manifest
set LINE=!LINE:"=!
set LINE=!LINE: =!
for /f "tokens=2 delims=:," %%V in ("!LINE!") do set "VERSION=%%V"
if not defined VERSION goto :bad_manifest
echo !VERSION!| findstr /r /c:"^[0-9][0-9.]*[0-9]$" >nul
if errorlevel 1 goto :bad_manifest

set "URL=https://linsotracker.com/tracker/patchs/LinSoTracker-win-!VERSION!.zip"
echo       Latest published version: !VERSION!
echo.

echo [2/4] Downloading !VERSION! ...
curl -L --fail -o "%WORK_DIR%\update.zip" "!URL!"
if errorlevel 1 goto :no_archive

set "ZIP_SIZE=0"
for %%A in ("%WORK_DIR%\update.zip") do set "ZIP_SIZE=%%~zA"
if !ZIP_SIZE! LSS 1000000 goto :bad_archive
echo       Downloaded !ZIP_SIZE! bytes.
echo.

echo [3/4] Extracting...
mkdir "%WORK_DIR%\staging" 2>nul
tar -xf "%WORK_DIR%\update.zip" -C "%WORK_DIR%\staging"
if errorlevel 1 goto :bad_archive
if not exist "%WORK_DIR%\staging\LinSoTracker.exe" goto :bad_archive

echo [4/4] Installing...
robocopy "%WORK_DIR%\staging" "%INSTALL_DIR%" /E /IS /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :copy_failed

rmdir /s /q "%WORK_DIR%" 2>nul

echo.
echo ============================================
echo   LinSoTracker !VERSION! installed.
echo ============================================
echo.
echo Starting the tracker...
start "" /D "%INSTALL_DIR%" "%INSTALL_DIR%\LinSoTracker.exe"
exit /b 0

:wrong_folder
echo [ERROR] LinSoTracker.exe was not found in this folder.
echo.
echo         Move this file into the LinSoTracker folder, next to
echo         LinSoTracker.exe and updater.exe, then run it again.
goto :halt

:still_running
echo [ERROR] LinSoTracker is currently running.
echo         Close it completely, then run this file again.
goto :halt

:updater_failed
echo [ERROR] updater.exe returned an error.
echo         Run this file again. If it keeps failing, report it on Discord.
goto :halt

:no_tools
echo [ERROR] curl.exe or tar.exe is missing from this system.
echo         They ship with Windows 10 version 1803 and newer.
echo         Download the build manually from linsotracker.com instead.
goto :halt

:fail_temp
echo [ERROR] Cannot create the temporary folder:
echo         %WORK_DIR%
goto :halt

:no_network
echo [ERROR] Cannot reach linsotracker.com.
echo         Check your internet connection, a VPN or a firewall.
goto :halt

:bad_manifest
echo [ERROR] The version manifest could not be read.
echo         Report this on Discord.
goto :halt

:no_archive
echo [ERROR] Download failed:
echo         !URL!
echo         The archive may not be published yet. Report this on Discord.
goto :halt

:bad_archive
echo [ERROR] The downloaded archive is invalid or incomplete.
echo         Run this file again. If it keeps failing, report it on Discord.
goto :halt

:copy_failed
echo [ERROR] The files could not be written into:
echo         %INSTALL_DIR%
echo         Make sure LinSoTracker is closed, and try running this file
echo         as administrator if the folder is protected.
goto :halt

:halt
echo.
pause
exit /b 1
