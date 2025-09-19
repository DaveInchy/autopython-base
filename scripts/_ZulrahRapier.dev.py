"""
Main script for the Zulrah helper.

This script continuously checks for nearby NPCs and prints their information
to the console for debugging purposes.
"""

import json
import time
import threading
import sys

# pip packages/module
import pyautogui # type: ignore
from pynput import mouse  # type: ignore # Add this line
import keyboard # For scoped hotkeys

# --- OSRS Macro SDK Imports ---
from src import game_screen
from src.graphics.window_overlay import WindowOverlay, DrawCursorPosition
from src.client_window import RuneLiteClientWindow
from src.ui_utils import HumanizedGridClicker, Inventory as ResizableInventoryGrid, Prayer as ResizablePrayerGrid, UIInteraction
from src.runelite_api import RuneLiteAPI
from src.hotkeys import HotkeyManager
from src.osrs_items import OSRSItems


combat_mode_active = False

SCRIPT={
    "version": "1.3",
    "title": "ZulrahRapier",
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
        "switch_speed": 0.0025,
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
        "enable_smart_ticks": False, #TODO, like when you dont need to pray or its advised to already use ranged to kill the implings or you just wanna know when the attacks switch for melee, when jad is activated, when rotations have been reset etc etc etc.... cuz each rotation is the same. zulrah isnt even alive, its just a puppet that does stuff because the gnome king is using dark magics to try and kill us so we dont know he went to epsteins island...
        "use_hotkeys": True,
        "enable_extra_hotkeys": False, #TODO, Like healing, teleport, phase confirm
        "use_overlays": False, #TODO
        "use_phase_counter": True,
        "use_jad_indicator": True,
        "use_performance_mode": True,
        "mode": "hotkeys",
        "manual_spell_slot": 1,
        "manual_spell_book": "ancient",
        "render_grids_and_clicks": False,
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
    ]
}

