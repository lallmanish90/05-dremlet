#!/bin/bash

# ============================================================================
#  DREAMLET DISTRIBUTION CREATOR
#  Creates secure distribution packages WITHOUT source code
# ============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ️${NC} $1"; }
print_error() { echo -e "${RED}❌${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠️${NC} $1"; }

echo -e "${BLUE}"
echo "============================================================================"
echo "  DREAMLET SECURE DISTRIBUTION CREATOR"
echo "  Creates user packages WITHOUT exposing source code"
echo "============================================================================"
echo -e "${NC}"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is required to create secure distributions"
    echo "Please install Docker and run this script again"
    exit 1
fi

print_status "Docker found - creating secure distribution"

# Create distribution directory
DIST_DIR="dreamlet_distribution"
print_info "Creating distribution directory: $DIST_DIR"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

echo ""
echo "[1/5] Building Docker images with embedded code..."

# Build license server image
print_info "Building license server image..."
if ! docker build -t dreamlet-license-server:latest ../license_server/ > /dev/null 2>&1; then
    print_error "Failed to build license server image"
    exit 1
fi

# Build main application image (with demo license for now)
print_info "Building main application image..."
if ! docker build \
    --build-arg LICENSE_KEY="DL_demo_secure_key_$(date +%s)" \
    --build-arg USER_ID="demo_user" \
    --build-arg LICENSE_SERVER_URL="http://host.docker.internal:5000/api/validate" \
    --build-arg FALLBACK_EXPIRY="2025-12-31T23:59:59" \
    -f ../Dockerfile \
    -t dreamlet-app:latest ../.. > /dev/null 2>&1; then
    print_error "Failed to build main application image"
    exit 1
fi

print_status "Docker images built successfully"

echo ""
echo "[2/5] Saving Docker images (no source code exposed)..."

# Save images to tar files (these contain only compiled code, no source)
print_info "Saving license server image..."
docker save dreamlet-license-server:latest | gzip > "$DIST_DIR/dreamlet-license-server.tar.gz"

print_info "Saving main application image..."
docker save dreamlet-app:latest | gzip > "$DIST_DIR/dreamlet-app.tar.gz"

print_status "Docker images saved to distribution"

echo ""
echo "[3/5] Creating secure startup scripts..."

# Create secure Windows startup script (loads from Docker images)
cat > "$DIST_DIR/START_DREAMLET.bat" << 'EOF'
@echo off
REM ============================================================================
REM   DREAMLET EDUCATIONAL VIDEO SYSTEM - SECURE STARTUP
REM   No source code included - runs from pre-built Docker images
REM ============================================================================

echo.
echo =============================================
echo   DREAMLET EDUCATIONAL VIDEO SYSTEM
echo   Secure Startup - Please Wait...
echo =============================================
echo.

set SCRIPT_DIR=%~dp0
set DESKTOP=%USERPROFILE%\Desktop

echo [1/5] Checking Docker installation...
docker --version >nul 2>&1
if errorlevel 1 (
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
)

echo ✅ Docker found

echo [2/5] Loading Dreamlet images...
echo    Loading license server...
docker load -i "%SCRIPT_DIR%\dreamlet-license-server.tar.gz" >nul 2>&1
if errorlevel 1 (
    echo ❌ Failed to load license server image
    pause
    exit /b 1
)

echo    Loading main application...
docker load -i "%SCRIPT_DIR%\dreamlet-app.tar.gz" >nul 2>&1
if errorlevel 1 (
    echo ❌ Failed to load main application image
    pause
    exit /b 1
)

echo ✅ Images loaded successfully

echo [3/5] Starting license server...
docker stop dreamlet-license-server >nul 2>&1
docker rm dreamlet-license-server >nul 2>&1
docker run -d --name dreamlet-license-server -p 5000:5000 dreamlet-license-server:latest >nul 2>&1
if errorlevel 1 (
    echo ❌ License server failed to start
    pause
    exit /b 1
)

timeout /t 5 /nobreak >nul
echo ✅ License server ready

echo [4/5] Creating desktop folders...
mkdir "%DESKTOP%\dreamlet_input" >nul 2>&1
mkdir "%DESKTOP%\dreamlet_output" >nul 2>&1
echo ✅ Input/Output folders created on Desktop

