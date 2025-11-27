#!/usr/bin/env python3
"""
Nemo Miller Columns - A Miller Columns file viewer
Inspired by macOS Finder
"""

import sys
import os
import gi
import subprocess
import mimetypes
import urllib.parse
import threading
from pathlib import Path
from dataclasses import dataclass
from typing import Generator, Optional

gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Pango', '1.0')

from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib, Pango


class FileItem:
    """Represents a file or directory"""

    def __init__(self, path):
        self.path = Path(path)
        self.name = self.path.name or str(self.path)
        self.is_dir = self.path.is_dir()
        self.is_symlink = self.path.is_symlink()

    def get_icon(self, icon_theme, size=24):
        """Gets the appropriate icon for the file"""
        try:
            if self.is_dir:
                icon_name = "folder"
            else:
                mime_type, _ = mimetypes.guess_type(str(self.path))
                if mime_type:
                    # Convert MIME type to icon name
                    icon_name = mime_type.replace('/', '-')
                    if not icon_theme.has_icon(icon_name):
                        # Try with generic category
                        icon_name = mime_type.split('/')[0] + "-x-generic"
                        if not icon_theme.has_icon(icon_name):
                            icon_name = "text-x-generic"
                else:
                    icon_name = "text-x-generic"

            if icon_theme.has_icon(icon_name):
                return icon_theme.load_icon(icon_name, size, Gtk.IconLookupFlags.FORCE_SIZE)
            else:
                return icon_theme.load_icon("text-x-generic", size, Gtk.IconLookupFlags.FORCE_SIZE)
        except Exception:
            # Fallback to generic icon
            try:
                return icon_theme.load_icon("text-x-generic", size, Gtk.IconLookupFlags.FORCE_SIZE)
            except Exception:
                return None


