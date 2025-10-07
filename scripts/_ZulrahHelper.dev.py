"""
Main script for the Zulrah helper.

This script provides gear and prayer switching assistance for the Zulrah boss fight,
with a manual phase confirmation system and a real-time overlay.
"""

# --- Advanced Humanizer Ideas (Future Implementation) ---
#
# The current humanizer logic for timing and accuracy "learns" in one direction:
# it gets progressively better (faster and more accurate) with each action.
# To create a more realistic simulation, we can introduce a "focus" or "fatigue"
# mechanic that degrades these skills over time, especially during periods of
# inactivity (AFK).
#
# 1.  Focus/Activity Tracker:
#     -   Track the time since the last user-initiated action or script activity.
#     -   If the script is inactive for a certain threshold (e.g., > 2 minutes),
#         begin to degrade the "skill" variables.
#
# 2.  Skill Degradation (Losing Focus):
#     -   Timing Skill: Gradually increase the `timing_skill` multiplier back
#         towards its default (1.0) or even slightly higher to simulate being
#         "cold" or out of rhythm.
#     -   Accuracy Skill: Similarly, degrade the accuracy skill in the
#         `HumanizedGridClicker` to make clicks less precise.
#     -   Miss-click Chance: The probability of a miss-click could slightly
#         increase as focus is lost.
#
# 3.  Warm-up Period:
#     -   When activity resumes, the script would need to "warm up" again, with
#         the timing and accuracy skills improving at a potentially faster rate
#         for the first few actions before returning to the normal, gradual
#         improvement.
#
# This would create a dynamic where the script performs best during continuous
# activity but becomes less "perfect" after breaks, mimicking a human player's
# natural ebb and flow of concentration.
#
# --- End of Advanced Humanizer Ideas ---

import time
import threading
import sys
import queue
import signal
import random
from typing import Literal
import os
from PIL import Image # Import Image for type hinting
from pynput import mouse # For click detection
import json # Added for persisting humanizer state


# pip packages/module
import pyautogui # type: ignore
import keyboard # For scoped hotkeys

# --- OSRS Macro SDK Imports ---
from src.window_overlay import WindowOverlay
from src.client_window import RuneLiteClientWindow
from src.ui_utils import HumanizedGridClicker, UIInteraction
from src.runelite_api import RuneLiteAPI
from src.hotkeys import HotkeyManager
from src.osrs_items import OSRSItems
from src.phase_tracker import RotationManager as ColorDataManager # For color data
from src.ui_utils import UI_GRID_SPECS # For inventory slot detection

# --- Globals for Click Detection ---
CLICK_DETECTOR = None
LISTENING_FOR_PHASE_CLICK = False
AWAITING_MAGIC_XP_DROP = False
PREVIOUS_MAGIC_XP = 0

LAST_ZULRAH_SWAP_SCREENSHOT = None

MAGIC_GEAR_SET_IDS = []
RANGE_GEAR_SET_IDS = []

class ClickPhaseDetector:
    def __init__(self, client: RuneLiteClientWindow):
        self.listener = None
        self.client_window = client
        self.ui_interaction = UIInteraction(HumanizedGridClicker(), None, self.client_window)
        self.color_data_manager = ColorDataManager()
        self.phase_colors = {p_info['style']: p_info['colors'] for _, p_info in self.color_data_manager._get_zulrah_rotations_data()['types'].items()}
        self.tolerance = 20

    def get_phase_from_color(self, clicked_color: tuple) -> str:
        for phase, colors in self.phase_colors.items():
            for color in colors:
                if all(abs(int(clicked_color[i]) - color[i]) <= self.tolerance for i in range(3)):
                    return phase
        return None

    def on_click(self, x, y, button, pressed):
        global LISTENING_FOR_PHASE_CLICK, SCRIPT, PHASE_HANDLER, AWAITING_MAGIC_XP_DROP, combat_mode_active
        if not pressed or button != mouse.Button.left:
            return

        # --- Teleport Click Detection (Entry Trigger) ---
        # Zul-andra teleport click detection removed. Combat now starts on any magic XP drop when the script is active.
        # --- End of Teleport Click Detection ---

        if not LISTENING_FOR_PHASE_CLICK:
            return

        # --- Phase Click Detection ---
        clicked_color = pyautogui.pixel(x, y)
        detected_phase = self.get_phase_from_color(clicked_color)

        expected_phase = SCRIPT['state']['phase'] # Get expected phase for logging

        print(f"[ClickPhaseDetector] Clicked at ({x}, {y}). Color: {clicked_color}. Detected phase: {detected_phase}. Expected phase: {expected_phase}.")

        if detected_phase:
            if detected_phase == expected_phase:
                print(f"Correct phase detected and confirmed: {detected_phase}")
                
                SCRIPT['state']['manual_phase_index'] += 1
                if SCRIPT['state']['manual_phase_index'] == 1:
                    SCRIPT['state']['start_time'] = time.time()
                    SCRIPT['state']['time'] = 0
                
                if PHASE_HANDLER.update(phase=detected_phase):
                    print(f"Phase {SCRIPT['state']['manual_phase_index']} ({detected_phase}) confirmed.")
                    SCRIPT['state']['matched_rotation'] = PHASE_HANDLER.matched_rotation
                    next_phase_info = PHASE_HANDLER.fetch()
                    if next_phase_info:
                        if PHASE_HANDLER.wave_counted < len(next_phase_info['phases']):
                            next_phase_style = next_phase_info['phases'][PHASE_HANDLER.wave_counted]
                            SCRIPT['state']['next_phase_style'] = next_phase_style
                            SCRIPT['state']['phase'] = next_phase_style
                            SCRIPT['state']['phase_start_time'] = time.time()
                            SCRIPT['state']['current_phase_duration_ticks'] = next_phase_info['ticks'][PHASE_HANDLER.wave_counted - 1]
                        else:
                            SCRIPT['state']['next_phase_style'] = 'END'
                            SCRIPT['state']['phase'] = 'END'
                    else:
                        SCRIPT['state']['next_phase_style'] = 'UNKNOWN'
                        SCRIPT['state']['phase'] = 'UNKNOWN'
                else:
                    print(f"Failed to confirm phase: {detected_phase}")

                LISTENING_FOR_PHASE_CLICK = False
            else:
                print(f"Wrong phase detected! Expected {expected_phase}, but got {detected_phase}. Please click again.")
        else:
            print(f"Clicked color {clicked_color} at ({x}, {y}) did not match any phase.")

    def start(self):
        if self.listener is None:
            self.listener = mouse.Listener(on_click=self.on_click)
            self.listener.start()
            print("Click phase detector started.")

    def stop(self):
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
            print("Click phase detector stopped.")


combat_mode_active = False
health, prayer = 99, 99