class RotationManager:
    def __init__(self):
        # Hardcoded phase data, now internal to the class or loaded once.
        # This function encapsulates the data for clarity.
        self._ZULRAH_DATA = self._get_zulrah_rotations_data()

        self.current_zulrah_history = []  # Stores observed phases (NPC ID and position)
        self.identified_rotation = None     # Stores the confirmed rotation name (e.g., "rotation_1")

        # Reverse maps coordinates to keys for efficient lookup
        self._pos_key_to_coords = {
            "ZulrahPosCenter": {"x": 6720, "y": 7616},
            "ZulrahPosWest": {"x": 8000, "y": 7360},
            "ZulrahPosEast": {"x": 5440, "y": 7360},
            "ZulrahPosNorth": {"x": 6720, "y": 6208}
        }
        self._coords_to_pos_key = {
            (v["x"], v["y"]): k for k, v in self._pos_key_to_coords.items()
        }

        self._player_tile_key_to_coords = {
            "SWCornerTile": {"x": 7488, "y": 7872},
            "SWCornerTileMelee": {"x": 7232, "y": 8000},
            "WPillar": {"x": 7232, "y": 7232},
            "WPillarN": {"x": 7232, "y": 7104},
            "EPillar": {"x": 6208, "y": 7232},
            "EPillarN": {"x": 6208, "y": 7104},
            "SECornerTile": {"x": 6208, "y": 8000},
            "SECornerTileMelee": {"x": 5952, "y": 7744},
            "Middle": {"x": 6720, "y": 6848}
        }

    def _get_zulrah_rotations_data(self) -> dict:
        """
        Hardcoded Zulrah rotation data.
        """
        return {
            "types": {
                2042: {
                    "name": "Green",
                    "style": "RANGE", # The original Java code mapped 2042 (Green) to P_FROM_MISSILES, indicating RANGE.
                    "rgb": [
                        {"min": [82-4, 85-4, 30-4], "max": [82+4, 85+4, 30+4]}, # Example placeholder, requires tuning
                        {"min": [196-4, 202-4, 133-4], "max": [196+4, 202+4, 133+4]},
                        {"min": [163-4, 182-4, 22-4], "max": [163+4, 182+4, 22+4]},
                        {"min": [146-4, 149-4, 56-4], "max": [146+4, 149+4, 56+4]},
                        {"min": [128-4, 137-4, 31-4], "max": [128+4, 137+4, 31+4]},
                        {"min": [33-4, 39, 23-4], "max": [33+4, 39+4, 23+4]}
                    ]
                },
                2043: {
                    "name": "Red",
                    "style": "MELEE",
                    "rgb": [
                        {"min": [86-4, 68-4, 63-4], "max": [86+4, 68+4, 63+4]}, # Example placeholder, requires tuning
                        {"min": [205-4, 98-4, 27-4], "max": [205+4, 98+4, 27+4]},
                        {"min": [164-4, 74-4, 27-4], "max": [164+4, 74+4, 27+4]},
                        {"min": [37-4, 30-4, 26-4], "max": [37+4, 30+4, 26+4]}
                    ]
                },
                2044: {
                    "name": "Blue",
                    "style": "MAGIC", # The original Java code mapped 2044 (Blue) to P_FROM_MAGIC, indicating MAGIC.
                    "rgb": [
                        {"min": [11-4, 46-4, 56-4], "max": [11+4, 46+4, 56+4]}, # Example placeholder, requires tuning
                        {"min": [12-4, 87-4, 87-4], "max": [28+4, 192+4, 160+4]},
                        {"min": [96-4, 14-4, 149-4], "max": [118+4, 21+4, 185+4]},
                        {"min": [96-4, 14-4, 149-4], "max": [96+4, 14+4, 149+4]},
                        {"min": [12-4, 87-4, 87-4], "max": [12+4, 87+4, 87+4]}
                    ]
                },
            },
            "rotations": {
                "rotation_1": {
                    "types": [2042, 2043, 2044, 2042, 2044, 2043, 2042, 2044, 2042, 2043],
                    "positions": [
                        "ZulrahPosCenter", "ZulrahPosCenter", "ZulrahPosCenter", "ZulrahPosEast",
                        "ZulrahPosNorth", "ZulrahPosCenter", "ZulrahPosWest", "ZulrahPosNorth",
                        "ZulrahPosEast", "ZulrahPosCenter"
                    ],
                    "player_tiles": [
                        "SWCornerTile", "SWCornerTile", "SWCornerTile", "EPillar",
                        "EPillarN", "EPillar", "Middle", "EPillar",
                        "EPillar", "SWCornerTile"
                    ],
                    "jad": 9,
                    "ticks": [28, 20, 18, 28, 39, 22, 20, 36, 48, 20] # Adjusted to be 0-indexed for phase 0 to N-1
                },
                "rotation_2": {
                    "types": [2042, 2043, 2044, 2042, 2043, 2044, 2042, 2044, 2042, 2043],
                    "positions": [
                        "ZulrahPosCenter", "ZulrahPosCenter", "ZulrahPosCenter", "ZulrahPosNorth",
                        "ZulrahPosCenter", "ZulrahPosEast", "ZulrahPosNorth", "ZulrahPosNorth",
                        "ZulrahPosEast", "ZulrahPosCenter"
                    ],
                    "player_tiles": [
                        "SWCornerTile", "SWCornerTile", "SWCornerTile", "EPillar",
                        "EPillar", "EPillar", "WPillar", "WPillarN",
                        "EPillar", "SWCornerTile"
                    ],
                    "jad": 9,
                    "ticks": [28, 20, 17, 39, 22, 20, 28, 36, 48, 21] # Adjusted to be 0-indexed for phase 0 to N-1
                },
                "rotation_3": {
                    "types": [2042, 2042, 2043, 2044, 2042, 2044, 2042, 2042, 2044, 2042, 2044],
                    "positions": [
                        "ZulrahPosCenter", "ZulrahPosWest", "ZulrahPosCenter", "ZulrahPosEast",
                        "ZulrahPosNorth", "ZulrahPosWest", "ZulrahPosCenter", "ZulrahPosEast",
                        "ZulrahPosCenter", "ZulrahPosWest", "ZulrahPosCenter"
                    ],
                    "player_tiles": [
                        "SWCornerTile", "SWCornerTile", "SECornerTile", "EPillar",
                        "WPillar", "WPillar", "EPillar", "EPillar",
                        "WPillar", "WPillar", "SWCornerTile"
                    ],
                    "jad": 10,
                    "ticks": [28, 30, 40, 20, 20, 20, 25, 20, 36, 35, 18] # Adjusted to be 0-indexed for phase 0 to N-1
                },
                "rotation_4": {
                    "types": [2042, 2044, 2042, 2044, 2043, 2042, 2042, 2044, 2042, 2044, 2042, 2044],
                    "positions": [
                        "ZulrahPosCenter", "ZulrahPosWest", "ZulrahPosNorth", "ZulrahPosEast",
                        "ZulrahPosCenter", "ZulrahPosWest", "ZulrahPosNorth", "ZulrahPosEast",
                        "ZulrahPosCenter", "ZulrahPosCenter", "ZulrahPosWest", "ZulrahPosCenter"
                    ],
                    "player_tiles": [
                        "SWCornerTile", "SWCornerTile", "EPillar", "EPillar",
                        "WPillar", "WPillar", "WPillar", "EPillar",
                        "WPillar", "WPillar", "WPillar", "SWCornerTile"
                    ],
                    "jad": 11,
                    "ticks": [28, 36, 24, 30, 28, 17, 34, 33, 20, 27, 29, 18] # Adjusted to be 0-indexed for phase 0 to N-1
                }
            }
        }

    def _get_position_key(self, local_point_x: int, local_point_y: int) -> str | None:
        """
        Reverse-maps LocalPoint coordinates to their string key in the zulrah_positions.
        """
        return self._coords_to_pos_key.get((local_point_x, local_point_y))

    def reset(self):
        """Resets the tracker for a new Zulrah fight."""
        self.current_zulrah_history = []
        self.identified_rotation = None

    def add_observed_phase(self, zulrah_id: int, local_point_x: int, local_point_y: int):
        """
        Adds a new observed Zulrah phase to the history.

        Args:
            zulrah_id: The NPC ID of Zulrah (e.g., 2042, 2043, 2044).
            local_point_x: The X coordinate of Zulrah's local position.
            local_point_y: The Y coordinate of Zulrah's local position.
        """
        self.current_zulrah_history.append({
            "id": zulrah_id,
            "position": {"x": local_point_x, "y": local_point_y}
        })

    def get_next_zulrah_phase_info(self) -> dict:
        """
        Determines the current Zulrah rotation, phase index, and the *next* expected
        Zulrah combat style and player position.

        Returns:
            A dictionary containing:
                "identified_rotation": The name of the identified rotation (e.g., "rotation_1"), or None.
                "current_phase_index": The 0-indexed position of the *last observed* phase in the rotation.
                "next_combat_style": The combat style of the *next* Zulrah phase ("RANGE", "MELEE", "MAGIC"), or None.
                "next_zulrah_position": Dictionary {"x": int, "y": int} of the next Zulrah position, or None.
                "next_player_tile": Dictionary {"x": int, "y": int} of the next recommended player tile, or None.
                "next_phase_ticks": The tick duration of the *upcoming* phase, or None.
                "is_last_phase_in_rotation": True if the last observed phase was the final one in its rotation.
                "possible_rotations": List of rotation names that still match (useful if not uniquely identified).
                "error": An error message if something went wrong, otherwise None.
        """
        if not self.current_zulrah_history:
            return {
                "identified_rotation": None,
                "current_phase_index": -1,
                "next_combat_style": None,
                "next_zulrah_position": None,
                "next_player_tile": None,
                "next_phase_ticks": None,
                "is_last_phase_in_rotation": False,
                "possible_rotations": list(self._ZULRAH_DATA["rotations"].keys()),
                "error": None
            }

        processed_history = []
        for obs in self.current_zulrah_history:
            pos_key = self._get_position_key(obs["position"]["x"], obs["position"]["y"])
            if pos_key is None:
                return {
                    "identified_rotation": None,
                    "current_phase_index": -1,
                    "next_combat_style": None,
                    "next_zulrah_position": None,
                    "next_player_tile": None,
                    "next_phase_ticks": None,
                    "is_last_phase_in_rotation": False,
                    "possible_rotations": [],
                    "error": f"Observed Zulrah position {obs['position']} not found in known positions."
                }
            processed_history.append({"id": obs["id"], "position_key": pos_key})

        num_observed_phases = len(processed_history)
        
        # Determine which rotations to check: all if not identified, else only the identified one.
        rotations_to_check = [self.identified_rotation] if self.identified_rotation else self._ZULRAH_DATA["rotations"].keys()
        
        matching_rotations = []

        for rotation_name in rotations_to_check:
            rotation_data = self._ZULRAH_DATA["rotations"].get(rotation_name)
            if not rotation_data:
                continue

            # Check if observed history can possibly match this rotation's length
            if num_observed_phases > len(rotation_data["types"]):
                continue

            is_match = True
            for i in range(num_observed_phases):
                observed_type = processed_history[i]["id"]
                observed_pos_key = processed_history[i]["position_key"]
                
                expected_type = rotation_data["types"][i]
                expected_pos_key = rotation_data["positions"][i]

                if observed_type != expected_type or observed_pos_key != expected_pos_key:
                    is_match = False
                    break
            
            if is_match:
                matching_rotations.append(rotation_name)

        # Update identified_rotation if a unique match is found
        if len(matching_rotations) == 1:
            self.identified_rotation = matching_rotations[0]
        elif len(matching_rotations) == 0:
            return {
                "identified_rotation": None,
                "current_phase_index": num_observed_phases - 1,
                "next_combat_style": None,
                "next_zulrah_position": None,
                "next_player_tile": None,
                "next_phase_ticks": None,
                "is_last_phase_in_rotation": False,
                "possible_rotations": [],
                "error": "Observed sequence does not match any known rotation."
            }
        # If multiple matches, self.identified_rotation remains what it was, or None if still ambiguous.

        current_phase_index = num_observed_phases - 1 # 0-indexed position of the *last observed* phase
        
        next_combat_style = None
        next_zulrah_position = None
        next_player_tile = None
        next_phase_ticks = None
        is_last_phase = False

        if self.identified_rotation:
            rotation_data = self._ZULRAH_DATA["rotations"][self.identified_rotation]
            
            # Check if the *current observed phase* is the final phase in the rotation.
            if current_phase_index >= len(rotation_data["types"]) - 1:
                is_last_phase = True
                # No next phase info to provide as the rotation is complete.
            else:
                next_phase_index = current_phase_index + 1
                next_zulrah_type_id = rotation_data["types"][next_phase_index]
                
                # Get combat style from zulrah_forms
                next_combat_style = self._ZULRAH_DATA["types"].get(next_zulrah_type_id, {}).get("style")

                # Get next Zulrah position
                next_zulrah_pos_key = rotation_data["positions"][next_phase_index]
                next_zulrah_position = self._pos_key_to_coords.get(next_zulrah_pos_key)

                # Get next player tile
                next_player_tile_key = rotation_data["player_tiles"][next_phase_index]
                next_player_tile = self._player_tile_key_to_coords.get(next_player_tile_key)

                # Get the ticks for the *upcoming* phase
                if next_phase_index < len(rotation_data["ticks"]):
                    next_phase_ticks = rotation_data["ticks"][next_phase_index]
                
        return {
            "identified_rotation": self.identified_rotation,
            "current_phase_index": current_phase_index,
            "next_combat_style": next_combat_style,
            "next_zulrah_position": next_zulrah_position,
            "next_player_tile": next_player_tile,
            "next_phase_ticks": next_phase_ticks,
            "is_last_phase_in_rotation": is_last_phase,
            "possible_rotations": matching_rotations,
            "error": None
        }
    
