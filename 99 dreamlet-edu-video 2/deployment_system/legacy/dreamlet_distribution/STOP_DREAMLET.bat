@echo off
REM ==================================================
REM   DREAMLET - STOP ALL SERVICES
REM   Completely removes all containers and data
REM ==================================================

echo.
echo =============================================
echo   STOPPING DREAMLET SERVICES
echo =============================================
echo.

echo Stopping Dreamlet application...
docker stop dreamlet-app >nul 2>&1
docker rm dreamlet-app >nul 2>&1

echo Stopping license server...
docker stop dreamlet-license-server >nul 2>&1
docker rm dreamlet-license-server >nul 2>&1

echo Cleaning up Docker images...
docker rmi dreamlet-app >nul 2>&1
docker rmi dreamlet-license-server >nul 2>&1

echo.
echo ✅ All Dreamlet services stopped!
echo.
echo NOTE: Your input/output folders on Desktop are preserved.
echo To completely remove everything, delete those folders manually.
echo.
pause