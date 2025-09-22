import os
import re
import time
import pyautogui
import random
import threading
import difflib
import math # Added import
import keyboard # Added import
import signal # Added import
import sys # Added import

from src.client_window import RuneLiteClientWindow
from src.game_screen import GameScreen
from src.hotkeys import HotkeyManager
from src.ui_utils import UIInteraction, HumanizedGridClicker
from src.graphics.window_overlay import WindowOverlay # Added import

class RoutePather:
    """
    A class to follow a predefined path on the minimap using image matching.
    """
    def __init__(self, route_name: str, confidence=0.8, overlay: WindowOverlay = None):
        """
        Initializes the RoutePather.

        Args:
            route_name (str): The name of the route directory in 'scripts/res/pathing/'.
            confidence (float): The confidence level for image matching.
            overlay (WindowOverlay, optional): An optional WindowOverlay instance for visual feedback.
        """
        self.client = RuneLiteClientWindow()
        self.route_path = os.path.join(os.path.dirname(__file__), 'res', 'pathing', route_name)
        if not os.path.isdir(self.route_path):
            raise FileNotFoundError(f"Route directory not found at: {self.route_path}")
            
        self.steps = self._get_route_steps()
        self.confidence = confidence
        self.overlay = overlay # Assign the passed overlay

        print(f"Initialized RoutePather for route '{route_name}' with {len(self.steps)} steps.")

    def _get_minimap_region(self) -> tuple | None:
        """
        Calculates the absolute screen coordinates of the minimap.

        Returns:
            A tuple (left, top, right, bottom) for the minimap region, or None.
        """
        rect = self.client.get_rect()
        if not rect:
            print("Error: Could not get RuneLite window dimensions.")
            return None
        
        minimap_width = 200
        minimap_height = 200
        
        left = rect['left'] + rect['w'] - minimap_width - 15
        top = rect['top'] + 25
        right = left + minimap_width
        bottom = top + minimap_height
        
        return (left, top, right, bottom)

    def _get_route_steps(self) -> dict:
        """
        Scans the route directory and organizes step images into a structured dictionary.
        """
        steps = {}
        pattern = re.compile(r"step\.(\d{3})(?:\.opt(\d+))?\.png")

        for filename in sorted(os.listdir(self.route_path)):
            match = pattern.match(filename)
            if match:
                step_num = int(match.group(1))
                
                if step_num not in steps:
                    steps[step_num] = {
                        'images': [],
                        'wait': 5.0,
                        'action': 'click',
                        'confidence': None
                    }
                
                full_path = os.path.join(self.route_path, filename)
                steps[step_num]['images'].append(full_path)
        
        for step_num in steps:
            steps[step_num]['images'].sort(key=lambda x: 'opt' in x)

        if 4 in steps:
            steps[4]['confidence'] = 0.7
            steps[4]['wait'] = 8.0

        if 5 in steps:
            steps[5]['confidence'] = 0.9

        if 6 in steps:
            steps[6]['confidence'] = 0.9

        return steps

    def _get_minimap_center(self) -> tuple | None:
        minimap_region = self._get_minimap_region()
        if not minimap_region:
            return None
        
        left, top, right, bottom = minimap_region
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        return (center_x, center_y)

    def move_minimap_direction(self, direction: str, range_pixels: int):
        center_x, center_y = self._get_minimap_center()
        if center_x is None:
            print("Error: Could not determine minimap center.")
            return

        # Define direction vectors (dx, dy)
        # These are conceptual vectors, will be normalized and scaled
        direction_vectors = {
            "N": (0, -1),
            "NE": (1, -1),
            "E": (1, 0),
            "SE": (1, 1),
            "S": (0, 1),
            "SW": (-1, 1),
            "W": (-1, 0),
            "NW": (-1, -1),
        }

        direction = direction.upper()
        if direction not in direction_vectors:
            print(f"Error: Invalid direction '{direction}'. Must be one of {list(direction_vectors.keys())}")
            return

        dx_norm, dy_norm = direction_vectors[direction]

        # Normalize the vector (for diagonals) and scale by range_pixels
        magnitude = math.sqrt(dx_norm**2 + dy_norm**2)
        if magnitude == 0: # Should not happen with defined vectors
            print("Error: Zero magnitude direction vector.")
            return

        scale_factor = range_pixels / magnitude
        
        target_x = int(center_x + dx_norm * scale_factor)
        target_y = int(center_y + dy_norm * scale_factor)

        print(f"Moving minimap in direction {direction} by {range_pixels} pixels to ({target_x}, {target_y}).")
        pyautogui.click(target_x, target_y)
        time.sleep(random.uniform(0.5, 1.0)) # Small delay after click

    def _find_and_click_step(self, image_paths: list, minimap_region: tuple, confidence: float) -> bool:
        """
        Tries to find and click any of the images for a given step within the minimap.
        """
        for image_path in image_paths:
            try:
                location = pyautogui.locateCenterOnScreen(
                    image_path,
                    region=minimap_region,
                    confidence=confidence
                )
                if location:
                    print(f"  - Found step image: {os.path.basename(image_path)} with confidence {confidence:.2f}")
                    pyautogui.click(location)
                    return True
            except pyautogui.PyAutoGUIException as e:
                print(f"  - PyAutoGUI error for {os.path.basename(image_path)}: {e}")
                continue
        return False

    def reset_client_view(self) -> bool:
        """
        Resets the client camera view by clicking the compass and scrolling out.
        """
        try:
            self.client.bring_to_foreground()
            ui_interaction = UIInteraction(HumanizedGridClicker(), self.overlay, self.client) # Pass self.overlay
            
            compass_coords_relative = (213, 492)
            abs_compass_coords = ui_interaction._get_abs_coords(compass_coords_relative)
            if not abs_compass_coords:
                print("Error: Could not calculate absolute coordinates for compass.")
                return False
            
            print("Clicking compass to reset view...")
            pyautogui.click(abs_compass_coords)
            time.sleep(0.5)

            p1_rel = (766, 508)
            p2_rel = (258, 176)
            mid_x_rel = (p1_rel[0] + p2_rel[0]) / 2
            mid_y_rel = (p1_rel[1] + p2_rel[1]) / 2
            
            scroll_midpoint_abs = ui_interaction._get_abs_coords((mid_x_rel, mid_y_rel))
            if not scroll_midpoint_abs:
                print("Error: Could not calculate absolute coordinates for scroll point.")
                return False

            print("Moving mouse to screen center...")
            pyautogui.moveTo(scroll_midpoint_abs)
            time.sleep(0.3)

            print("Scrolling down to zoom out...")
            scroll_duration = 2
            scroll_start_time = time.time()
            while time.time() - scroll_start_time < scroll_duration:
                pyautogui.scroll(-1000)
                time.sleep(0.1)
            
            print("Client view reset successfully.")
            return True

        except Exception as e:
            print(f"An error occurred while resetting client view: {e}")
            return False

    def run(self, stop_event: threading.Event):
        """
        Executes the entire route pathing sequence.
        """
        def fuzzy_text_match(ocr_text: str, target_text: str, word_similarity_threshold=0.7, required_match_percentage=1.0) -> bool:
            if not ocr_text or not target_text:
                return False

            ocr_words = ocr_text.lower().split()
            target_words = target_text.lower().split()
            
            if not target_words:
                return False

            matched_words = 0
            for target_word in target_words:
                if not ocr_words:
                    break
                best_similarity = max(difflib.SequenceMatcher(None, target_word, ocr_word).ratio() for ocr_word in ocr_words)
                
                if best_similarity >= word_similarity_threshold:
                    matched_words += 1
            
            match_ratio = matched_words / len(target_words)
            
            return match_ratio >= required_match_percentage

        print("\n--- Starting Route Pathing ---")
        self.client.bring_to_foreground()
        time.sleep(0.5)

        if not self.reset_client_view():
            print("Failed to reset client view. Aborting pathing.")
            return

        minimap_region = self._get_minimap_region()
        if not minimap_region:
            print("Could not determine minimap region. Aborting.")
            return
        
        ui_interaction = UIInteraction(HumanizedGridClicker(), self.overlay, self.client) # Pass self.overlay

        for step_num in sorted(self.steps.keys()):
            if stop_event.is_set():
                print("Route pathing stopped by user.")
                break

            print(f"Executing Step {step_num}...")

            if step_num == 5:
                # Press Arrow Down key for 1 second before scan
                print("Pressing 'Arrow Down' key for 1 second...")
                keyboard.press('down')
                time.sleep(1)
                keyboard.release('down')
                print("'Arrow Down' key released.")

                # --- Custom Hover-Scan-OCR Logic for Step 5 ---
                game_screen = GameScreen()

                # Define the target area to scan, relative to bottom-right
                x_offset = random.randint(1, 5)
                y_offset = random.randint(1, 5)
                target_rel_coords = (441 - x_offset, 412 - y_offset)
                
                abs_target_coords = ui_interaction._get_abs_coords(target_rel_coords)
                if not abs_target_coords:
                    print("Error: Could not calculate absolute coordinates for step 5. Aborting.")
                    break

                # Define a 10x10 pixel search box to scan
                box_size = 10
                scan_region = (
                    int(abs_target_coords[0] - box_size / 2),
                    int(abs_target_coords[1] - box_size / 2),
                    int(abs_target_coords[0] + box_size / 2),
                    int(abs_target_coords[1] + box_size / 2)
                )

                # Define the OCR region for the top-left action text
                p1_rel = (768, 505)
                p2_rel = (261, 487)
                abs_p1 = ui_interaction._get_abs_coords(p1_rel)
                abs_p2 = ui_interaction._get_abs_coords(p2_rel)
                if not abs_p1 or not abs_p2:
                    print("Error: Could not calculate OCR region coordinates. Aborting.")
                    break
                ocr_region = (min(abs_p1[0], abs_p2[0]), min(abs_p1[1], abs_p2[1]), max(abs_p1[0], abs_p2[0]), max(abs_p1[1], abs_p2[1]))

                print(f"  - Scanning region {scan_region} for 'Climb-into Underwall tunnel' action...") # Updated print statement
                
                step_5_success = False
                # Scan the search region by hovering and reading the action text
                for x in range(scan_region[0], scan_region[2], 2): # Scan every 2nd pixel
                    for y in range(scan_region[1], scan_region[3], 2):
                        if stop_event.is_set(): break
                        pyautogui.moveTo(x, y)
                        time.sleep(0.2)

                        # Define OCR region below-right the mouse
                        ocr_region_below_mouse = (x + 10, y + 10, x + 10 + 150, y + 10 + 20) # Corrected dimensions

                        # Draw highlight around original OCR region
                        if self.overlay:
                            self.overlay.add_highlight(
                                top_left=(ocr_region[0], ocr_region[1]),
                                bottom_right=(ocr_region[2], ocr_region[3]),
                                color_start=(0, 0, 255), # Blue
                                color_end=(0, 0, 255),
                                duration=1.0
                            )

                            # Draw highlight around OCR region below mouse
                            self.overlay.add_highlight(
                                top_left=(ocr_region_below_mouse[0], ocr_region_below_mouse[1]),
                                bottom_right=(ocr_region_below_mouse[2], ocr_region_below_mouse[3]),
                                color_start=(128, 0, 128), # Purple
                                color_end=(128, 0, 128),
                                duration=1.0
                            )

                        action_text_main = game_screen.read_text_from_region(*ocr_region)
                        action_text_below = game_screen.read_text_from_region(*ocr_region_below_mouse)

                        print(f"  - OCR Result (Main) at ({x},{y}): '{action_text_main}'")
                        print(f"  - OCR Result (Below Mouse) at ({x},{y}): '{action_text_below}'")

                        target_action = "Climb-into Underwall tunnel" # Updated target action
                        
                        # Fuzzy match for the target action text in either region
                        if (fuzzy_text_match(action_text_main, target_action, word_similarity_threshold=0.3, required_match_percentage=0.7) or
                            fuzzy_text_match(action_text_below, target_action, word_similarity_threshold=0.3, required_match_percentage=0.7)):
                            print(f"  - OCR validation successful. Found action similar to '{target_action}'. Clicking at ({x},{y}).")
                            pyautogui.click(x, y)
                            print("Step 5 complete. Waiting 5s...")
                            time.sleep(5)
                            step_5_success = True
                            break
                    if step_5_success or stop_event.is_set():
                        break
                
                if not step_5_success:
                    print(f"Error: Could not find '{target_action}' action in the specified area. Aborting route.") # Updated error message
                    break
                
                # New: Move SE twice after step 5
                print("Executing post-Step 5 minimap movements...")
                self.move_minimap_direction("SE", 50)
                time.sleep(1)
                self.move_minimap_direction("SE", 50)
                print("Post-Step 5 minimap movements complete.")
            else:
                # --- Default Image-based Logic for all other steps ---
                step_data = self.steps[step_num]
                image_options = step_data['images']
                wait_time = step_data['wait']
                step_confidence = step_data.get('confidence') or self.confidence
                
                if self._find_and_click_step(image_options, minimap_region, step_confidence):
                    if step_num == 6 or step_num == 4:
                        print(f"Step {step_num} complete. Waiting {wait_time:.2f}s...")
                    else:
                        print(f"Step {step_num} complete. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Error: Could not find any image for step {step_num}. Aborting route.")
                    break
        
        print("--- Route Pathing Finished ---")


