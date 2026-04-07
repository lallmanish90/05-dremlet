@echo off
REM Dreamlet Educational Video Production System - Windows Setup
REM This script sets up the Docker container with proper volume mounting

echo.
echo ========================================
echo  Dreamlet Educational Video System
echo  Windows Setup Script
echo ========================================
echo.

REM Check if Docker is installed and running
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop for Windows first
    echo Download from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo Docker is available...

REM Get current directory
set CURRENT_DIR=%CD%

REM Create input and output directories
echo Creating directories...
if not exist "%CURRENT_DIR%\dreamlet_input" mkdir "%CURRENT_DIR%\dreamlet_input"
if not exist "%CURRENT_DIR%\dreamlet_output" mkdir "%CURRENT_DIR%\dreamlet_output"

echo Input directory:  %CURRENT_DIR%\dreamlet_input
echo Output directory: %CURRENT_DIR%\dreamlet_output

REM Stop any existing container
echo Stopping any existing Dreamlet containers...
docker stop dreamlet-app 2>nul
docker rm dreamlet-app 2>nul

REM Pull the Docker image (replace with your actual image)
echo Pulling Dreamlet Docker image...
docker pull dreamlet/educational-video-system:latest
if errorlevel 1 (
    echo WARNING: Could not pull latest image. Using local image if available.
)

REM Run the container with volume mounts
echo Starting Dreamlet application...
docker run -d ^
    --name dreamlet-app ^
    -p 8501:8501 ^
    -v "%CURRENT_DIR%\dreamlet_input:/app/input" ^
    -v "%CURRENT_DIR%\dreamlet_output:/app/output" ^
    --restart unless-stopped ^
    dreamlet/educational-video-system:latest

if errorlevel 1 (
    echo ERROR: Failed to start Docker container
    echo Please check Docker logs: docker logs dreamlet-app
    pause
    exit /b 1
)

REM Wait a moment for the container to start
echo Waiting for application to start...
timeout /t 10 /nobreak >nul

REM Check if container is running
docker ps | findstr dreamlet-app >nul
if errorlevel 1 (
    echo ERROR: Container failed to start
    echo Checking logs:
    docker logs dreamlet-app
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo Dreamlet is now running at: http://localhost:8501
echo.
echo IMPORTANT FOLDERS:
echo   Input:  %CURRENT_DIR%\dreamlet_input
echo   Output: %CURRENT_DIR%\dreamlet_output
echo.
echo HOW TO USE:
echo 1. Put your files in the 'dreamlet_input' folder
echo 2. Open http://localhost:8501 in your browser
echo 3. Process your files using the web interface
echo 4. Find results in the 'dreamlet_output' folder
echo.
echo To stop the application, run: docker stop dreamlet-app
echo To restart the application, run this script again
echo.

REM Try to open browser automatically
echo Opening browser...
start http://localhost:8501

echo Setup complete! The application is running.
echo Keep this window open or press any key to exit.
pause >nul