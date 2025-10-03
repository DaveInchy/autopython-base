import pyautogui
import time
import threading
import keyboard
import json
import os
import sys
import random

from src.client_window import RuneLiteClientWindow
from src.ui_utils import UIInteraction, HumanizedGridClicker
from src.runelite_api import RuneLiteAPI
from src.osrs_items import OSRSItems

# --- Configuration ---
CLICK_DELAY_RANGE = (0.04, 0.08)  # Delay between clicks in seconds
HOTKEY_SWAP_GEAR = 'ctrl+alt+g'  # Hotkey to trigger gear swap
MAX_RETRIES = 2 # Maximum number of times to retry a failed swap

# --- Globals for managing state ---
stop_event = threading.Event()
execution_thread = None

LAST_SWAP_SCREENSHOT = None

# --- Initialize API and Item Database ---
api = RuneLiteAPI()
items_db = OSRSItems()

# --- Data Loading ---
def load_gear_setups():
    """Loads gear setups from the JSON file."""
    json_path = os.path.join(os.path.dirname(__file__), 'src', 'data', 'gear-setups.json')
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading gear setups: {e}. Using empty data.")
        return {}

GEAR_SETUPS = load_gear_setups()

def swap_gear(gear_setup: dict):
    """Swaps gear based on the provided setup and verifies the switch."""
    slots_to_click = gear_setup.get('slots_to_click', [])
    expected_gear_names = gear_setup.get('expected_gear', [])
    
    if not slots_to_click or not expected_gear_names:
        print("[GearSwapper] Invalid gear setup provided.")
        return

    # Convert item names to IDs
    expected_gear_ids = [items_db.get_item_id(name) for name in expected_gear_names]
    if None in expected_gear_ids:
        print(f"[GearSwapper] Could not find item IDs for all items in setup. Check names in gear-setups.json")
        return

    print(f"[GearSwapper] Initiating gear swap for setup '{gear_setup.get('name', 'Unknown')}'...")
    
    original_x, original_y = pyautogui.position()

    client = RuneLiteClientWindow()
    client.bring_to_foreground()
    time.sleep(0.1);

    pyautogui.press('f2')
    time.sleep(0.1);

    ui_interaction = UIInteraction(HumanizedGridClicker(), None, client)

    for attempt in range(MAX_RETRIES + 1):
        if stop_event.is_set():
            print("[GearSwapper] Gear swap interrupted.")
            break

        print(f"[GearSwapper] Swap attempt #{attempt + 1}")
        
        # Randomize click order
        if random.choice([True, False]):
            slots_to_click.reverse()

        for slot in slots_to_click:
            if stop_event.is_set():
                break
            print(f"[GearSwapper] Clicking inventory slot {slot}...")
            ui_interaction.click_inventory_slot(slot)
            time.sleep(random.uniform(*CLICK_DELAY_RANGE))

        # --- Screenshot Step ---
        win_rect = client.get_rect()
        if win_rect:
            # These values are from user-interface.json
            # Top-left of inventory grid, relative to bottom-right of window
            rel_x_start = 216 
            rel_y_start = 304
            inv_width = 4 * 42
            inv_height = 7 * 36

            abs_x_start = win_rect['left'] + win_rect['w'] - rel_x_start
            abs_y_start = win_rect['top'] + win_rect['h'] - rel_y_start

            screenshot_region = (abs_x_start, abs_y_start, inv_width, inv_height)

            global LAST_SWAP_SCREENSHOT
            LAST_SWAP_SCREENSHOT = pyautogui.screenshot(region=screenshot_region)
            print("[GearSwapper] Took a screenshot of the inventory and stored it in memory.")

        # --- Verification Step ---
        time.sleep(0.4) # Wait for equipment to update
        equipped_items = api.get_equipment()
        if equipped_items:
            equipped_ids = {item['id'] for item in equipped_items if item['id'] != -1}
            expected_ids = set(expected_gear_ids)

            if expected_ids.issubset(equipped_ids):
                print("[GearSwapper] Gear swap successful and verified.")
                pyautogui.moveTo(original_x, original_y)
                return
            else:
                missing_items = expected_ids - equipped_ids
                missing_names = [items_db.get_item_name(item_id) for item_id in missing_items]
                print(f"[GearSwapper] Verification failed. Missing items: {missing_names}")
                if attempt < MAX_RETRIES:
                    print("[GearSwapper] Retrying...")
                else:
                    print("[GearSwapper] Max retries reached. Gear swap failed.")
        else:
            print("[GearSwapper] Could not retrieve equipped items for verification.")

    pyautogui.moveTo(original_x, original_y)
    print("[GearSwapper] Gear swap process finished.")

def start_gear_swapper_loop(setup_name: str):
    global execution_thread
    if execution_thread and execution_thread.is_alive():
        print("[GearSwapper] Gear swapper is already running.")
        return

    gear_setup = GEAR_SETUPS.get(setup_name)
    if not gear_setup:
        print(f"[GearSwapper] Setup '{setup_name}' not found in gear-setups.json")
        return
    
    gear_setup['name'] = setup_name # Add name to setup for logging

    print(f"[GearSwapper] Hotkey Detected: Starting gear swap for setup '{setup_name}'.")
    stop_event.clear()
    execution_thread = threading.Thread(target=swap_gear, args=(gear_setup,))
    execution_thread.start()

if __name__ == "__main__":
    # --- Command-line argument for setup ---
    setup_to_use = 'melee' # Default setup
    if len(sys.argv) > 1:
        setup_to_use = sys.argv[1]

    if setup_to_use not in GEAR_SETUPS:
        print(f"Error: Setup '{setup_to_use}' not found in gear-setups.json.")
        print(f"Available setups: {list(GEAR_SETUPS.keys())}")
        sys.exit(1)

    print("--- Gear Swapper Script ---")
    print(f"Using gear setup: '{setup_to_use}'")
    print(f"Press {HOTKEY_SWAP_GEAR} to perform the gear swap.")
    print("Press Ctrl+C in this terminal to exit the script.")

    # Register hotkey
    keyboard.add_hotkey(HOTKEY_SWAP_GEAR, lambda: start_gear_swapper_loop(setup_to_use))

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\n[GearSwapper] Exiting script.")
        if execution_thread and execution_thread.is_alive():
            stop_event.set()