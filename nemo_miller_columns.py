#!/usr/bin/env python3
"""
Nemo Miller Columns - A Miller Columns file viewer
Inspired by macOS Finder
"""

import sys
import gi
import subprocess
import mimetypes
import urllib.parse
from pathlib import Path

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

        self._setup_css()

        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        # Toolbar
        self._create_toolbar(main_box)

        # Main area
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.pack_start(self.main_paned, True, True, 0)

        # Columns container
        self.columns_container = MillerColumnsContainer(
            self._on_item_selected,
            self._on_item_activated
        )

        # Frame for columns
        columns_frame = Gtk.Frame()
        columns_frame.add(self.columns_container)
        self.main_paned.pack1(columns_frame, True, False)

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

    def _on_key_press(self, widget, event):
        """Handles keyboard shortcuts"""
        if event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        elif event.keyval == Gdk.KEY_BackSpace:
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