global PHASE_HANDLER
PHASE_HANDLER: RotationManager = RotationManager()

# --- Zulrah Constants ---
ZULRAH_IDS = [2042, 2043, 2044] # Green, Red, Blue,
ZULRAH_TYPES = ["RANGE", "MELEE", "MAGE"]
# but theres also a green one that does mage type damage

ZULRAH_PHASE_MAP = {
    1: {"type": "RANGE", "gear": "MAGE"},
    2: {"type": "MELEE", "gear": "RANGE"},
    3: {"type": "MAGE", "gear": "RANGE"},
}

ZULRAH_PHASE_PRAYER = {
    1: {"type": "RANGE", "offense": 21, "protect": 18},
    2: {"type": "MELEE", "offense": 20, "protect": 19},
    3: {"type": "MAGE", "offense": 20, "protect": 17},
}

# --- Configuration ---
HOTKEY_START_LOOP = 'ctrl+shift+z'
HOTKEY_STOP_LOOP = 'ctrl+z'
HOTKEY_SWITCH_GEAR_FOR_MAGE = 'q'
HOTKEY_SWITCH_GEAR_FOR_RANGE = 'w'
HOTKEY_SWITCH_GEAR_FOR_MELEE = 'e'
HOTKEY_CONFIRM_PHASE=' ';
HOTKEY_START_FIGHT='.';