SCRIPT={
    "version": "1.7.2",
    "title": "Zulrah Helper",
    "description": "A script that switches gear and prayers for Zulrah based on the current phase and what you have in your inventory",
    "tags": ["combat", "zulrah", "prayer", "gear"],
    "help": [
        "Semi automated, Uses http api plugin in RuneLite (not owned by me) for information",
        "Dynamic UI and confirmed quick-actions, you will not loose control and everything can be done in 1 tick (not recommended).",
        "Prayer dropped? Just re-use your phase key",
        "Acts so much like humans its quite ridiculous ask GPT if he knows each important note on how to act human. he knows...",
        "Almost OP, you only need to click the boss",
        "Learns 2 play better with machine learning and will try and mimic your specific clicking accuracy, so when you get better, the program does too! W0W",
        "Planned features include, smart-consume, better performance, mouse movement visuals (yes we actually move the mouse), And Quick banking, Phase counter, Jad indicator, guidance, target tiles, Tick perfect rotations (preserve consumables)."
    ],
    "category": "PVM",
    "author": "NobodyByAnybody420N0SCOP3_XXx_Doritos_Gatorade <www.doonline.nl>",
    "ref": "https://www.github.com//NobodyByAnybody420N0SCOP3_XXx_Doritos_Gatorade/ZulrahRapier/releases",
    "settings": {
        "_done": False,
        "_started": False,
        "timings": 0.05, # Base delay for actions
        "use_chatbox_overlay": True,
        "switch_count": 5,
        "api_port": 8080,
        "use_rotation_tracker": False, #TODO
        "use_humanizers": True,
        "hk_magic": "q",
        "hk_range": "w",
        "hk_melee": "e",
        "use_prayers": True,
        "use_equipment": True, #DUH
        "use_consumables": True, #TODO
        "use_quick_tabs": True, #TODO Quick Tele Tabbing
        "enable_antideath": False, #TODO
        "enable_smart_consume": False, #TODO
        "enable_insecure_phase_tracker": False,
        "disable_confident_phase_tracker": True,
        "enable_rotation_counter": True,
        "enable_smart_ticks": False, #TODO
        "use_hotkeys": True,
        "enable_extra_hotkeys": False, #TODO, Like healing, teleport, phase confirm
        "use_overlays": True,
        "use_phase_counter": True,
        "use_jad_indicator": True,
        "use_performance_mode": True,
        "use_wave_images": True,
        "use_image_recognition": False,
        "mode": "hotkeys",
        "manual_spell_slot": 1,
        "manual_spell_book": "standard",
        "render_grids_and_clicks": False,
    },
    "state": {
        "start_time": int(0),
        "time": int(0),
        "phase": "UNKNOWN",
        "manual_phase_index": 0,
        "last_eat_time": 0,
        "Warning": None,
        "player_style": "UNKNOWN",
        "activated": False,
        "matched_rotation": 0,
        "next_phase_style": "UNKNOWN",
        "phase_start_time": 0,
        "current_phase_duration_ticks": 0,
        "timing_skill": 1.0, # Multiplier, starts at 1.0, decreases as skill increases
        "last_action_time": 0,
    },
    "setup": [
        {
            "context": "how many switches do you use per style (can be different using 2-handed weapons, make sure slot 1 is weapon, and slot 2 is your off-hand/nothing)",
            "options": {
                "1": "4",
                "2": "5",
                "3": "6",
                "4": "7",
                "5": "8",
            },
            "default": 4,
            "setting": "switch_count",
        }
    ],
}

class RotationManager:
    def __init__(self):
        self.confirmed_phases = []
        self.matched_rotation = 0
        self.wave_counted = 0

        self.data = {
            "types": {
                2042: {"name": "Green", "style": "RANGE"},
                2043: {"name": "Red", "style": "MELEE"},
                2044: {"name": "Blue", "style": "MAGIC"},
            },
            "waves": {
                1: {
                    "phases": ["RANGE", "MELEE", "MAGIC", "RANGE", "MAGIC", "MELEE", "RANGE", "MAGIC", "RANGE", "MELEE"],
                    "jad": 9,
                    "ticks": [28, 20, 18, 28, 39, 22, 20, 36, 48, 20]
                },
                2: {
                    "phases": ["RANGE", "MELEE", "MAGIC", "RANGE", "MELEE", "MAGIC", "RANGE", "MAGIC", "RANGE", "MELEE"],
                    "jad": 9,
                    "ticks": [28, 20, 17, 39, 22, 20, 28, 36, 48, 21]
                },
                3: {
                    "phases": ["RANGE", "RANGE", "MELEE", "MAGIC", "RANGE", "MAGIC", "RANGE", "RANGE", "MAGIC", "RANGE", "MAGIC"],
                    "jad": 10,
                    "ticks": [28, 30, 40, 20, 20, 20, 25, 20, 36, 35, 18]
                },
                4: {
                    "phases": ["RANGE", "MAGIC", "RANGE", "MAGIC", "MELEE", "RANGE", "RANGE", "MAGIC", "RANGE", "MAGIC", "RANGE", "MAGIC"],
                    "jad": 11,
                    "ticks": [28, 36, 24, 30, 28, 17, 34, 33, 20, 27, 29, 18]
                }
            }
        }

    def match_rotation(self, confirmed_list: list) -> int:
        if not confirmed_list:
            return 0
        possible_rotations = []
        for rot_id, rot_data in self.data["waves"].items():
            if rot_data["phases"][:len(confirmed_list)] == confirmed_list:
                possible_rotations.append(rot_id)
        if len(possible_rotations) == 1:
            return possible_rotations[0]
        return 0

    def update(self, phase: str) -> bool:
        if not phase or phase == "UNKNOWN":
            return False
        self.confirmed_phases.append(phase)
        self.wave_counted = len(self.confirmed_phases)
        self.matched_rotation = self.match_rotation(self.confirmed_phases)
        return True
    
    def fetch(self):
        if self.matched_rotation in self.data["waves"]:
            return self.data["waves"][self.matched_rotation]
        return None

    def reset(self):
        """Resets the rotation tracking state."""
        self.confirmed_phases = []
        self.matched_rotation = 0
        self.wave_counted = 0
        print("RotationManager reset.")

    
global PHASE_HANDLER, CHATBOX_IMAGE, PHASE_IMAGE_CACHE
PHASE_HANDLER: RotationManager = RotationManager()
CHATBOX_IMAGE = None
PHASE_IMAGE_CACHE = {}

HOTKEY_START_FIGHT='.'

def get_weapon_style_from_slot_one(api: RuneLiteAPI, items_db: OSRSItems) -> str:
    inventory = api.get_inventory()
    if not inventory or len(inventory) == 0:
        return "UNKNOWN"
    slot_one_item = inventory[0]
    item_id = slot_one_item.get('id')
    if item_id == -1:
        return "EMPTY"
    item_name = items_db.get_item_name(item_id)
    magic_ids = [12903, 12904, 12905, 27676, 27679]
    ranged_ids = [28869]
    if not item_id in magic_ids and not item_id in ranged_ids:
        if not item_name:
            return "UNKNOWN"
    if item_name:
        item_name = item_name.lower()
    else:
        item_name = "dwarf remains"
    if "staff" in item_name or "wand" in item_name or "sceptre" in item_name or "trident" in item_name or item_id in magic_ids:
        return "MAGIC"
    if "bow" in item_name or "blowpipe" in item_name or "crossbow" in item_name or "dart" in item_name or "thrownaxe" in item_name or "knife" in item_name or item_id in ranged_ids:
        return "RANGE"
    return "UNKNOWN"

