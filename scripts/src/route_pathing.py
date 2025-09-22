import os
import re
import time
import pyautogui
import random
import threading
import difflib
import math
import keyboard
import signal
import sys
import json # Added for JSON loading

# Imports from ui_utils.py
import cv2
import numpy as np
from PIL import Image
from typing import Literal, Optional, Dict, Any, Tuple

# Local imports
from src.client_window import RuneLiteClientWindow
from src.game_screen import GameScreen
from src.hotkeys import HotkeyManager
from src.graphics.window_overlay import WindowOverlay

# --- Data Loading (Copied from ui_utils.py) ---
def _load_ui_data():
    """Loads the JSONC file, stripping comments first."""
    # For now, hardcode the data as it was in ui_utils.py
    # In a later step, we might load from a file
    return {
        "//": "This file maps the static coordinates and grid data of various user interface elements.",
        "equipment": {
            "f_key": "F3",
            "helm": { "x": 132, "y": 282 },
            "necklace": { "x": 131, "y": 247 },
            "body": { "x": 133, "y": 208 },
            "legs": { "x": 133, "y": 165 },
            "feet": { "x": 135, "y": 126 },
            "gloves": { "x": 187, "y": 128 },
            "ring": { "x": 75, "y": 129 },
            "offHand": { "x": 92, "y": 245 },
            "mainHand": { "x": 176, "y": 254 },
            "cape": { "x": 193, "y": 204 },
            "ammo": { "x": 76, "y": 204 }
        },
        "inventory": {
            "f_key": "F2",
            "rows": 7,
            "columns": 4,
            "slots": 28,
            "cellSize": {
            "width": 42,
            "height": 36
            },
            "layout_mode": "packed",
            "coordinate_type": "corner",
            "start": { "x": 216, "y": 304 },
            "end": { "x": 49, "y": 52 }
        },
        "prayer": {
            "f_key": "F4",
            "rows": 6,
            "columns": 5,
            "slots": 29,
            "cellSize": {
            "width": 33,
            "height": 33
            },
            "layout_mode": "stretched",
            "coordinate_type": "corner",
            "start": { "x": 220, "y": 295 },
            "end": { "x": 39, "y": 86 }
        },
        "magic": {
            "f_key": "F1",
            "rows": 10,
            "columns": 7,
            "slots": 66,
            "cellSize": {
            "width": 27,
            "height": 26
            },
            "layout_mode": "stretched",
            "coordinate_type": "center",
            "start": { "x": 211, "y": 295 },
            "end": { "x": 53, "y": 79 }
        }
    }

_ui_data = _load_ui_data()

# --- Type Hinting (Copied from ui_utils.py) ---
EquipmentSlot = Literal['helm', 'cape', 'necklace', 'mainHand', 'body', 'offHand', 'legs', 'gloves', 'feet', 'ring', 'ammo']
Grid = Literal['inventory', 'prayer', 'magic', "magic_ancient"]

# --- Generic Grid Calculation (Copied from ui_utils.py) ---
def _get_grid_slot_coords(grid_name: Grid, slot: int) -> tuple | None:
    """
    Calculates the (x, y) coordinates for a slot in a given grid based on its layout mode
    and coordinate type (center or corner).
    Returns the center coordinates of the slot.
    """
    grid_data = _ui_data.get(grid_name.lower())
    if not grid_data:
        return None

    slots = grid_data['slots']
    if not (1 <= slot <= slots):
        raise ValueError(f"Slot must be between 1 and {slots} for {grid_name}")

    cols = grid_data['columns']
    rows = grid_data['rows']
    start_coord_raw = grid_data['start']
    end_coord_raw = grid_data.get('end') # End coord might not be present for packed
    cell_size = grid_data['cellSize']
    layout_mode = grid_data.get('layout_mode', 'packed') # Default to packed if not specified
    coordinate_type = grid_data.get('coordinate_type', 'center') # Default to center

    col = (slot - 1) % cols
    row = (slot - 1) // cols

    # Adjust raw start/end coordinates to be center-based if they are corner-based
    start_x, start_y = start_coord_raw['x'], start_coord_raw['y']
    end_x, end_y = (end_coord_raw['x'], end_coord_raw['y']) if end_coord_raw else (0,0)

    if coordinate_type == 'corner':
        # Convert corner to center for start_coord
        start_x = start_x - (cell_size['width'] / 2)
        start_y = start_y - (cell_size['height'] / 2)
        
        if end_coord_raw: # Only adjust end if it exists
            # Convert corner to center for end_coord
            end_x = end_x + (cell_size['width'] / 2)
            end_y = end_y + (cell_size['height'] / 2)

    if layout_mode == 'packed':
        x = start_x - (col * cell_size['width'])
        y = start_y - (row * cell_size['height'])
    elif layout_mode == 'stretched':
        x_step = (start_x - end_x) / (cols - 1) if cols > 1 else 0
        y_step = (start_y - end_y) / (rows - 1) if rows > 1 else 0

        x = start_x - (col * x_step)
        y = start_y - (row * y_step)
    else:
        raise ValueError(f"Unknown layout_mode: {layout_mode} for {grid_name}")

    return (int(round(x)), int(round(y)))