class ColumnView(Gtk.Box):
    """A single column in the Miller view"""

    MIN_WIDTH = 100

    def __init__(self, path, on_item_selected, on_item_activated):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.path = Path(path)
        self.on_item_selected = on_item_selected
        self.on_item_activated = on_item_activated
        self.icon_theme = Gtk.IconTheme.get_default()

        # Set minimum width
        self.set_size_request(self.MIN_WIDTH, -1)

        # ScrolledWindow for the list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)

        # ListBox for items
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-selected", self._on_row_selected)
        self.listbox.connect("row-activated", self._on_row_activated)
        self.listbox.get_style_context().add_class("miller-column")

        scroll.add(self.listbox)
        self.pack_start(scroll, True, True, 0)

        self.populate()

    def populate(self):
        """Populates the column with directory contents"""
        for child in self.listbox.get_children():
            self.listbox.remove(child)

        try:
            items = []
            for entry in self.path.iterdir():
                try:
                    # Skip hidden files
                    if not entry.name.startswith('.'):
                        items.append(FileItem(entry))
                except PermissionError:
                    continue

            # Sort: directories first, then files, alphabetically
            items.sort(key=lambda x: (not x.is_dir, x.name.lower()))

            for item in items:
                row = self._create_row(item)
                self.listbox.add(row)

        except PermissionError:
            label = Gtk.Label(label="Permission denied")
            label.set_margin_top(20)
            label.set_margin_bottom(20)
            self.listbox.add(label)
        except Exception as e:
            label = Gtk.Label(label=f"Error: {str(e)}")
            label.set_margin_top(20)
            self.listbox.add(label)

        self.listbox.show_all()

    def _create_row(self, item):
        """Creates a row for an item"""
        row = Gtk.ListBoxRow()
        row.item = item

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hbox.set_margin_start(8)
        hbox.set_margin_end(8)
        hbox.set_margin_top(4)
        hbox.set_margin_bottom(4)

        # Icon
        icon = item.get_icon(self.icon_theme, 24)
        if icon:
            image = Gtk.Image.new_from_pixbuf(icon)
        else:
            image = Gtk.Image.new_from_icon_name("text-x-generic", Gtk.IconSize.LARGE_TOOLBAR)
        hbox.pack_start(image, False, False, 0)

        # File name
        label = Gtk.Label(label=item.name)
        label.set_xalign(0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_hexpand(True)
        hbox.pack_start(label, True, True, 0)

        # Arrow for directories
        if item.is_dir:
            arrow = Gtk.Image.new_from_icon_name("go-next-symbolic", Gtk.IconSize.MENU)
            arrow.set_opacity(0.5)
            hbox.pack_end(arrow, False, False, 0)

        row.add(hbox)
        return row

    def _on_row_selected(self, listbox, row):
        """Handles row selection"""
        if row and hasattr(row, 'item'):
            self.on_item_selected(self, row.item)

    def _on_row_activated(self, listbox, row):
        """Handles row activation (double-click)"""
        if row and hasattr(row, 'item'):
            self.on_item_activated(row.item)

    def select_path(self, path):
        """Selects an item by its path"""
        path = Path(path)
        for row in self.listbox.get_children():
            if hasattr(row, 'item') and row.item.path == path:
                self.listbox.select_row(row)
                return True
        return False


class ResizeHandle(Gtk.EventBox):
    """Handle for resizing columns"""

    def __init__(self, on_drag):
        super().__init__()
        self.on_drag = on_drag
        self.dragging = False
        self.start_x = 0

        # Visual separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.add(separator)

        # Style
        self.get_style_context().add_class("resize-handle")
        self.set_size_request(6, -1)

        # Events
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                       Gdk.EventMask.BUTTON_RELEASE_MASK |
                       Gdk.EventMask.POINTER_MOTION_MASK)

        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion)
        self.connect("enter-notify-event", self._on_enter)
        self.connect("leave-notify-event", self._on_leave)

    def _on_button_press(self, widget, event):
        """Handles mouse button press"""
        if event.button == 1:
            self.dragging = True
            self.start_x = event.x_root
            return True
        return False

    def _on_button_release(self, widget, event):
        """Handles mouse button release"""
        self.dragging = False
        return True

    def _on_motion(self, widget, event):
        """Handles mouse motion during drag"""
        if self.dragging:
            delta = event.x_root - self.start_x
            self.start_x = event.x_root
            self.on_drag(self, delta)
            return True
        return False

    def _on_enter(self, widget, event):
        """Handles mouse enter - changes cursor"""
        window = self.get_window()
        if window:
            window.set_cursor(Gdk.Cursor.new_from_name(self.get_display(), "col-resize"))

    def _on_leave(self, widget, event):
        """Handles mouse leave - resets cursor"""
        if not self.dragging:
            window = self.get_window()
            if window:
                window.set_cursor(None)


