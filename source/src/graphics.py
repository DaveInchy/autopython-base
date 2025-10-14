import threading
import win32api
import time
from .client_window import RuneLiteClientWindow
from .window_overlay import WindowOverlay

def render_zulrah_phase(overlay: WindowOverlay, stop_event: threading.Event):
    """
    
    """
    client_window = overlay.client_window
    while not stop_event.is_set():
        cursor_x, cursor_y = win32api.GetCursorPos()
        # Get client window position and size
        win_rect = client_window.get_rect()  # (left, top, right, bottom)
        win_left, win_top, win_right, win_bottom = win_rect[1], win_rect[2], win_rect[3], win_rect[4]
        win_width = win_rect["w"]
        win_height = win_rect["h"]

        # Calculate cursor position relative to the client window (origin at bottom-right)
        rel_x = (cursor_x - win_left)
        rel_y = (cursor_y - win_top)
        offset_x = win_width - rel_x
        offset_y = win_height - rel_y

        overlay.clear()
        overlay.draw_text(
            f"PHASE: ",
            position=(20, 40),
            font_size=32,
            color=(251, 252, 253)
        )
        overlay.update_overlay()
        time.sleep(1/10)
