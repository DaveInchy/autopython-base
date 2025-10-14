import sys
import pyautogui

class OperatingSystemInput:
    def get_cursor_pos(self):
        return pyautogui.position()
