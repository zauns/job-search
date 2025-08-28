@echo off
REM Job Matching App Runner for Windows
REM This batch file provides easy access to the application

setlocal enabledelayedexpansion

REM Check if virtual environment exists and activate it
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found at venv\Scripts\activate.bat
    echo You may need to create a virtual environment first.
)

REM Run the application with provided arguments
if "%1"=="" (
    python scripts\run_app.py help
) else (
    python scripts\run_app.py %*
)

pause