def render(client: RuneLiteClientWindow, overlay: WindowOverlay, api: RuneLiteAPI, items_db: OSRSItems, chatbox_image: Image.Image | None):
    global SCRIPT, combat_mode_active, LISTENING_FOR_PHASE_CLICK
    chatbox_height = 165
    _font_size = 20

    if not SCRIPT['state']['activated']:
        overlay.draw_rectangle((0, 0), (overlay.width - 1, overlay.height - 1), outline_color=(255, 0, 0), width=2)
        overlay.draw_text("Overlay Inactive (Press '.' to activate)", position=(10, 7), color=(255, 0, 0), font_size=17)
        if SCRIPT['settings']['use_chatbox_overlay'] and chatbox_image:
            overlay.draw_pil_image(chatbox_image, position=(0, overlay.height - chatbox_height))
        return
    
    if not combat_mode_active:
        overlay.draw_rectangle((0, 0), (overlay.width - 1, overlay.height - 1), outline_color=(255, 165, 0), width=2) # Orange border for waiting
        overlay.draw_text("Waiting for combat to start...", position=(10, 7), color=(0, 255, 255), font_size=17)
        if SCRIPT['settings']['use_chatbox_overlay'] and chatbox_image:
            overlay.draw_pil_image(chatbox_image, position=(0, overlay.height - chatbox_height))
        return
    
    if SCRIPT['settings']['use_chatbox_overlay'] and chatbox_image:
        overlay.draw_pil_image(chatbox_image, position=(0, overlay.height - chatbox_height))

    # --- New Rendering Logic ---
    info_pos_x = 18
    info_pos_y = overlay.height - chatbox_height + 10

    # Display current rotation and wave
    rotation_num = SCRIPT['state'].get('matched_rotation', 0)
    wave_num = SCRIPT['state'].get('manual_phase_index', 0)
    overlay.draw_text(f"Rotation: {rotation_num} | Wave: {wave_num}", position=(info_pos_x, info_pos_y), font_size=_font_size, color=(0, 0, 0))

    # --- Focus Meter ---
    timing_skill = SCRIPT['state'].get('timing_skill', 1.0)
    focus_metric = (1.0 - timing_skill) / 0.5 # Maps [1.0, 0.5] to [0, 1]
    focus_percent = int(focus_metric * 100)

    METER_LENGTH = 10
    FULL_GLYPH = '⁞'
    EMPTY_GLYPH = '⁚'

    filled_segments = int(focus_metric * METER_LENGTH)
    meter_string = FULL_GLYPH * filled_segments + EMPTY_GLYPH * (METER_LENGTH - filled_segments)

    meter_color = (0, 255, 0) # Green
    if focus_metric <= 0.7:
        meter_color = (255, 255, 0) # Yellow
    if focus_metric <= 0.3:
        meter_color = (255, 0, 0) # Red

    overlay.draw_text(f"Focus: {meter_string} {focus_percent}%", position=(info_pos_x, info_pos_y + (_font_size + 5)), font_size=_font_size, color=meter_color)

    # Display Phase Cooldown Timer
    phase_start_time = SCRIPT['state'].get('phase_start_time', 0)
    phase_duration_ticks = SCRIPT['state'].get('current_phase_duration_ticks', 0)

    if phase_start_time > 0 and phase_duration_ticks > 0:
        phase_duration_sec = phase_duration_ticks * 0.6
        elapsed_time = time.time() - phase_start_time
        remaining_time = phase_duration_sec - elapsed_time

        if remaining_time > 0:
            overlay.draw_text(f"Next in: {remaining_time:.1f}s", position=(info_pos_x, info_pos_y + (_font_size + 5)), font_size=_font_size, color=(0, 0, 0))
        else:
            overlay.draw_text("Next: NOW", position=(info_pos_x, info_pos_y + (_font_size + 5)), font_size=_font_size, color=(255, 0, 0))

    # Display listening status
    if LISTENING_FOR_PHASE_CLICK:
        overlay.draw_text("Click Boss to Confirm Phase", position=(info_pos_x, info_pos_y + 2 * (_font_size + 5)), font_size=_font_size, color=(0, 0, 0))

    # --- Render Phase Graphic ---
    if SCRIPT['settings']['use_wave_images']:
        rotation_num = SCRIPT['state'].get('matched_rotation', 0)
        rotation_num = SCRIPT['state'].get('matched_rotation', 0)
        wave_num = SCRIPT['state'].get('manual_phase_index', 0)

        if rotation_num > 0 and wave_num > 0:
            base_rotation_path = os.path.join(os.path.dirname(__file__), 'res', 'zulrah', f'rotation-{rotation_num}')
            specific_image_path = os.path.join(base_rotation_path, f'wave_{wave_num:02d}.png')
            default_image_path = os.path.join(base_rotation_path, 'wave_01.png')

            phase_image = None

            # 1. Check cache for the specific image
            if specific_image_path in PHASE_IMAGE_CACHE:
                if PHASE_IMAGE_CACHE[specific_image_path] != "not_found":
                    phase_image = PHASE_IMAGE_CACHE[specific_image_path]
            else:
                # 2. Try to load specific image and cache it
                try:
                    phase_image = Image.open(specific_image_path).convert("RGBA")
                    PHASE_IMAGE_CACHE[specific_image_path] = phase_image
                except FileNotFoundError:
                    PHASE_IMAGE_CACHE[specific_image_path] = "not_found"

            # 3. If specific image failed, try the default (wave_01)
            if phase_image is None:
                if default_image_path in PHASE_IMAGE_CACHE:
                    if PHASE_IMAGE_CACHE[default_image_path] != "not_found":
                        phase_image = PHASE_IMAGE_CACHE[default_image_path]
                else:
                    try:
                        phase_image = Image.open(default_image_path).convert("RGBA")
                        PHASE_IMAGE_CACHE[default_image_path] = phase_image
                    except FileNotFoundError:
                        PHASE_IMAGE_CACHE[default_image_path] = "not_found"

            if phase_image:
                # Resize the image to 0.4 times the original size
                new_width = int(phase_image.width * 0.4)
                new_height = int(phase_image.height * 0.4)
                resized_image = phase_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Center the image in the right half of the chatbox
                chatbox_right_half_center_x = overlay.width * 0.75
                image_pos_x = int(chatbox_right_half_center_x - (resized_image.width / 2))
                image_pos_y = int(overlay.height - chatbox_height + (chatbox_height - resized_image.height) / 2) # Vertically centered in chatbox
                overlay.draw_pil_image(resized_image, position=(image_pos_x, image_pos_y))

    return

