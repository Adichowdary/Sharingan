@echo off
REM ═══════════════════════════════════════════════════════════
REM  Sharingan — Windows Startup Script
REM  Usage: start.bat
REM         start.bat setup
REM         start.bat check
REM ═══════════════════════════════════════════════════════════

title Sharingan v2.0

if "%1"=="setup" (
    echo [*] Running Sharingan setup...
    python sharingan.py setup
    pause
    exit /b
)

if "%1"=="check" (
    echo [*] Running health check...
    python sharingan.py check
    pause
    exit /b
)

python sharingan.py %*
pause
