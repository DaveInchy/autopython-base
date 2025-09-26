import random
import time
import threading
import pyautogui
import keyboard
import tkinter as tk
from tkinter import messagebox

from src.game_screen import GameScreen
from src.xp_tracker import XPTracker
from src.client_window import RuneLiteClientWindow

# --- Configuration ---
HOTKEY_START = 'ctrl+shift+r'
HOTKEY_STOP = 'ctrl+r'
WAIT_INTERVAL = 2  # Wait time between loops

# --- Global variables for managing state ---
stop_event = threading.Event()
execution_thread = None
xp_tracker_thread = None
xp_tracker = None

def show_info_popup(title, message):
    """Displays a non-blocking popup message."""
    root = tk.Tk()
    root.withdraw()
    root.call('wm', 'attributes', '.', '-topmost', True)
    messagebox.showinfo(title, message)
    root.destroy()

def execute_single_sequence():
    """Executes one iteration of the mouse and keyboard actions."""
    client = RuneLiteClientWindow()
    client.bring_to_foreground()
    rect = client.get_rect()
    if not rect:
        print("RuneLite window not found. Skipping sequence.")
        return

    x0, y0 = rect['left'], rect['top']
    width, height = rect['w'], rect['h']

    # Example positions (tune as needed for your layout)
    inv_x = x0 + width - random.randint(180, 155)
    inv_y = y0 + height - random.randint(110, 85)
    alch_x = x0 + width - random.randint(350, 320)
    alch_y = y0 + height - random.randint(110, 85)
    snare_x = x0 + width - random.randint(350, 320)
    snare_y = y0 + height - random.randint(300, 270)
    tele_x = x0 + width - random.randint(120, 90)
    tele_y = y0 + height - random.randint(300, 270)

    pyautogui.press('1')
    time.sleep(random.uniform(0.05, 0.2))
    pyautogui.moveTo(alch_x, alch_y)
    pyautogui.click()

    time.sleep(random.uniform(0.1, 0.4))
    pyautogui.moveTo(inv_x, inv_y)
    pyautogui.click()

    pyautogui.press('1')
    time.sleep(random.uniform(0.05, 0.2))
    pyautogui.moveTo(snare_x, snare_y)
    pyautogui.click()

    time.sleep(random.uniform(0.1, 0.4))
    game_screen = GameScreen()
    guard_color = (187, 169, 117)
    # The spectrum range should be tuned for accuracy
    guard_pos = game_screen.move_to_color(color=guard_color, spectrum_range=[180, 160, 110, 195, 180, 125], region=(x0, y0, x0+width, y0+height))
    if guard_pos:
        print(f"Guard found at ({guard_pos[0]}, {guard_pos[1]}), clicking to snare.")
        pyautogui.click()
    else:
        print("No guard found to snare.")

    pyautogui.press('1')
    time.sleep(random.uniform(0.6, 3.6))
    pyautogui.moveTo(tele_x, tele_y)
    pyautogui.click()
    time.sleep(random.uniform(0.5, 1.2))

def sequence_loop():
    """The main loop that repeatedly calls the sequence function."""
    while not stop_event.is_set():
        execute_single_sequence()
        print(f"--- Waiting for {WAIT_INTERVAL} seconds... (Press {HOTKEY_STOP} to stop) ---")
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
    
    xp_tracker = XPTracker(skill_name='MAGIC')
    if xp_tracker.using_runelite:
        print("Successfully connected to RuneLite API for XP tracking!")
    else:
        print("RuneLite API not available for XP tracking, falling back to OCR...")
    
    xp_tracker_thread = threading.Thread(target=xp_tracker.run)
    xp_tracker.stop_event.clear()
    xp_tracker_thread.start()
    
    execution_thread = threading.Thread(target=sequence_loop)
    execution_thread.start()
    print(f"Sequence Started. Press {HOTKEY_STOP} to stop.")

def stop_loop():
    """Signals all threads to stop."""
    global xp_tracker_thread
    if execution_thread and execution_thread.is_alive():
        print(f"\nHotkey Detected: Stopping loop...")
        stop_event.set()
        if xp_tracker_thread and xp_tracker_thread.is_alive():
            xp_tracker.stop_event.set()
            xp_tracker_thread.join()
    else:
        print("Loop is not currently running.")

def main():
    """Sets up the keyboard hotkeys and runs the script."""
    print("Fortis Mage Trainer is running and listening for hotkeys.")
    print("-"*20)
    print(f"Press {HOTKEY_START} to START the sequence loop.")
    print(f"Press {HOTKEY_STOP} to STOP the sequence loop.")
    print("Press CTRL+C here to exit the script entirely.")

    keyboard.add_hotkey(HOTKEY_START, start_loop)
    keyboard.add_hotkey(HOTKEY_STOP, stop_loop)

    try:
        keyboard.wait()  # Wait forever, listening for hotkeys
    except KeyboardInterrupt:
        print("\nExiting script.")

if __name__ == "__main__":
    main()