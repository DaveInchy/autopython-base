import os
import time
import pyautogui
import random
import threading
import math
import keyboard
import json
from typing import Dict, Any

from .client_window import RuneLiteClientWindow
from .game_screen import GameScreen
from . import ui_utils
from .graphics.window_overlay import WindowOverlay

class RoutePather:
    """
    A class to follow a predefined path from a JSON file using image matching and OCR.
    """
    def __init__(self, route_name: str, confidence=0.8, overlay: WindowOverlay = None):
        self.client = RuneLiteClientWindow()
        self.game_screen = GameScreen()
        self.route_data = self._load_route_data_from_json(route_name)
        if not self.route_data or 'steps' not in self.route_data:
            raise ValueError(f"Invalid or empty route data in {route_name}.json")

        self.confidence = confidence
        self.overlay = overlay
        self.stop_event = threading.Event()

        self.ui_interaction = ui_utils.UIInteraction(
            ui_utils.HumanizedGridClicker(), 
            self.overlay,
            self.client
        )

        print(f"Initialized RoutePather for route '{route_name}' with {len(self.route_data['steps'])} steps.")

    def _load_route_data_from_json(self, route_name: str) -> Dict[str, Any]:
        json_path = os.path.join(os.path.dirname(__file__), 'data', 'routes', f"{route_name}.json")
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Route JSON file not found at: {json_path}")
        
        with open(json_path, 'r') as f:
            return json.load(f)

    def _get_minimap_center(self) -> tuple | None:
        minimap_rect = self.client.get_minimap_rect()
        if not minimap_rect:
            return None
        
        center_x = minimap_rect['left'] + minimap_rect['w'] // 2
        center_y = minimap_rect['top'] + minimap_rect['h'] // 2
        return (center_x, center_y)

    def _execute_minimap_compass_direction(self, args: Dict[str, Any]) -> bool:
        direction = args.get("direction")
        range_pixels = args.get("range_pixels")
        if not direction or range_pixels is None:
            print("Error: 'minimap-compass-direction' requires 'direction' and 'range_pixels' arguments.")
            return False

        center_x, center_y = self._get_minimap_center()
        if center_x is None:
            print("Error: Could not determine minimap center.")
            return False

        direction_vectors = {
            "N": (0, -1), "NE": (1, -1), "E": (1, 0), "SE": (1, 1),
            "S": (0, 1), "SW": (-1, 1), "W": (-1, 0), "NW": (-1, -1),
        }

        direction = direction.upper()
        if direction not in direction_vectors:
            print(f"Error: Invalid direction '{direction}'.")
            return False

        dx_norm, dy_norm = direction_vectors[direction]
        magnitude = math.sqrt(dx_norm**2 + dy_norm**2)
        scale_factor = range_pixels / magnitude if magnitude != 0 else 0
        
        target_x = int(center_x + dx_norm * scale_factor)
        target_y = int(center_y + dy_norm * scale_factor)

        print(f"Moving minimap in direction {direction} by {range_pixels} pixels to ({target_x}, {target_y}).")
        pyautogui.click(target_x, target_y)
        return True

    def _execute_minimap_image_recognition(self, args: Dict[str, Any]) -> bool:
        image_file = args.get("image_file")
        confidence = args.get("confidence", self.confidence)
        if not image_file:
            print("Error: 'minimap-image-recognition' requires 'image_file' argument.")
            return False

        minimap_region = self.client.get_minimap_rect()
        if not minimap_region:
            print("Could not determine minimap region. Aborting.")
            return False
        
        region_tuple = (minimap_region['left'], minimap_region['top'], minimap_region['w'], minimap_region['h'])
        location = self.game_screen.find_image(image_file, confidence=confidence, region=region_tuple)

        if location:
            print(f"  - Found step image: {image_file}")
            pyautogui.click(location)
            return True
        else:
            print(f"Error: Could not find image {image_file} for minimap-image-recognition.")
            return False

    def _execute_gamescreen_action_sampler(self, args: Dict[str, Any]) -> bool:
        target_action = args.get("target_action")
        scan_region_offset_x = args.get("scan_region_offset_x", 1)
        scan_region_offset_y = args.get("scan_region_offset_y", 1)
        scan_region_box_size = args.get("scan_region_box_size", 10)
        ocr_region_p1_rel = args.get("ocr_region_p1_rel")
        ocr_region_p2_rel = args.get("ocr_region_p2_rel")
        ocr_region_below_mouse_offset_x = args.get("ocr_region_below_mouse_offset_x", 10)
        ocr_region_below_mouse_offset_y = args.get("ocr_region_below_mouse_offset_y", 10)
        ocr_region_below_mouse_width = args.get("ocr_region_below_mouse_width", 150)
        ocr_region_below_mouse_height = args.get("ocr_region_below_mouse_height", 20)
        word_similarity_threshold = args.get("word_similarity_threshold", 0.3)
        required_match_percentage = args.get("required_match_percentage", 0.7)
        pre_scan_keyboard_press = args.get("pre_scan_keyboard_press")
        pre_scan_keyboard_press_duration = args.get("pre_scan_keyboard_press_duration", 1.0)

        if not target_action or not ocr_region_p1_rel or not ocr_region_p2_rel:
            print("Error: 'gamescreen-action-sampler' requires 'target_action', 'ocr_region_p1_rel', 'ocr_region_p2_rel' arguments.")
            return False

        if pre_scan_keyboard_press:
            print(f"Pressing '{pre_scan_keyboard_press}' key for {pre_scan_keyboard_press_duration} second(s)...")
            keyboard.press(pre_scan_keyboard_press)
            time.sleep(pre_scan_keyboard_press_duration)
            keyboard.release(pre_scan_keyboard_press)
            print(f"'{pre_scan_keyboard_press}' key released.")

        # Define the target area to scan, relative to bottom-right
        x_offset = random.randint(1, scan_region_offset_x)
        y_offset = random.randint(1, scan_region_offset_y)
        target_rel_coords = (441 - x_offset, 412 - y_offset)
        
        abs_target_coords = self.ui_interaction._get_abs_coords(target_rel_coords)
        if not abs_target_coords:
            print("Error: Could not calculate absolute coordinates for action sampler. Aborting.")
            return False

        scan_region = (
            int(abs_target_coords[0] - scan_region_box_size / 2),
            int(abs_target_coords[1] - scan_region_box_size / 2),
            int(abs_target_coords[0] + scan_region_box_size / 2),
            int(abs_target_coords[1] + scan_region_box_size / 2)
        )

        abs_p1 = self.ui_interaction._get_abs_coords(tuple(ocr_region_p1_rel))
        abs_p2 = self.ui_interaction._get_abs_coords(tuple(ocr_region_p2_rel))
        if not abs_p1 or not abs_p2:
            print("Error: Could not calculate OCR region coordinates. Aborting.")
            return False
        ocr_region = (min(abs_p1[0], abs_p2[0]), min(abs_p1[1], abs_p2[1]), max(abs_p1[0], abs_p2[0]), max(abs_p1[1], abs_p2[1]))

        print(f"  - Scanning region {scan_region} for '{target_action}' action...")
        
        step_success = False
        for x_scan in range(scan_region[0], scan_region[2], 2):
            for y_scan in range(scan_region[1], scan_region[3], 2):
                if self.stop_event.is_set(): break
                pyautogui.moveTo(x_scan, y_scan)
                time.sleep(0.2)

                ocr_region_below_mouse = (
                    x_scan + ocr_region_below_mouse_offset_x,
                    y_scan + ocr_region_below_mouse_offset_y,
                    x_scan + ocr_region_below_mouse_offset_x + ocr_region_below_mouse_width,
                    y_scan + ocr_region_below_mouse_offset_y + ocr_region_below_mouse_height
                )

                if self.overlay:
                    self.overlay.add_highlight(top_left=(ocr_region[0], ocr_region[1]), bottom_right=(ocr_region[2], ocr_region[3]), color_start=(0, 0, 255), duration=1.0)
                    self.overlay.add_highlight(top_left=(ocr_region_below_mouse[0], ocr_region_below_mouse[1]), bottom_right=(ocr_region_below_mouse[2], ocr_region_below_mouse[3]), color_start=(128, 0, 128), duration=1.0)

                action_text_main = self.game_screen.read_text_from_region(*ocr_region)
                action_text_below = self.game_screen.read_text_from_region(*ocr_region_below_mouse)

                print(f"  - OCR Result (Main) at ({x_scan},{y_scan}): '{action_text_main}'")
                print(f"  - OCR Result (Below Mouse) at ({x_scan},{y_scan}): '{action_text_below}'")
                
                if (self.game_screen.fuzzy_text_match(action_text_main, target_action, word_similarity_threshold, required_match_percentage) or
                    self.game_screen.fuzzy_text_match(action_text_below, target_action, word_similarity_threshold, required_match_percentage)):
                    print(f"  - OCR validation successful. Found action similar to '{target_action}'. Clicking at ({x_scan},{y_scan}).")
                    pyautogui.click(x_scan, y_scan)
                    step_success = True
                    break
            if step_success or self.stop_event.is_set():
                break
        
        if not step_success:
            print(f"Error: Could not find '{target_action}' action in the specified area. Aborting route.")
            return False
        return True

    def _execute_view_reset_zoomout_stable(self, args: Dict[str, Any]) -> bool:
        try:
            self.client.bring_to_foreground()
            compass_coords_relative = (213, 492) # Example coords, may need adjustment
            abs_compass_coords = self.ui_interaction._get_abs_coords(compass_coords_relative)
            if not abs_compass_coords:
                print("Error: Could not calculate absolute coordinates for compass.")
                return False
            
            pyautogui.click(abs_compass_coords)
            time.sleep(0.5)

            pyautogui.scroll(-5000) # Scroll down a large amount
            time.sleep(0.5)
            print("Client view reset.")
            return True
        except Exception as e:
            print(f"An error occurred while resetting client view: {e}")
            return False

    def run(self, stop_event: threading.Event):
        self.stop_event = stop_event
        print("\n--- Starting Route Pathing ---")
        self.client.bring_to_foreground()
        time.sleep(0.5)

        method_dispatch = {
            "minimap-image-recognition": self._execute_minimap_image_recognition,
            "gamescreen-action-sampler": self._execute_gamescreen_action_sampler,
            "minimap-compass-direction": self._execute_minimap_compass_direction,
            "view-reset-zoomout-stable": self._execute_view_reset_zoomout_stable,
        }

        for i, step_data in enumerate(self.route_data['steps']):
            if self.stop_event.is_set():
                print("Route pathing stopped by user.")
                break

            step_method = step_data.get("method")
            step_args = step_data.get("args", {})
            step_timing = step_data.get("timing", {"before": 0, "after": 0})

            print(f"Executing Step {i+1}/{len(self.route_data['steps'])}: {step_method}...")
            time.sleep(step_timing.get("before", 0))

            if step_method in method_dispatch:
                if not method_dispatch[step_method](step_args):
                    print(f"Step {i+1} ({step_method}) failed. Aborting route.")
                    break
            else:
                print(f"Error: Unknown method '{step_method}' in step {i+1}. Aborting route.")
                break
            
            time.sleep(step_timing.get("after", 0))
        
        print("--- Route Pathing Finished ---")
