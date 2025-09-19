import threading
import keyboard
import win32api
from src.graphics.window_overlay import WindowOverlay, DrawCursorPosition
from src.client_window import RuneLiteClientWindow

if __name__ == "__main__":
    print("Starting Coordinate Mapper...")
    print("Press '`' to record the current coordinates.")
    print("Press Ctrl+C in this terminal to stop.")

    stop_event = threading.Event()
    client = RuneLiteClientWindow()

    def record_coordinates():
        """Records and prints the current relative mouse coordinates."""
        try:
            cursor_x, cursor_y = win32api.GetCursorPos()
            win_rect = client.get_rect()
            if not win_rect:
                return

            win_left, win_top = win_rect['left'], win_rect['top']
            win_width, win_height = win_rect["w"], win_rect["h"]

            rel_x = cursor_x - win_left
            rel_y = cursor_y - win_top
            offset_x = win_width - rel_x
            offset_y = win_height - rel_y
            print(f"Recorded Coordinates: X={offset_x}, Y={offset_y}")
        except win32api.error:
            # This can happen if the window is closed or not focused
            print("Could not record coordinates. Is the RuneLite window active?")

    keyboard.add_hotkey('`', record_coordinates)

    try:
        # Create the overlay and run the drawing function in the main thread
        win_rect = client.get_rect()
        if win_rect:
            overlay = WindowOverlay(title="CoordinateMapper", width=win_rect["w"], height=win_rect["h"], x=win_rect['left'], y=win_rect['top'])
            DrawCursorPosition(overlay, stop_event)
        else:
            print("RuneLite window not found. Exiting.")

    except (KeyboardInterrupt, SystemExit):
        # This will be triggered by Ctrl+C
        pass
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("\nStopping Coordinate Mapper...")
        stop_event.set()