def find_ui_element_by_image(image_file: str, screenshot_region: tuple | None = None) -> tuple | None:
    """
    Finds a UI element on the screen using a template image.
    Returns the center (x, y) coordinates of the found element, or None if not found.
    """
    try:
        # pyautogui.locateOnScreen returns a Box(left, top, width, height)
        # We need to convert the template_path to an absolute path
        absolute_template_path = os.path.join(os.path.dirname(__file__), '..', 'res', 'image', image_file) # Adjusted path
        
        # Confidence can be adjusted based on how precise the match needs to be
        # The region parameter can be used to limit the search area for performance
        location = pyautogui.locateOnScreen(absolute_template_path, confidence=0.8, region=screenshot_region)
        
        if location:
            # Calculate the center of the found image
            center_x = location.left + location.width // 2
            center_y = location.top + location.height // 2
            return (center_x, center_y)
        else:
            return None
    except pyautogui.PyAutoGUIException as e:
        print(f"Error finding UI element by image: {e}")
        return None

# --- UI Component Classes (Copied from ui_utils.py) ---

class Equipment:
    _equipment_data = _ui_data.get('equipment', {})

    @staticmethod
    def get_slot_coords(slot_name: EquipmentSlot) -> tuple | None:
        slot_info = Equipment._equipment_data.get(slot_name.lower())
        return (slot_info['x'], slot_info['y']) if slot_info else None

    @classmethod
    def render(cls, overlay):
        # This render method is for visualization, not direct use in RoutePather
        pass 

class Inventory:
    _grid_data = _ui_data.get('inventory', {})

    @staticmethod
    def get_slot_coords(slot: int) -> tuple | None:
        return _get_grid_slot_coords('inventory', slot)
    
    @staticmethod
    def get_slot_xy(slot: int, rect=None) -> tuple | None:
        return _get_grid_slot_coords('inventory', slot)

    @classmethod
    def render(cls, overlay):
        # This render method is for visualization, not direct use in RoutePather
        pass

class Prayer:
    _grid_data = _ui_data.get('prayer', {})

    @staticmethod
    def get_slot_coords(slot: int) -> tuple | None:
        return _get_grid_slot_coords('prayer', slot)
    
    @staticmethod
    def get_slot_xy(slot: int, rect=None) -> tuple | None:
        return _get_grid_slot_coords('prayer', slot)
    
    @classmethod
    def render(cls, overlay):
        # This render method is for visualization, not direct use in RoutePather
        pass

class Magic:
    _grid_data = _ui_data.get('magic', {})

    @staticmethod
    def get_slot_coords(slot: int) -> tuple | None:
        return _get_grid_slot_coords('magic', slot)

    @classmethod
    def render(cls, overlay):
        # This render method is for visualization, not direct use in RoutePather
        pass

# --- Humanized Clicking Logic (Copied from ui_utils.py) ---