class PreviewPanel(Gtk.Box):
    """Preview panel for the selected file"""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_size_request(280, -1)

        self.icon_theme = Gtk.IconTheme.get_default()

        # Large icon
        self.icon_image = Gtk.Image()
        self.pack_start(self.icon_image, False, False, 0)

        # File name
        self.name_label = Gtk.Label()
        self.name_label.set_line_wrap(True)
        self.name_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.name_label.set_max_width_chars(25)
        self.name_label.get_style_context().add_class("preview-title")
        self.pack_start(self.name_label, False, False, 0)

        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(separator, False, False, 10)

        # Information grid
        self.info_grid = Gtk.Grid()
        self.info_grid.set_column_spacing(12)
        self.info_grid.set_row_spacing(6)
        self.pack_start(self.info_grid, False, False, 0)

        # Image preview
        self.preview_scroll = Gtk.ScrolledWindow()
        self.preview_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.preview_image = Gtk.Image()
        self.preview_scroll.add(self.preview_image)
        self.pack_start(self.preview_scroll, True, True, 0)

        self.show_all()
        self.preview_scroll.hide()

    def update(self, item):
        """Updates the preview with item information"""
        if item is None:
            self.clear()
            return

        icon = item.get_icon(self.icon_theme, 64)
        if icon:
            self.icon_image.set_from_pixbuf(icon)

        self.name_label.set_markup(f"<b>{GLib.markup_escape_text(item.name)}</b>")

        # Clear previous info
        for child in self.info_grid.get_children():
            self.info_grid.remove(child)

        row = 0

        # Type
        if item.is_dir:
            file_type = "Folder"
        else:
            mime_type, _ = mimetypes.guess_type(str(item.path))
            file_type = mime_type or "File"
        self._add_info_row("Type:", file_type, row)
        row += 1

        # Size
        try:
            if item.is_dir:
                count = sum(1 for _ in item.path.iterdir())
                size_str = f"{count} items"
            else:
                size = item.path.stat().st_size
                size_str = self._format_size(size)
            self._add_info_row("Size:", size_str, row)
            row += 1
        except (PermissionError, OSError):
            pass

        # Modified date
        try:
            mtime = item.path.stat().st_mtime
            from datetime import datetime
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            self._add_info_row("Modified:", mtime_str, row)
            row += 1
        except (PermissionError, OSError):
            pass

        # Path
        self._add_info_row("Path:", str(item.path.parent), row)

        # Image preview
        self._update_image_preview(item)
        self.info_grid.show_all()

    def _add_info_row(self, label_text, value_text, row):
        """Adds an information row"""
        label = Gtk.Label(label=label_text)
        label.set_xalign(1)
        label.get_style_context().add_class("dim-label")
        self.info_grid.attach(label, 0, row, 1, 1)

        value = Gtk.Label(label=value_text)
        value.set_xalign(0)
        value.set_line_wrap(True)
        value.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        value.set_max_width_chars(20)
        value.set_selectable(True)
        self.info_grid.attach(value, 1, row, 1, 1)

    def _format_size(self, size):
        """Formats size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def _update_image_preview(self, item):
        """Shows preview if item is an image"""
        if item.is_dir:
            self.preview_scroll.hide()
            return

        mime_type, _ = mimetypes.guess_type(str(item.path))
        if mime_type and mime_type.startswith('image/'):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(item.path), 250, 250, True
                )
                self.preview_image.set_from_pixbuf(pixbuf)
                self.preview_scroll.show()
            except Exception:
                self.preview_scroll.hide()
        else:
            self.preview_scroll.hide()

    def clear(self):
        """Clears the preview panel"""
        self.icon_image.clear()
        self.name_label.set_text("")
        for child in self.info_grid.get_children():
            self.info_grid.remove(child)
        self.preview_scroll.hide()


@dataclass
class SearchResult:
    """Represents a search result"""
    path: Path
    name: str
    is_dir: bool
    match_type: str  # "name" or "content"


class SearchEngine:
    """Handles file searching with name and content matching"""

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit for content search

    def __init__(self):
        self.cancelled = False

    def cancel(self):
        """Cancels the current search"""
        self.cancelled = True

    def search(self, root_path: Path, query: str) -> Generator[SearchResult, None, None]:
        """
        Searches for files matching the query.
        Yields SearchResult objects as they are found.
        """
        self.cancelled = False
        query_lower = query.lower()

        for dirpath, dirnames, filenames in os.walk(root_path):
            if self.cancelled:
                return

            # Skip hidden directories
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]

            current_dir = Path(dirpath)

            # Search in directory names
            for dirname in dirnames:
                if self.cancelled:
                    return
                if query_lower in dirname.lower():
                    yield SearchResult(
                        path=current_dir / dirname,
                        name=dirname,
                        is_dir=True,
                        match_type="name"
                    )

            # Search in file names and contents
            for filename in filenames:
                if self.cancelled:
                    return

                # Skip hidden files
                if filename.startswith('.'):
                    continue

                file_path = current_dir / filename

                # Check if name matches
                name_match = query_lower in filename.lower()
                if name_match:
                    yield SearchResult(
                        path=file_path,
                        name=filename,
                        is_dir=False,
                        match_type="name"
                    )
                    continue  # Don't search content if name already matches

                # Search in file content
                if self._search_in_content(file_path, query_lower):
                    yield SearchResult(
                        path=file_path,
                        name=filename,
                        is_dir=False,
                        match_type="content"
                    )

    def _search_in_content(self, file_path: Path, query: str) -> bool:
        """Searches for query in file content. Returns True if found."""
        try:
            # Check file size
            if file_path.stat().st_size > self.MAX_FILE_SIZE:
                return False

            # Check if it's a text file
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                return False

            # Only search text-like files
            text_types = ('text/', 'application/json', 'application/xml',
                         'application/javascript', 'application/x-python',
                         'application/x-sh', 'application/x-perl')
            if not any(mime_type.startswith(t) for t in text_types):
                return False

            # Read and search
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return query in content.lower()

        except (PermissionError, OSError, UnicodeDecodeError):
            return False


class SearchResultsView(Gtk.Box):
    """View for displaying search results"""

    def __init__(self, on_result_activated):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.on_result_activated = on_result_activated
        self.icon_theme = Gtk.IconTheme.get_default()

        # Header with result count and close button
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_start(12)
        header.set_margin_end(12)
        header.set_margin_top(8)
        header.set_margin_bottom(8)

        self.status_label = Gtk.Label(label="Searching...")
        self.status_label.set_xalign(0)
        header.pack_start(self.status_label, True, True, 0)

        # Spinner for loading
        self.spinner = Gtk.Spinner()
        header.pack_start(self.spinner, False, False, 0)

        self.pack_start(header, False, False, 0)

        # Scrolled window for results
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        # ListBox for results
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-activated", self._on_row_activated)
        self.listbox.get_style_context().add_class("search-results")

        scroll.add(self.listbox)
        self.pack_start(scroll, True, True, 0)

        self.result_count = 0

    def clear(self):
        """Clears all results"""
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        self.result_count = 0
        self.status_label.set_text("Searching...")

    def start_search(self):
        """Called when search starts"""
        self.clear()
        self.spinner.start()

    def stop_search(self):
        """Called when search completes"""
        self.spinner.stop()
        if self.result_count == 0:
            self.status_label.set_text("No results found")
        else:
            self.status_label.set_text(f"{self.result_count} results")

    def add_result(self, result: SearchResult):
        """Adds a search result to the list"""
        self.result_count += 1

        row = Gtk.ListBoxRow()
        row.result = result

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hbox.set_margin_start(12)
        hbox.set_margin_end(12)
        hbox.set_margin_top(6)
        hbox.set_margin_bottom(6)

        # Icon
        if result.is_dir:
            icon_name = "folder"
        else:
            mime_type, _ = mimetypes.guess_type(str(result.path))
            if mime_type:
                icon_name = mime_type.replace('/', '-')
                if not self.icon_theme.has_icon(icon_name):
                    icon_name = "text-x-generic"
            else:
                icon_name = "text-x-generic"

        try:
            icon = self.icon_theme.load_icon(icon_name, 24, Gtk.IconLookupFlags.FORCE_SIZE)
            image = Gtk.Image.new_from_pixbuf(icon)
        except Exception:
            image = Gtk.Image.new_from_icon_name("text-x-generic", Gtk.IconSize.LARGE_TOOLBAR)
        hbox.pack_start(image, False, False, 0)

        # Text container
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        # File name with match type indicator
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name_label = Gtk.Label(label=result.name)
        name_label.set_xalign(0)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        name_box.pack_start(name_label, False, False, 0)

        # Match type badge
        if result.match_type == "content":
            badge = Gtk.Label(label="content")
            badge.get_style_context().add_class("dim-label")
            badge.set_markup("<small><i>in content</i></small>")
            name_box.pack_start(badge, False, False, 0)

        text_box.pack_start(name_box, False, False, 0)

        # Path
        path_label = Gtk.Label(label=str(result.path.parent))
        path_label.set_xalign(0)
        path_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        path_label.get_style_context().add_class("dim-label")
        text_box.pack_start(path_label, False, False, 0)

        hbox.pack_start(text_box, True, True, 0)

        # Arrow
        arrow = Gtk.Image.new_from_icon_name("go-next-symbolic", Gtk.IconSize.MENU)
        arrow.set_opacity(0.5)
        hbox.pack_end(arrow, False, False, 0)

        row.add(hbox)
        self.listbox.add(row)
        row.show_all()

        # Update status
        self.status_label.set_text(f"{self.result_count} results...")

    def _on_row_activated(self, listbox, row):
        """Handles result activation"""
        if row and hasattr(row, 'result'):
            self.on_result_activated(row.result)


class MillerColumnsContainer(Gtk.Box):
    """Container for Miller columns with resizing support"""

    def __init__(self, on_item_selected, on_item_activated):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.on_item_selected_callback = on_item_selected
        self.on_item_activated_callback = on_item_activated

        self.columns = []  # List of ColumnView
        self.handles = []  # List of ResizeHandle
        self.column_widths = []  # Column widths (-1 = auto)

        self.get_style_context().add_class("miller-columns-container")

    def add_column(self, path):
        """Adds a new column"""
        column = ColumnView(path, self._on_item_selected, self.on_item_activated_callback)

        # If there are existing columns, add a resize handle
        if self.columns:
            handle = ResizeHandle(self._on_handle_drag)
            handle.column_index = len(self.columns) - 1
            self.handles.append(handle)
            self.pack_start(handle, False, False, 0)
            handle.show_all()

        self.columns.append(column)
        self.column_widths.append(-1)  # -1 means "auto"

        self.pack_start(column, True, True, 0)
        column.show_all()

        # Recalculate widths
        GLib.idle_add(self._distribute_widths)

        return column

    def remove_columns_after(self, column):
        """Removes all columns after the specified one"""
        if column not in self.columns:
            return

        idx = self.columns.index(column)

        # Remove columns and handles
        while len(self.columns) > idx + 1:
            col = self.columns.pop()
            self.remove(col)
            col.destroy()
            self.column_widths.pop()

            if self.handles:
                handle = self.handles.pop()
                self.remove(handle)
                handle.destroy()

        # Recalculate widths
        GLib.idle_add(self._distribute_widths)

    def clear(self):
        """Removes all columns"""
        for col in self.columns:
            self.remove(col)
            col.destroy()
        for handle in self.handles:
            self.remove(handle)
            handle.destroy()
        self.columns.clear()
        self.handles.clear()
        self.column_widths.clear()

    def _on_item_selected(self, column, item):
        """Handles selection and recalculates widths"""
        self.on_item_selected_callback(column, item)
        GLib.idle_add(self._distribute_widths)

    def _distribute_widths(self):
        """Distributes widths equally among columns"""
        if not self.columns:
            return False

        allocation = self.get_allocation()
        total_width = allocation.width

        if total_width <= 1:
            return False

        # Calculate space for handles
        handle_width = 6 * len(self.handles)
        available_width = total_width - handle_width

        # Count columns with auto width
        auto_count = sum(1 for w in self.column_widths if w == -1)
        fixed_width = sum(w for w in self.column_widths if w != -1)

        if auto_count > 0:
            auto_width = max(ColumnView.MIN_WIDTH, (available_width - fixed_width) // auto_count)
        else:
            auto_width = 0

        # Apply widths
        for i, col in enumerate(self.columns):
            if self.column_widths[i] == -1:
                col.set_size_request(auto_width, -1)
            else:
                col.set_size_request(self.column_widths[i], -1)

        return False

    def _on_handle_drag(self, handle, delta):
        """Handles dragging of a resize handle"""
        idx = handle.column_index

        if idx >= len(self.columns) - 1:
            return

        # Get current widths
        left_col = self.columns[idx]
        right_col = self.columns[idx + 1]

        left_width = left_col.get_allocation().width
        right_width = right_col.get_allocation().width

        # Calculate new widths
        new_left = left_width + delta
        new_right = right_width - delta

        # Respect minimum widths
        if new_left < ColumnView.MIN_WIDTH:
            delta = ColumnView.MIN_WIDTH - left_width
            new_left = ColumnView.MIN_WIDTH
            new_right = right_width - delta

        if new_right < ColumnView.MIN_WIDTH:
            delta = right_width - ColumnView.MIN_WIDTH
            new_right = ColumnView.MIN_WIDTH
            new_left = left_width + delta

        # Update stored widths
        self.column_widths[idx] = max(ColumnView.MIN_WIDTH, int(new_left))
        self.column_widths[idx + 1] = max(ColumnView.MIN_WIDTH, int(new_right))

        # Apply
        left_col.set_size_request(self.column_widths[idx], -1)
        right_col.set_size_request(self.column_widths[idx + 1], -1)


class MillerColumnsWindow(Gtk.ApplicationWindow):
    """Main window with Miller Columns view"""

    def __init__(self, app, start_path=None):
        super().__init__(application=app, title="Nemo Miller Columns")

        self.set_default_size(1200, 700)
        self.current_path = Path(start_path or Path.home())

        # Search state
        self.search_mode = False
        self.search_engine = SearchEngine()
        self.search_thread = None
        self.search_timeout_id = None

        self._setup_css()

        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        # Toolbar
        self._create_toolbar(main_box)

        # Main area
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.pack_start(self.main_paned, True, True, 0)

        # Stack for switching between columns and search results
        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.content_stack.set_transition_duration(150)

        # Columns container
        self.columns_container = MillerColumnsContainer(
            self._on_item_selected,
            self._on_item_activated
        )
        columns_frame = Gtk.Frame()
        columns_frame.add(self.columns_container)
        self.content_stack.add_named(columns_frame, "columns")

        # Search results view
        self.search_results_view = SearchResultsView(self._on_search_result_activated)
        search_frame = Gtk.Frame()
        search_frame.add(self.search_results_view)
        self.content_stack.add_named(search_frame, "search")

        self.main_paned.pack1(self.content_stack, True, False)

        # Preview panel
        self.preview_panel = PreviewPanel()
        preview_frame = Gtk.Frame()
        preview_frame.add(self.preview_panel)
        preview_frame.get_style_context().add_class("preview-frame")
        self.main_paned.pack2(preview_frame, False, False)

        self.main_paned.set_position(900)

        # Navigate to initial path
        self._navigate_to(self.current_path)

        self.connect("key-press-event", self._on_key_press)
        self.show_all()

    def _setup_css(self):
        """Sets up custom CSS styles"""
        css = b"""
        .miller-columns-container {
            background-color: @theme_base_color;
        }

        .miller-column {
            background-color: @theme_base_color;
        }

        .miller-column row {
            padding: 2px;
        }

        .miller-column row:selected {
            background-color: @theme_selected_bg_color;
            color: @theme_selected_fg_color;
        }

        .preview-frame {
            background-color: @theme_base_color;
        }

        .preview-title {
            font-size: 14px;
        }

        .path-bar {
            padding: 4px 8px;
            background-color: @theme_bg_color;
        }

        .path-button {
            padding: 2px 6px;
            min-height: 24px;
        }

        .resize-handle {
            background-color: @borders;
            min-width: 6px;
        }

        .resize-handle:hover {
            background-color: @theme_selected_bg_color;
        }

        .search-results {
            background-color: @theme_base_color;
        }

        .search-results row {
            padding: 4px;
        }

        .search-results row:selected {
            background-color: @theme_selected_bg_color;
            color: @theme_selected_fg_color;
        }
        """

        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _create_toolbar(self, container):
        """Creates the navigation toolbar"""
        toolbar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar_box.set_margin_start(6)
        toolbar_box.set_margin_end(6)
        toolbar_box.set_margin_top(6)
        toolbar_box.set_margin_bottom(6)

        # Back button
        back_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON)
        back_btn.set_tooltip_text("Back")
        back_btn.connect("clicked", self._on_go_back)
        toolbar_box.pack_start(back_btn, False, False, 0)

        # Home button
        home_btn = Gtk.Button.new_from_icon_name("go-home-symbolic", Gtk.IconSize.BUTTON)
        home_btn.set_tooltip_text("Home")
        home_btn.connect("clicked", self._on_go_home)
        toolbar_box.pack_start(home_btn, False, False, 0)

        # Path bar
        self.path_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.path_bar.get_style_context().add_class("path-bar")

        path_scroll = Gtk.ScrolledWindow()
        path_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        path_scroll.add(self.path_bar)
        toolbar_box.pack_start(path_scroll, True, True, 0)

        # Search entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search files and contents...")
        self.search_entry.set_width_chars(25)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("stop-search", self._on_search_stopped)
        toolbar_box.pack_start(self.search_entry, False, False, 0)

        # Open in Nemo button
        nemo_btn = Gtk.Button.new_from_icon_name("folder-open-symbolic", Gtk.IconSize.BUTTON)
        nemo_btn.set_tooltip_text("Open in Nemo")
        nemo_btn.connect("clicked", self._on_open_in_nemo)
        toolbar_box.pack_end(nemo_btn, False, False, 0)

        # Terminal button
        terminal_btn = Gtk.Button.new_from_icon_name("utilities-terminal-symbolic", Gtk.IconSize.BUTTON)
        terminal_btn.set_tooltip_text("Open Terminal here")
        terminal_btn.connect("clicked", self._on_open_terminal)
        toolbar_box.pack_end(terminal_btn, False, False, 0)

        container.pack_start(toolbar_box, False, False, 0)

    def _update_path_bar(self):
        """Updates the path bar"""
        for child in self.path_bar.get_children():
            self.path_bar.remove(child)

        parts = self.current_path.parts
        for i, part in enumerate(parts):
            if i > 0:
                sep = Gtk.Label(label="/")
                sep.set_opacity(0.5)
                self.path_bar.pack_start(sep, False, False, 0)

            btn = Gtk.Button(label=part or "/")
            btn.get_style_context().add_class("path-button")
            btn.get_style_context().add_class("flat")
            btn.path = Path(*parts[:i+1])
            btn.connect("clicked", self._on_path_button_clicked)
            self.path_bar.pack_start(btn, False, False, 0)

        self.path_bar.show_all()

    def _navigate_to(self, path):
        """Navigates to a specific path"""
        path = Path(path).resolve()

        if not path.exists():
            return

        self.columns_container.clear()

        parts = path.parts
        current = Path(parts[0])

        self.columns_container.add_column(current)

        for part in parts[1:]:
            next_path = current / part
            if next_path.is_dir():
                if self.columns_container.columns:
                    self.columns_container.columns[-1].select_path(next_path)
                self.columns_container.add_column(next_path)
                current = next_path

        self.current_path = path
        self._update_path_bar()

    def _on_item_selected(self, column, item):
        """Handles item selection"""
        self.columns_container.remove_columns_after(column)

        if item.is_dir:
            self.columns_container.add_column(item.path)
            self.current_path = item.path
        else:
            self.current_path = item.path.parent

        self._update_path_bar()
        self.preview_panel.update(item)

    def _on_item_activated(self, item):
        """Handles item activation (double-click)"""
        if not item.is_dir:
            try:
                subprocess.Popen(['xdg-open', str(item.path)])
            except Exception as e:
                dialog = Gtk.MessageDialog(
                    transient_for=self,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text=f"Cannot open file: {e}"
                )
                dialog.run()
                dialog.destroy()

    def _on_go_back(self, button):
        """Goes to parent directory"""
        if self.current_path.parent != self.current_path:
            self._navigate_to(self.current_path.parent)

    def _on_go_home(self, button):
        """Goes to home directory"""
        self._navigate_to(Path.home())

    def _on_path_button_clicked(self, button):
        """Handles path button click"""
        self._navigate_to(button.path)

    def _on_open_in_nemo(self, button):
        """Opens current folder in Nemo"""
        try:
            subprocess.Popen(['nemo', str(self.current_path)])
        except Exception as e:
            print(f"Error opening Nemo: {e}")

    def _on_open_terminal(self, button):
        """Opens a terminal in the current folder"""
        try:
            terminals = ['gnome-terminal', 'xfce4-terminal', 'konsole', 'xterm']
            for term in terminals:
                try:
                    subprocess.Popen([term, '--working-directory', str(self.current_path)])
                    return
                except FileNotFoundError:
                    continue
        except Exception as e:
            print(f"Error opening terminal: {e}")

    def _on_search_changed(self, search_entry):
        """Handles search text changes with debounce"""
        # Cancel any pending search timeout
        if self.search_timeout_id:
            GLib.source_remove(self.search_timeout_id)
            self.search_timeout_id = None

        query = search_entry.get_text().strip()

        if not query:
            # Clear search and return to columns view
            self._exit_search_mode()
            return

        # Debounce: wait 300ms before starting search
        self.search_timeout_id = GLib.timeout_add(300, self._start_search, query)

    def _on_search_stopped(self, search_entry):
        """Handles search stop (Escape in search entry)"""
        self._exit_search_mode()

    def _start_search(self, query):
        """Starts the actual search in a background thread"""
        self.search_timeout_id = None

        # Cancel any running search
        if self.search_thread and self.search_thread.is_alive():
            self.search_engine.cancel()
            self.search_thread.join(timeout=0.5)

        # Enter search mode
        self.search_mode = True
        self.content_stack.set_visible_child_name("search")
        self.search_results_view.start_search()

        # Start new search thread
        self.search_thread = threading.Thread(
            target=self._search_thread_func,
            args=(self.current_path, query),
            daemon=True
        )
        self.search_thread.start()

        return False  # Don't repeat timeout

    def _search_thread_func(self, root_path, query):
        """Search function running in background thread"""
        try:
            for result in self.search_engine.search(root_path, query):
                if self.search_engine.cancelled:
                    break
                # Add result to UI via main thread
                GLib.idle_add(self.search_results_view.add_result, result)
        finally:
            # Signal search complete
            GLib.idle_add(self.search_results_view.stop_search)

    def _exit_search_mode(self):
        """Exits search mode and returns to columns view"""
        # Cancel any running search
        if self.search_thread and self.search_thread.is_alive():
            self.search_engine.cancel()

        self.search_mode = False
        self.content_stack.set_visible_child_name("columns")
        self.search_entry.set_text("")
        self.search_results_view.clear()

    def _on_search_result_activated(self, result: SearchResult):
        """Handles activation of a search result"""
        # Navigate to the file's parent directory
        if result.is_dir:
            target_path = result.path
        else:
            target_path = result.path.parent

        # Exit search mode and navigate
        self._exit_search_mode()
        self._navigate_to(target_path)

        # If it's a file, open it
        if not result.is_dir:
            try:
                subprocess.Popen(['xdg-open', str(result.path)])
            except Exception as e:
                print(f"Error opening file: {e}")

    def _on_key_press(self, widget, event):
        """Handles keyboard shortcuts"""
        # Ctrl+F: Focus search entry
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            if event.keyval == Gdk.KEY_f:
                self.search_entry.grab_focus()
                return True

        # Escape: Exit search mode or close window
        if event.keyval == Gdk.KEY_Escape:
            if self.search_mode:
                self._exit_search_mode()
                return True
            else:
                self.close()
                return True

        # Backspace: Go back (only if not in search entry)
        if event.keyval == Gdk.KEY_BackSpace:
            # Don't intercept if focus is on search entry
            if not self.search_entry.has_focus():
                self._on_go_back(None)
                return True

        return False


class MillerColumnsApp(Gtk.Application):
    """Main application"""

    def __init__(self, start_path=None):
        super().__init__(
            application_id="org.nemo.miller-columns",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        )
        self.start_path = start_path

    def do_activate(self):
        """Activates the application"""
        win = MillerColumnsWindow(self, self.start_path)
        win.present()

    def do_command_line(self, command_line):
        """Handles command line arguments"""
        args = command_line.get_arguments()

        if len(args) > 1:
            path = args[1]
            # Handle file:// URI
            if path.startswith('file://'):
                path = urllib.parse.unquote(path[7:])
            self.start_path = path

        self.activate()
        return 0


def main():
    """Entry point"""
    start_path = None

    if len(sys.argv) > 1:
        path = sys.argv[1]
        # Handle file:// URI
        if path.startswith('file://'):
            path = urllib.parse.unquote(path[7:])
        start_path = path

    app = MillerColumnsApp(start_path)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