def disable_user_mouse_input():
    pyautogui.FAILSAFE = False
    try:
        import ctypes
        ctypes.windll.user32.BlockInput(True)
    except: pass

def enable_user_mouse_input():
    pyautogui.FAILSAFE = True
    try:
        import ctypes
        ctypes.windll.user32.BlockInput(False)
    except: pass

HUMANIZER_STATE_FILE = os.path.join(os.path.expanduser('~'), '.zulrah_humanizer_state.json')

def save_humanizer_state():
    global SCRIPT
    state_to_save = {
        'last_action_time': SCRIPT['state'].get('last_action_time', time.time()),
        'timing_skill': SCRIPT['state'].get('timing_skill', 1.0)
    }
    try:
        with open(HUMANIZER_STATE_FILE, 'w') as f:
            json.dump(state_to_save, f)
    except Exception as e:
        print(f"Error saving humanizer state: {e}")

def load_humanizer_state():
    global SCRIPT
    try:
        if os.path.exists(HUMANIZER_STATE_FILE):
            with open(HUMANIZER_STATE_FILE, 'r') as f:
                loaded_state = json.load(f)
                SCRIPT['state']['last_action_time'] = loaded_state.get('last_action_time', time.time())
                SCRIPT['state']['timing_skill'] = loaded_state.get('timing_skill', 1.0)
                print(f"Loaded humanizer state: last_action_time={SCRIPT['state']['last_action_time']:.2f}, timing_skill={SCRIPT['state']['timing_skill']:.3f}")
                
                # Apply degradation if script was off for a long time
                time_since_last_action = time.time() - SCRIPT['state']['last_action_time']
                if time_since_last_action > 120: # If inactive for more than 2 minutes
                    # Simulate degradation over the offline period
                    degradation_factor = time_since_last_action / 120 # How many 2-minute intervals passed
                    current_skill = SCRIPT['state']['timing_skill']
                    # Degradation is 0.0005 per 2 minutes (from update_humanizer_focus)
                    degraded_skill = min(1.0, current_skill + (0.0005 * degradation_factor))
                    SCRIPT['state']['timing_skill'] = degraded_skill
                    print(f"Applied offline degradation. New timing_skill={SCRIPT['state']['timing_skill']:.3f}")

    except Exception as e:
        print(f"Error loading humanizer state: {e}")
    
    # Ensure last_action_time is always updated to now if not loaded or error occurred
    if 'last_action_time' not in SCRIPT['state']:
        SCRIPT['state']['last_action_time'] = time.time()
    if 'timing_skill' not in SCRIPT['state']:
        SCRIPT['state']['timing_skill'] = 1.0

def update_humanizer_focus():
    """Gradually degrades timing skill if the script is inactive."""
    if time.time() - SCRIPT['state'].get('last_action_time', 0) > 120: # 2 minutes
        current_skill = SCRIPT['state'].get('timing_skill', 1.0)
        # Degrade skill back towards 1.0 (default)
        degraded_skill = min(1.0, current_skill + 0.0005)
        if degraded_skill != current_skill:
            SCRIPT['state']['timing_skill'] = degraded_skill
            save_humanizer_state() # Save state after degradation

def update_timing_skill():
    """Gradually decreases the timing skill multiplier to simulate getting faster."""
    current_skill = SCRIPT['state'].get('timing_skill', 1.0)
    # Gets 2.5% faster each time, down to a max of 50% faster (0.5 multiplier)
    new_skill = max(0.5, current_skill * 0.975)
    SCRIPT['state']['timing_skill'] = new_skill
    save_humanizer_state() # Save state after improvement

def is_on_cooldown(cooldown_name: str, duration: float) -> bool:
    last_action_time = SCRIPT['state'].get(f'last_{cooldown_name}_time', 0)
    return time.time() - last_action_time < duration

def set_cooldown(cooldown_name: str):
    SCRIPT['state'][f'last_{cooldown_name}_time'] = time.time()

def search_inventory(name="Shark") -> int | None:
    api = RuneLiteAPI()
    inventory = api.get_inventory()
    if not inventory: return None
    for index, item in enumerate(inventory):
        if name.lower() in item.get('name', '').lower():
            return 1 + index
    return None

    return 1 + index

def get_item_display_name(item_id: int) -> str:
    name = items_db.get_item_name(item_id)
    return name if name is not None else f"ID: {item_id}"

def establish_gear_sets():
    global MAGIC_GEAR_SET_IDS, RANGE_GEAR_SET_IDS, SCRIPT
    print("[ZulrahHelper] Establishing gear sets...")

    # Assume currently equipped gear is MAGIC_GEAR_SET_IDS
    equipped_items = api.get_equipment()
    if equipped_items:
        MAGIC_GEAR_SET_IDS = [item['id'] for item in equipped_items if item['id'] != -1]
        print(f"[ZulrahHelper] Identified Magic Gear Set (equipped): {[get_item_display_name(item_id) for item_id in MAGIC_GEAR_SET_IDS]}")
    else:
        print("[ZulrahHelper] Could not retrieve equipped items to establish Magic Gear Set. Assuming empty.")
        MAGIC_GEAR_SET_IDS = []

    # Assume items in switch slots in inventory are RANGE_GEAR_SET_IDS
    num_switches = int(SCRIPT["settings"]["switch_count"])
    switch_slots_indices = [s - 1 for s in [1, 2, 5, 6, 9, 10, 13, 14, 17, 18, 21, 22, 25, 26][:num_switches]]

    inventory_items = api.get_inventory()
    if inventory_items:
        RANGE_GEAR_SET_IDS = []
        for index in switch_slots_indices:
            if index < len(inventory_items):
                item_id = inventory_items[index].get('id')
                if item_id != -1:
                    RANGE_GEAR_SET_IDS.append(item_id)
        print(f"[ZulrahHelper] Identified Range Gear Set (from inventory switch slots): {[get_item_display_name(item_id) for item_id in RANGE_GEAR_SET_IDS]}")
    else:
        print("[ZulrahHelper] Could not retrieve inventory items to establish Range Gear Set. Assuming empty.")
        RANGE_GEAR_SET_IDS = []

    if not MAGIC_GEAR_SET_IDS or not RANGE_GEAR_SET_IDS:
        print("[ZulrahHelper] Warning: Could not fully establish both gear sets. Gear switching may not work correctly.")

