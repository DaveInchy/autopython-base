import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json
import random
import time
import pyautogui
import cv2
import numpy as np
from PIL import Image
from typing import Literal
from scripts.src.client_window import RuneLiteClientWindow

# --- Data Loading ---
def _load_ui_data():
    """Loads the JSONC file, stripping comments first."""
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

# --- Type Hinting ---
EquipmentSlot = Literal['helm', 'cape', 'necklace', 'mainHand', 'body', 'offHand', 'legs', 'gloves', 'feet', 'ring', 'ammo']
Grid = Literal['inventory', 'prayer', 'magic', "magic_ancient"]

# --- Generic Grid Calculation ---
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
        absolute_template_path = os.path.join(os.path.dirname(__file__), '..\\..\\..\\res\\image\\', image_file)
        
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

# --- UI Component Classes ---

class Equipment:
    _equipment_data = _ui_data.get('equipment', {})

    @staticmethod
    def get_slot_coords(slot_name: EquipmentSlot) -> tuple | None:
        slot_info = Equipment._equipment_data.get(slot_name.lower())
        return (slot_info['x'], slot_info['y']) if slot_info else None

    @classmethod
    def render(cls, overlay):
        for slot_name, coords in cls._equipment_data.items():
            if slot_name == "f_key": continue # Skip f_key entry
            
            # coords are already relative to the RuneLite window's top-left
            overlay_rel_x = coords['x']
            overlay_rel_y = coords['y']

            # Draw a small square around the center point of the equipment slot
            # Assuming a small fixed size for visualization, e.g., 20x20 pixels
            half_size = 15 # Adjust this value to change the size of the square
            top_left = (overlay_rel_x - half_size, overlay_rel_y - half_size)
            bottom_right = (overlay_rel_x + half_size, overlay_rel_y + half_size)
            overlay.draw_rectangle(top_left, bottom_right, outline_color=(255, 165, 0), width=1) # Orange outline
            overlay.draw_text(slot_name, position=(overlay_rel_x, overlay_rel_y), color=(255, 165, 0), font_size=10)

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
        win_width = overlay.width
        win_height = overlay.height
        slots = cls._grid_data.get('slots', 0)
        cell_size = cls._grid_data.get('cellSize', {})
        cell_w, cell_h = cell_size.get('width', 0), cell_size.get('height', 0)

        for i in range(1, slots + 1):
            coords = cls.get_slot_coords(i)
            if coords:
                abs_x = win_width - coords[0]
                abs_y = win_height - coords[1]

                top_left = (abs_x - cell_w // 2, abs_y - cell_h // 2)
                bottom_right = (abs_x + cell_w // 2, abs_y + cell_h // 2)
                overlay.draw_rectangle(top_left, bottom_right, outline_color=(0, 255, 0), width=1)
                overlay.draw_text(str(i), position=(abs_x, abs_y), color=(255, 255, 0))

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
        win_width = overlay.width
        win_height = overlay.height
        slots = cls._grid_data.get('slots', 0)
        cell_size = cls._grid_data.get('cellSize', {})
        cell_w, cell_h = cell_size.get('width', 0), cell_size.get('height', 0)

        for i in range(1, slots + 1):
            coords = cls.get_slot_coords(i)
            if coords:
                abs_x = win_width - coords[0]
                abs_y = win_height - coords[1]

                top_left = (abs_x - cell_w // 2, abs_y - cell_h // 2)
                bottom_right = (abs_x + cell_w // 2, abs_y + cell_h // 2)
                overlay.draw_rectangle(top_left, bottom_right, outline_color=(0, 255, 255), width=1)
                overlay.draw_text(str(i), position=(abs_x, abs_y), color=(255, 255, 0))

class Magic:
    _grid_data = _ui_data.get('magic', {})

    @staticmethod
    def get_slot_coords(slot: int) -> tuple | None:
        return _get_grid_slot_coords('magic', slot)

    @classmethod
    def render(cls, overlay):
        win_width = overlay.width
        win_height = overlay.height
        slots = cls._grid_data.get('slots', 0)
        cell_size = cls._grid_data.get('cellSize', {})
        cell_w, cell_h = cell_size.get('width', 0), cell_size.get('height', 0)

        for i in range(1, slots + 1):
            coords = cls.get_slot_coords(i)
            if coords:
                abs_x = win_width - coords[0]
                abs_y = win_height - coords[1]

                top_left = (abs_x - cell_w // 2, abs_y - cell_h // 2)
                bottom_right = (abs_x + cell_w // 2, abs_y + cell_h // 2)
                overlay.draw_rectangle(top_left, bottom_right, outline_color=(255, 0, 255), width=1)
                overlay.draw_text(str(i), position=(abs_x, abs_y), color=(255, 255, 0))

# --- Humanized Clicking Logic ---

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


# --- UI Interaction Class ---

class UIInteraction:
    def __init__(self, clicker: HumanizedGridClicker, overlay, client_window: RuneLiteClientWindow):
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


if __name__ == '__main__':
    import time
    from scripts.src.graphics.window_overlay import WindowOverlay
    from scripts.src.client_window import RuneLiteClientWindow

    print("--- Automated UI Grid Renderer Demo ---")
    
    client = RuneLiteClientWindow()
    win_rect = client.get_rect()

    if not win_rect:
        print("RuneLite window not found. Please open RuneLite and try again. Exiting.")
    else:
        overlay = WindowOverlay(title="GridRenderer", width=win_rect["w"], height=win_rect["h"], x=win_rect['left'], y=win_rect['top'])
        client.bring_to_foreground()
        time.sleep(0.5)

        clicker = HumanizedGridClicker()
        ui_interaction = UIInteraction(clicker, overlay, client)

        print(f"\n--- Demo Mode: {'Image Recognition'} ---")

        # --- Continuous Update Loop for Debug Info ---
        print("\nDebug info will display. Press Ctrl+C to exit.")
        try:
            while True:
                # 1. Clear the entire image buffer for this frame
                overlay.clear()

                # 2. Draw debug info: absolute mouse coordinates
                abs_mouse_x, abs_mouse_y = pyautogui.position()
                overlay.draw_text(f"Abs Mouse: ({abs_mouse_x}, {abs_mouse_y})", position=(10, 70), color=(255, 255, 255), font_size=24)

                # Get RuneLite window position
                win_rect = client.get_rect()
                if win_rect:
                    overlay.draw_text(f"RuneLite Win: ({win_rect['w']}, {win_rect['h']})", position=(10, 40), color=(255, 255, 255), font_size=24)

                # 3. Update the Tkinter overlay
                overlay.update_overlay()
                time.sleep(1/60) # Update at 60 FPS
        except KeyboardInterrupt:
            pass

        overlay.close()
        print("\n--- Demo Complete ---")