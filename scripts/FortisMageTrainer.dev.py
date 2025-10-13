
import random
import time
import threading
import pyautogui
import keyboard  # Use the keyboard library for global hotkeys
import tkinter as tk
from tkinter import messagebox
import os
from src.game_screen import GameScreen
from src.xp_tracker import XPTracker
from src.client_window import RuneLiteClientWindow

# Example :: > move_to_color.search(color='229,194,105', tolerance=10, spectrum_range=[200, 255, 0, 50, 0, 50])

# --- Configuration ---
HOTKEY_START = 'ctrl+shift+r'
HOTKEY_STOP = 'ctrl+r'
WAIT_INTERVAL = 2  # Wait time between loops (0.4 * 5)

# --- Global variables for managing state ---
stop_event = threading.Event()
execution_thread = None
xp_tracker_thread = None
xp_tracker = None  # Global XPTracker instance

def show_info_popup(title, message):
    """Displays a non-blocking popup message."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.call('wm', 'attributes', '.', '-topmost', True) # Make popup appear on top
    messagebox.showinfo(title, message)
    root.destroy()

def execute_single_sequence():
    """Executes one iteration of the mouse and keyboard actions, using client window offsets."""
    client = RuneLiteClientWindow()
    client.bring_to_foreground()
    rect = client.get_rect()
    # Assume client is right half of 1080p: 960x1080, inventory bottom right above taskbar
    # All coordinates are relative to the client window's top-left
    x0, y0 = rect['left'], rect['top']
    width, height = rect['w'], rect['h']

    # Example positions (tune as needed for your layout)
    # Inventory slot 1 (bottom right corner, above taskbar)
    inv_x = x0 + width - random.randint(180, 155)
    inv_y = y0 + height - random.randint(110, 85)
    # Alchemy spell (left of inventory)
    alch_x = x0 + width - random.randint(350, 320)
    alch_y = y0 + height - random.randint(110, 85)
    # Snare spell (upper left of spellbook area)
    snare_x = x0 + width - random.randint(350, 320)
    snare_y = y0 + height - random.randint(300, 270)
    # Teleport spell (upper right of spellbook area)
    tele_x = x0 + width - random.randint(120, 90)
    tele_y = y0 + height - random.randint(300, 270)

    # 1. Store current mouse position
    original_x, original_y = pyautogui.position()

    # 2. Press '1' key (Open Magic Tab)
    pyautogui.press('1')

    # 3. Move and click at the Alchemy Spell position
    time.sleep(random.uniform(0.05, 0.2))
    pyautogui.moveTo(alch_x, alch_y)
    pyautogui.click()

    # 4. Move and click at the Inventory position (Slot 1 Inventory)
    time.sleep(random.uniform(0.1, 0.4))
    pyautogui.moveTo(inv_x, inv_y)
    pyautogui.click()

    # 5. Press '1' key (Open Magic Tab)
    pyautogui.press('1')

    # 6. Move and click at the Snare Spell position
    time.sleep(random.uniform(0.05, 0.2))
    pyautogui.moveTo(snare_x, snare_y)
    pyautogui.click()

    # 7. Try to find and click the guard
    time.sleep(random.uniform(0.1, 0.4))
    game_screen = GameScreen()
    guard_color = (187,169,117)  # Example color value, replace with actual
    guard_pos = game_screen.move_to_color(color=guard_color, spectrum_range=[187, 190, 169, 175, 117, 120])
    if guard_pos:
        guard_x, guard_y = guard_pos[0], guard_pos[1]
        print(f"Guard found at ({guard_x}, {guard_y}), clicking to snare.")
        pyautogui.moveTo(guard_x, guard_y)
        pyautogui.click()
    else:
        print("No guard found to snare.")

    # 8. Press '1' key (Open Magic Tab)
    pyautogui.press('1')

    # 9. Move and click at the Teleport Spell position
    time.sleep(random.uniform(0.6, 3.6))
    pyautogui.moveTo(tele_x, tele_y)
    pyautogui.click()

    time.sleep(random.uniform(0.5, 1.2))

def sequence_loop():
    """The main loop that repeatedly calls the sequence function."""
    while not stop_event.is_set():
        execute_single_sequence()
        print(f"--- Waiting for {WAIT_INTERVAL} seconds... (Press CTRL+R to stop) ---")
        for _ in range(int(WAIT_INTERVAL / 0.1)):
            if stop_event.is_set():
                break
            time.sleep(0.1)
    print("\nLoop has been stopped.")
    show_info_popup("Sequence Stopped", "The automated loop has been stopped successfully.")

def start_loop():
    """Starts the sequence loop and XP tracker in new threads."""
    global execution_thread, xp_tracker_thread, xp_tracker
    if execution_thread and execution_thread.is_alive():
        print("Loop is already running.")
        return

    print("\nHotkey Detected: Starting loop...")
    stop_event.clear()
    
    # Start XP tracker (specifically for Magic skill)
    xp_tracker = XPTracker(skill_name='MAGIC')
    
    if xp_tracker.using_runelite:
        print("Successfully connected to RuneLite API!")
    else:
        print("RuneLite API not available, falling back to OCR...")
    
    xp_tracker_thread = threading.Thread(target=xp_tracker.run)
    xp_tracker.stop_event.clear()
    xp_tracker_thread.start()
    
    # Start main bot loop
    execution_thread = threading.Thread(target=sequence_loop)
    execution_thread.start()
    print("Sequence Started\nThe loop has started.\nPress CTRL+R to stop.")

def stop_loop():
    """Signals all threads to stop."""
    global xp_tracker_thread
    if execution_thread and execution_thread.is_alive():
        print("\nHotkey Detected: Stopping loop...")
        stop_event.set()
        if xp_tracker_thread and xp_tracker_thread.is_alive():
            xp_tracker.stop_event.set()
            xp_tracker_thread.join()
    else:
        print("Loop is not currently running.")

def main():
    """Sets up the keyboard hotkeys and runs the script."""
    print("Script is running and listening for hotkeys.")
    print("-"*10)
    print("Press CTRL+SHIFT+R to START the sequence loop.")
    print("Press CTRL+R to STOP the sequence loop.")
    print("Press CTRL+C here to exit the script entirely.")

    # Register hotkeys using the keyboard library
    keyboard.add_hotkey(HOTKEY_START, start_loop)
    keyboard.add_hotkey(HOTKEY_STOP, stop_loop)

    try:
        keyboard.wait()  # Wait forever, listening for hotkeys
    except KeyboardInterrupt:
        print("\nExiting script.")

if __name__ == "__main__":
    main()