def switch_to_gear_set(humanizer: UIInteraction, target_gear_set_ids: list[int]):
    SCRIPT['state']['last_action_time'] = time.time()
    disable_user_mouse_input()

    # Get current equipped items and inventory
    current_equipped = {item['id'] for item in api.get_equipment() if item['id'] != -1}
    current_inventory = api.get_inventory()
    
    print(f"[ZulrahHelper] Switching to gear set: {[get_item_display_name(item_id) for item_id in target_gear_set_ids]}")
    print(f"[ZulrahHelper] Currently equipped: {[get_item_display_name(item_id) for item_id in current_equipped]}")
    
    # Identify items to click from inventory
    items_to_click_from_inv = []
    for target_item_id in target_gear_set_ids:
        if target_item_id not in current_equipped:
            # Find item in inventory
            found_in_inv = False
            for i, inv_item in enumerate(current_inventory):
                if inv_item['id'] == target_item_id:
                    items_to_click_from_inv.append(i + 1) # 1-based slot index
                    found_in_inv = True
                    print(f"[ZulrahHelper] Found {get_item_display_name(target_item_id)} in inventory slot {i+1} for clicking.")
                    break
            if not found_in_inv:
                print(f"[ZulrahHelper] Warning: {get_item_display_name(target_item_id)} needed but not found in inventory.")
    
    items_to_click_from_inv.sort() # Ensure slot 1 is clicked before slot 2

    for slot in items_to_click_from_inv:
        print(f"[ZulrahHelper] Clicking inventory slot {slot} to equip.")
        humanizer.click_inventory_slot(slot)
        time.sleep(random.uniform(SCRIPT['settings']['timings'] * 0.8, SCRIPT['settings']['timings'] * 1.6) * SCRIPT['state']['timing_skill']) # Randomized click delay

    # --- Verification and Correction ---
    time.sleep(SCRIPT['settings']['timings'] * 8 * SCRIPT['state']['timing_skill']) # Wait for game tick to update equipment

    equipped_after_switch = {item['id'] for item in api.get_equipment() if item['id'] != -1}
    print(f"[ZulrahHelper] Equipped after initial switch attempt: {[get_item_display_name(item_id) for item_id in equipped_after_switch]}")
    
    # Primary Check: Ensure all target items are equipped
    missing_from_target = set(target_gear_set_ids) - equipped_after_switch
    if missing_from_target:
        print(f"[ZulrahHelper] Gear switch failed. Missing items: {[get_item_display_name(item_id) for item_id in missing_from_target]}. Retrying...")
        
        # Re-fetch inventory once for retry
        current_inventory_list = api.get_inventory()
        for missing_item_id in missing_from_target:
            found_in_inv = False
            for i, inv_item in enumerate(current_inventory_list):
                if inv_item['id'] == missing_item_id:
                    humanizer.click_inventory_slot(i + 1)
                    time.sleep(random.uniform(SCRIPT['settings']['timings'] * 0.8, SCRIPT['settings']['timings'] * 1.6) * SCRIPT['state']['timing_skill'])
                    found_in_inv = True
                    break
            if not found_in_inv:
                print(f"[ZulrahHelper] Error: {get_item_display_name(missing_item_id)} still missing and not found in inventory for retry.")
        time.sleep(SCRIPT['settings']['timings'] * 8 * SCRIPT['state']['timing_skill']) # Wait again after correction attempt
        equipped_after_switch = {item['id'] for item in api.get_equipment() if item['id'] != -1} # Re-check
        print(f"[ZulrahHelper] Equipped after primary correction: {[get_item_display_name(item_id) for item_id in equipped_after_switch]}")

    # Secondary Check: Ensure no items from the *other* gear set are equipped
    other_gear_set_ids = MAGIC_GEAR_SET_IDS if target_gear_set_ids == RANGE_GEAR_SET_IDS else RANGE_GEAR_SET_IDS
    unexpectedly_equipped = equipped_after_switch.intersection(other_gear_set_ids)
    if unexpectedly_equipped:
        print(f"[ZulrahHelper] Correcting unexpected gear. Unequipped items: {[get_item_display_name(item_id) for item_id in unexpectedly_equipped]}. Retrying...")
        
        # Re-fetch inventory once for retry
        current_inventory_list = api.get_inventory()
        for unexpected_item_id in unexpectedly_equipped:
            found_in_inv = False
            for i, inv_item in enumerate(current_inventory_list):
                if inv_item['id'] == unexpected_item_id:
                    print(f"[ZulrahHelper] Clicking {get_item_display_name(unexpected_item_id)} in inventory slot {i+1} to unequip.")
                    humanizer.click_inventory_slot(i + 1)
                    time.sleep(random.uniform(SCRIPT['settings']['timings'] * 0.8, SCRIPT['settings']['timings'] * 1.6) * SCRIPT['state']['timing_skill'])
                    found_in_inv = True
                    break
            if not found_in_inv:
                print(f"[ZulrahHelper] Error: {get_item_display_name(unexpected_item_id)} unexpectedly equipped but not found in inventory for unequip retry.")
        time.sleep(SCRIPT['settings']['timings'] * 8 * SCRIPT['state']['timing_skill']) # Wait again after correction attempt
        equipped_after_switch = {item['id'] for item in api.get_equipment() if item['id'] != -1} # Re-check
        print(f"[ZulrahHelper] Equipped after secondary correction: {[get_item_display_name(item_id) for item_id in equipped_after_switch]}")

    update_timing_skill()

def equip_gear(target_type: str):
    global SCRIPT
    original_pause = pyautogui.PAUSE
    pyautogui.PAUSE = SCRIPT['settings']['timings']
    try:
        original_x, original_y = pyautogui.position()
        client = RuneLiteClientWindow()
        client.bring_to_foreground()
        humanizer = UIInteraction(HumanizedGridClicker(), None, client)
        
        # Determine which gear set to switch to
        if target_type == "MAGIC":
            target_gear_set = RANGE_GEAR_SET_IDS # For magic phase, equip range gear
        elif target_type == "RANGE" or target_type == "MELEE":
            target_gear_set = MAGIC_GEAR_SET_IDS # For range/melee phase, equip magic gear
        else:
            print(f"[ZulrahHelper] Unknown target type: {target_type}. No gear switch performed.")
            return

        # --- MODIFIED FLOW ---
        # 1. Switch prayers first
        pyautogui.press('F4')
        time.sleep(random.uniform(SCRIPT['settings']['timings'] * 1.6, SCRIPT['settings']['timings'] * 3.0) * SCRIPT['state']['timing_skill'])
        if target_type == "MAGIC":
            humanizer.click_prayer_slot(17) # Protect from Magic
            humanizer.click_prayer_slot(20) # Offensive Ranged Prayer
        elif target_type == "RANGE":
            humanizer.click_prayer_slot(18) # Protect from Missiles
            humanizer.click_prayer_slot(21) # Offensive Magic Prayer
        elif target_type == "MELEE":
            humanizer.click_prayer_slot(23) # Protect from Melee (or whatever is appropriate)
            humanizer.click_prayer_slot(21) # Offensive Magic Prayer

        # 2. Switch to inventory and perform gear switch
        pyautogui.press('F2') # Open inventory tab
        time.sleep(random.uniform(SCRIPT['settings']['timings'] * 1.6, SCRIPT['settings']['timings'] * 3.0) * SCRIPT['state']['timing_skill'])
        switch_to_gear_set(humanizer, target_gear_set)

        pyautogui.moveTo(original_x, original_y)
        global LISTENING_FOR_PHASE_CLICK
        LISTENING_FOR_PHASE_CLICK = True
        print("Ready for phase-defining click...")
    finally:
        pyautogui.PAUSE = original_pause
    return

