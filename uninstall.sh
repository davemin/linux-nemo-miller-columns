#!/bin/bash
#
# Uninstallation script for Nemo Miller Columns
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  Nemo Miller Columns - Uninstallation ${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Installation directories
APP_DIR="$HOME/.local/share/nemo-miller-columns"
EXTENSION_DIR="$HOME/.local/share/nemo-python/extensions"
DESKTOP_DIR="$HOME/.local/share/applications"

# Confirmation
read -p "Are you sure you want to uninstall Nemo Miller Columns? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

echo ""

# Remove application
if [ -d "$APP_DIR" ]; then
    echo -e "${YELLOW}Removing application...${NC}"
    rm -rf "$APP_DIR"
    echo -e "${GREEN}Application removed.${NC}"
fi

# Remove extension
if [ -f "$EXTENSION_DIR/nemo-miller-columns-extension.py" ]; then
    echo -e "${YELLOW}Removing Nemo extension...${NC}"
    rm -f "$EXTENSION_DIR/nemo-miller-columns-extension.py"
    echo -e "${GREEN}Extension removed.${NC}"
fi

# Remove launcher
if [ -f "$DESKTOP_DIR/nemo-miller-columns.desktop" ]; then
    echo -e "${YELLOW}Removing launcher...${NC}"
    rm -f "$DESKTOP_DIR/nemo-miller-columns.desktop"
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    echo -e "${GREEN}Launcher removed.${NC}"
fi

# Restart Nemo
echo -e "${YELLOW}Restarting Nemo...${NC}"
nemo -q 2>/dev/null || true

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Uninstallation complete!             ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
