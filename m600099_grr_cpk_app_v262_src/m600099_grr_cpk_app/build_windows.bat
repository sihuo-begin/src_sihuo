@echo off
REM ============================================================
REM  Build Script for M600099 GRR & CPK Analyzer (Windows)
REM  Run this on a Windows machine with Python 3.9+ installed
REM ============================================================

echo [1/3] Installing Python dependencies…
pip install -r requirements.txt

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [2/3] Building executable with PyInstaller…
pyinstaller --name=M600099_GRR_CPK_Analyzer ^
            --windowed ^
            --onefile ^
            --icon=NONE ^
            --distpath=dist ^
            --workpath=build ^
            --specpath=. ^
            main.py

if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)

echo [3/3] Done!
echo.
echo The executable is at: dist\M600099_GRR_CPK_Analyzer.exe
echo.
pause