def equip_range(): equip_gear(target_type="RANGE")
def equip_mage(): equip_gear(target_type="MAGIC")
def equip_melee(): equip_gear(target_type="MELEE")

def get_async_hp_prayer(api: RuneLiteAPI, stop_event: threading.Event):
    global health, prayer
    try:
        while not stop_event.is_set():
            health = api.get_health_points()
            prayer = api.get_prayer_points()
            time.sleep(0.1) # Polling interval
    finally:
        print("HP/Prayer thread stopped")

def update(ui: UIInteraction, stop_event: threading.Event):
    original_x, original_y = pyautogui.position()
    min_hp_threshold = random.randint(45, 60)
    min_pray_threshold = random.randint(8, 15)
    global SCRIPT, health, prayer
    
    if health is None or health == 0:
        print("Death detected")
        SCRIPT['state']["Warning"] = "YOU DIED IDIOT"
        on_death(stop_event)
        return

    if health <= min_hp_threshold:
        if is_on_cooldown('eat', 1.8):
            return
        SCRIPT['state']["Warning"] = "HEALTH is low"
        disable_user_mouse_input()
        ui.client_window.bring_to_foreground()
        pyautogui.press('F2')
        on_low_health(ui, stop_event)
        pyautogui.moveTo(original_x, original_y)
        enable_user_mouse_input()
    
    if prayer is not None and prayer <= min_pray_threshold:
        SCRIPT['state']["Warning"] = "PRAYER is low"
        disable_user_mouse_input()
        ui.client_window.bring_to_foreground()
        pyautogui.press('F2')
        on_low_prayer(ui, stop_event)
        pyautogui.moveTo(original_x, original_y)
        enable_user_mouse_input()
    elif prayer is not None and prayer == 0:
        print("Supply shortage detected")
        SCRIPT['state']["Warning"] = "No PRAYER points left"
        panic_teleport(ui, stop_event)

def assume_wave_one_is_range():
    """Resets state and assumes the first wave is RANGE."""
    print("Assuming Wave 1 is RANGE.")
    if PHASE_HANDLER.update(phase="RANGE"):
        SCRIPT['state']['phase'] = "RANGE"
        SCRIPT['state']['manual_phase_index'] = PHASE_HANDLER.wave_counted
        SCRIPT['state']['matched_rotation'] = PHASE_HANDLER.matched_rotation
        next_phase_info = PHASE_HANDLER.fetch()
        if next_phase_info:
            # Start timer for the first phase
            SCRIPT['state']['phase_start_time'] = time.time()
            SCRIPT['state']['current_phase_duration_ticks'] = next_phase_info['ticks'][0]
            SCRIPT['state']['next_phase_style'] = next_phase_info['phases'][1]

def enable_combat_mode(stop_event: threading.Event, q: queue.Queue):
    global SCRIPT, combat_mode_active, PHASE_HANDLER, AWAITING_MAGIC_XP_DROP
    client = RuneLiteClientWindow()
    humanized_clicker = HumanizedGridClicker(focus_metric=SCRIPT['state']['timing_skill'])
    ui = UIInteraction(humanized_clicker, None, client)
    api = RuneLiteAPI()
    
    if not AWAITING_MAGIC_XP_DROP:
        # Script is being activated by the hotkey, not an XP drop
        print("Script activated. Waiting for combat to start.")
        SCRIPT['state']["activated"] = True # UI is active
        combat_mode_active = False # Combat is NOT active yet
        return # Don't start combat loop yet

    AWAITING_MAGIC_XP_DROP = False
    # If we reach here, AWAITING_MAGIC_XP_DROP is True, so combat should start
    print("Combat mode enabled. Gear/prayer hotkeys are active.")
    
    # Reset state for a new fight
    PHASE_HANDLER.reset()
    reset_combat_state()

    # Establish gear sets
    establish_gear_sets()

    # Assume Wave 1 is always RANGE
    assume_wave_one_is_range()

    SCRIPT['state']["activated"] = True # Combat UI is active

    # --- State for Teleport Reset ---
    previous_inventory = None
    HOME_TELEPORT_IDS = [8013, 2552] # House Teleport tablet, Ring of Dueling

    def check_for_teleport_and_reset(current_inventory, stop_event: threading.Event):
        nonlocal previous_inventory
        global AWAITING_MAGIC_XP_DROP
        if previous_inventory is None:
            previous_inventory = {f"{item['id']}_{i}": item['quantity'] for i, item in enumerate(current_inventory)}
            return

        current_inventory_map = {f"{item['id']}_{i}": item['quantity'] for i, item in enumerate(current_inventory)}

        for item_key, prev_quantity in previous_inventory.items():
            item_id = int(item_key.split('_')[0])
            if item_id in HOME_TELEPORT_IDS:
                curr_quantity = current_inventory_map.get(item_key, 0)
                if curr_quantity < prev_quantity:
                    print(f"Home teleport used (Item ID: {item_id}). Stopping combat loop.")
                    stop_event.set() # Stop the combat loop
                    AWAITING_MAGIC_XP_DROP = True # Ready for next fight
                    break # Exit after finding one used teleport
        
        previous_inventory = current_inventory_map

    def run_combat_mode(stop_event: threading.Event, q: queue.Queue):
        global combat_mode_active
        nonlocal client, ui, api, previous_inventory
        if combat_mode_active: return

        thread2 = threading.Thread(target=get_async_hp_prayer, args=(api,stop_event,))
        thread2.daemon = True
        thread2.start()

        combat_mode_active = True
        try:
            loop_interval = random.uniform(0.09, 0.12)
            last_click_time = time.time() # For testing show_click
            while not stop_event.is_set():
                start_time = time.time()

                # --- Automatic Phase Advancement ---
                phase_start_time = SCRIPT['state'].get('phase_start_time', 0)
                phase_duration_ticks = SCRIPT['state'].get('current_phase_duration_ticks', 0)

                if phase_start_time > 0 and phase_duration_ticks > 0:
                    phase_duration_sec = phase_duration_ticks * 0.6 # 0.6 seconds per tick
                    phase_end_time = phase_start_time + phase_duration_sec

                    if time.time() >= phase_end_time:
                        print("[ZulrahHelper] Automatically advancing phase due to duration expiry.")
                        confirm_phase() # Reuse existing logic to advance phase
                        # Reset phase timer to prevent immediate re-trigger
                        SCRIPT['state']['phase_start_time'] = 0
                        SCRIPT['state']['current_phase_duration_ticks'] = 0

                # Check for teleport reset
                current_inventory = api.get_inventory()
                if current_inventory:
                    check_for_teleport_and_reset(current_inventory, stop_event)
                    if stop_event.is_set():
                        return # Exit the combat loop

                update_humanizer_focus() # Degrade skill if AFK
                update(ui, stop_event)
                SCRIPT['state']["time"] = (time.time() - SCRIPT['state']["start_time"])
                q.put({'type': 'render', 'state': SCRIPT['state'], 'client_rect': client.get_rect()})

                elapsed_time = time.time() - start_time
                if elapsed_time < loop_interval:
                    time.sleep(loop_interval - elapsed_time)
                if elapsed_time > loop_interval:
                    print(f"Loop took too long: {elapsed_time:.2f} seconds")
            combat_mode_active = False
            print("Combat mode disabled. Gear/prayer hotkeys are inactive.")
        except Exception as e:
            print(f"An error occurred: {e}")
            combat_mode_active = False
            SCRIPT['state']['activated'] = False
            q.put({'type': 'close'})
            raise e

    thread1 = threading.Thread(target=run_combat_mode, args=(stop_event, q))
    thread1.daemon = True 
    thread1.start()

