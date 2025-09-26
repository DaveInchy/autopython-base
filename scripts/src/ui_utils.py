import sys
import os
import json
import random
import time
import pyautogui
from typing import Literal

# Add the project root to sys.path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.client_window import RuneLiteClientWindow
from src.graphics.window_overlay import WindowOverlay

# --- Data Loading ---
def _load_ui_data():
    """Loads the JSONC file, stripping comments first."""
    jsonc_path = os.path.join(os.path.dirname(__file__), 'data', 'user-interface.jsonc')
    try:
        with open(jsonc_path, 'r') as f:
            lines = f.readlines()
        # Strip comments
        lines = [line for line in lines if not line.strip().startswith('//')]
        return json.loads(''.join(lines))
    except FileNotFoundError:
        print(f"Error: UI data file not found at {jsonc_path}. Using empty data.")
        return {}

_ui_data = _load_ui_data()

# --- Type Hinting ---
EquipmentSlot = Literal['helm', 'cape', 'necklace', 'mainHand', 'body', 'offHand', 'legs', 'gloves', 'feet', 'ring', 'ammo']
Grid = Literal['inventory', 'prayer', 'magic', "magic_ancient"]

# --- Generic Grid & Element Functions ---
def _get_grid_slot_coords(grid_name: Grid, slot: int) -> tuple | None:
    grid_data = _ui_data.get(grid_name.lower())
    if not grid_data: return None
    if not (1 <= slot <= grid_data['slots']): raise ValueError(f"Slot must be between 1 and {grid_data['slots']} for {grid_name}")
    
    cols, rows = grid_data['columns'], grid_data['rows']
    start_coord_raw, end_coord_raw = grid_data['start'], grid_data.get('end')
    cell_size = grid_data['cellSize']
    layout_mode = grid_data.get('layout_mode', 'packed')
    coordinate_type = grid_data.get('coordinate_type', 'center')
    col, row = (slot - 1) % cols, (slot - 1) // cols
    start_x, start_y = start_coord_raw['x'], start_coord_raw['y']
    end_x, end_y = (end_coord_raw['x'], end_coord_raw['y']) if end_coord_raw else (0,0)

    if coordinate_type == 'corner':
        start_x -= (cell_size['width'] / 2)
        start_y -= (cell_size['height'] / 2)
        if end_coord_raw:
            end_x += (cell_size['width'] / 2)
            end_y += (cell_size['height'] / 2)

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

def find_ui_element_by_image(image_file: str, confidence=0.8, region: tuple | None = None) -> tuple | None:
    if not os.path.exists(image_file):
        print(f"Warning: Image file not found at {image_file}")
        return None
    try:
        return pyautogui.locateCenterOnScreen(image_file, confidence=confidence, region=region)
    except pyautogui.PyAutoGUIException as e:
        print(f"Error finding UI element by image '{image_file}': {e}")
        return None

# --- UI Component Classes ---
class Equipment:
    _equipment_data = _ui_data.get('equipment', {})
    @staticmethod
    def get_slot_coords(slot_name: EquipmentSlot) -> tuple | None:
        slot_info = Equipment._equipment_data.get(slot_name.lower())
        return (slot_info['x'], slot_info['y']) if slot_info else None

class Inventory:
    _grid_data = _ui_data.get('inventory', {})
    @staticmethod
    def get_slot_coords(slot: int) -> tuple | None:
        return _get_grid_slot_coords('inventory', slot)

class Prayer:
    _grid_data = _ui_data.get('prayer', {})
    @staticmethod
    def get_slot_coords(slot: int) -> tuple | None:
        return _get_grid_slot_coords('prayer', slot)

class Magic:
    _grid_data = _ui_data.get('magic', {})
    @staticmethod
    def get_slot_coords(slot: int) -> tuple | None:
        return _get_grid_slot_coords('magic', slot)

# --- Humanized Clicking Logic ---
class HumanizedGridClicker:
    def __init__(self, learning_rate=0.05, initial_std_dev_factor=0.25):
        self.proficiency = {'inventory': 0, 'prayer': 0, 'magic': 0, 'magic_ancient': 0}
        self.learning_rate = learning_rate
        self.initial_std_dev_factor = initial_std_dev_factor

    def get_randomized_coords(self, grid_name: Grid, slot: int) -> tuple | None:
        grid_data = _ui_data.get(grid_name)
        if not grid_data: return None
        center_coords = _get_grid_slot_coords(grid_name, slot)
        if not center_coords: return None
        center_x, center_y = center_coords
        cell_w, cell_h = grid_data['cellSize']['width'], grid_data['cellSize']['height']
        self.proficiency[grid_name] += 1
        proficiency_factor = 1 + self.proficiency[grid_name] * self.learning_rate
        std_dev_x = (cell_w * self.initial_std_dev_factor) / proficiency_factor
        std_dev_y = (cell_h * self.initial_std_dev_factor) / proficiency_factor
        rand_x, rand_y = random.gauss(center_x, std_dev_x), random.gauss(center_y, std_dev_y)
        min_x, max_x = center_x - cell_w / 3, center_x + cell_w / 3
        min_y, max_y = center_y - cell_h / 3, center_y + cell_h / 3
        clamped_x, clamped_y = max(min_x, min(rand_x, max_x)), max(min_y, min(rand_y, max_y))
        return (int(round(clamped_x)), int(round(clamped_y)))