class HumanizedGridClicker:
    """
    Generates human-like randomized click coordinates for UI grids.
    - Clicks are biased towards the center of a cell.
    - Accuracy increases over time to simulate muscle memory.
    """
    def __init__(self, learning_rate=0.05, initial_std_dev_factor=0.25):
        self.proficiency = {
            'inventory': 0,
            'prayer': 0,
            'magic': 0,
            'magic_ancient': 0
        }
        self.learning_rate = learning_rate
        self.initial_std_dev_factor = initial_std_dev_factor

    def get_randomized_coords(self, grid_name: Grid, slot: int) -> tuple | None:
        """ 
        Calculates a randomized (x, y) coordinate within a grid cell.
        """ 
        grid_data = _ui_data.get(grid_name)
        if not grid_data:
            return None

        center_coords = _get_grid_slot_coords(grid_name, slot)
        if not center_coords:
            return None
        
        center_x, center_y = center_coords
        cell_w = grid_data['cellSize']['width']
        cell_h = grid_data['cellSize']['height']

        # Update proficiency for this grid type
        self.proficiency[grid_name] += 1
        
        # As proficiency increases, standard deviation decreases, making clicks more accurate
        proficiency_factor = 1 + self.proficiency[grid_name] * self.learning_rate
        std_dev_x = (cell_w * self.initial_std_dev_factor) / proficiency_factor
        std_dev_y = (cell_h * self.initial_std_dev_factor) / proficiency_factor

        # Generate a random point using a Gaussian distribution
        rand_x = random.gauss(center_x, std_dev_x)
        rand_y = random.gauss(center_y, std_dev_y)

        # Clamp the coordinates to the cell boundaries
        min_x = center_x - cell_w / 3
        max_x = center_x + cell_w / 3
        min_y = center_y - cell_h / 3
        max_y = center_y + cell_h / 3

        clamped_x = max(min_x, min(rand_x, max_x))
        clamped_y = max(min_y, min(rand_y, max_y))

        return (int(round(clamped_x)), int(round(clamped_y)))


# --- UI Interaction Class (Copied from ui_utils.py) ---

class UIInteraction:
    def __init__(self, clicker: HumanizedGridClicker, overlay: WindowOverlay, client_window: RuneLiteClientWindow):
        self.clicker = clicker
        self.overlay = overlay
        self.client_window = client_window

    def _get_abs_coords(self, relative_coords: tuple) -> tuple | None:
        """Converts bottom-right relative coordinates to absolute screen coordinates.
        Returns None if the RuneLite client window cannot be found.
        """
        win_rect = self.client_window.get_rect()
        if not win_rect:
            return None # Indicate that client window was not found

        win_left = win_rect['left']
        win_top = win_rect['top']
        win_width = win_rect["w"]
        win_height = win_rect["h"]

        rel_x = relative_coords[0]
        rel_y = relative_coords[1]

        abs_x = win_left + (win_width - rel_x)
        abs_y = win_top + (win_height - rel_y)
        
        return (abs_x, abs_y)
    
    def _perform_click(self, grid_name: Grid | None, slot_coords: tuple, cell_size: dict | None = None):
        """Performs the actual click and adds a visual highlight."""
        abs_click_coords = self._get_abs_coords(slot_coords)
        pyautogui.click(abs_click_coords[0], abs_click_coords[1])
        time.sleep(0.001)

    def click_inventory_slot(self, slot: int):
        rand_coords = self.clicker.get_randomized_coords('inventory', slot)
        self._perform_click('inventory', rand_coords, Inventory._grid_data['cellSize'])

    def click_prayer_slot(self, slot: int):
        rand_coords = self.clicker.get_randomized_coords('prayer', slot)
        self._perform_click('prayer', rand_coords, Prayer._grid_data['cellSize'])

    def click_magic_slot(self, slot: int):
        rand_coords = self.clicker.get_randomized_coords('magic', slot)
        self._perform_click('magic', rand_coords, Magic._grid_data['cellSize'])

    def click_equipment_slot(self, slot_name: EquipmentSlot):
        center_coords = Equipment.get_slot_coords(slot_name)
        # Equipment slots don't have randomized clicks or cell sizes in HumanizedGridClicker
        # So we just use the center_coords directly for click and highlight
        self._perform_click(None, center_coords, None) # No grid_name or cell_size for equipment