def on_death(stop_event: threading.Event):
    global combat_mode_active, AWAITING_MAGIC_XP_DROP
    if combat_mode_active:
        print("Combat mode disabled due to death.")
        combat_mode_active = False
        AWAITING_MAGIC_XP_DROP = True # Ready for next fight
        stop_event.set()

def on_low_health(ui: UIInteraction, stop_event: threading.Event):
    def consume_food():
        SCRIPT['state']['last_action_time'] = time.time()
        food_ated, health_ated = 0, 0
        if search_inventory("shark"):
            ui.click_inventory_slot(search_inventory("shark"))
            food_ated += 1; health_ated += 21; set_cooldown('eat')
        if search_inventory("karambwan"):
            ui.click_inventory_slot(search_inventory("karambwan"))
            food_ated += 1; health_ated += 18
        if search_inventory("brew") and search_inventory("restore"):
            ui.click_inventory_slot(search_inventory("brew") )
            food_ated += 1; health_ated += 7
        if food_ated == 0: return False
        if health_ated >= 41: print(f"You over-ate maybe with healing {health_ated} points")
        return True
    if not consume_food():
       panic_teleport(ui, stop_event)
       return True

def panic_teleport(ui: UIInteraction, stop_event):
    global combat_mode_active, SCRIPT, AWAITING_MAGIC_XP_DROP
    if not combat_mode_active: return
    teleport_slot = search_inventory("teleport")
    if teleport_slot:
        disable_user_mouse_input()
        ui.click_inventory_slot(teleport_slot)
        SCRIPT['state']["Warning"] = "Panic teleporting!"
        print("Panic teleporting and stopping combat loop.")
        enable_user_mouse_input()
        combat_mode_active = False
        AWAITING_MAGIC_XP_DROP = True # Ready for next fight
        stop_event.set()
        return True

def on_low_prayer(ui: UIInteraction, stop_event: threading.Event):
    def consume_potion():
        SCRIPT['state']['last_action_time'] = time.time()
        potion_slot = search_inventory("prayer") or search_inventory("restore")
        if potion_slot:
            ui.click_inventory_slot(potion_slot)
            return True
        return False
    if not consume_potion():
        panic_teleport(ui, stop_event)
        return True

def manual_blood_blitz():
    global SCRIPT, combat_mode_active
    original_pause = pyautogui.PAUSE
    pyautogui.PAUSE = SCRIPT['settings']['timings']
    SCRIPT['state']['last_action_time'] = time.time()
    try:
        if not combat_mode_active: return
        original_x, original_y = pyautogui.position()
        client = RuneLiteClientWindow()
        client.bring_to_foreground()
        humanizer = UIInteraction(HumanizedGridClicker(), None, client)
        pyautogui.press('F1')
        time.sleep(random.uniform(SCRIPT['settings']['timings'] * 1.6, SCRIPT['settings']['timings'] * 3.0) * SCRIPT['state']['timing_skill'])
        humanizer.click_magic_slot(SCRIPT["settings"]["manual_spell_slot"])
        pyautogui.press('F2') # Open inventory tab
        time.sleep(random.uniform(SCRIPT['settings']['timings'] * 1.6, SCRIPT['settings']['timings'] * 3.0) * SCRIPT['state']['timing_skill'])
        pyautogui.click(original_x, original_y)
    finally:
        pyautogui.PAUSE = original_pause
    return

def reset_combat_state():
    global SCRIPT
    if not combat_mode_active: return
    print("Resetting combat state...")
    SCRIPT['state']['start_time'] = time.time()
    SCRIPT['state']['time'] = 0
    SCRIPT['state']['phase'] = "UNKNOWN"
    SCRIPT['state']['manual_phase_index'] = 0
    SCRIPT['state']['Warning'] = "State Reset"

def confirm_phase():
    if not combat_mode_active: return
    SCRIPT['state']['manual_phase_index'] += 1
    if SCRIPT['state']['manual_phase_index'] == 1:
        SCRIPT['state']['start_time'] = time.time()
        SCRIPT['state']['time'] = 0
    current_style = SCRIPT['state'].get('phase', 'UNKNOWN')
    if PHASE_HANDLER.update(phase=current_style):
        print(f"Phase {SCRIPT['state']['manual_phase_index']} ({current_style}) confirmed.")
        SCRIPT['state']['matched_rotation'] = PHASE_HANDLER.matched_rotation
        next_phase_info = PHASE_HANDLER.fetch()
        if next_phase_info:
            if PHASE_HANDLER.wave_counted < len(next_phase_info['phases']):
                next_phase_style = next_phase_info['phases'][PHASE_HANDLER.wave_counted]
                SCRIPT['state']['next_phase_style'] = next_phase_style
                SCRIPT['state']['phase'] = next_phase_style
            else:
                SCRIPT['state']['next_phase_style'] = 'END'
                SCRIPT['state']['phase'] = 'END'
        else:
            SCRIPT['state']['next_phase_style'] = 'UNKNOWN'
            SCRIPT['state']['phase'] = 'UNKNOWN'
    else:
        print(f"Failed to confirm phase: {current_style}")

