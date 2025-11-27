#!/bin/bash
#
# Installation script for Nemo Miller Columns
# For Linux Mint 22 with Nemo 6.4.x
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Nemo Miller Columns - Installation   ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Installation directories
APP_DIR="$HOME/.local/share/nemo-miller-columns"
EXTENSION_DIR="$HOME/.local/share/nemo-python/extensions"
DESKTOP_DIR="$HOME/.local/share/applications"

# 1. Check dependencies
echo -e "${YELLOW}[1/5] Checking dependencies...${NC}"

MISSING_DEPS=""

# Check python3
if ! command -v python3 &> /dev/null; then
    MISSING_DEPS="$MISSING_DEPS python3"
fi

# Check nemo
if ! command -v nemo &> /dev/null; then
    echo -e "${RED}Error: Nemo not found. This script is for systems with Nemo file manager.${NC}"
    exit 1
fi

# Check GTK and other Python dependencies
python3 -c "import gi; gi.require_version('Gtk', '3.0')" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS gir1.2-gtk-3.0"
python3 -c "import gi; gi.require_version('Nemo', '3.0')" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS nemo-python"

if [ -n "$MISSING_DEPS" ]; then
    echo -e "${YELLOW}Missing dependencies:$MISSING_DEPS${NC}"
    echo ""
    echo -e "${YELLOW}Installing dependencies with apt...${NC}"
    sudo apt update
    sudo apt install -y python3 python3-gi gir1.2-gtk-3.0 nemo-python
    echo ""
fi

echo -e "${GREEN}All dependencies satisfied.${NC}"
echo ""

# 2. Create directories
echo -e "${YELLOW}[2/5] Creating directories...${NC}"
mkdir -p "$APP_DIR"
mkdir -p "$EXTENSION_DIR"
mkdir -p "$DESKTOP_DIR"
echo -e "${GREEN}Directories created.${NC}"
echo ""

# 3. Copy application files
echo -e "${YELLOW}[3/5] Installing application...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$SCRIPT_DIR/nemo_miller_columns.py" "$APP_DIR/"
chmod +x "$APP_DIR/nemo_miller_columns.py"
echo -e "${GREEN}Application installed in $APP_DIR${NC}"
echo ""

# 4. Install Nemo extension
echo -e "${YELLOW}[4/5] Installing Nemo extension...${NC}"
cp "$SCRIPT_DIR/nemo-miller-columns-extension.py" "$EXTENSION_DIR/"
echo -e "${GREEN}Extension installed in $EXTENSION_DIR${NC}"
echo ""

# 5. Create .desktop file
echo -e "${YELLOW}[5/5] Creating launcher...${NC}"
cat > "$DESKTOP_DIR/nemo-miller-columns.desktop" << EOF
[Desktop Entry]
Name=Nemo Miller Columns
Comment=Miller Columns file viewer
Exec=python3 $APP_DIR/nemo_miller_columns.py %U
Icon=view-column-symbolic
Terminal=false
Type=Application
Categories=Utility;FileTools;FileManager;
MimeType=inode/directory;
Keywords=file;manager;miller;columns;finder;
EOF

# Update desktop database
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo -e "${GREEN}Launcher created.${NC}"
echo ""

# Restart Nemo to load the extension
echo -e "${YELLOW}Restarting Nemo to load the extension...${NC}"
nemo -q 2>/dev/null || true
sleep 1

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Installation complete!               ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "How to use:"
echo "  1. Open Nemo and navigate to a folder"
echo "  2. Right-click on a folder or on the background"
echo "  3. Select 'Open in Miller Columns'"
echo ""
echo "Or launch directly:"
echo "  python3 $APP_DIR/nemo_miller_columns.py [path]"
echo ""
echo -e "${YELLOW}Note: If the option doesn't appear in the menu, restart your system or run:${NC}"
echo "  nemo -q && nemo"
echo ""