LOOP_INTERVAL = 1.0 # Seconds between checks

global CURRENT_EQUIPPED_STYLE
# global ACTION_QEUE
# ACTION_QEUE=[]



def detect_and_update_phase(client: RuneLiteClientWindow, screen: game_screen.GameScreen):
    """
    Detects the current Zulrah phase by searching for its colors in the full client window
    and calculating a confidence score for each phase.
    """
    global PHASE_HANDLER

    client_rect = client.get_rect()
    if not client_rect:
        print("Client window not found.")
        return

    full_window_region = (
        client_rect['left'],
        client_rect['top'],
        client_rect['right'],
        client_rect['bottom']
    )

    phase_scores = {}

    # Iterate over each type of Zulrah (color)
    for npc_id, type_data in PHASE_HANDLER._ZULRAH_DATA["types"].items():
        match_count = 0
        total_ranges = len(type_data["rgb"])

        # Check how many of the color ranges for this phase are found
        for color_range in type_data["rgb"]:
            min_vals = color_range["min"]
            max_vals = color_range["max"]
            
            if screen.find_color(color=(0,0,0), spectrum_range=[min_vals[0], min_vals[1], min_vals[2], max_vals[0], max_vals[1], max_vals[2]], region=full_window_region):
                match_count += 1
        
        # Calculate confidence score
        score = (match_count / total_ranges) * 100 if total_ranges > 0 else 0
        phase_scores[type_data['name']] = score

    # Find the phase with the highest score
    if not phase_scores:
        return

    best_phase_name = max(phase_scores, key=phase_scores.get)
    best_score = phase_scores[best_phase_name]

    # Confidence threshold to consider a detection valid
    DETECTION_THRESHOLD = 50.0

    if best_score >= DETECTION_THRESHOLD:
        print(f"Phase Detected: {best_phase_name} (Confidence: {best_score:.2f}%)")
        # Position is unknown, so we cannot update the rotation manager yet.
    else:
        # This is useful for debugging color ranges
        print(f"No phase detected above {DETECTION_THRESHOLD}%. Best guess: {best_phase_name} ({best_score:.2f}%)")

