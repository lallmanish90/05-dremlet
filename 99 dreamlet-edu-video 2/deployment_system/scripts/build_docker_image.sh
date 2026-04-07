#!/bin/bash

# Docker Image Builder for Dreamlet Educational Video Production System
# This script builds customized Docker images with embedded license keys

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${BLUE}"
echo "======================================================="
echo "  Dreamlet Docker Image Builder"
echo "======================================================="
echo -e "${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi

# Get build parameters
echo "Enter build parameters:"
echo

read -p "User ID (e.g., john.doe): " USER_ID
if [[ -z "$USER_ID" ]]; then
    print_error "User ID is required"
    exit 1
fi

read -p "License Key (leave empty to generate): " LICENSE_KEY
if [[ -z "$LICENSE_KEY" ]]; then
    # Generate a temporary license key for demo
    LICENSE_KEY="DL_$(date +%s)_$(openssl rand -hex 8)"
    print_warning "Generated demo license key: $LICENSE_KEY"
fi

read -p "License Server URL [https://license.dreamlet.com/api/validate]: " LICENSE_SERVER_URL
LICENSE_SERVER_URL=${LICENSE_SERVER_URL:-"https://license.dreamlet.com/api/validate"}

read -p "Fallback Expiry Date (YYYY-MM-DD) [2025-12-31]: " FALLBACK_EXPIRY
FALLBACK_EXPIRY=${FALLBACK_EXPIRY:-"2025-12-31"}

read -p "Docker Image Tag [dreamlet/educational-video-system:${USER_ID}]: " IMAGE_TAG
IMAGE_TAG=${IMAGE_TAG:-"dreamlet/educational-video-system:${USER_ID}"}

echo
print_status "Building Docker image with following parameters:"
echo "  User ID: $USER_ID"
echo "  License Key: ${LICENSE_KEY:0:10}..."
echo "  License Server: $LICENSE_SERVER_URL"
echo "  Fallback Expiry: $FALLBACK_EXPIRY"
echo "  Image Tag: $IMAGE_TAG"
echo

read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Build cancelled"
    exit 0
fi

# Build the Docker image
print_status "Building Docker image..."
if docker build \
    --build-arg LICENSE_KEY="$LICENSE_KEY" \
    --build-arg USER_ID="$USER_ID" \
    --build-arg LICENSE_SERVER_URL="$LICENSE_SERVER_URL" \
    --build-arg FALLBACK_EXPIRY="${FALLBACK_EXPIRY}T23:59:59" \
    -t "$IMAGE_TAG" \
    -f ../Dockerfile \
    ../..; then
    
    print_status "Docker image built successfully!"
    
    # Show image details
    echo
    print_status "Image details:"
    docker images | grep "$IMAGE_TAG" | head -1
    
    echo
    print_status "Image size optimization tips:"
    echo "  - This image includes all necessary dependencies"
    echo "  - Source code is compiled to bytecode for security"
    echo "  - Runtime optimizations are applied"
    
    # Generate deployment files for this user
    print_status "Generating deployment files..."
    
    # Create user-specific directory
    USER_DIR="deployments/${USER_ID}"
    mkdir -p "$USER_DIR"
    
    # Copy and customize setup scripts
    sed "s|dreamlet/educational-video-system:latest|$IMAGE_TAG|g" ../legacy/setup_windows.bat > "$USER_DIR/setup_windows.bat"
    sed "s|dreamlet/educational-video-system:latest|$IMAGE_TAG|g" ../legacy/setup_unix.sh > "$USER_DIR/setup_unix.sh"
    chmod +x "$USER_DIR/setup_unix.sh"
    
    # Create user-specific README
    cat > "$USER_DIR/README.md" << EOF
# Dreamlet Educational Video Production System
## User: $USER_ID

### Quick Start

#### Windows Users:
1. Double-click \`setup_windows.bat\`
2. Wait for setup to complete
3. Open http://localhost:8501 in your browser

#### Mac/Linux Users:
1. Open terminal and navigate to this folder
2. Run: \`./setup_unix.sh\`
3. Open http://localhost:8501 in your browser

### Folder Structure
After running the setup script, you'll have:
- \`dreamlet_input/\` - Put your files here
- \`dreamlet_output/\` - Processed results appear here

### File Management
The application supports two methods for file access:
1. **Local Folders**: Use the input/output folders created by setup
2. **Web Upload**: Use the File Manager page in the web interface

### Support
If you encounter issues:
1. Check Docker is running
2. Ensure ports 8501 is available
3. Contact your administrator for license issues

### License Information
- User ID: $USER_ID
- License Server: $LICENSE_SERVER_URL
- Fallback Expiry: $FALLBACK_EXPIRY

Build Date: $(date)
Image: $IMAGE_TAG
EOF
    
    print_status "Deployment files created in: $USER_DIR"
    
    echo
    echo -e "${GREEN}======================================================="
    echo "  Build Complete!"
    echo "=======================================================${NC}"
    echo
    echo "Next steps:"
    echo "1. Test the image locally:"
    echo "   docker run -p 8501:8501 $IMAGE_TAG"
    echo
    echo "2. Push to registry (if needed):"
    echo "   docker push $IMAGE_TAG"
    echo
    echo "3. Distribute to user:"
    echo "   - Send them the deployment folder: $USER_DIR"
    echo "   - They need Docker installed"
    echo "   - They run the setup script for their platform"
    echo
    echo "4. License management:"
    echo "   - Add user to license server: $USER_ID"
    echo "   - License key: $LICENSE_KEY"
    echo "   - Monitor usage through license server API"
    echo
    
else
    print_error "Docker build failed!"
    exit 1
fi