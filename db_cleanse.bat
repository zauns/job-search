@echo off
REM Database Cleansing Script for Windows
REM This batch file provides easy access to database maintenance

setlocal enabledelayedexpansion

REM Check if virtual environment exists and activate it
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found at venv\Scripts\activate.bat
    echo You may need to create a virtual environment first.
)

REM Run the database cleansing script with provided arguments
if "%1"=="" (
    python scripts\db_cleanse.py interactive
) else (
    python scripts\db_cleanse.py %*
)

pause