@echo off
REM ═══════════════════════════════════════════════════════════
REM  PhishGuard — Windows Startup Script
REM  Usage: start.bat
REM         start.bat setup
REM         start.bat check
REM ═══════════════════════════════════════════════════════════

title PhishGuard v2.0

if "%1"=="setup" (
    echo [*] Running PhishGuard setup...
    python phishguard.py setup
    pause
    exit /b
)

if "%1"=="check" (
    echo [*] Running health check...
    python phishguard.py check
    pause
    exit /b
)

echo.
echo  ======================================
echo   PhishGuard v2.0 - Starting Server
echo  ======================================
echo.

python phishguard.py start %*
pause