def get_weapon_style_from_slot_one(api: RuneLiteAPI, items_db: OSRSItems) -> str:
    """
    Checks the item in inventory slot one and determines its combat style.
    """
    inventory = api.get_inventory()
    if not inventory or len(inventory) == 0:
        return "UNKNOWN"

    slot_one_item = inventory[0]
    item_id = slot_one_item.get('id')

    if item_id == -1:
        return "EMPTY"

    item_name = items_db.get_item_name(item_id)
    magic_ids = [12903, 12904, 12905, 27676, 27679] # g.e. manual lookup for toxic staff
    ranged_ids = [28869]
    if not item_id in magic_ids and not item_id in ranged_ids:
        if not item_name:
            return "UNKNOWN"
    
    if item_name:
        item_name = item_name.lower()
    else:
        item_name = "dwarf remains"
    
    if "staff" in item_name or "wand" in item_name or "sceptre" in item_name or "trident" in item_name or item_id in magic_ids:
        return "MAGE"
    if "bow" in item_name or "blowpipe" in item_name or "crossbow" in item_name or "dart" in item_name or "thrownaxe" in item_name or "knife" in item_name or item_id in ranged_ids:
        return "RANGE"

    return "UNKNOWN"

# def get_snake_style() -> str:
#     """
#     Placeholder function to determine the snake's current style.
#     In a real implementation, this would use image recognition or other methods.
#     For now, it randomly returns "MAGE" or "RANGE".
#     """
#     import random
#     return random.choice(["MAGE", "RANGE"])

def disable_user_mouse_input():
    """
    Disable user mouse input temporarily to prevent interference.
    """
    # print("User mouse input disabled temporarily.")
    pyautogui.FAILSAFE = False  # Disable failsafe for uninterrupted operation
    
    # Backup method: Block all input on Windows
    try:
        import ctypes
        ctypes.windll.user32.BlockInput(True)
    except:
        pass

def enable_user_mouse_input():
    """
    Re-enable user mouse input after being disabled.
    """
    # print("User mouse input re-enabled.")
    pyautogui.FAILSAFE = True  # Re-enable failsafe
    
    # Re-enable input if blocked
    try:
        import ctypes
        ctypes.windll.user32.BlockInput(False)
    except:
        pass

