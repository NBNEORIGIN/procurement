@echo off
echo Changing directory to script location...
cd /d "%~dp0"
echo Current directory: %cd%
echo Starting Procurement Application...
python procurement_app_gui.py
echo Application closed.
pause