echo [5/5] Starting Dreamlet application...
docker stop dreamlet-app >nul 2>&1
docker rm dreamlet-app >nul 2>&1
docker run -d --name dreamlet-app -p 8501:8501 -v "%DESKTOP%\dreamlet_input:/app/input" -v "%DESKTOP%\dreamlet_output:/app/output" dreamlet-app:latest >nul 2>&1
if errorlevel 1 (
    echo ❌ Application failed to start
    pause
    exit /b 1
)

echo    Waiting for application to be ready...
timeout /t 10 /nobreak >nul

echo.
echo =============================================
echo   🎉 DREAMLET IS READY! 🎉
echo =============================================
echo.
echo ✅ Application URL: http://localhost:8501
echo ✅ Input folder: %DESKTOP%\dreamlet_input
echo ✅ Output folder: %DESKTOP%\dreamlet_output
echo.
echo Opening browser...
start http://localhost:8501
echo.
echo Keep this window open while using Dreamlet
echo To stop: Close this window and run STOP_DREAMLET.bat
echo.
pause
EOF

# Create secure Linux/Mac startup script  
cat > "$DIST_DIR/START_DREAMLET.sh" << 'EOF'
#!/bin/bash

# ============================================================================
#   DREAMLET EDUCATIONAL VIDEO SYSTEM - SECURE STARTUP
#   No source code included - runs from pre-built Docker images
# ============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ️${NC} $1"; }
print_error() { echo -e "${RED}❌${NC} $1"; }

echo -e "${BLUE}"
echo "============================================="
echo "   DREAMLET EDUCATIONAL VIDEO SYSTEM"
echo "   Secure Startup - Please Wait..."
echo "============================================="
echo -e "${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP="$HOME/Desktop"

echo "[1/5] Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    echo ""
    echo "PLEASE INSTALL DOCKER FIRST:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Go to: https://www.docker.com/products/docker-desktop"
    else
        echo "Go to: https://docs.docker.com/engine/install/"
    fi
    exit 1
fi

if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

print_status "Docker found and running"

echo "[2/5] Loading Dreamlet images..."
print_info "Loading license server..."
if ! docker load -i "$SCRIPT_DIR/dreamlet-license-server.tar.gz" > /dev/null 2>&1; then
    print_error "Failed to load license server image"
    exit 1
fi

print_info "Loading main application..."
if ! docker load -i "$SCRIPT_DIR/dreamlet-app.tar.gz" > /dev/null 2>&1; then
    print_error "Failed to load main application image"
    exit 1
fi

print_status "Images loaded successfully"

echo "[3/5] Starting license server..."
docker stop dreamlet-license-server > /dev/null 2>&1 || true
docker rm dreamlet-license-server > /dev/null 2>&1 || true
if ! docker run -d --name dreamlet-license-server -p 5000:5000 dreamlet-license-server:latest > /dev/null 2>&1; then
    print_error "License server failed to start"
    exit 1
fi

sleep 5
print_status "License server ready"

echo "[4/5] Creating desktop folders..."
mkdir -p "$DESKTOP/dreamlet_input"
mkdir -p "$DESKTOP/dreamlet_output"
print_status "Input/Output folders created on Desktop"

echo "[5/5] Starting Dreamlet application..."
docker stop dreamlet-app > /dev/null 2>&1 || true
docker rm dreamlet-app > /dev/null 2>&1 || true
if ! docker run -d --name dreamlet-app -p 8501:8501 -v "$DESKTOP/dreamlet_input:/app/input" -v "$DESKTOP/dreamlet_output:/app/output" dreamlet-app:latest > /dev/null 2>&1; then
    print_error "Application failed to start"
    exit 1
fi

print_info "Waiting for application to be ready..."
sleep 10

echo ""
echo -e "${GREEN}"
echo "============================================="
echo "   🎉 DREAMLET IS READY! 🎉"
echo "============================================="
echo -e "${NC}"
echo ""
print_status "Application URL: http://localhost:8501"
print_status "Input folder: $DESKTOP/dreamlet_input"
print_status "Output folder: $DESKTOP/dreamlet_output"
echo ""

# Open browser
print_info "Opening browser..."
if command -v open &> /dev/null; then
    open http://localhost:8501
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8501
fi

