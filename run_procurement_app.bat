@echo off
REM Batch file to run the Procurement Application GUI

REM --- IMPORTANT: SET YOUR PROJECT PATH ---
REM Replace the path below with the ACTUAL FULL PATH to the directory 
REM where your 'procurement_app_gui.py' and CSV files are located.
SET "PROJECT_DIR=C:\path	o\your\procurement-main"

REM Navigate to the script's directory
cd /D "%PROJECT_DIR%"
IF ERRORLEVEL 1 (
    echo Failed to change directory to %PROJECT_DIR%
    pause
    exit /b 1
)

REM --- OPTIONAL: VIRTUAL ENVIRONMENT ACTIVATION ---
REM If you are using a Python virtual environment (e.g., named 'venv' or 'myenv')
REM uncomment and adjust the lines below.
REM SET "VENV_NAME=venv"
REM IF EXIST "%VENV_NAME%\Scripts ctivate.bat" (
REM    echo Activating virtual environment: %VENV_NAME%
REM    CALL "%VENV_NAME%\Scripts ctivate.bat"
REM ) ELSE (
REM    echo Virtual environment '%VENV_NAME%' not found at %PROJECT_DIR%\%VENV_NAME%\Scripts ctivate.bat
REM    REM Decide if you want to pause or exit if venv not found
REM    REM pause 
REM )

echo Starting Procurement Application...
REM This assumes 'python' is in your system PATH and has PyQt6/pandas.
REM If not, you might need the full path to python.exe
python procurement_app_gui.py

echo.
echo Procurement Application has finished or was closed.
REM The 'pause' below will keep this window open until a key is pressed.
pause
