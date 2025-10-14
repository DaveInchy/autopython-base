
import sys
import os
import time
import pyautogui

# Add the project root to sys.path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.client_window import RuneLiteClientWindow
from src.window_overlay import WindowOverlay
from src.ui_utils import UIInteraction, HumanizedGridClicker, _get_grid_slot_coords, UI_GRID_SPECS

def run_debugger():
    print("--- UI Grid Debugger ---")
    client = RuneLiteClientWindow()
    win_rect = client.get_client_rect()

    if not win_rect:
        print("RuneLite window not found. Exiting.")
        return

    overlay = WindowOverlay(title="UI Grid Debugger", width=win_rect["w"], height=win_rect["h"], x=win_rect['left'], y=win_rect['top'])
    # We don't need a real clicker for the debugger
    dummy_clicker = HumanizedGridClicker()
    ui_interaction = UIInteraction(dummy_clicker, overlay, client)

    print("Debugger running. Press Ctrl+C in the console where the agent is running to stop.")
    
    try:
        while True:
            # --- Clear and Update Overlay Position ---
            overlay.clear()
            client_rect = client.get_rect()
            if not client_rect:
                print("Client window lost.")
                break
            overlay.set_position(client_rect['left'], client_rect['top'])
            overlay.set_size(client_rect['w'], client_rect['h'])

            # --- Draw Client Rect (now the basis for scaling) ---
            if client_rect:
                overlay.draw_rectangle(
                    (0, 0), 
                    (client_rect['w'], client_rect['h']), 
                    outline_color=(255, 255, 0), 
                    width=2
                )
                overlay.draw_text("Client Rect (Scaling Basis)", (5, 5), color=(255, 255, 0), font_size=12)

            # --- Draw Grids ---
            grids_to_draw = ['inventory', 'prayer']
            for grid_name in grids_to_draw:
                grid_spec = UI_GRID_SPECS.get(grid_name)
                if not grid_spec:
                    continue
                
                for slot in range(1, grid_spec['slots'] + 1):
                    ref_coords = _get_grid_slot_coords(grid_name, slot)
                    if not ref_coords:
                        continue
                    
                    # Transform to live absolute coordinates
                    abs_coords = ui_interaction._get_abs_coords(ref_coords)
                    if not abs_coords:
                        continue

                    # Make coords relative to the overlay for drawing
                    draw_x = abs_coords[0] - client_rect['left']
                    draw_y = abs_coords[1] - client_rect['top']

                    # Draw a crosshair
                    # Draw a crosshair using rectangles
                    line_length = 5 # Half length of the line
                    line_thickness = 1 # Half thickness of the line
                    overlay.draw_rectangle(
                        (draw_x - line_length, draw_y - line_thickness), 
                        (draw_x + line_length, draw_y + line_thickness), 
                        fill_color=(0, 255, 0)
                    )
                    overlay.draw_rectangle(
                        (draw_x - line_thickness, draw_y - line_length), 
                        (draw_x + line_thickness, draw_y + line_length), 
                        fill_color=(0, 255, 0)
                    )

            # --- Print Live Info ---
            print(f"\rClient Rect: {client_rect} | Mouse: {pyautogui.position()}", end="")
            sys.stdout.flush()

            overlay.update_overlay()
            time.sleep(1/10)

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Shutting down debugger.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        overlay.close()
        print("\nDebugger finished.")

if __name__ == '__main__':
    run_debugger()
