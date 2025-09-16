import win32gui
import win32con
import win32api
import win32process
import ctypes

class RuneLiteClientWindow:
	def get_window_title(self):
		if not self.hwnd:
			return None
		return win32gui.GetWindowText(self.hwnd)


	def get_logged_in_username(self):
		title = self.get_window_title()
		if title and "RuneLite" in title:
			# Try to extract username after 'RuneLite' (with or without dash/space)
			import re
			match = re.search(r"RuneLite\s*-?\s*(.*)", title)
			if match and match.group(1):
				return match.group(1).strip()
		return None

	def is_logged_in(self):
		return self.get_logged_in_username() is not None

	def secure_login(self, username, password):
		"""
		Securely log in to RuneLite. This is a stub: actual implementation would require automation and secure credential handling.
		"""
		# TODO: Implement secure login automation (e.g., using pywinauto, pyautogui, or direct input)
		# Ensure credentials are handled securely (never hardcode!)
		raise NotImplementedError("Secure login automation is not implemented.")

	def secure_logout(self):
		"""
		Securely log out of RuneLite. This is a stub: actual implementation would require automation.
		"""
		# TODO: Implement secure logout automation (e.g., send ESC, click logout, etc.)
		raise NotImplementedError("Secure logout automation is not implemented.")
	def __init__(self, window_title="RuneLite"):
		self.window_title = window_title
		self.hwnd = self._find_window()
		if not self.hwnd:
			raise Exception(f"RuneLite window with title '{window_title}' not found.")

	def _find_window(self):
		# Enumerate all windows and find one containing 'RuneLite' (case-insensitive)
		def enum_handler(hwnd, result):
			if win32gui.IsWindowVisible(hwnd):
				title = win32gui.GetWindowText(hwnd)
				if title and 'runelite' in title.lower():
					result.append(hwnd)
		found = []
		win32gui.EnumWindows(enum_handler, found)
		return found[0] if found else None

	def get_rect(self):
		if not self.hwnd:
			return None
		rect = win32gui.GetWindowRect(self.hwnd)
		# rect: (topleft, topright, bottomright, bottomleft)
		return {
			1: rect[0],
			2: rect[1],
			3: rect[2],
            4: rect[3],
			'w': rect[2] - rect[0],
			'h': rect[3] - rect[1],
		}

	def move(self, x, y):
		rect = self.get_rect()
		if rect:
			win32gui.MoveWindow(self.hwnd, x, y, rect['width'], rect['height'], True)

	def resize(self, width, height):
		rect = self.get_rect()
		if rect:
			win32gui.MoveWindow(self.hwnd, rect['left'], rect['top'], width, height, True)

	def set_position_and_size(self, x, y, width, height):
		win32gui.MoveWindow(self.hwnd, x, y, width, height, True)

	def is_custom_ui(self):
		# Checks if the window does NOT have the standard window style (WS_OVERLAPPEDWINDOW)
		style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE)
		# Standard style: WS_OVERLAPPEDWINDOW
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
		print(f"Attempting to bring window with handle {self.hwnd} to foreground.")
		try:
			win32gui.SetForegroundWindow(self.hwnd)
		except Exception as e:
			print(f"Error bringing window to foreground: {e}")
			print("Please ensure the RuneLite window is not minimized.")
