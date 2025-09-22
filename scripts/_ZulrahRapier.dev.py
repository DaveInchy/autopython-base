"""
Main script for the Zulrah helper.

This script continuously checks for nearby NPCs and prints their information
to the console for debugging purposes.
"""
import time
import threading
import sys
import queue
import signal
from typing import Literal

# pip packages/module
import pyautogui # type: ignore
from pynput import mouse  # type: ignore # Add this line
import keyboard # For scoped hotkeys

# --- OSRS Macro SDK Imports ---
from src.graphics.window_overlay import WindowOverlay, DrawCursorPosition
from src.client_window import RuneLiteClientWindow
from src.ui_utils import HumanizedGridClicker, Inventory as ResizableInventoryGrid, Prayer as ResizablePrayerGrid, UIInteraction, Inventory, Prayer, Equipment, Magic
from src.runelite_api import RuneLiteAPI
from src.hotkeys import HotkeyManager
from src.osrs_items import OSRSItems


combat_mode_active = False
health, prayer = 99, 99

SCRIPT={
    "version": "1.6",
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
        "switch_speed": 0.05, # Half of pyautogui's default 0.1s pause
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
        "use_image_recognition": False,
        "mode": "hotkeys",
        "manual_spell_slot": 1,
        "manual_spell_book": "standard",
        "render_grids_and_clicks": False,
    },
    "state": {
        "start_time": int(0),
        "time": int(0),
        "phase": int(0),
        "manual_phase_index": 0,
        "last_eat_time": 0,
        "Warning": None,
        "player_style": "UNKNOWN",
        "activated": False,
        "matched_rotation": 0,
        "next_phase_style": "UNKNOWN",
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

PhaseTableType = type({"phases": list, "jad": int, "ticks": list})
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
        """
        Finds the best rotation match based on a list of confirmed phases.
        Returns the rotation ID (1-4) or 0 if no definitive match is found.
        """
        if not confirmed_list:
            return 0

        possible_rotations = []
        for rot_id, rot_data in self.data["waves"].items():
            # Check if the confirmed phases are a prefix of this rotation's phases
            if rot_data["phases"][:len(confirmed_list)] == confirmed_list:
                possible_rotations.append(rot_id)

        # If we have exactly one possible rotation, that's our match.
        if len(possible_rotations) == 1:
            return possible_rotations[0]
        
        # If multiple rotations are still possible, we don't have a definitive match yet.
        # We return 0 to indicate ambiguity.
        return 0

    def update(self, phase: str) -> bool:
        """
        Adds a confirmed phase to the list and attempts to identify the rotation.
        """
        if not phase or phase == "UNKNOWN":
            return False
        
        self.confirmed_phases.append(phase)
        self.wave_counted = len(self.confirmed_phases)
        self.matched_rotation = self.match_rotation(self.confirmed_phases)
        return True
    
    def fetch(self) -> ({list, int, list}):
        """
        Fetches the data for the currently matched rotation.
        """
        if self.matched_rotation in self.data["waves"]:
            return self.data["waves"][self.matched_rotation]
        return None

    
    
global PHASE_HANDLER
PHASE_HANDLER: RotationManager = RotationManager()

# --- Zulrah Constants ---
ZULRAH_IDS = [2042, 2043, 2044] # Green, Red, Blue,
ZULRAH_TYPES = ["RANGE", "MELEE", "MAGIC"]
# but theres also a green one that does mage type damage

ZULRAH_PHASE_MAP = {
    1: {"type": "RANGE", "gear": "MAGIC"},
    2: {"type": "MELEE", "gear": "RANGE"},
    3: {"type": "MAGIC", "gear": "RANGE"},
}

ZULRAH_PHASE_PRAYER = {
    1: {"type": "RANGE", "offense": 21, "protect": 18},
    2: {"type": "MELEE", "offense": 20, "protect": 19},
    3: {"type": "MAGIC", "offense": 20, "protect": 17},
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
        return "MAGIC"
    if "bow" in item_name or "blowpipe" in item_name or "crossbow" in item_name or "dart" in item_name or "thrownaxe" in item_name or "knife" in item_name or item_id in ranged_ids:
        return "RANGE"

    return "UNKNOWN"

# def get_snake_style() -> str:
#     """
#     Placeholder function to determine the snake's current style.
#     In a real implementation, this would use image recognition or other methods.
#     For now, it randomly returns "MAGIC" or "RANGE".
#     """
#     import random
#     return random.choice(["MAGIC", "RANGE"])

def render(client: RuneLiteClientWindow, overlay: WindowOverlay, api: RuneLiteAPI, items_db: OSRSItems):
    """
    Renders useful information with an overlay
    """
    global SCRIPT
    _list_start = [18, 124]
    _font_size = 16

    _list = [
        {
            "type": any,
            "name": "time",
            "display_name": "Time"
        },
        {
            "type": Literal["RANGE", "MAGIC", "MELEE", "UNKNOWN"],
            "name": "phase", # based on what hotkey has been pressed last,
            "display_name": "Phase"
        },
        {
            "type": str,
            "name": "next_phase_style",
            "display_name": "Next"
        },
        {
            "type": int,
            "name": "manual_phase_index",
            "display_name": "Wave"
        },
    ]
    
    weapon = get_weapon_style_from_slot_one(api, items_db)
    SCRIPT['state']["player_style"] = (weapon == "MAGIC" and "RANGE" or "MAGIC")

    # Fetch rotation data but check if it's None before using it
    rotation = PHASE_HANDLER.fetch()

    if rotation:
        # Safely get data from the rotation dictionary
        jad_wave = rotation.get("jad")
        ticks = rotation.get("ticks")

        overlay.draw_text(
            f"Jad Wave: {jad_wave}",
            position=(_list_start[0], _list_start[1] + i * (_font_size+2)),
            font_size=_font_size,
            color=(0, 250, 0)
        )

        cooldown = ticks[SCRIPT['state']["manual_phase_index"]] * 0.4
        formatted = value and time.strftime("%M:%S", time.gmtime(cooldown)) or "00.00"
        if cooldown > 0:
            overlay.draw_text(
                f"{display_name}: {formatted}",
                position=(_list_start[0], _list_start[1] + i * (_font_size+2)),
                font_size=_font_size,
                color=(250, 250, 0)
            )

    for i, item in enumerate(_list):
        value = SCRIPT['state'].get(item['name'], '') 
        display_name = item['display_name'] or item['name'].replace("_", " ").capitalize()

        if item['name'] == "time":
            formatted = value and time.strftime("%M:%S", time.gmtime(value)) or "00.00"
            overlay.draw_text(
                f"{display_name}: {formatted}",
                position=(_list_start[0], _list_start[1] + i * (_font_size+2)),
                font_size=_font_size,
                color=(250, 250, 0)
            )
        else:
            overlay.draw_text(
                f"{display_name}: {value}",
                position=(_list_start[0], _list_start[1] + i * (_font_size+2)),
                font_size=_font_size,
                color=(250, 250, 0)
            )

    return

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

def is_on_cooldown(cooldown_name: str, duration: float) -> bool:
    """
    Checks if a named cooldown is currently active by checking the script's state.
    """
    last_action_time = SCRIPT['state'].get(f'last_{cooldown_name}_time', 0)
    return time.time() - last_action_time < duration

def set_cooldown(cooldown_name: str):
    """
    Sets the timestamp for a named cooldown in the script's state.
    """
    SCRIPT['state'][f'last_{cooldown_name}_time'] = time.time()

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

def equip_next_gear(humanizer, api, items_db):
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
    global SCRIPT, CURRENT_EQUIPPED_STYLE

    # --- Store original pause value and set a new one for speed ---
    original_pause = pyautogui.PAUSE
    pyautogui.PAUSE = SCRIPT['settings']['switch_speed'] # Use configurable pause for switching

    try:
        # get current mouse position
        original_x, original_y = pyautogui.position()

        client = RuneLiteClientWindow()
        client.bring_to_foreground()

        humanizer = UIInteraction(HumanizedGridClicker(), None, client)
        
        api = RuneLiteAPI()
        items_db = OSRSItems()
        
        weapon = get_weapon_style_from_slot_one(api, items_db)
        CURRENT_EQUIPPED_STYLE = (weapon == "MAGIC" and "RANGE" or "MAGIC")

        SCRIPT['state']["phase"] = type

        # select a prayer based on the type
        if type == "MAGIC":
            pyautogui.press('F4')
            humanizer.click_prayer_slot(17)
            if CURRENT_EQUIPPED_STYLE == "MAGIC":
                equip_next_gear(humanizer, api, items_db)
                pyautogui.press('F4')
                humanizer.click_prayer_slot(20)
            # pyautogui.press('F4')  # Stay on prayer book for prayer switches
            pyautogui.press('F2')  # Close Prayers into Inventory

        elif type == "RANGE":
            pyautogui.press('F4')
            humanizer.click_prayer_slot(18)
            if CURRENT_EQUIPPED_STYLE == "RANGE":
                equip_next_gear(humanizer, api, items_db)
                pyautogui.press('F4')
                humanizer.click_prayer_slot(21)
            pyautogui.press('F2')  # Close Prayers into Inventory

        elif type == "MELEE":

            # Protect from Melee doesnt have a use. you will need to dodge manually, so would only use this to make sure we have the right gear equipped
            if CURRENT_EQUIPPED_STYLE == "MAGIC":
                equip_next_gear(humanizer, api, items_db)
                pyautogui.press('F4')
                humanizer.click_prayer_slot(20)
            pyautogui.press('F2')  # Close Prayers into Inventory
        
        # move mouse back to original position
        pyautogui.moveTo(original_x, original_y)
        
    finally:
        # --- Restore the original pause value ---
        pyautogui.PAUSE = original_pause

    return
        
def equip_range():
    equip_gear(type="RANGE")

def equip_melee():
    equip_gear(type="MELEE")

def equip_mage():
    equip_gear(type="MAGIC")

def get_async_hp_prayer(api: RuneLiteAPI, stop_event: threading.Event):
    """
    Get the current health and prayer points asynchronously.
    """
    try:
        global health, prayer
        while not stop_event.is_set():
            health = api.get_health_points()
            prayer = api.get_prayer_points()
    finally:
        print("Thread stopped")
    
    

def update(ui: UIInteraction, client: RuneLiteClientWindow=None, api: RuneLiteAPI=None, stop_event: threading.Event=None):
    # process_q()
    # get mouse position
    original_x, original_y = pyautogui.position()

    MIN_HP=50
    MIN_PRAY=10
    
    global SCRIPT
    global current_rendered_grid
    global health, prayer
    
    if health == None or health == 0:
        print("Death detected")
        SCRIPT['state']["Warning"] = "YOU DIED IDIOT"
        on_death(stop_event)
    
    if health:
        if health <= MIN_HP:
            # Check for eating cooldown before attempting to eat.
            # OSRS eating is 3 ticks (1.8s). We'll use a slightly longer cooldown
            # to ensure the health has time to update via the API.
            if is_on_cooldown('eat', 1.8):
                return # Still on cooldown, skip eating logic

            SCRIPT['state']["Warning"] = "HEALTH is low"
            disable_user_mouse_input()
            ui.client_window.bring_to_foreground()
            pyautogui.press('F2')
            on_low_health(ui, stop_event)
            pyautogui.moveTo(original_x, original_y)
    
            enable_user_mouse_input()
    
    if prayer:
        if prayer <= MIN_PRAY:
    
            SCRIPT['state']["Warning"] = "PRAYER is low"
            disable_user_mouse_input()
            ui.client_window.bring_to_foreground()
            pyautogui.press('F2')
            on_low_prayer(ui, stop_event)
            pyautogui.moveTo(original_x, original_y)
    
            enable_user_mouse_input()
    
    else: # this means we have 0 prayer
        print("Supply shortage detected")
        SCRIPT['state']["Warning"] = "No PRAYER points left"
        panic_teleport(ui, stop_event)

def enable_combat_mode(stop_event: threading.Event, q: queue.Queue):
    client: RuneLiteClientWindow = RuneLiteClientWindow()

    # The overlay is now created in the main thread.
    # We pass the queue to the combat thread.
    ui = UIInteraction(HumanizedGridClicker(), None, client)
    api = RuneLiteAPI()
    items_db = OSRSItems()
    
    global SCRIPT, combat_mode_active
    print("Combat mode enabled. Gear/prayer hotkeys are active.")
    SCRIPT['state']["activated"] = True
    SCRIPT['state']["Warning"] = ""
    SCRIPT['state']["phase"] = "UNKNOWN"
    SCRIPT['state']["player_style"] = "UNKNOWN"
    SCRIPT['state']["start_time"] = time.time()
    SCRIPT['state']["time"] = 0

    def run_combat_mode(stop_event: threading.Event, q: queue.Queue):
        global combat_mode_active
        nonlocal client, ui, api, items_db
        if combat_mode_active:
            return  # Already running
        
        # The overlay is no longer created or managed here.

        thread2 = threading.Thread(target=get_async_hp_prayer, args=(api,stop_event,))
        thread2.daemon = True
        thread2.start()

        combat_mode_active = True
        try:
            loop_interval = .1 # seconds
            while not stop_event.is_set():
                start_time = time.time()
                
                update(ui, client, api, stop_event)
                SCRIPT['state']["time"] = (time.time() - SCRIPT['state']["start_time"])

                # Instead of drawing, put the state into the queue for the main thread to render.
                q.put({'type': 'render', 'state': SCRIPT['state'], 'client_rect': client.get_rect()})

                # Wait for the next iteration
                end_time = time.time()
                elapsed_time = end_time - start_time
                if elapsed_time < loop_interval:
                    time.sleep(loop_interval - elapsed_time)
                if elapsed_time > loop_interval:
                    print(f"Loop took too long: {elapsed_time:.2f} seconds")

            # Signal the main thread to close the overlay
            q.put({'type': 'close'})
            combat_mode_active = False
            print("Combat mode disabled. Gear/prayer hotkeys are inactive.")
            SCRIPT['state']['activated'] = False
        except Exception as e:
            print(f"An error occurred: {e}")
            combat_mode_active = False
            SCRIPT['state']['activated'] = False
            q.put({'type': 'close'}) # Ensure cleanup on error
            raise e

    thread1 = threading.Thread(target=run_combat_mode, args=(stop_event, q))
    thread1.daemon = True 
    thread1.start()
    # Do not join, as it would block the hotkey trigger.

def on_same_health():
    pass

def on_damage_taken():
    pass

def on_damage_healed():
    pass

def on_death(stop_event: threading.Event):
    global combat_mode_active
    if combat_mode_active:
        print("Combat mode disabled due to death.")
        combat_mode_active = False
        stop_event.set()
    pass

def on_low_health(ui: UIInteraction, stop_event: threading.Event):

    def consume_food():
        food_ated = 0
        health_ated = 0

        # find a food and click it
        primary = search_inventory("shark")
        if primary:
            print(f"Found food in slot {primary}")
            ui.click_inventory_slot(primary)
            food_ated += 1
            health_ated += 21
            set_cooldown('eat') # Set cooldown because primary food was eaten
        
        combo_food = search_inventory("karambwan")
        if combo_food:
            print(f"Found combo food in slot {combo_food}")
            ui.click_inventory_slot(combo_food)
            food_ated += 1
            health_ated += 18
        
        triple_food = search_inventory("brew")
        restore_triple = search_inventory("restore")
        if triple_food and restore_triple:
            print(f"Found triple food in slot {triple_food}")
            ui.click_inventory_slot(triple_food)
            food_ated += 1
            health_ated += 7


        if food_ated == 0:
            print("No food ated")
            return False
        
        if health_ated >= 41:
            print(f"You over-ate maybe with healing {health_ated} points")
        
        return True

    ated = consume_food()

    if not ated:
       panic_teleport(ui, stop_event)
       return True

def panic_teleport(ui: UIInteraction, stop_event):
    """
    Panic teleport.
    """
    global combat_mode_active
    global SCRIPT
    if not combat_mode_active:
        return

    # get current mouse position
    original_x, original_y = pyautogui.position()

    teleport = search_inventory("teleport")
    if teleport:
        disable_user_mouse_input()
        print(f"Found teleport in slot {teleport}")
        ui.click_inventory_slot(teleport)
        SCRIPT['state']["Warning"] = "Panic teleporting and stopping combat loop."
        print("Panic teleporting and stopping combat loop.")
        pyautogui.moveTo(original_x, original_y)
        enable_user_mouse_input()
        combat_mode_active = False
        stop_event.set()
        return True

def on_low_prayer(ui: UIInteraction, stop_event: threading.Event):

    def consume_potion():
        # find a potion and click it
        potion = search_inventory("prayer") or search_inventory("restore")
        if potion:
            print(f"Found potion in slot {potion}")
            # Using a generic template name for prayer/restore potions
            ui.click_inventory_slot(potion)
            return True
        return False
    
    drinked = consume_potion()
    if not drinked:
        panic_teleport(ui, stop_event)
        return True

def manual_blood_blitz():
    """
    Manually trigger blood blitz.
    """
    global SCRIPT, combat_mode_active

    # --- Store original pause value and set a new one for speed ---
    original_pause = pyautogui.PAUSE
    pyautogui.PAUSE = SCRIPT['settings']['switch_speed'] # Use configurable pause for switching

    try:
        if not combat_mode_active:
            return

        # get current mouse position
        original_x, original_y = pyautogui.position()

        client = RuneLiteClientWindow()
        client.bring_to_foreground()

        humanizer = UIInteraction(HumanizedGridClicker(), None, client)

        # select blood blitz
        pyautogui.press('F1')
        if SCRIPT["settings"]["manual_spell_book"] == "ancient":
            humanizer.click_magic_slot(21) # Blood blitz
        else:
            humanizer.click_magic_slot(21) #@TODO IDK, should be a setup part

        pyautogui.press('F2')

        # move mouse back to original position
        pyautogui.click(original_x, original_y)
    finally:
        # --- Restore the original pause value ---
        pyautogui.PAUSE = original_pause

def reset_combat_state():
    """
    Resets the combat state variables to their initial values.
    """
    global SCRIPT
    if not combat_mode_active:
        print("Combat mode is not active. Nothing to reset.")
        return

    print("Resetting combat state...")
    SCRIPT['state']['start_time'] = time.time()
    SCRIPT['state']['time'] = 0
    SCRIPT['state']['phase'] = "UNKNOWN"
    SCRIPT['state']['manual_phase_index'] = 0
    SCRIPT['state']['Warning'] = "State Reset"
    # We don't reset 'activated' or 'player_style' as the loop is still active.

def confirm_phase():
    """
    Manually confirms the current combat style as the next phase in the rotation,
    updates the rotation manager, and increments the phase counter.
    """
    if not combat_mode_active:
        return

    # Increment the visual counter
    SCRIPT['state']['manual_phase_index'] += 1
    if SCRIPT['state']['manual_phase_index'] == 1:
        SCRIPT['state']['start_time'] = time.time()
        SCRIPT['state']['time'] = 0
    
    # Get the current combat style (set by q, w, e)
    current_style = SCRIPT['state'].get('phase', 'UNKNOWN')

    # Update the rotation manager with the confirmed style
    if PHASE_HANDLER.update(phase=current_style):
        print(f"Phase {SCRIPT['state']['manual_phase_index']} ({current_style}) confirmed.")
        
        # Store the results in the SCRIPT state so we can render them
        SCRIPT['state']['matched_rotation'] = PHASE_HANDLER.matched_rotation
        
        next_phase_info = PHASE_HANDLER.fetch()
        if next_phase_info:
            # Ensure we don't go out of bounds
            if PHASE_HANDLER.wave_counted < len(next_phase_info['phases']):
                SCRIPT['state']['next_phase_style'] = next_phase_info['phases'][PHASE_HANDLER.wave_counted]
            else:
                SCRIPT['state']['next_phase_style'] = 'END'
        else:
            # If no rotation is matched yet, we don't know the next phase
            SCRIPT['state']['next_phase_style'] = 'UNKNOWN'

    else:
        print(f"Failed to confirm phase: {current_style}")

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
    switches=6;

    for k in sys.argv:
        if "-y" in k:
            prompt=False
            continue
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
        if "--spell-num=" in k:
            v = k.split("=")[1]
            SCRIPT["settings"]["manual_spell_slot"] = int(v)
            continue
        if "--spell-book=" in k:
            v = k.split("=")[1]
            SCRIPT["settings"]["manual_spell_book"] = v
            continue
        if "--render-grids-and-clicks=" in k or "--render=" in k:
            v = k.split("=")[1]
            SCRIPT["settings"]["render_grids_and_clicks"] = v.lower() == "true"
            continue
    
    if prompt==True:
        result = prompt_for_setup()
        if result==False:
            exit(0)

    # --- Hotkey Registration ---
    # This section is refactored to handle hotkeys in a non-blocking way.
    # Each hotkey action runs in a new thread, and a lock prevents spamming.
    action_lock = threading.Lock()
    action_thread = None
    def run_action_once(target_func):
        """
        Wrapper to run a function in a thread-safe manner, ensuring only one
        action runs at a time.
        """
        if not action_lock.acquire(blocking=False):
            # If we can't acquire the lock, another action is already running.
            print("Action already in progress. Ignoring new request.")
            return

        try:
            target_func()
        finally:
            # Release the lock when the action is done.
            action_lock.release()

    def create_action_thread(target):
        """
        Checks if combat mode is active and, if so, starts the target 
        action in a new, non-blocking daemon thread.
        """
        if combat_mode_active:
            global action_thread
            # We pass the target function to `run_action_once`
            thread = threading.Thread(target=run_action_once, args=(target,))
            thread.daemon = True  # Allows main program to exit even if threads are running
            thread.start()
            

    # Scoped action hotkeys. They only work if combat_mode_active is True.
    # They now use the `create_action_thread` helper to run without blocking.
    keyboard.add_hotkey(HOTKEY_SWITCH_GEAR_FOR_MAGE, lambda: create_action_thread(equip_mage))
    keyboard.add_hotkey(HOTKEY_SWITCH_GEAR_FOR_RANGE, lambda: create_action_thread(equip_range))
    keyboard.add_hotkey(HOTKEY_SWITCH_GEAR_FOR_MELEE, lambda: create_action_thread(equip_melee))
    keyboard.add_hotkey("r", lambda: create_action_thread(manual_blood_blitz))
    keyboard.add_hotkey("space", lambda: create_action_thread(confirm_phase))
    keyboard.add_hotkey("ctrl+r", lambda: create_action_thread(reset_combat_state))

    print(f"Action hotkeys ('{HOTKEY_SWITCH_GEAR_FOR_MAGE}', '{HOTKEY_SWITCH_GEAR_FOR_RANGE}', '{HOTKEY_SWITCH_GEAR_FOR_MELEE}', 'r', 'space', 'ctrl+r') are registered.")
    print("They will only function when combat mode is active.")

    # --- Main Application Setup ---
    # Create a queue for communication between threads
    gui_queue = queue.Queue()

    # Create the overlay in the main thread
    client = RuneLiteClientWindow()
    win_rect = client.get_rect()
    if not win_rect:
        print("RuneLite client not found. Exiting.")
        exit()
        
    overlay = WindowOverlay(title="Zulrah Overlay", width=win_rect["w"], height=win_rect['h'], x=win_rect['left'], y=win_rect['top'])
    api = RuneLiteAPI()
    items_db = OSRSItems()

    def process_gui_queue():
        """
        Process messages from the GUI queue to update the overlay.
        This function runs in the main thread.
        """
        try:
            message = gui_queue.get_nowait()

            if message.get('type') == 'render':
                state = message.get('state')
                client_rect = message.get('client_rect')
                
                # Update SCRIPT state with the data from the combat thread
                global SCRIPT
                SCRIPT['state'] = state

                overlay.clear()
                if client_rect:
                    overlay.set_position(client_rect['left'], client_rect['top'])
                    overlay.set_size(client_rect['w'], client_rect['h'])
                    overlay.bring_to_foreground()
                    # The render function needs the overlay object
                    render(client, overlay, api, items_db)
                
                overlay.update_overlay()

            elif message.get('type') == 'close':
                overlay.close()
                # We might want to exit the script here, but closing the window
                # will cause root.mainloop() to exit if it's the only window.
                # For a clean exit, we can call root.quit()
                overlay.root.quit()
                return # Stop the after loop

        except queue.Empty:
            pass  # No messages in the queue

        # Reschedule the function to run again after 10ms
        overlay.root.after(10, process_gui_queue)

    # Main combat loop manager
    # We now pass the queue to the enable_combat_mode function
    combat_loop_manager = HotkeyManager(HOTKEY_START_FIGHT, f"ctrl+{HOTKEY_START_FIGHT}")
    combat_loop_manager.register_hotkeys(lambda stop_event: enable_combat_mode(stop_event, gui_queue))

    print("Press Ctrl+C in the console to exit.")
    
    # --- Signal Handler for Ctrl+C ---
    def sigint_handler(sig, frame):
        print("\nEOF>>")
        # Destroying the root window will cause the mainloop to exit.
        overlay.root.destroy()

    signal.signal(signal.SIGINT, sigint_handler)

    # Start the GUI queue processor
    overlay.root.after(10, process_gui_queue)
    
    # Start the Tkinter main loop. This is a blocking call.
    overlay.root.mainloop()

    print("Script finished.")