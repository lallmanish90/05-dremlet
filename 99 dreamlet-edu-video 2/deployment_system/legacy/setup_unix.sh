#!/bin/bash

# Dreamlet Educational Video Production System - Unix Setup (Mac/Linux)
# This script sets up the Docker container with proper volume mounting

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "========================================"
echo "  Dreamlet Educational Video System"
echo "  Unix Setup Script (Mac/Linux)"
echo "========================================"
echo -e "${NC}"

# Function to print status
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed and running
print_status "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    echo "Please install Docker first:"
    echo "  Mac: https://www.docker.com/products/docker-desktop"
    echo "  Linux: https://docs.docker.com/engine/install/"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    print_error "Docker is not running"
    echo "Please start Docker and try again"
    exit 1
fi

print_status "Docker is available..."

# Get current directory
CURRENT_DIR="$(pwd)"

# Create input and output directories
print_status "Creating directories..."
mkdir -p "${CURRENT_DIR}/dreamlet_input"
mkdir -p "${CURRENT_DIR}/dreamlet_output"

# Set proper permissions (especially important on Linux)
chmod 755 "${CURRENT_DIR}/dreamlet_input"
chmod 755 "${CURRENT_DIR}/dreamlet_output"

echo "Input directory:  ${CURRENT_DIR}/dreamlet_input"
echo "Output directory: ${CURRENT_DIR}/dreamlet_output"

# Stop any existing container
print_status "Stopping any existing Dreamlet containers..."
docker stop dreamlet-app 2>/dev/null || true
docker rm dreamlet-app 2>/dev/null || true

# Pull the Docker image
print_status "Pulling Dreamlet Docker image..."
if ! docker pull dreamlet/educational-video-system:latest; then
    print_warning "Could not pull latest image. Using local image if available."
fi

# Run the container with volume mounts
print_status "Starting Dreamlet application..."
if docker run -d \
    --name dreamlet-app \
    -p 8501:8501 \
    -v "${CURRENT_DIR}/dreamlet_input:/app/input" \
    -v "${CURRENT_DIR}/dreamlet_output:/app/output" \
    --restart unless-stopped \
    dreamlet/educational-video-system:latest; then
    
    print_status "Container started successfully"
else
    print_error "Failed to start Docker container"
    echo "Check Docker logs with: docker logs dreamlet-app"
    exit 1
fi

# Wait for the container to start
print_status "Waiting for application to start..."
sleep 10

# Check if container is running
if docker ps | grep -q dreamlet-app; then
    print_status "Container is running successfully"
else
    print_error "Container failed to start"
    echo "Checking logs:"
    docker logs dreamlet-app
    exit 1
fi

# Display success message
echo -e "${GREEN}"
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo -e "${NC}"
echo
echo "Dreamlet is now running at: http://localhost:8501"
echo
echo -e "${BLUE}IMPORTANT FOLDERS:${NC}"
echo "  Input:  ${CURRENT_DIR}/dreamlet_input"
echo "  Output: ${CURRENT_DIR}/dreamlet_output"
echo
echo -e "${BLUE}HOW TO USE:${NC}"
echo "1. Put your files in the 'dreamlet_input' folder"
echo "2. Open http://localhost:8501 in your browser"
echo "3. Process your files using the web interface"
echo "4. Find results in the 'dreamlet_output' folder"
echo
echo -e "${BLUE}MANAGEMENT COMMANDS:${NC}"
echo "  Stop:     docker stop dreamlet-app"
echo "  Restart:  docker restart dreamlet-app"
echo "  Logs:     docker logs dreamlet-app"
echo "  Remove:   docker stop dreamlet-app && docker rm dreamlet-app"
echo

# Try to open browser automatically
if command -v open &> /dev/null; then
    # macOS
    print_status "Opening browser..."
    open http://localhost:8501
elif command -v xdg-open &> /dev/null; then
    # Linux
    print_status "Opening browser..."
    xdg-open http://localhost:8501
else
    echo "Please open http://localhost:8501 in your browser"
fi

print_status "Setup complete! The application is running."

# Check for container health
print_status "Performing health check..."
sleep 5
if curl -f http://localhost:8501/_stcore/health &> /dev/null; then
    print_status "Health check passed - application is ready!"
else
    print_warning "Health check failed - application may still be starting"
    echo "If the application doesn't work, check logs: docker logs dreamlet-app"
fi

echo
echo "Press Enter to exit..."
read