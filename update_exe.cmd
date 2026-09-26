@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Creation de l'environnement Python...
    py -3 -m venv "%~dp0.venv"
    if errorlevel 1 goto failed
)

echo Installation des dependances de build...
"%PYTHON%" -m pip install -r requirements-build.txt
if errorlevel 1 goto failed

echo Construction de dist\AMMDF.exe...
"%PYTHON%" -m PyInstaller --noconfirm --clean --onefile --windowed --name AMMDF --add-data "images\logo.jpg;images" --collect-all pymupdf --collect-all reportlab app.py
if errorlevel 1 goto failed

if not exist "dist\AMMDF.exe" goto failed

echo.
echo Mise a jour terminee : %~dp0dist\AMMDF.exe
exit /b 0

:failed
echo.
echo Echec de la mise a jour. Verifiez les messages ci-dessus.
exit /b 1
