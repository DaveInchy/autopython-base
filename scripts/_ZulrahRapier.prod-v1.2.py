"""
Main script for the Zulrah helper.

This script continuously checks for nearby NPCs and prints their information
to the console for debugging purposes.
"""

import json
import time
import threading

# pip packages/module
import pyautogui

# --- OSRS Macro SDK Imports ---
from src.graphics.window_overlay import WindowOverlay, DrawCursorPosition
from src.client_window import RuneLiteClientWindow
from src.ui_utils import HumanizedGridClicker, Inventory as ResizableInventoryGrid, Prayer as ResizablePrayerGrid, UIInteraction
from src.runelite_api import RuneLiteAPI
from src.hotkeys import HotkeyManager
from src.osrs_items import OSRSItems

SCRIPT={
    "version": "1.2",
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
        "switch_count": 7,
        "use_smart_consumer": False, #TODO
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
global ACTION_QEUE
global STATE
STATE={
    "started": False,
    "phase": 1,
    "path": 1,
    "last_phase": 1,
    "last_path": 1,
    "last_action": None,
}
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
    if not item_name:
        return "UNKNOWN"

    item_name = item_name.lower()
    if "staff" in item_name or "wand" in item_name or "sceptre" in item_name or "trident" in item_name:
        return "MAGE"
    if "bow" in item_name or "blowpipe" in item_name or "crossbow" in item_name or "dart" in item_name or "thrownaxe" in item_name or "knife" in item_name:
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

def get_current_vitality() -> {int,int}:
    """
    poll the current player vitality (health/prayer points)
    """
    try:
        api = RuneLiteAPI()
        health, prayer = api.get_health_points(), api.get_prayer_points()
        return {health: health, prayer: prayer}
    except Exception as e:
        print(e)

    return {health: -1, prayer: -1}

# def qeue_action(action=str, data=any, callback=any):
#     ACTION_QEUE[len(ACTION_QEUE)+1] = {
#         "data": data,
#         "creation": time.time(),
#         "done": False,
#         "locked": False,
#         "code": action,
#         "message": "success",
#         "callback": callback
#     }

# def process_action():
#     if len(ACTION_QEUE) == 0:
#         return

#     action = ACTION_QEUE[len(ACTION_QEUE)+1]
#     if action["locked"]:
#         return
#     if action["done"]:
#         return

#     action["locked"] = True
#     result = action["callback"](action["data"]) or "success";
#     action["message"] = f"{result}"
#     action["done"] = True
#     action["locked"] = False

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
    def get_inventory_slots():
        # based on the setup settings, determine how many slots to use
        len = int(SCRIPT["settings"]["switch_count"])
        return [1, 2, 5, 6, 9, 10, 13, 14, 17, 18][:len]
    
    for slot in get_inventory_slots():
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
    CURRENT_EQUIPPED_STYLE = (weapon_style == "MAGE" and "RANGE" or "MAGE")

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

def get_zulrah_rotations():
    phase_data = {
        # "positions": {
        #     "ZulrahPosCenter": {"x": 6720, "y": 7616},
        #     "ZulrahPosWest": {"x": 8000, "y": 7360},
        #     "ZulrahPosEast": {"x": 5440, "y": 7360},
        #     "ZulrahPosNorth": {"x": 6720, "y": 6208}
        # },
        # "movement_tiles": {
        #     "SWCornerTile": {"x": 7488, "y": 7872},
        #     "SWCornerTileMelee": {"x": 7232, "y": 8000},
        #     "WPillar": {"x": 7232, "y": 7232},
        #     "WPillarN": {"x": 7232, "y": 7104},
        #     "EPillar": {"x": 6208, "y": 7232},
        #     "EPillarN": {"x": 6208, "y": 7104},
        #     "SECornerTile": {"x": 6208, "y": 8000},
        #     "SECornerTileMelee": {"x": 5952, "y": 7744},
        #     "Middle": {"x": 6720, "y": 6848}
        # },
        "types": {
            2042: {
                "name": "Green", 
                "style": "RANGE", 
                "rgb": [
                    {[250,0,0], [255,0,0]} # min and max for spectrum of colors, tune manually by sampling
                ]
            },
            2043: {
                "name": "Red", 
                "style": "MELEE", 
                "rgb": [
                    {[250,0,0], [255,0,0]} # min and max for spectrum of colors, tune manually by sampling
                ]
            },
            2044: {
                "name": "Blue", 
                "style": "MAGIC", 
                "rgb": [
                    {[250,0,0], [255,0,0]} # min and max for spectrum of colors, tune manually by sampling
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
                "ticks": [0, 28, 20, 18, 28, 39, 22, 20, 36, 48, 20]
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
                "ticks": [0, 28, 20, 17, 39, 22, 20, 28, 36, 48, 21]
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
                "ticks": [0, 28, 30, 40, 20, 20, 20, 25, 20, 36, 35, 18]
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
                "ticks": [0, 28, 36, 24, 30, 28, 17, 34, 33, 20, 27, 29, 18]
            }
        }
    }
    return phase_data

def update(ui: UIInteraction):
    # process_q()
    # get mouse position
    original_x, original_y = pyautogui.position()

    MIN_HP=45
    MIN_PRAY=10

    health, prayer = get_current_vitality()

    if health!=-1:
        if health <= MIN_HP:
            ui.client_window.bring_to_foreground()
            pyautogui.press('F2')
            on_low_health(ui)
            pyautogui.moveTo(original_x, original_y)
    else:
        print("No health data")
    
    if prayer!=-1:
        if prayer <= MIN_PRAY:
            ui.client_window.bring_to_foreground()
            pyautogui.press('F2')
            on_low_prayer(ui)
            pyautogui.moveTo(original_x, original_y)
    else:
        print("No prayer data")

    # if the ticks have gone by, wait for user (not machine) click, use color_utils to then match it with a color spectrum for each boss phase. ase soon as its confirmed. you can then calculate the next phase and add a progress point because of the ticks
    

def enable_combat_mode(stop_event: threading.Event):
    # Start by enabling magic prayer, assuming you press W to start against the green snake, assures youre really ready
    # Reset the state machine to its default for phase 1
    # Start a loop with 0.4 seconds interval, make sure that we have a onGameTick(count=int) method so we can just cycle the start to end with each tich since the rotations themselves are static and run all on programmed timings etc.
    client = RuneLiteClientWindow()
    ui = UIInteraction(HumanizedGridClicker(), None, client)
    
    while not stop_event.is_set():
        
        update(ui)

        # Wait for the next iteration
        time.sleep(0.1)
        

def on_same_health(time=5000):
    pass

def on_death():
    pass

def on_low_health(ui: UIInteraction):

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

        if choice == "y":

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
            print("Setup complete!")
            print(50*"=")
            return True

        elif choice == "n":
            print("Starting Script...")

    result = prompt_for_setup();
    if result==False:
        exit(0)

    hk = HOTKEY_SWITCH_GEAR_FOR_MAGE
    hotkey_1 = HotkeyManager(hk, f"ctrl+{hk}")
    hotkey_1.register_hotkeys(equip_mage);

    hk = HOTKEY_SWITCH_GEAR_FOR_RANGE
    hotkey_2 = HotkeyManager(hk, f"ctrl+{hk}")
    hotkey_2.register_hotkeys(equip_range);

    hk = HOTKEY_SWITCH_GEAR_FOR_MELEE
    hotkey_3 = HotkeyManager(hk, f"ctrl+{hk}")
    hotkey_3.register_hotkeys(equip_melee);

    hotkey_4 = HotkeyManager(HOTKEY_START_FIGHT, f"ctrl+{HOTKEY_START_FIGHT}")
    hotkey_4.register_hotkeys(enable_combat_mode);

    hotkey_1.wait_for_exit()
    
