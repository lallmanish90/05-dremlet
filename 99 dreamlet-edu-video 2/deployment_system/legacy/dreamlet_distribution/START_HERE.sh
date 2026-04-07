#!/bin/bash

# ==================================================
#   DREAMLET EDUCATIONAL VIDEO SYSTEM
#   AUTOMATIC SETUP FOR MAC/LINUX
#   Just run this script and wait!
# ==================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC} $1"
}

echo -e "${BLUE}"
echo "============================================="
echo "   DREAMLET EDUCATIONAL VIDEO SYSTEM"
echo "   Automatic Setup - Please Wait..."
echo "============================================="
echo -e "${NC}"

# Get script directory and desktop path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP="$HOME/Desktop"

echo "[1/6] Checking Docker installation..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    echo ""
    echo "PLEASE INSTALL DOCKER FIRST:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "1. Go to: https://www.docker.com/products/docker-desktop"
        echo "2. Download Docker Desktop for Mac"
    else
        echo "1. Go to: https://docs.docker.com/engine/install/"
        echo "2. Follow instructions for your Linux distribution"
    fi
    echo "3. Install Docker"
    echo "4. Run this script again"
    echo ""
    exit 1
fi

print_status "Docker found"

# Check if Docker daemon is running
echo "[2/6] Starting Docker service..."
if ! docker info &> /dev/null; then
    print_warning "Docker is not running, attempting to start..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - start Docker Desktop
        if [ -d "/Applications/Docker.app" ]; then
            open -a Docker
            print_info "Starting Docker Desktop (this takes 1-2 minutes)..."
        else
            print_error "Docker Desktop not found in Applications folder"
            exit 1
        fi
    else
        # Linux - try to start docker service
        if command -v systemctl &> /dev/null; then
            sudo systemctl start docker
        elif command -v service &> /dev/null; then
            sudo service docker start
        else
            print_error "Cannot start Docker service automatically"
            echo "Please start Docker manually and run this script again"
            exit 1
        fi
    fi
    
    # Wait for Docker to be ready (max 3 minutes)
    count=0
    while ! docker info &> /dev/null && [ $count -lt 18 ]; do
        sleep 10
        count=$((count + 1))
        print_info "Still waiting for Docker... ($count/18)"
    done
    
    if ! docker info &> /dev/null; then
        print_error "Docker failed to start. Please start Docker manually and try again."
        exit 1
    fi
fi

print_status "Docker is ready!"

echo "[3/6] Setting up license server..."
cd "$SCRIPT_DIR/license_server"

# Stop any existing containers
docker stop dreamlet-license-server &> /dev/null || true
docker rm dreamlet-license-server &> /dev/null || true

# Build and start license server
print_info "Building license server..."
if ! docker build -t dreamlet-license-server . &> /dev/null; then
    print_error "License server build failed"
    exit 1
fi

print_info "Starting license server..."
if ! docker run -d --name dreamlet-license-server -p 5000:5000 dreamlet-license-server &> /dev/null; then
    print_error "License server start failed"
    exit 1
fi

# Wait for license server to be ready
sleep 5
print_status "License server ready!"

echo "[4/6] Creating demo user license..."
# Get admin API key from logs
ADMIN_KEY=$(docker logs dreamlet-license-server 2>&1 | grep "Admin API Key:" | awk '{print $4}')

# Create demo user (if curl is available)
if command -v curl &> /dev/null; then
    RESPONSE=$(curl -s -X POST http://localhost:5000/api/admin/licenses \
        -H "X-API-Key: $ADMIN_KEY" \
        -H "Content-Type: application/json" \
        -d '{"user_id":"demo_user","email":"demo@company.com","days_valid":365}')
    
    # Extract license key from response
    LICENSE_KEY=$(echo "$RESPONSE" | grep -o '"license_key":"[^"]*' | cut -d'"' -f4)
    
    if [ -n "$LICENSE_KEY" ]; then
        print_status "Demo license created"
    else
        LICENSE_KEY="DL_demo_fallback_key"
        print_warning "Using fallback license"
    fi
else
    LICENSE_KEY="DL_demo_fallback_key"
    print_warning "Using fallback license (curl not available)"
fi

echo "[5/6] Building Dreamlet application..."
cd "$SCRIPT_DIR"

# Stop any existing app containers
docker stop dreamlet-app &> /dev/null || true
docker rm dreamlet-app &> /dev/null || true

# Create license config for demo user
cat > .license_config << EOF
LICENSE_KEY=$LICENSE_KEY
USER_ID=demo_user
LICENSE_SERVER_URL=http://host.docker.internal:5000/api/validate
FALLBACK_EXPIRY=2025-12-31T23:59:59
EOF

print_info "Building application (this takes 2-3 minutes)..."
if ! docker build \
    --build-arg LICENSE_KEY="$LICENSE_KEY" \
    --build-arg USER_ID="demo_user" \
    --build-arg LICENSE_SERVER_URL="http://host.docker.internal:5000/api/validate" \
    -t dreamlet-app . &> /dev/null; then
    print_error "Application build failed"
    exit 1
fi

echo "[6/6] Starting Dreamlet application..."

# Create desktop folders for input/output
mkdir -p "$DESKTOP/dreamlet_input"
mkdir -p "$DESKTOP/dreamlet_output"

# Start the application with volume mounts
if ! docker run -d \
    --name dreamlet-app \
    -p 8501:8501 \
    -v "$DESKTOP/dreamlet_input:/app/input" \
    -v "$DESKTOP/dreamlet_output:/app/output" \
    dreamlet-app &> /dev/null; then
    print_error "Application start failed"
    exit 1
fi

# Wait for application to be ready
print_info "Waiting for application to start..."
sleep 10

# Check if application is running
if ! docker ps | grep -q dreamlet-app; then
    print_error "Application failed to start properly"
    echo "Checking logs:"
    docker logs dreamlet-app
    exit 1
fi

# Cleanup
rm -f .license_config

echo ""
echo -e "${GREEN}"
echo "============================================="
echo "   🎉 SETUP COMPLETE! 🎉"
echo "============================================="
echo -e "${NC}"
echo ""
print_status "Dreamlet is running at: http://localhost:8501"
print_status "Input folder: $DESKTOP/dreamlet_input"
print_status "Output folder: $DESKTOP/dreamlet_output"
echo ""
echo -e "${BLUE}HOW TO USE:${NC}"
echo "1. Put your files in: dreamlet_input folder"
echo "2. Use the web app at: http://localhost:8501"
echo "3. Get results from: dreamlet_output folder"
echo ""
echo -e "${BLUE}TO STOP:${NC} Run ./STOP_DREAMLET.sh"
echo ""

# Open browser
print_info "Opening Dreamlet in your browser..."
if command -v open &> /dev/null; then
    # macOS
    open http://localhost:8501
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open http://localhost:8501
else
    echo "Please open http://localhost:8501 in your browser"
fi

echo ""
echo -e "${GREEN}"
echo "============================================="
echo "   Ready to process educational videos!"
echo "   Press Enter to finish..."
echo "============================================="
echo -e "${NC}"
echo ""

read -p "Press Enter to continue..."