from typing import Literal
import win32gui
import win32con
import win32api
import win32process
import ctypes
import re

class RuneLiteClientWindow:
    def __init__(self, window_title="RuneLite"):
        self.window_title = window_title
        self.hwnd = self._find_window()
        if not self.hwnd:
            raise Exception(f"RuneLite window with title '{window_title}' not found.")

    def _find_window(self):
        def enum_handler(hwnd, result):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and 'runelite' in title.lower():
                    result.append(hwnd)
        found = []
        win32gui.EnumWindows(enum_handler, found)
        return found[0] if found else None

    def get_window_title(self):
        if not self.hwnd:
            return None
        return win32gui.GetWindowText(self.hwnd)

    def get_logged_in_username(self):
        title = self.get_window_title()
        if title and "RuneLite" in title:
            match = re.search(r"RuneLite\s*-?\s*(.*)", title)
            if match and match.group(1):
                return match.group(1).strip()
        return None

    def is_logged_in(self):
        return self.get_logged_in_username() is not None

    def secure_login(self, username, password):
        raise NotImplementedError("Secure login automation is not implemented.")

    def secure_logout(self, password):
        raise NotImplementedError("Secure logout automation is not implemented.")

    def get_rect(self) -> dict:
        if not self.hwnd:
            return None
        rect = win32gui.GetWindowRect(self.hwnd)
        left, top, right, bottom = rect
        return {
            'left': left,
            'top': top,
            'right': right,
            'bottom': bottom,
            'w': right - left,
            'h': bottom - top,
        }

    def is_minimized(self):
        return win32gui.IsIconic(self.hwnd)

    def move(self, x, y):
        rect = self.get_rect()
        if rect:
            win32gui.MoveWindow(self.hwnd, x, y, rect['w'], rect['h'], True)

    def resize(self, width, height):
        rect = self.get_rect()
        if rect:
            win32gui.MoveWindow(self.hwnd, rect['left'], rect['top'], width, height, True)

    def set_position_and_size(self, x, y, width, height):
        win32gui.MoveWindow(self.hwnd, x, y, width, height, True)

    def is_custom_ui(self):
        style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE)
        standard = win32con.WS_OVERLAPPEDWINDOW
        return (style & standard) != standard

    def get_window_styles(self):
        style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE)
        ex_style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
        return {'style': style, 'ex_style': ex_style}

    def get_process_id(self):
        _, pid = win32process.GetWindowThreadProcessId(self.hwnd)
        return pid

    def bring_to_foreground(self):
        current_foreground_window = win32gui.GetForegroundWindow()
        if self.hwnd != current_foreground_window:
            try:
                win32gui.SetForegroundWindow(self.hwnd)
            except Exception as e:
                pass

    def get_minimap_rect(self):
        """
        Calculates the bounding box of the minimap.
        This is an estimation and might need tuning.
        Assumes a resizable client layout.
        """
        client_rect = self.get_rect()
        if not client_rect:
            return None

        # These are estimations for the minimap's position and size
        # relative to the bottom-right corner of the client window.
        # Values are (right_offset, bottom_offset, width, height)
        minimap_relative_pos = (230, 180) # Approx. pixels from bottom-right
        minimap_size = (160, 160) # Approx. size of the minimap

        # Calculate top-left corner of the minimap
        right_x = client_rect['left'] + client_rect['w']
        bottom_y = client_rect['top'] + client_rect['h']

        map_left = right_x - minimap_relative_pos[0]
        map_top = bottom_y - minimap_relative_pos[1]

        return {
            'left': map_left,
            'top': map_top,
            'w': minimap_size[0],
            'h': minimap_size[1]
        }