def search_inventory(name="Shark") -> int | None:
    """
    Get the inventory slot of a specific item by name.
    """
    
    api = RuneLiteAPI()

    inventory = api.get_inventory()
    if not inventory:
        return None
    for index, item in enumerate(inventory):
        item_name = item.get('name', '').lower()
        if name.lower() in item_name:
            return 1+index
    
    return None

def equip_next_gear(humanizer):
    """
    Example function to equip mage gear by clicking specific inventory slots.
    Adjust slot numbers as needed based on your inventory layout.
    """

    # Disable user mouse input to prevent interference
    disable_user_mouse_input()

    pyautogui.press('F2')  # Open Inventory

    # Example slot numbers for mage gear (adjust as necessary)
    def get_inventory_slots():
        # based on the setup settings, determine how many slots to use
        len = int(SCRIPT["settings"]["switch_count"])
        return [1, 2, 5, 6, 9, 10, 13, 14, 17, 18, 21, 22, 25, 26][:len]
    
    for slot in get_inventory_slots():
        humanizer.click_inventory_slot(slot)
    
    enable_user_mouse_input()

def equip_gear(type):
    """
    Equip gear based on the current equipped style.
    """
    # get current mouse position
    original_x, original_y = pyautogui.position()

    client = RuneLiteClientWindow()
    client.bring_to_foreground()

    ui_interaction = UIInteraction(HumanizedGridClicker(), None, client)
    
    api = RuneLiteAPI()
    items_db = OSRSItems()

    weapon_style = get_weapon_style_from_slot_one(api, items_db)
    CURRENT_EQUIPPED_STYLE = (weapon_style == "MAGE" and "RANGE" or "MAGE")

    # select a prayer based on the type
    if type == "MAGE":
        pyautogui.press('F4')
        ui_interaction.click_prayer_slot(17)
        if CURRENT_EQUIPPED_STYLE == "MAGE":
            equip_next_gear(ui_interaction)
            pyautogui.press('F4')
            ui_interaction.click_prayer_slot(20)
        # pyautogui.press('F4')  # Stay on prayer book for prayer switches
        pyautogui.press('F2')  # Close Prayers into Inventory

    elif type == "RANGE":
        pyautogui.press('F4')
        ui_interaction.click_prayer_slot(18)
        if CURRENT_EQUIPPED_STYLE == "RANGE":
            equip_next_gear(ui_interaction)
            pyautogui.press('F4')
            ui_interaction.click_prayer_slot(21)
        pyautogui.press('F2')  # Close Prayers into Inventory

    elif type == "MELEE":

        # Protect from Melee doesnt have a use. you will need to dodge manually, so would only use this to make sure we have the right gear equipped
        if CURRENT_EQUIPPED_STYLE == "MAGE":
            equip_next_gear(ui_interaction)
            pyautogui.press('F4')
            ui_interaction.click_prayer_slot(20)
        pyautogui.press('F2')  # Close Prayers into Inventory
    
    # move mouse back to original position
    pyautogui.moveTo(original_x, original_y)

    return
        

def equip_range():
    equip_gear(type="RANGE")

def equip_melee():
    equip_gear(type="MELEE")

def equip_mage():
    equip_gear(type="MAGE")

def update(ui: UIInteraction, client: RuneLiteClientWindow=None, api: RuneLiteAPI=None, stop_event: threading.Event=None):
    # process_q()
    # get mouse position
    original_x, original_y = pyautogui.position()

    MIN_HP=45
    MIN_PRAY=10
    
    global PHASE_HANDLER
    
    health, prayer = api and (api.get_health_points(), api.get_prayer_points())

    if health:
        if health <= MIN_HP:
    
            disable_user_mouse_input()
            ui.client_window.bring_to_foreground()
            pyautogui.press('F2')
            on_low_health(ui, stop_event)
            pyautogui.moveTo(original_x, original_y)
    
            enable_user_mouse_input()
    else:
        print("No health data")
    
    if prayer:
        if prayer <= MIN_PRAY:
    
            disable_user_mouse_input()
            ui.client_window.bring_to_foreground()
            pyautogui.press('F2')
            on_low_prayer(ui)
            pyautogui.moveTo(original_x, original_y)
    
            enable_user_mouse_input()
    else:
        print("No prayer data")
    
    # phase = PHASE_HANDLER.get_next_zulrah_phase_info()
    # print(phase)
    # if phase:
    #    if phase["error"]:
    #        print(f"Error: {phase.error}")
    #    else:
    #        print(f"Current Rotation: {phase["identified_rotation"]}")
    # if the ticks have gone by, wait for user (not machine) click, use color_utils to then match it with a color spectrum for each boss phase. ase soon as its confirmed. you can then calculate the next phase and add a progress point because of the ticks
    

