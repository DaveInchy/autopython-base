"""
Main script for the Zulrah helper.

This script continuously checks for nearby NPCs and prints their information
to the console for debugging purposes.
"""

import time
import threading

# --- OSRS Macro SDK Imports ---
from src.graphics.window_overlay import WindowOverlay, DrawCursorPosition
from src.client_window import RuneLiteClientWindow
from src.ui_utils import HumanizedGridClicker, Inventory as ResizableInventoryGrid, Prayer as ResizablePrayerGrid, UIInteraction
from src.runelite_api import RuneLiteAPI
from src.hotkeys import HotkeyManager
from src.osrs_items import OSRSItems

import pyautogui

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

LOOP_INTERVAL = 1.0 # Seconds between checks

global CURRENT_EQUIPPED_STYLE

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
    if not item_name:
        return "UNKNOWN"

    item_name = item_name.lower()
    if "staff" in item_name or "wand" in item_name or "sceptre" in item_name or "trident" in item_name:
        return "MAGE"
    if "bow" in item_name or "blowpipe" in item_name or "crossbow" in item_name or "dart" in item_name or "thrownaxe" in item_name or "knife" in item_name:
        return "RANGE"

    return "UNKNOWN"

def get_snake_style() -> str:
    """
    Placeholder function to determine the snake's current style.
    In a real implementation, this would use image recognition or other methods.
    For now, it randomly returns "MAGE" or "RANGE".
    """
    import random
    return random.choice(["MAGE", "RANGE"])

def click_inventory_slot(slot):
    """
    Click a specific inventory slot (1-28) in resizable mode.
    """
    client = RuneLiteClientWindow()
    client.bring_to_foreground()
    pyautogui.press('F2')  # Open Inventory
    rect = client.get_rect()
    x, y = ResizableInventoryGrid.get_slot_xy(slot, rect)
    # print(f"Clicking slot {slot} at ({x}, {y})")
    pyautogui.click(x, y)
    time.sleep(0.05);

def click_prayer_slot(slot):
    """
    Click a specific prayer slot (1-26) in resizable mode.
    """
    client = RuneLiteClientWindow()
    client.bring_to_foreground()
    pyautogui.press('F4')  # Open Prayers
    rect = client.get_rect()
    x, y = ResizablePrayerGrid.get_slot_xy(slot, rect)
    # print(f"Clicking prayer slot {slot} at ({x}, {y})")
    pyautogui.click(x, y)

def disable_user_mouse_input():
    """
    Disable user mouse input temporarily to prevent interference.
    """
    # print("User mouse input disabled temporarily.")
    pyautogui.FAILSAFE = False  # Disable failsafe for uninterrupted operation

def enable_user_mouse_input():
    """
    Re-enable user mouse input after being disabled.
    """
    # print("User mouse input re-enabled.")
    pyautogui.FAILSAFE = True  # Re-enable failsafe

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

def get_current_vitality() -> {int,int}:
    """
    poll the current player vitality (health/prayer points)
    """
    
    api = RuneLiteAPI()
    health, prayer = api.get_health_points(), api.get_prayer_points()
    return {health: health, prayer: prayer}

def get_current_equipped_combat_style():
    return "MAGE" # or "RANGE";

def equip_next_gear(humanizer):
    """
    Example function to equip mage gear by clicking specific inventory slots.
    Adjust slot numbers as needed based on your inventory layout.
    """

    # Disable user mouse input to prevent interference
    disable_user_mouse_input()

    pyautogui.press('F2')  # Open Inventory

    # Example slot numbers for mage gear (adjust as necessary)
    mage_gear_slots = [1, 2, 5, 6, 9, 10, 13]
    for slot in mage_gear_slots:
        humanizer.click_inventory_slot(slot)
    
    enable_user_mouse_input()

def equip_gear(type="RANGE"):
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
    CURRENT_EQUIPPED_STYLE = (weapon_style == "MAGE" and "RANGE" or "MAGE");

    # select a prayer based on the type
    print(f"Activated PHASE type={type}")
    if type == "MAGE":
        pyautogui.press('F4')
        ui_interaction.click_prayer_slot(17)
        if CURRENT_EQUIPPED_STYLE == "MAGE":
            print("Equipping RANGE gear...")
            equip_next_gear(ui_interaction)
            pyautogui.press('F4')
            ui_interaction.click_prayer_slot(20)
        # pyautogui.press('F4')  # Stay on prayer book for prayer switches
        pyautogui.press('F2')  # Close Prayers into Inventory

    elif type == "RANGE":
        pyautogui.press('F4')
        ui_interaction.click_prayer_slot(18)
        if CURRENT_EQUIPPED_STYLE == "RANGE":
            print("Equipping MAGE gear...")
            equip_next_gear(ui_interaction)
            pyautogui.press('F4')
            ui_interaction.click_prayer_slot(21)
        pyautogui.press('F2')  # Close Prayers into Inventory

    elif type == "MELEE":

        # Protect from Melee doesnt have a use. you will need to dodge manually, so would only use this to make sure we have the right gear equipped
        if CURRENT_EQUIPPED_STYLE == "MAGE":
            print("Equipping RANGE gear...")
            equip_next_gear(ui_interaction)
            pyautogui.press('F4')
            ui_interaction.click_prayer_slot(20)
        pyautogui.press('F2')  # Close Prayers into Inventory
    
    # move mouse back to original position
    pyautogui.moveTo(original_x, original_y);

def equip_range(stop_event: threading.Event):
    equip_gear(type="RANGE");

def equip_melee(stop_event: threading.Event):
    equip_gear(type="MELEE");

def equip_mage(stop_event: threading.Event):
    equip_gear(type="MAGE");

def update_zulrah_phase(phase: str):
    """
    Update the text on the client about what phase we are in
    """
    win_rect = RuneLiteClientWindow().get_rect()
    overlay = WindowOverlay(title="ZulrahPhase", width=win_rect["w"], height=win_rect["h"], x=win_rect[1], y=win_rect[2], transparency=0.8)
    # Get client window position and size
    overlay.clear()
    overlay.draw_text(
        f"PHASE: {phase}",
        position=(20, 40),
        font_size=32,
        color=(251, 252, 253)
    )
    overlay.update_overlay()

if __name__ == "__main__":
    print("Initializing OSRS Debug Helper...")
    
    # hotkey_manager = HotkeyManager(HOTKEY_START_LOOP, HOTKEY_STOP_LOOP)
    # hotkey_manager.register_hotkeys(npc_debug_loop)

    hotkey_1 = HotkeyManager(HOTKEY_SWITCH_GEAR_FOR_MAGE, "esc")
    hotkey_1.register_hotkeys(equip_mage);

    hotkey_2 = HotkeyManager(HOTKEY_SWITCH_GEAR_FOR_RANGE, "esc")
    hotkey_2.register_hotkeys(equip_range);

    hotkey_3 = HotkeyManager(HOTKEY_SWITCH_GEAR_FOR_MELEE, "esc")
    hotkey_3.register_hotkeys(equip_melee);

    hotkey_1.wait_for_exit()
    
