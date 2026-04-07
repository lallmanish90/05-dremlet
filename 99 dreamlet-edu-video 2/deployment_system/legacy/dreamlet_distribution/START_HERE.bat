@echo off
REM ==================================================
REM   DREAMLET EDUCATIONAL VIDEO SYSTEM
REM   AUTOMATIC SETUP FOR WINDOWS
REM   Just double-click and wait!
REM ==================================================

echo.
echo =============================================
echo   DREAMLET EDUCATIONAL VIDEO SYSTEM
echo   Automatic Setup - Please Wait...
echo =============================================
echo.

REM Get the USB/current directory
set SCRIPT_DIR=%~dp0
set DESKTOP=%USERPROFILE%\Desktop

echo [1/6] Checking Docker installation...

REM Check if Docker Desktop is installed
if exist "%PROGRAMFILES%\Docker\Docker\Docker Desktop.exe" (
    echo ✅ Docker Desktop found
    goto CHECK_DOCKER_RUNNING
)

REM Try alternative Docker path
if exist "%LOCALAPPDATA%\Programs\Docker\Docker\Docker Desktop.exe" (
    echo ✅ Docker Desktop found
    goto CHECK_DOCKER_RUNNING
)

REM Docker not found - provide download instructions
echo ❌ Docker Desktop not found
echo.
echo PLEASE INSTALL DOCKER DESKTOP FIRST:
echo 1. Go to: https://www.docker.com/products/docker-desktop
echo 2. Download Docker Desktop for Windows
echo 3. Install it (requires restart)
echo 4. Run this script again
echo.
pause
exit /b 1

:CHECK_DOCKER_RUNNING
echo [2/6] Starting Docker Desktop...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ⏳ Starting Docker Desktop (this takes 1-2 minutes)...
    
    REM Try to start Docker Desktop
    if exist "%PROGRAMFILES%\Docker\Docker\Docker Desktop.exe" (
        start "" "%PROGRAMFILES%\Docker\Docker\Docker Desktop.exe"
    ) else (
        start "" "%LOCALAPPDATA%\Programs\Docker\Docker\Docker Desktop.exe"
    )
    
    REM Wait for Docker to start (max 3 minutes)
    set /a count=0
    :WAIT_DOCKER
    timeout /t 10 /nobreak >nul
    docker --version >nul 2>&1
    if not errorlevel 1 goto DOCKER_READY
    
    set /a count+=1
    if %count% LSS 18 (
        echo    Still waiting for Docker... (%count%/18)
        goto WAIT_DOCKER
    )
    
    echo ❌ Docker failed to start. Please start Docker Desktop manually and try again.
    pause
    exit /b 1
)

:DOCKER_READY
echo ✅ Docker is ready!

echo [3/6] Setting up license server...
cd /d "%SCRIPT_DIR%license_server"

REM Stop any existing containers
docker stop dreamlet-license-server >nul 2>&1
docker rm dreamlet-license-server >nul 2>&1

REM Build and start license server
echo    Building license server...
docker build -t dreamlet-license-server . >nul 2>&1
if errorlevel 1 (
    echo ❌ License server build failed
    pause
    exit /b 1
)

echo    Starting license server...
docker run -d --name dreamlet-license-server -p 5000:5000 dreamlet-license-server >nul 2>&1
if errorlevel 1 (
    echo ❌ License server start failed
    pause
    exit /b 1
)

REM Wait for license server to be ready
timeout /t 5 /nobreak >nul
echo ✅ License server ready!

echo [4/6] Creating demo user license...
REM Get admin API key from logs
for /f "tokens=4" %%a in ('docker logs dreamlet-license-server 2^>^&1 ^| findstr "Admin API Key:"') do set ADMIN_KEY=%%a

REM Create demo user (using curl if available, otherwise skip)
curl --version >nul 2>&1
if not errorlevel 1 (
    curl -s -X POST http://localhost:5000/api/admin/licenses -H "X-API-Key: %ADMIN_KEY%" -H "Content-Type: application/json" -d "{\"user_id\":\"demo_user\",\"email\":\"demo@company.com\",\"days_valid\":365}" >temp_license.json 2>&1
    
    REM Extract license key from response
    for /f "tokens=2 delims=:" %%a in ('type temp_license.json ^| findstr "license_key"') do (
        set LICENSE_KEY=%%a
        set LICENSE_KEY=!LICENSE_KEY:"=!
        set LICENSE_KEY=!LICENSE_KEY:,=!
        set LICENSE_KEY=!LICENSE_KEY: =!
    )
    del temp_license.json >nul 2>&1
    echo ✅ Demo license created
) else (
    set LICENSE_KEY=DL_demo_fallback_key
    echo ⚠️  Using fallback license (curl not available)
)

echo [5/6] Building Dreamlet application...
cd /d "%SCRIPT_DIR%"

REM Stop any existing app containers
docker stop dreamlet-app >nul 2>&1
docker rm dreamlet-app >nul 2>&1

REM Create license config for demo user
echo LICENSE_KEY=%LICENSE_KEY%> .license_config
echo USER_ID=demo_user>> .license_config
echo LICENSE_SERVER_URL=http://host.docker.internal:5000/api/validate>> .license_config
echo FALLBACK_EXPIRY=2025-12-31T23:59:59>> .license_config

echo    Building application (this takes 2-3 minutes)...
docker build --build-arg LICENSE_KEY="%LICENSE_KEY%" --build-arg USER_ID="demo_user" --build-arg LICENSE_SERVER_URL="http://host.docker.internal:5000/api/validate" -t dreamlet-app . >nul 2>&1
if errorlevel 1 (
    echo ❌ Application build failed
    pause
    exit /b 1
)

echo [6/6] Starting Dreamlet application...

REM Create desktop folders for input/output
mkdir "%DESKTOP%\dreamlet_input" >nul 2>&1
mkdir "%DESKTOP%\dreamlet_output" >nul 2>&1

REM Start the application with volume mounts
docker run -d --name dreamlet-app -p 8501:8501 -v "%DESKTOP%\dreamlet_input:/app/input" -v "%DESKTOP%\dreamlet_output:/app/output" dreamlet-app >nul 2>&1
if errorlevel 1 (
    echo ❌ Application start failed
    pause
    exit /b 1
)

REM Wait for application to be ready
echo    Waiting for application to start...
timeout /t 10 /nobreak >nul

REM Check if application is running
docker ps | findstr dreamlet-app >nul
if errorlevel 1 (
    echo ❌ Application failed to start properly
    echo Checking logs:
    docker logs dreamlet-app
    pause
    exit /b 1
)

REM Cleanup
del .license_config >nul 2>&1

echo.
echo =============================================
echo   🎉 SETUP COMPLETE! 🎉
echo =============================================
echo.
echo ✅ Dreamlet is running at: http://localhost:8501
echo ✅ Input folder: %DESKTOP%\dreamlet_input
echo ✅ Output folder: %DESKTOP%\dreamlet_output
echo.
echo HOW TO USE:
echo 1. Put your files in: dreamlet_input folder
echo 2. Use the web app at: http://localhost:8501
echo 3. Get results from: dreamlet_output folder
echo.
echo TO STOP: Close this window and run "STOP_DREAMLET.bat"
echo.

REM Open browser
echo Opening Dreamlet in your browser...
start http://localhost:8501

echo.
echo =============================================
echo   Ready to process educational videos!
echo   Keep this window open...
echo =============================================
echo.

REM Keep the window open
pause