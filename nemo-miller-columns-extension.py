#!/usr/bin/env python3
"""
Nemo extension to open folders in Miller Columns view
Adds a context menu entry "Open in Miller Columns"
"""

import os
import subprocess
from urllib.parse import unquote
from gi.repository import Nemo, GObject


class MillerColumnsExtension(GObject.GObject, Nemo.MenuProvider):
    """Extension that adds Miller Columns option to context menu"""

    def __init__(self):
        super().__init__()
        # Path to the Miller Columns application
        self.app_path = os.path.expanduser("~/.local/share/nemo-miller-columns/nemo_miller_columns.py")

    def _open_miller_columns(self, menu, folder_path):
        """Opens the folder in Miller Columns"""
        try:
            subprocess.Popen(['python3', self.app_path, folder_path])
        except Exception as e:
            print(f"Error opening Miller Columns: {e}")

    def _get_file_path(self, file_info):
        """Extracts the file path from a NemoFileInfo"""
        uri = file_info.get_uri()
        if uri.startswith('file://'):
            return unquote(uri[7:])
        return None

    def get_file_items(self, window, files):
        """Context menu for selected files/folders"""
        if len(files) != 1:
            return []

        file_info = files[0]

        # Only for directories
        if not file_info.is_directory():
            return []

        path = self._get_file_path(file_info)
        if not path:
            return []

        # Create menu item
        item = Nemo.MenuItem(
            name="MillerColumnsExtension::OpenMillerColumns",
            label="Open in Miller Columns",
            tip="Open this folder in Miller Columns view",
            icon="view-column-symbolic"
        )
        item.connect('activate', self._open_miller_columns, path)

        return [item]

    def get_background_items(self, window, folder):
        """Context menu for folder background (click on empty area)"""
        path = self._get_file_path(folder)
        if not path:
            return []

        # Create menu item
        item = Nemo.MenuItem(
            name="MillerColumnsExtension::OpenMillerColumnsBackground",
            label="Open in Miller Columns",
            tip="Open this folder in Miller Columns view",
            icon="view-column-symbolic"
        )
        item.connect('activate', self._open_miller_columns, path)

        return [item]