def enable_combat_mode(stop_event: threading.Event):
    global combat_mode_active
    if combat_mode_active:
        return  # Already running
    combat_mode_active = True
    print("Combat mode enabled. Gear/prayer hotkeys are active.")
    
    try:
        # Start by enabling magic prayer, assuming you press W to start against the green snake, assures youre really ready
        # Reset the state machine to its default for phase 1
        # Start a loop with 0.4 seconds interval, make sure that we have a onGameTick(count=int) method so we can just cycle the start to end with each tich since the rotations themselves are static and run all on programmed timings etc.
        client: RuneLiteClientWindow = RuneLiteClientWindow()
        ui = UIInteraction(HumanizedGridClicker(), None, client)
        api = RuneLiteAPI()

        loop_interval = 0.4 # seconds
        while not stop_event.is_set():
            start_time = time.time()
            
            update(ui, client, api, stop_event)

            # Wait for the next iteration
            end_time = time.time()
            elapsed_time = end_time - start_time
            sleep_time = loop_interval - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)
    finally:
        combat_mode_active = False
        print("Combat mode disabled. Gear/prayer hotkeys are inactive.")
        

def on_same_health(time=5000):
    pass

def on_death():
    pass

def on_low_health(ui: UIInteraction, stop_event: threading.Event):

    def consume_food():
        food_ated=0

        # find a food and click it
        primary = search_inventory("shark")
        if primary:
            print(f"Found food in slot {primary}")
            ui.click_inventory_slot(primary)
            food_ated+=1
        
        combo_food = search_inventory("karambwan")
        if combo_food:
            print(f"Found combo food in slot {combo_food}")
            ui.click_inventory_slot(combo_food)
            food_ated+=1

        if food_ated==0:
            print("No food ated")
            return False
        
        return True

    ated = consume_food()

    if not ated:
        teleport = search_inventory("teleport")
        if teleport:
            print(f"Found teleport in slot {teleport}")
            ui.click_inventory_slot(teleport)
            print("Panic teleporting and stopping combat loop.")
            stop_event.set()
            return True

def on_low_prayer(ui):

    def consume_potion():
        # find a potion and click it
        potion = search_inventory("prayer") or search_inventory("restore")
        if potion:
            print(f"Found potion in slot {potion}")
            ui.click_inventory_slot(potion)
            return True
        return False
    
    drinked = consume_potion()
    if not drinked:
        print("No potion drinked")

# @TODO: Save and Load Settings

def manual_blood_blitz():
    """
    Manually trigger blood blitz.
    """
    global combat_mode_active
    if not combat_mode_active:
        return

    # get current mouse position
    original_x, original_y = pyautogui.position()

    client = RuneLiteClientWindow()
    client.bring_to_foreground()

    _static_local_position_from_bottomright_in_runelite_window = [193, 146]
    win_rect = client.get_rect()
    if not win_rect:
        print("RuneLite window not found, cannot cast.")
        return
    
    x1 = win_rect['left']
    y1 = win_rect['top']
    w = win_rect['w']
    h = win_rect['h']
    
    abs_x = x1 + w - _static_local_position_from_bottomright_in_runelite_window[0]
    abs_y = y1 + h - _static_local_position_from_bottomright_in_runelite_window[1]

    # select blood blitz
    pyautogui.press('F1')
    
    # move mouse to blood blitz
    pyautogui.click(abs_x, abs_y)

    pyautogui.press('F2')

    # move mouse back to original position
    pyautogui.moveTo(original_x, original_y)
    time.sleep(0.025)
    pyautogui.click(original_x, original_y)

