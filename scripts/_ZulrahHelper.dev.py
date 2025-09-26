"""
Main script for the Zulrah helper.

This script provides gear and prayer switching assistance for the Zulrah boss fight,
with a manual phase confirmation system and a real-time overlay.
"""
import time
import threading
import sys
import queue
import signal
from typing import Literal

# pip packages/module
import pyautogui # type: ignore
import keyboard # For scoped hotkeys

# --- OSRS Macro SDK Imports ---
from src.graphics.window_overlay import WindowOverlay
from src.client_window import RuneLiteClientWindow
from src.ui_utils import HumanizedGridClicker, UIInteraction
from src.runelite_api import RuneLiteAPI
from src.hotkeys import HotkeyManager
from src.osrs_items import OSRSItems


combat_mode_active = False
health, prayer = 99, 99

SCRIPT={
    "version": "1.6.1",
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
        "enable_smart_ticks": False, #TODO
        "use_hotkeys": True,
        "enable_extra_hotkeys": False, #TODO, Like healing, teleport, phase confirm
        "use_overlays": True,
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
        "phase": "UNKNOWN",
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

    
global PHASE_HANDLER
PHASE_HANDLER: RotationManager = RotationManager()

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

def render(client: RuneLiteClientWindow, overlay: WindowOverlay, api: RuneLiteAPI, items_db: OSRSItems):
    global SCRIPT
    _list_start = [18, 124]
    _font_size = 16
    _list = [
        {"type": any, "name": "time", "display_name": "Time"},
        {"type": Literal["RANGE", "MAGIC", "MELEE", "UNKNOWN"], "name": "Zulrah", "display_name": "Phase"},
        {"type": str, "name": "next_phase_style", "display_name": "Next"},
        {"type": int, "name": "manual_phase_index", "display_name": "Wave"},
        {"type": Literal["RANGE", "MAGIC", "UNKNOWN"], "name": "player_style", "display_name": "Player Style"},
        {"type": str | None, "name": "Warning", "display_name": "Warning"},
    ]
    
    weapon = get_weapon_style_from_slot_one(api, items_db)
    SCRIPT['state']["player_style"] = (weapon == "MAGIC" and "RANGE" or "MAGIC")

    rotation = PHASE_HANDLER.fetch()

    lines=0
    for i, item in enumerate(_list):
        value = SCRIPT['state'].get(item['name'], '') 
        display_name = item.get('display_name') or item['name'].replace("_", " ").capitalize()

        if item['name'] == "time":
            formatted = value and time.strftime("%M:%S", time.gmtime(value)) or "00.00"
            overlay.draw_text(f"{display_name}: {formatted}", position=(_list_start[0], _list_start[1] + i * (_font_size+2)), font_size=_font_size, color=(250, 250, 0))
        else:
            overlay.draw_text(f"{display_name}: {value}", position=(_list_start[0], _list_start[1] + i * (_font_size+2)), font_size=_font_size, color=(250, 250, 0))
        lines = i

    if rotation:
        jad_wave = rotation.get("jad")
        ticks = rotation.get("ticks")
        overlay.draw_text(f"Jad Wave: {jad_wave}", position=(_list_start[0], _list_start[1] + (lines + 2) * (_font_size+2)), font_size=_font_size, color=(0, 250, 0))
        if SCRIPT['state']["manual_phase_index"] < len(ticks):
            cooldown = ticks[SCRIPT['state']["manual_phase_index"]] * 0.6
            formatted = time.strftime("%M:%S", time.gmtime(cooldown)) or "00.00"
            if cooldown > 0:
                overlay.draw_text(f"Next Phase in: {formatted}", position=(_list_start[0], _list_start[1] + (lines + 3) * (_font_size+2)), font_size=_font_size, color=(250, 250, 0))
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

def equip_next_gear(humanizer: UIInteraction):
    disable_user_mouse_input()
    pyautogui.press('F2')
    num_switches = int(SCRIPT["settings"]["switch_count"])
    slots_to_click = [1, 2, 5, 6, 9, 10, 13, 14, 17, 18, 21, 22, 25, 26][:num_switches]
    for slot in slots_to_click:
        humanizer.click_inventory_slot(slot)
    enable_user_mouse_input()

def equip_gear(type: str):
    global SCRIPT, CURRENT_EQUIPPED_STYLE
    original_pause = pyautogui.PAUSE
    pyautogui.PAUSE = SCRIPT['settings']['switch_speed']
    try:
        original_x, original_y = pyautogui.position()
        client = RuneLiteClientWindow()
        client.bring_to_foreground()
        humanizer = UIInteraction(HumanizedGridClicker(), None, client)
        api = RuneLiteAPI()
        items_db = OSRSItems()
        weapon = get_weapon_style_from_slot_one(api, items_db)
        CURRENT_EQUIPPED_STYLE = (weapon == "MAGIC" and "RANGE" or "MAGIC")
        SCRIPT['state']["phase"] = type

        if type == "MAGIC":
            pyautogui.press('F4')
            humanizer.click_prayer_slot(17)
            if CURRENT_EQUIPPED_STYLE == "MAGIC":
                equip_next_gear(humanizer)
                pyautogui.press('F4')
                humanizer.click_prayer_slot(20)
            pyautogui.press('F2')
        elif type == "RANGE":
            pyautogui.press('F4')
            humanizer.click_prayer_slot(18)
            if CURRENT_EQUIPPED_STYLE == "RANGE":
                equip_next_gear(humanizer)
                pyautogui.press('F4')
                humanizer.click_prayer_slot(21)
            pyautogui.press('F2')
        elif type == "MELEE":
            if CURRENT_EQUIPPED_STYLE == "MAGIC":
                equip_next_gear(humanizer)
                pyautogui.press('F4')
                humanizer.click_prayer_slot(20)
            pyautogui.press('F2')
        pyautogui.moveTo(original_x, original_y)
    finally:
        pyautogui.PAUSE = original_pause
    return

def equip_range(): equip_gear(type="RANGE")
def equip_melee(): equip_gear(type="MELEE")
def equip_mage(): equip_gear(type="MAGIC")

def get_async_hp_prayer(api: RuneLiteAPI, stop_event: threading.Event):
    global health, prayer
    try:
        while not stop_event.is_set():
            health = api.get_health_points()
            prayer = api.get_prayer_points()
            time.sleep(0.2) # Polling interval
    finally:
        print("HP/Prayer thread stopped")

def update(ui: UIInteraction, stop_event: threading.Event):
    original_x, original_y = pyautogui.position()
    MIN_HP=50
    MIN_PRAY=10
    global SCRIPT, health, prayer
    
    if health is None or health == 0:
        print("Death detected")
        SCRIPT['state']["Warning"] = "YOU DIED IDIOT"
        on_death(stop_event)
        return

    if health <= MIN_HP:
        if is_on_cooldown('eat', 1.8):
            return
        SCRIPT['state']["Warning"] = "HEALTH is low"
        disable_user_mouse_input()
        ui.client_window.bring_to_foreground()
        pyautogui.press('F2')
        on_low_health(ui, stop_event)
        pyautogui.moveTo(original_x, original_y)
        enable_user_mouse_input()
    
    if prayer is not None and prayer <= MIN_PRAY:
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

def enable_combat_mode(stop_event: threading.Event, q: queue.Queue):
    client = RuneLiteClientWindow()
    ui = UIInteraction(HumanizedGridClicker(), None, client)
    api = RuneLiteAPI()
    
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
        nonlocal client, ui, api
        if combat_mode_active: return

        thread2 = threading.Thread(target=get_async_hp_prayer, args=(api,stop_event,))
        thread2.daemon = True
        thread2.start()

        combat_mode_active = True
        try:
            loop_interval = .1
            while not stop_event.is_set():
                start_time = time.time()
                update(ui, stop_event)
                SCRIPT['state']["time"] = (time.time() - SCRIPT['state']["start_time"])
                q.put({'type': 'render', 'state': SCRIPT['state'], 'client_rect': client.get_rect()})
                elapsed_time = time.time() - start_time
                if elapsed_time < loop_interval:
                    time.sleep(loop_interval - elapsed_time)
                if elapsed_time > loop_interval:
                    print(f"Loop took too long: {elapsed_time:.2f} seconds")
            q.put({'type': 'close'})
            combat_mode_active = False
            print("Combat mode disabled. Gear/prayer hotkeys are inactive.")
            SCRIPT['state']['activated'] = False
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
    global combat_mode_active
    if combat_mode_active:
        print("Combat mode disabled due to death.")
        combat_mode_active = False
        stop_event.set()

def on_low_health(ui: UIInteraction, stop_event: threading.Event):
    def consume_food():
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
    global combat_mode_active, SCRIPT
    if not combat_mode_active: return
    teleport_slot = search_inventory("teleport")
    if teleport_slot:
        disable_user_mouse_input()
        ui.click_inventory_slot(teleport_slot)
        SCRIPT['state']["Warning"] = "Panic teleporting!"
        print("Panic teleporting and stopping combat loop.")
        enable_user_mouse_input()
        combat_mode_active = False
        stop_event.set()
        return True

def on_low_prayer(ui: UIInteraction, stop_event: threading.Event):
    def consume_potion():
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
    pyautogui.PAUSE = SCRIPT['settings']['switch_speed']
    try:
        if not combat_mode_active: return
        original_x, original_y = pyautogui.position()
        client = RuneLiteClientWindow()
        client.bring_to_foreground()
        humanizer = UIInteraction(HumanizedGridClicker(), None, client)
        pyautogui.press('F1')
        humanizer.click_magic_slot(SCRIPT["settings"]["manual_spell_slot"])
        pyautogui.press('F2')
        pyautogui.click(original_x, original_y)
    finally:
        pyautogui.PAUSE = original_pause

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
                SCRIPT['state']['next_phase_style'] = next_phase_info['phases'][PHASE_HANDLER.wave_counted]
            else:
                SCRIPT['state']['next_phase_style'] = 'END'
        else:
            SCRIPT['state']['next_phase_style'] = 'UNKNOWN'
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

    for arg in sys.argv:
        if arg.startswith("--port="): SCRIPT["settings"]["api_port"] = int(arg.split("=")[1])
        elif arg.startswith("--switches="): SCRIPT["settings"]["switch_count"] = int(arg.split("=")[1])
        elif arg.startswith("--spell-num="): SCRIPT["settings"]["manual_spell_slot"] = int(arg.split("=")[1])
        elif arg.startswith("--spell-book="): SCRIPT["settings"]["manual_spell_book"] = arg.split("=")[1]
        elif arg.startswith("--render"): SCRIPT["settings"]["render_grids_and_clicks"] = "true" in arg.lower()

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
    win_rect = client.get_rect()
    if not win_rect: exit("RuneLite client not found. Exiting.")
        
    overlay = WindowOverlay(title="Zulrah Overlay", width=win_rect["w"], height=win_rect['h'], x=win_rect['left'], y=win_rect['top'])
    api = RuneLiteAPI()
    items_db = OSRSItems()

    def process_gui_queue():
        try:
            message = gui_queue.get_nowait()
            if message.get('type') == 'render':
                SCRIPT['state'] = message.get('state')
                client_rect = message.get('client_rect')
                overlay.clear()
                if client_rect:
                    overlay.set_position(client_rect['left'], client_rect['top'])
                    overlay.set_size(client_rect['w'], client_rect['h'])
                    overlay.bring_to_foreground()
                    render(client, overlay, api, items_db)
                overlay.update_overlay()
            elif message.get('type') == 'close':
                overlay.root.quit()
                return
        except queue.Empty:
            pass
        overlay.root.after(10, process_gui_queue)

    combat_loop_manager = HotkeyManager(HOTKEY_START_FIGHT, f"ctrl+{HOTKEY_START_FIGHT}")
    combat_loop_manager.register_hotkeys(lambda stop_event: enable_combat_mode(stop_event, gui_queue))

    print("Press Ctrl+C in the console to exit.")
    
    def sigint_handler(sig, frame):
        print("\nInterrupted! Shutting down...")
        overlay.root.destroy()

    signal.signal(signal.SIGINT, sigint_handler)

    overlay.root.after(10, process_gui_queue)
    overlay.root.mainloop()

    print("Script finished.")