if __name__ == "__main__":
    def prompt_for_setup():
        print(f"[{SCRIPT["title"]} version: {SCRIPT["version"]}]")
        print(50*"=")
        if "y" in input(f"Setup {SCRIPT["title"]} (y/n):").lower():
            print(50*"=")
            for setup in SCRIPT["setup"]:
                print(setup["context"])
                for option, text in setup["options"].items(): print(f"{option}: {text}")
                choice = input(f"Choose an option (default: {setup["default"]}):") or setup["default"]
                SCRIPT["settings"][setup["setting"]] = setup["options"].get(str(choice), setup["options"][str(setup["default"])])
            print(50*"=")
            return True
        else:
            print(50*"=")
            print("Using default Configuration.")
            return True

    if "-y" not in sys.argv:
        if not prompt_for_setup():
            exit(0)

    load_humanizer_state() # Load humanizer state at startup

    for arg in sys.argv:
        if arg.startswith("--port="): SCRIPT["settings"]["api_port"] = int(arg.split("=")[1])
        elif arg.startswith("--switches="): SCRIPT["settings"]["switch_count"] = int(arg.split("=")[1])
        elif arg.startswith("--spell-num="): SCRIPT["settings"]["manual_spell_slot"] = int(arg.split("=")[1])
        elif arg.startswith("--spell-book="): SCRIPT["settings"]["manual_spell_book"] = arg.split("=")[1]
        elif arg.startswith("--render"): SCRIPT["settings"]["render_grids_and_clicks"] = "true" in arg.lower()
        elif arg.startswith("--timings="): SCRIPT["settings"]["timings"] = float(arg.split("=")[1])
        elif arg == "-no-chat-overlay": SCRIPT["settings"]["use_chatbox_overlay"] = False
        elif arg == "-no-wave-images": SCRIPT["settings"]["use_wave_images"] = False

    action_lock = threading.Lock()
    def run_action_once(target_func):
        if not action_lock.acquire(blocking=False):
            print("Action already in progress. Ignoring new request.")
            return
        try: target_func()
        finally: action_lock.release()

    def create_action_thread(target):
        if combat_mode_active:
            thread = threading.Thread(target=run_action_once, args=(target,))
            thread.daemon = True
            thread.start()

    keyboard.add_hotkey(SCRIPT['settings']['hk_magic'], lambda: create_action_thread(equip_mage))
    keyboard.add_hotkey(SCRIPT['settings']['hk_range'], lambda: create_action_thread(equip_range))
    keyboard.add_hotkey(SCRIPT['settings']['hk_melee'], lambda: create_action_thread(equip_melee))
    keyboard.add_hotkey("r", lambda: create_action_thread(manual_blood_blitz))
    keyboard.add_hotkey("space", lambda: create_action_thread(confirm_phase))
    keyboard.add_hotkey("ctrl+r", lambda: create_action_thread(reset_combat_state))

    print("Action hotkeys registered.")
    print("They will only function when combat mode is active.")

    gui_queue = queue.Queue()
    client = RuneLiteClientWindow()
    client_area_rect = client.get_client_rect()
    if not client_area_rect: exit("RuneLite client area not found. Exiting.")
        
    OVERLAY_OFFSET_X = 0
    OVERLAY_OFFSET_Y = 0

# ... (rest of the code)

    overlay = WindowOverlay(
        title="Zulrah Overlay",
        width=client_area_rect["w"],
        height=client_area_rect['h'],
        x=client_area_rect['left'] + OVERLAY_OFFSET_X,
        y=client_area_rect['top'] + OVERLAY_OFFSET_Y
    )
    api = RuneLiteAPI()
    items_db = OSRSItems()

    # Load chatbox image once
    chatbox_image_path = os.path.join(os.path.dirname(__file__), 'res', 'chatbox.png')
    try:
        CHATBOX_IMAGE = Image.open(chatbox_image_path).convert("RGBA")
        print(f"Chatbox image loaded successfully from {chatbox_image_path}")
    except Exception as e:
        print(f"Error loading chatbox image from {chatbox_image_path}: {e}")
        CHATBOX_IMAGE = None

    def process_gui_queue():
        global AWAITING_MAGIC_XP_DROP, PREVIOUS_MAGIC_XP, combat_mode_active

        # --- XP Drop Detection Logic ---
        if AWAITING_MAGIC_XP_DROP and not combat_mode_active:
            try:
                current_xp = api.get_skill_xp('magic')
                if current_xp is not None:
                    if PREVIOUS_MAGIC_XP == 0:
                        PREVIOUS_MAGIC_XP = current_xp
                    elif current_xp > PREVIOUS_MAGIC_XP:
                        print("Magic XP drop detected! Starting combat mode.")
                        PREVIOUS_MAGIC_XP = 0
                        # This is where the combat mode is now started
                        stop_event = threading.Event()
                        enable_combat_mode(stop_event, gui_queue)
                        combat_loop_manager.set_stop_event(stop_event)
            except Exception as e:
                print(f"Error checking XP: {e}")
        # --- End of XP Drop Logic ---

        try:
            # Process all available messages in the queue to update state
            while not gui_queue.empty():
                message = gui_queue.get_nowait()
                if message.get('type') == 'render':
                    # Just update the state, don't render yet
                    SCRIPT['state'] = message.get('state')
                elif message.get('type') == 'show_click':
                    pos = message.get('pos')
                    if pos:
                        overlay.show_click(pos)
                elif message.get('type') == 'close':
                    overlay.root.quit()
                    return
        except queue.Empty:
            pass

        # --- Drawing logic (happens every frame) ---
        client_area_rect = client.get_client_rect()
        overlay.clear() # Clear canvas to transparent
        if client_area_rect:
            overlay.set_position(client_area_rect['left'] + OVERLAY_OFFSET_X, client_area_rect['top'] + OVERLAY_OFFSET_Y)
            overlay.set_size(client_area_rect['w'], client_area_rect['h'])
            overlay.bring_to_foreground()
            # Render text based on the last known state
            render(client, overlay, api, items_db, CHATBOX_IMAGE)
        
        # Always update the overlay to draw highlights and push to screen
        overlay.update_overlay()
        
        # Reschedule the next frame
        overlay.root.after(10, process_gui_queue)

    combat_loop_manager = HotkeyManager(HOTKEY_START_FIGHT, f"ctrl+{HOTKEY_START_FIGHT}")

    def toggle_script_activation(stop_event: threading.Event):
        global SCRIPT, combat_mode_active, AWAITING_MAGIC_XP_DROP, PREVIOUS_MAGIC_XP
        if SCRIPT['state']['activated']:
            # Script is currently active, so deactivate it
            print("Deactivating script.")
            SCRIPT['state']['activated'] = False
            combat_mode_active = False # Ensure combat mode is also off
            AWAITING_MAGIC_XP_DROP = False # Reset XP waiting state
            PREVIOUS_MAGIC_XP = 0 # Reset XP
            overlay.root.withdraw() # Hide overlay
            stop_event.set() # Signal combat loop to stop if running
        else:
            # Script is currently inactive, so activate it
            print("Activating script. Waiting for combat to start.")
            SCRIPT['state']['activated'] = True
            AWAITING_MAGIC_XP_DROP = True
            overlay.root.deiconify() # Show overlay
            # The combat_mode_active and AWAITING_MAGIC_XP_DROP remain False until teleport click and XP drop

    combat_loop_manager.register_hotkeys(lambda stop_event: toggle_script_activation(stop_event))

    print("Press Ctrl+C in the console to exit.")
    
    def sigint_handler(sig, frame):
        print("\nInterrupted! Shutting down...")
        overlay.root.quit()

    signal.signal(signal.SIGINT, sigint_handler)

    # Start the global click detector
    CLICK_DETECTOR = ClickPhaseDetector(client)
    CLICK_DETECTOR.start()

    overlay.root.after(10, process_gui_queue)
    overlay.root.mainloop()

    # Stop the click detector on exit
    if CLICK_DETECTOR:
        CLICK_DETECTOR.stop()

    print("Script finished.")