# --- UI Interaction Class ---
class UIInteraction:
    def __init__(self, clicker: HumanizedGridClicker, overlay, client_window: RuneLiteClientWindow, templates_dir: str = '../res/image'):
        self.clicker = clicker
        self.overlay = overlay
        self.client_window = client_window
        self.templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), templates_dir))

    def _get_abs_coords(self, relative_coords: tuple) -> tuple | None:
        win_rect = self.client_window.get_rect()
        if not win_rect: return None
        abs_x = win_rect['left'] + (win_rect["w"] - relative_coords[0])
        abs_y = win_rect['top'] + (win_rect["h"] - relative_coords[1])
        return (abs_x, abs_y)

    def _get_abs_coords_from_image(self, template_filename: str) -> tuple | None:
        template_path = os.path.join(self.templates_dir, template_filename)
        win_rect = self.client_window.get_rect()
        if not win_rect: return None
        region = (win_rect['left'], win_rect['top'], win_rect['w'], win_rect['h'])
        return find_ui_element_by_image(template_path, region=region)

    def _perform_click(self, abs_click_coords: tuple):
        if not abs_click_coords: return
        pyautogui.click(abs_click_coords[0], abs_click_coords[1])
        if self.overlay:
            self.overlay.add_highlight((abs_click_coords[0]-5, abs_click_coords[1]-5), (abs_click_coords[0]+5, abs_click_coords[1]+5), duration=0.5)
        time.sleep(0.01)

    def _click_slot(self, grid_name: Grid, slot: int, template_filename: str | None, use_image_recognition: bool):
        abs_coords = None
        if use_image_recognition and template_filename:
            abs_coords = self._get_abs_coords_from_image(template_filename)
            if not abs_coords:
                print(f"Warning: Template '{template_filename}' not found for {grid_name} slot {slot}. Falling back to coordinate-based click.")
        if not abs_coords:
            rand_coords = self.clicker.get_randomized_coords(grid_name, slot)
            abs_coords = self._get_abs_coords(rand_coords)
        self._perform_click(abs_coords)

    def click_inventory_slot(self, slot: int, template_filename: str | None = None, use_image_recognition: bool = False):
        self._click_slot('inventory', slot, template_filename, use_image_recognition)

    def click_prayer_slot(self, slot: int, template_filename: str | None = None, use_image_recognition: bool = False):
        self._click_slot('prayer', slot, template_filename, use_image_recognition)

    def click_magic_slot(self, slot: int, template_filename: str | None = None, use_image_recognition: bool = False):
        self._click_slot('magic', slot, template_filename, use_image_recognition)

    def click_equipment_slot(self, slot_name: EquipmentSlot, template_filename: str | None = None, use_image_recognition: bool = False):
        abs_coords = None
        if use_image_recognition and template_filename:
            abs_coords = self._get_abs_coords_from_image(template_filename)
            if not abs_coords:
                print(f"Warning: Template '{template_filename}' not found for equipment slot {slot_name}. Falling back to coordinate-based click.")
        if not abs_coords:
            center_coords = Equipment.get_slot_coords(slot_name)
            abs_coords = self._get_abs_coords(center_coords)
        self._perform_click(abs_coords)

if __name__ == '__main__':
    print("--- UI Utils Demo ---")
    client = RuneLiteClientWindow()
    win_rect = client.get_rect()
    if not win_rect:
        print("RuneLite window not found. Exiting.")
    else:
        overlay = WindowOverlay(title="UI Utils Demo", width=win_rect["w"], height=win_rect["h"], x=win_rect['left'], y=win_rect['top'])
        client.bring_to_foreground()
        time.sleep(0.5)
        ui_interaction = UIInteraction(HumanizedGridClicker(), overlay, client)

        print("\n--- Demo Mode: Image Recognition (with coordinate fallback) ---")
        print("NOTE: This demo requires template images in 'scripts/res/image/'")

        # --- Test Inventory ---
        print("Pressing F2, attempting to click Inventory Slot 5 via image...")
        pyautogui.press('f2')
        time.sleep(0.5)
        overlay.draw_text("Clicking Inventory Slot 5 (image-based)", position=(20, 10), font_size=20, color=(255,255,255))
        ui_interaction.click_inventory_slot(5, template_filename='inventory_shark.png', use_image_recognition=True)
        time.sleep(2)

        # --- Test Prayer ---
        print("Pressing F4, attempting to click Prayer Slot 10 (Rigour) via image...")
        pyautogui.press('f4')
        time.sleep(0.5)
        overlay.draw_text("Clicking Prayer Slot 10 (image-based)", position=(20, 10), font_size=20, color=(255,255,255))
        ui_interaction.click_prayer_slot(21, template_filename='prayer_rigour.png', use_image_recognition=True)
        time.sleep(2)

        # --- Test Magic ---
        print("Pressing F1, clicking Magic Slot 15 (coordinate-based only)...")
        pyautogui.press('f1')
        time.sleep(0.5)
        overlay.draw_text("Clicking Magic Slot 15 (coordinate-based)", position=(20, 10), font_size=20, color=(255,255,255))
        ui_interaction.click_magic_slot(15)
        time.sleep(2)

        print("\nHighlights will now fade. Press Ctrl+C to exit.")
        try:
            while True:
                overlay.update_overlay()
                time.sleep(1/60)
        except KeyboardInterrupt:
            pass

        overlay.close()
        print("\n--- Demo Complete ---")
