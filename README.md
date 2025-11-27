# Nemo Miller Columns

A Nemo extension (Linux Mint/Cinnamon file manager) that provides a **Miller Columns** view, similar to macOS Finder.

![Miller Columns](https://upload.wikimedia.org/wikipedia/commons/thumb/5/50/Miller_columns.png/800px-Miller_columns.png)

*[Leggi in Italiano](README_IT.md)*

## Features

- **Miller Columns View**: Navigate folders in side-by-side columns
- **Resizable Columns**: Drag separators to adjust column widths
- **Equal Distribution**: Columns automatically share available space equally (e.g., 4 columns = 25% each)
- **Preview Panel**: Shows file information and image previews
- **Nemo Integration**: Right-click menu option "Open in Miller Columns"
- **Quick Navigation**: Clickable path bar, home and back buttons
- **Image Preview**: Displays thumbnails for image files
- **Open in Terminal**: Button to open a terminal in the current folder
- **Keyboard Shortcuts**: Backspace to go back, Esc to close

## Requirements

- Linux Mint 22 (or other distribution with Nemo)
- Nemo 6.x
- Python 3
- GTK 3
- nemo-python (for the extension)

## Installation

### Automatic (recommended)

```bash
cd /path/to/nemo-miller-columns
./install.sh
```

The script will automatically install missing dependencies.

### Manual

1. **Install dependencies**:

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-3.0 nemo-python
```

2. **Create directories**:

```bash
mkdir -p ~/.local/share/nemo-miller-columns
mkdir -p ~/.local/share/nemo-python/extensions
```

3. **Copy files**:

```bash
# Main application
cp nemo_miller_columns.py ~/.local/share/nemo-miller-columns/
chmod +x ~/.local/share/nemo-miller-columns/nemo_miller_columns.py

# Nemo extension
cp nemo-miller-columns-extension.py ~/.local/share/nemo-python/extensions/
```

4. **Restart Nemo**:

```bash
nemo -q
```

## Usage

### From Nemo (context menu)

1. Open Nemo and navigate to a folder
2. Right-click on a folder **or** on the empty background
3. Select **"Open in Miller Columns"**

### From terminal

```bash
python3 ~/.local/share/nemo-miller-columns/nemo_miller_columns.py [path]
```

Examples:
```bash
# Open home directory
python3 ~/.local/share/nemo-miller-columns/nemo_miller_columns.py

# Open a specific folder
python3 ~/.local/share/nemo-miller-columns/nemo_miller_columns.py /home/user/Documents
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Backspace` | Go to parent folder |
| `Esc` | Close the application |
| `Enter` / Double-click on file | Open with default application |
| `Enter` / Click on folder | Navigate into folder |

## Column Resizing

- **Automatic distribution**: Columns automatically share space equally
- **Manual resize**: Drag the vertical separators between columns to adjust widths
- **Minimum width**: Each column has a minimum width of 100px
- **Visual feedback**: Cursor changes to resize cursor when hovering over separators

## Project Structure

```
nemo-miller-columns/
├── nemo_miller_columns.py           # Main GTK application
├── nemo-miller-columns-extension.py # Nemo context menu extension
├── install.sh                       # Installation script
├── uninstall.sh                     # Uninstallation script
├── README.md                        # English documentation
└── README_IT.md                     # Italian documentation
```

## Uninstallation

```bash
cd /path/to/nemo-miller-columns
./uninstall.sh
```

## Troubleshooting

### The option doesn't appear in the context menu

1. Make sure `nemo-python` is installed:
   ```bash
   sudo apt install nemo-python
   ```

2. Verify the extension is in the correct folder:
   ```bash
   ls ~/.local/share/nemo-python/extensions/
   ```

3. Restart Nemo completely:
   ```bash
   nemo -q
   nemo &
   ```

4. If it still doesn't work, try restarting your system.

### "Nemo module not found" error

The `gi.repository.Nemo` module is only available inside Nemo. The extension will work correctly when loaded by Nemo itself.

### The application doesn't start

Verify that GTK 3 is installed correctly:
```bash
python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk; print('OK')"
```

## License

MIT License - You are free to use, modify, and distribute this software.

## Contributing

Contributions, bug reports, and feature requests are welcome!