if __name__ == "__main__":

    # hotkey_manager = HotkeyManager(HOTKEY_START_LOOP, HOTKEY_STOP_LOOP)
    # hotkey_manager.register_hotkeys(npc_debug_loop)

    def prompt_for_setup():
        """
        Prompt the user for configuration options.
        """
        print(f"[{SCRIPT["title"]} version: {SCRIPT["version"]}]")
        print(50*"=")
        choice = input(f"Setup {SCRIPT["title"]} (y/n):")

        if "y" in choice.lower():

            print(50*"=")
            
            for setup in SCRIPT["setup"]:
                print(setup["context"])
                for option in setup["options"]:
                    print(f"{option}: {setup["options"][option]}")
                choice = input(f"Choose an option (default: {setup["default"]}): ")
                if choice == "":
                    choice = setup["default"]
                SCRIPT["settings"][setup["setting"]] = setup["options"][choice]

            print(50*"=")
            # Manual Spell Slot
            choice = input(f"Enter manual spell slot (default: {SCRIPT['settings']['manual_spell_slot']}): ")
            if choice.isdigit():
                SCRIPT["settings"]["manual_spell_slot"] = int(choice)
            
            print(50*"=")
            # Manual Spell Book
            choice = input(f"Enter manual spell book (ancient/standard) (default: {SCRIPT['settings']['manual_spell_book']}): ")
            if choice in ["ancient", "standard"]:
                SCRIPT["settings"]["manual_spell_book"] = choice

            print(50*"=")
            # Render Grids and Clicks
            choice = input(f"Render debug grids and clicks (true/false) (default: {SCRIPT['settings']['render_grids_and_clicks']}): ")
            if choice.lower() in ["true", "false"]:
                SCRIPT["settings"]["render_grids_and_clicks"] = choice.lower() == "true"

            print(50*"=")
            print("Configuration Done!")
            return True

        else:
            print(50*"=")
            print("Using default Configuration.")
            return True

    prompt=True;
    switches=5;
    for k in sys.argv:
        if "--port=" in k:
            v = k.split("=")[1]
            SCRIPT["settings"]["api_port"] = v
            continue
        if "--switches=" in k:
            v = k.split("=")[1]
            switches = int(v)
            # set single setting
            SCRIPT["settings"]["switch_count"] = switches
            continue
        if k == "-y":
            prompt=False
            continue
        if "--manual-spell-slot=" in k:
            v = k.split("=")[1]
            SCRIPT["settings"]["manual_spell_slot"] = int(v)
            continue
        if "--manual-spell-book=" in k:
            v = k.split("=")[1]
            SCRIPT["settings"]["manual_spell_book"] = v
            continue
        if "--render-grids-and-clicks=" in k:
            v = k.split("=")[1]
            SCRIPT["settings"]["render_grids_and_clicks"] = v.lower() == "true"
            continue
    
    if prompt==True:
        result = prompt_for_setup();
        if result==False:
            exit(0)

    # --- Hotkey Registration ---

    # Scoped action hotkeys. They only work if combat_mode_active is True.
    def scoped_equip_mage():
        if combat_mode_active:
            equip_mage()

    def scoped_equip_range():
        if combat_mode_active:
            equip_range()

    def scoped_equip_melee():
        if combat_mode_active:
            equip_melee()
            
    def scoped_manual_blood_blitz():
        if combat_mode_active:
            manual_blood_blitz()

    keyboard.add_hotkey(HOTKEY_SWITCH_GEAR_FOR_MAGE, scoped_equip_mage)
    keyboard.add_hotkey(HOTKEY_SWITCH_GEAR_FOR_RANGE, scoped_equip_range)
    keyboard.add_hotkey(HOTKEY_SWITCH_GEAR_FOR_MELEE, scoped_equip_melee)
    keyboard.add_hotkey("r", scoped_manual_blood_blitz)

    print(f"Action hotkeys ('{HOTKEY_SWITCH_GEAR_FOR_MAGE}', '{HOTKEY_SWITCH_GEAR_FOR_RANGE}', '{HOTKEY_SWITCH_GEAR_FOR_MELEE}', 'r') are registered.")
    print("They will only function when combat mode is active.")

    # Main combat loop manager
    combat_loop_manager = HotkeyManager(HOTKEY_START_FIGHT, f"ctrl+{HOTKEY_START_FIGHT}")
    combat_loop_manager.register_hotkeys(enable_combat_mode)

    # Keep the script running until Ctrl+C is pressed
    combat_loop_manager.wait_for_exit()