echo ""
echo "Keep this terminal open while using Dreamlet"
echo "To stop: Run ./STOP_DREAMLET.sh"
echo ""
read -p "Press Enter to continue..."
EOF

chmod +x "$DIST_DIR/START_DREAMLET.sh"

print_status "Secure startup scripts created"

echo ""
echo "[4/5] Creating stop scripts..."

# Create stop script for Windows
cat > "$DIST_DIR/STOP_DREAMLET.bat" << 'EOF'
@echo off
echo Stopping Dreamlet services...
docker stop dreamlet-app dreamlet-license-server >nul 2>&1
docker rm dreamlet-app dreamlet-license-server >nul 2>&1
echo ✅ Dreamlet stopped
echo.
echo Your files in Desktop folders are preserved.
pause
EOF

# Create stop script for Linux/Mac
cat > "$DIST_DIR/STOP_DREAMLET.sh" << 'EOF'
#!/bin/bash
echo "Stopping Dreamlet services..."
docker stop dreamlet-app dreamlet-license-server > /dev/null 2>&1
docker rm dreamlet-app dreamlet-license-server > /dev/null 2>&1
echo "✅ Dreamlet stopped"
echo ""
echo "Your files in Desktop folders are preserved."
read -p "Press Enter to continue..."
EOF

chmod +x "$DIST_DIR/STOP_DREAMLET.sh"

print_status "Stop scripts created"

echo ""
echo "[5/5] Creating user documentation..."

# Create simple user README
cat > "$DIST_DIR/README.txt" << 'EOF'
🎉 DREAMLET EDUCATIONAL VIDEO SYSTEM

SIMPLE INSTRUCTIONS:

Windows Users:
1. Double-click: START_DREAMLET.bat
2. Wait for setup to complete
3. Browser opens automatically
4. To stop: Double-click STOP_DREAMLET.bat

Mac/Linux Users:
1. Double-click: START_DREAMLET.sh (or run in Terminal)
2. Wait for setup to complete  
3. Browser opens automatically
4. To stop: Double-click STOP_DREAMLET.sh

HOW TO USE:
- Put your files in: dreamlet_input folder (on Desktop)
- Get results from: dreamlet_output folder (on Desktop)
- OR use File Manager in the web interface

REQUIREMENTS:
- Docker Desktop must be installed
- 8GB RAM, 10GB free space
- Windows 10+, macOS 10.14+, or modern Linux

NO SOURCE CODE IS INCLUDED IN THIS PACKAGE
The application runs from secure Docker images only.

Contact your administrator for support.
EOF

print_status "User documentation created"

# Clean up Docker images from local system (optional)
print_info "Cleaning up build images..."
docker rmi dreamlet-license-server:latest > /dev/null 2>&1 || true
docker rmi dreamlet-app:latest > /dev/null 2>&1 || true

echo ""
echo -e "${GREEN}"
echo "============================================================================"
echo "  🎉 SECURE DISTRIBUTION CREATED! 🎉"
echo "============================================================================"
echo -e "${NC}"
echo ""
echo "Distribution folder: $DIST_DIR"
echo ""
echo "CONTENTS (NO SOURCE CODE):"
echo "├── START_DREAMLET.bat          (Windows startup)"
echo "├── START_DREAMLET.sh           (Mac/Linux startup)" 
echo "├── STOP_DREAMLET.bat           (Windows stop)"
echo "├── STOP_DREAMLET.sh            (Mac/Linux stop)"
echo "├── dreamlet-license-server.tar.gz (License server - compiled only)"
echo "├── dreamlet-app.tar.gz         (Main app - compiled bytecode only)"
echo "└── README.txt                  (User instructions)"
echo ""
echo -e "${GREEN}✅ SECURE:${NC} Only compiled Docker images included"
echo -e "${GREEN}✅ PORTABLE:${NC} Copy this folder to USB/network drive"  
echo -e "${GREEN}✅ SIMPLE:${NC} Users just double-click and wait"
echo ""
echo "To distribute:"
echo "1. Copy '$DIST_DIR' folder to USB drive"
echo "2. Give to users with Docker Desktop installed"
echo "3. They double-click START_DREAMLET and wait"
echo ""
print_status "Your source code remains completely protected!"
EOF