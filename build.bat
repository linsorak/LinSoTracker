@echo off
call .venv\Scripts\activate

:: Nettoyage des anciens fichiers
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "build" rmdir /s /q "build"
if exist "LinSoTracker.spec" del "LinSoTracker.spec"

:: Création de l'exécutable avec PyInstaller
pyinstaller --clean --onefile --version-file "properties.rc" --icon "icon.ico" "LinSoTracker.py"
if %ERRORLEVEL% NEQ 0 pause

:: Copie des fichiers nécessaires
robocopy "templates" "dist/templates" /E /NFL /NDL /NJH /NJS /NC /NS /NP
if exist "tracker.data" copy tracker.data dist\tracker.data /Y
if exist ".dev" copy .dev dist\.dev /Y

echo Build terminé avec succès !
pause
