import pyautogui
import time
import threading
import keyboard

from src.client_window import RuneLiteClientWindow
from src.ui_utils import UIInteraction, HumanizedGridClicker

# --- Configuration ---
GEAR_SLOTS = [1, 2, 5, 6, 9, 10, 13] # Inventory slots to click
CLICK_DELAY = 0.05 # Delay between clicks in seconds
HOTKEY_SWAP_GEAR = 'ctrl+alt+g' # Hotkey to trigger gear swap

# --- Global variables for managing state ---
stop_event = threading.Event()
execution_thread = None

def swap_gear():
    """Swaps gear by clicking specified inventory slots with human-like randomization."""
    print("[GearSwapper] Initiating gear swap...")
    
    # Store original mouse position
    original_x, original_y = pyautogui.position()

    client = RuneLiteClientWindow()
    client.bring_to_foreground()
    time.sleep(0.1) # Give window time to come to foreground

    # Press F2 to open inventory tab
    pyautogui.press('f2')
    time.sleep(0.1) # Give game time to switch tabs

    # Initialize UIInteraction for human-like clicks
    # Note: For a real bot, you'd pass an existing overlay if one is active
    # For this standalone script, we'll create a dummy one if needed, or just skip visual feedback
    # For now, we'll assume no overlay is passed, so no visual feedback for this script.
    # If you want visual feedback, you'd need to pass an active WindowOverlay instance.
    ui_interaction = UIInteraction(HumanizedGridClicker(), None, client) # Pass client for dimensions

    for slot in GEAR_SLOTS:
        if stop_event.is_set():
            print("[GearSwapper] Gear swap interrupted.")
            break
        print(f"[GearSwapper] Clicking inventory slot {slot}...")
        ui_interaction.click_inventory_slot(slot)
        time.sleep(CLICK_DELAY)

    # Return mouse to original position
    pyautogui.moveTo(original_x, original_y)
    print("[GearSwapper] Gear swap complete. Mouse returned to original position.")

def start_gear_swapper_loop():
    global execution_thread
    if execution_thread and execution_thread.is_alive():
        print("[GearSwapper] Gear swapper is already running.")
        return

    print(f"[GearSwapper] Hotkey Detected: Starting gear swap loop. Press {HOTKEY_SWAP_GEAR} to swap.")
    stop_event.clear()
    execution_thread = threading.Thread(target=swap_gear)
    execution_thread.start()

def stop_gear_swapper_loop():
    if execution_thread and execution_thread.is_alive():
        print("[GearSwapper] Hotkey Detected: Stopping gear swap loop.")
        stop_event.set()
    else:
        print("[GearSwapper] Gear swapper is not currently running.")


if __name__ == "__main__":
    print("--- Gear Swapper Script ---")
    print(f"Press {HOTKEY_SWAP_GEAR} to perform a gear swap.")
    print("Press Ctrl+C in this terminal to exit the script.")

    # Register hotkey
    keyboard.add_hotkey(HOTKEY_SWAP_GEAR, swap_gear)

    try:
        keyboard.wait() # Keep script running to listen for hotkeys
    except KeyboardInterrupt:
        print("\n[GearSwapper] Exiting script.")
        stop_gear_swapper_loop() # Ensure any running swap is signaled to stop