import threading
import keyboard
import win32api
import pyautogui
import time
from src.graphics.window_overlay import WindowOverlay
from src.client_window import RuneLiteClientWindow

if __name__ == "__main__":
    print("Starting Coordinate Mapper...")
    print("Press '`' to record the current coordinates and color.")
    print("Press Ctrl+C in this terminal to stop.")

    stop_event = threading.Event()
    client = RuneLiteClientWindow()

    def record_coordinates():
        """Records and prints the current relative mouse coordinates and color."""
        try:
            cursor_x, cursor_y = win32api.GetCursorPos()
            win_rect = client.get_rect()
            if not win_rect:
                return

            # Get color at cursor
            rgb_color = pyautogui.pixel(cursor_x, cursor_y)

            # Calculate relative coordinates
            win_left, win_top = win_rect['left'], win_rect['top']
            win_width, win_height = win_rect["w"], win_rect["h"]
            rel_x = cursor_x - win_left
            rel_y = cursor_y - win_top
            offset_x = win_width - rel_x
            offset_y = win_height - rel_y
            
            print(f"Recorded Coordinates: X={offset_x}, Y={offset_y}, Color={rgb_color}")
        except (win32api.error, pyautogui.PyAutoGUIException):
            print("Could not record coordinates. Is the RuneLite window active and cursor in bounds?")

    keyboard.add_hotkey('`', record_coordinates)

    try:
        win_rect = client.get_rect()
        if win_rect:
            overlay = WindowOverlay(title="CoordinateMapper", width=win_rect["w"], height=win_rect["h"], x=win_rect['left'], y=win_rect['top'])
            
            # Main drawing loop
            while not stop_event.is_set():
                cursor_x, cursor_y = win32api.GetCursorPos()
                
                try:
                    rgb_color = pyautogui.pixel(cursor_x, cursor_y)
                except pyautogui.PyAutoGUIException:
                    rgb_color = (0, 0, 0) # Default color if out of bounds

                win_rect = client.get_rect()
                if not win_rect:
                    time.sleep(0.1)
                    continue
                
                win_left, win_top, win_width, win_height = win_rect['left'], win_rect['top'], win_rect['w'], win_rect['h']

                rel_x = cursor_x - win_left
                rel_y = cursor_y - win_top
                offset_x = win_width - rel_x
                offset_y = win_height - rel_y

                overlay.clear()
                # Draw Coordinates Text
                overlay.draw_text(
                    f"X {offset_x} Y {offset_y}",
                    position=(10, 40),
                    font_size=32,
                    color=(255, 255, 0)  # Yellow
                )
                # Draw Color Text
                overlay.draw_text(
                    f"RGB {rgb_color[0]}, {rgb_color[1]}, {rgb_color[2]}",
                    position=(10, 80),
                    font_size=24,
                    color=(255, 255, 255)  # White
                )
                overlay.update_overlay()
                time.sleep(1/30) # Update at 30 FPS
        else:
            print("RuneLite window not found. Exiting.")

    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("\nStopping Coordinate Mapper...")
        stop_event.set()