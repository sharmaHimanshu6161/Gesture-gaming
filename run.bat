@echo off
echo ============================================================
echo   Hand Gesture Space Shooter - Launching...
echo ============================================================
echo.

if not exist venv (
    echo [INFO] Virtual environment not found. Running install.bat first...
    call install.bat
)

call venv\Scripts\activate.bat
python game.py
if errorlevel 1 (
    echo.
    echo [ERROR] Game exited with an error. Check output above.
    pause
)
