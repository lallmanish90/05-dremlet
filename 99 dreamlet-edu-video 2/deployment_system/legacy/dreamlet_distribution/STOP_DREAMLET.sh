#!/bin/bash

# ==================================================
#   DREAMLET - STOP ALL SERVICES
#   Completely removes all containers and data
# ==================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "============================================="
echo "   STOPPING DREAMLET SERVICES"
echo "============================================="
echo -e "${NC}"
echo ""

echo "Stopping Dreamlet application..."
docker stop dreamlet-app &> /dev/null
docker rm dreamlet-app &> /dev/null

echo "Stopping license server..."
docker stop dreamlet-license-server &> /dev/null
docker rm dreamlet-license-server &> /dev/null

echo "Cleaning up Docker images..."
docker rmi dreamlet-app &> /dev/null
docker rmi dreamlet-license-server &> /dev/null

echo ""
echo -e "${GREEN}✅ All Dreamlet services stopped!${NC}"
echo ""
echo "NOTE: Your input/output folders on Desktop are preserved."
echo "To completely remove everything, delete those folders manually."
echo ""

read -p "Press Enter to continue..."