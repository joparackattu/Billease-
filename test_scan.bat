@echo off
REM BILLESE - Quick Scan Test Script (Windows CMD)
REM Run this script to test the scanning feature

echo ========================================
echo BILLESE - Scan Test
echo ========================================
echo.

REM Check if server is running
echo Checking if server is running...
curl -s http://localhost:8000/ >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Server is NOT running!
    echo Please start the server first:
    echo   uvicorn main:app --reload
    pause
    exit /b
)
echo [OK] Server is running!
echo.

REM Get weight (default 200)
set /p weight="Enter weight in grams (default 200): "
if "%weight%"=="" set weight=200

REM Get session ID (default test)
set /p sessionId="Enter session ID (default test): "
if "%sessionId%"=="" set sessionId=test

echo.
echo Capturing image and detecting item...
echo.

REM Make the request
curl -X POST "http://localhost:8000/scan-item?session_id=%sessionId%" ^
  -H "Content-Type: application/json" ^
  -d "{\"weight_grams\": %weight%}"

echo.
echo.
echo ========================================
pause