if __name__ == "__main__":
    ROUTE_NAME = "route-1"
    CONFIDENCE = 0.5
    HOTKEY_START = 'ctrl+shift+p'
    HOTKEY_STOP = 'ctrl+p'

    print("--- Minimap Route Pather ---")
    print(f"Route to run: '{ROUTE_NAME}'")
    print(f"Press {HOTKEY_START} to START the sequence.")
    print(f"Press {HOTKEY_STOP} to STOP the sequence.")
    print("Press Ctrl+C in this terminal to exit.")

    try:
        # Initialize overlay on the main thread
        overlay = WindowOverlay(title=f"Route Pather Overlay - {ROUTE_NAME}", transparency=0.3)
        
        stop_event = threading.Event()
        pather = RoutePather(route_name=ROUTE_NAME, confidence=CONFIDENCE, overlay=overlay)
        
        # Function to run in the background thread, managed by HotkeyManager
        def pather_loop_function(hotkey_stop_event): # Accept the argument from HotkeyManager
            pather.run(hotkey_stop_event) # Use the stop_event passed by HotkeyManager
            # Once pather.run finishes, stop the overlay
            overlay.root.quit()

        # Hotkey manager runs on the main thread
        hotkey_manager = HotkeyManager(start_hotkey=HOTKEY_START, stop_hotkey=HOTKEY_STOP)
        hotkey_manager.register_hotkeys(loop_function=pather_loop_function)
        
        # Start the Tkinter mainloop for the overlay on the main thread
        # This will keep the script running and allow hotkeys to be detected
        try:
            overlay.root.mainloop()
        except KeyboardInterrupt:
            print("\nCtrl+C detected. Exiting script gracefully.")
            # Ensure the background thread is stopped if it's running
            hotkey_manager._stop_loop() # Call internal stop method
            overlay.root.quit() # Ensure tkinter mainloop is quit

    except FileNotFoundError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")