# --- RoutePather Class (Refactored from _RoutePathing.dev.py) ---
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
        self.route_path = os.path.join(os.path.dirname(__file__), '..', 'res', 'pathing', route_name) # Adjusted path
        if not os.path.isdir(self.route_path):
            raise FileNotFoundError(f"Route directory not found at: {self.route_path}")
            
        # Load route steps from JSON
        self.route_data = self._load_route_data_from_json(route_name)
        if not self.route_data or 'steps' not in self.route_data:
            raise ValueError(f"Invalid or empty route data in {route_name}.json")

        self.confidence = confidence
        self.overlay = overlay # Assign the passed overlay
        
        # Initialize HumanizedGridClicker and UIInteraction
        self.humanized_clicker = HumanizedGridClicker()
        self.ui_interaction = UIInteraction(self.humanized_clicker, self.overlay, self.client)

        print(f"Initialized RoutePather for route '{route_name}' from JSON with {len(self.route_data['steps'])} steps.")

    def _load_route_data_from_json(self, route_name: str) -> Dict[str, Any]:
        json_path = os.path.join(os.path.dirname(__file__), 'data', 'routes', f"{route_name}.json")
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Route JSON file not found at: {json_path}")
        
        with open(json_path, 'r') as f:
            # Simple JSON loading, assumes no comments for now
            return json.load(f)

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

    def _get_minimap_center(self) -> tuple | None:
        minimap_region = self._get_minimap_region()
        if not minimap_region:
            return None
        
        left, top, right, bottom = minimap_region
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        return (center_x, center_y)

    def _execute_minimap_compass_direction(self, args: Dict[str, Any]):
        direction = args.get("direction")
        range_pixels = args.get("range_pixels")
        if not direction or range_pixels is None:
            print("Error: 'minimap-compass-direction' requires 'direction' and 'range_pixels' arguments.")
            return

        center_x, center_y = self._get_minimap_center()
        if center_x is None:
            print("Error: Could not determine minimap center.")
            return

        # Define direction vectors (dx, dy)
        direction_vectors = {
            "N": (0, -1), "NE": (1, -1), "E": (1, 0), "SE": (1, 1),
            "S": (0, 1), "SW": (-1, 1), "W": (-1, 0), "NW": (-1, -1),
        }

        direction = direction.upper()
        if direction not in direction_vectors:
            print(f"Error: Invalid direction '{direction}'. Must be one of {list(direction_vectors.keys())}")
            return

        dx_norm, dy_norm = direction_vectors[direction]

        magnitude = math.sqrt(dx_norm**2 + dy_norm**2)
        scale_factor = range_pixels / magnitude if magnitude != 0 else 0
        
        target_x = int(center_x + dx_norm * scale_factor)
        target_y = int(center_y + dy_norm * scale_factor)

        print(f"Moving minimap in direction {direction} by {range_pixels} pixels to ({target_x}, {target_y}).")
        pyautogui.click(target_x, target_y)

    def _execute_minimap_image_recognition(self, args: Dict[str, Any]):
        image_file = args.get("image_file")
        confidence = args.get("confidence", self.confidence)
        if not image_file:
            print("Error: 'minimap-image-recognition' requires 'image_file' argument.")
            return False

        minimap_region = self._get_minimap_region()
        if not minimap_region:
            print("Could not determine minimap region. Aborting.")
            return False
        
        # Use find_ui_element_by_image which handles absolute path
        location = find_ui_element_by_image(image_file, screenshot_region=minimap_region)

        if location:
            print(f"  - Found step image: {image_file} with confidence {confidence:.2f}")
            pyautogui.click(location)
            return True
        else:
            print(f"Error: Could not find image {image_file} for minimap-image-recognition.")
            return False

    def _execute_gamescreen_action_sampler(self, args: Dict[str, Any]):
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

        # Press keyboard key before scan
        if pre_scan_keyboard_press:
            print(f"Pressing '{pre_scan_keyboard_press}' key for {pre_scan_keyboard_press_duration} second(s)...")
            keyboard.press(pre_scan_keyboard_press)
            time.sleep(pre_scan_keyboard_press_duration)
            keyboard.release(pre_scan_keyboard_press)
            print(f"'{pre_scan_keyboard_press}' key released.")

        game_screen = GameScreen()
        
        # Define the target area to scan, relative to bottom-right
        x_offset = random.randint(1, scan_region_offset_x)
        y_offset = random.randint(1, scan_region_offset_y)
        target_rel_coords = (441 - x_offset, 412 - y_offset) # Hardcoded for now, should be dynamic
        
        abs_target_coords = self.ui_interaction._get_abs_coords(target_rel_coords)
        if not abs_target_coords:
            print("Error: Could not calculate absolute coordinates for action sampler. Aborting.")
            return False

        # Define a pixel search box to scan
        scan_region = (
            int(abs_target_coords[0] - scan_region_box_size / 2),
            int(abs_target_coords[1] - scan_region_box_size / 2),
            int(abs_target_coords[0] + scan_region_box_size / 2),
            int(abs_target_coords[1] + scan_region_box_size / 2)
        )

        # Define the OCR region for the top-left action text
        abs_p1 = self.ui_interaction._get_abs_coords(tuple(ocr_region_p1_rel))
        abs_p2 = self.ui_interaction._get_abs_coords(tuple(ocr_region_p2_rel))
        if not abs_p1 or not abs_p2:
            print("Error: Could not calculate OCR region coordinates. Aborting.")
            return False
        ocr_region = (min(abs_p1[0], abs_p2[0]), min(abs_p1[1], abs_p2[1]), max(abs_p1[0], abs_p2[0]), max(abs_p1[1], abs_p2[1]))

        print(f"  - Scanning region {scan_region} for '{target_action}' action...")
        
        step_success = False
        # Scan the search region by hovering and reading the action text
        for x_scan in range(scan_region[0], scan_region[2], 2): # Scan every 2nd pixel
            for y_scan in range(scan_region[1], scan_region[3], 2):
                if self.stop_event.is_set(): break # Use self.stop_event
                pyautogui.moveTo(x_scan, y_scan)
                time.sleep(0.2)

                # Define OCR region below-right the mouse
                ocr_region_below_mouse = (
                    x_scan + ocr_region_below_mouse_offset_x,
                    y_scan + ocr_region_below_mouse_offset_y,
                    x_scan + ocr_region_below_mouse_offset_x + ocr_region_below_mouse_width,
                    y_scan + ocr_region_below_mouse_offset_y + ocr_region_below_mouse_height
                )

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

                print(f"  - OCR Result (Main) at ({x_scan},{y_scan}): '{action_text_main}'")
                print(f"  - OCR Result (Below Mouse) at ({x_scan},{y_scan}): '{action_text_below}'")
                
                # Fuzzy match for the target action text in either region
                if (self._fuzzy_text_match(action_text_main, target_action, word_similarity_threshold, required_match_percentage) or
                    self._fuzzy_text_match(action_text_below, target_action, word_similarity_threshold, required_match_percentage)):
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

    def _execute_view_reset_zoomout_stable(self, args: Dict[str, Any]):
        """
        Resets the client camera view by clicking the compass and scrolling out.
        """
        try:
            self.client.bring_to_foreground()
            
            compass_coords_relative = (213, 492)
            abs_compass_coords = self.ui_interaction._get_abs_coords(compass_coords_relative)
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
            
            scroll_midpoint_abs = self.ui_interaction._get_abs_coords((mid_x_rel, mid_y_rel))
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

    def _fuzzy_text_match(self, ocr_text: str, target_text: str, word_similarity_threshold=0.7, required_match_percentage=1.0) -> bool:
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

    def run(self, stop_event: threading.Event):
        """
        Executes the entire route pathing sequence based on loaded JSON data.
        """
        self.stop_event = stop_event # Store stop_event for use in methods

        print("\n--- Starting Route Pathing ---")
        self.client.bring_to_foreground()
        time.sleep(0.5)

        # The initial reset_client_view is now part of the JSON steps
        # if not self.reset_client_view():
        #     print("Failed to reset client view. Aborting pathing.")
        #     return

        # minimap_region = self._get_minimap_region()
        # if not minimap_region:
        #     print("Could not determine minimap region. Aborting.")
        #     return
        
        # ui_interaction = UIInteraction(HumanizedGridClicker(), self.overlay, self.client) # Pass self.overlay

        # Dispatch table for methods
        method_dispatch = {
            "minimap-image-recognition": self._execute_minimap_image_recognition,
            "gamescreen-action-sampler": self._execute_gamescreen_action_sampler,
            "minimap-compass-direction": self._execute_minimap_compass_direction,
            "view-reset-zoomout-stable": self._execute_view_reset_zoomout_stable,
            # Add other methods here as they are implemented
        }

        for i, step_data in enumerate(self.route_data['steps']):
            if self.stop_event.is_set():
                print("Route pathing stopped by user.")
                break

            step_method = step_data.get("method")
            step_args = step_data.get("args", {})
            step_timing = step_data.get("timing", {"before": 0, "after": 0})

            print(f"Executing Step {i+1}: {step_method}...")

            # Execute 'before' timing
            if step_timing.get("before", 0) > 0:
                time.sleep(step_timing["before"])

            if step_method in method_dispatch:
                success = method_dispatch[step_method](step_args)
                if not success: # Assuming methods return True on success, False on failure
                    print(f"Step {i+1} ({step_method}) failed. Aborting route.")
                    break
            else:
                print(f"Error: Unknown method '{step_method}' in step {i+1}. Aborting route.")
                break
            
            # Execute 'after' timing
            if step_timing.get("after", 0) > 0:
                time.sleep(step_timing["after"])
        
        print("--- Route Pathing Finished ---")
