@echo off
title CookieRun Bot Launcher
echo ==========================================
echo    CookieRun Bot - Startup Script
echo ==========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3, add it to your PATH, and restart this script.
    pause
    exit /b 1
)

:: Install requirements
echo [INFO] Checking and installing requirements from requirements.txt...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install requirements. Please check your internet connection.
    pause
    exit /b 1
)

echo.
echo [INFO] Requirements are up to date!
echo [INFO] Starting CookieRun Bot...
echo ==========================================
echo.

:: Run the application
python main.py

pause
