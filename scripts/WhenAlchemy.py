import random
import time
import threading
import pyautogui
import keyboard  # Use the keyboard library for global hotkeys
import tkinter as tk
from tkinter import messagebox

# --- Configuration ---
HOTKEY_START = 'ctrl+shift+r'
HOTKEY_STOP = 'ctrl+shift+c'
WAIT_INTERVAL = 2  # Wait time between loops (0.4 * 5)

# --- Global variables for managing state ---
stop_event = threading.Event()
execution_thread = None

def show_info_popup(title, message):
    """Displays a non-blocking popup message."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.call('wm', 'attributes', '.', '-topmost', True) # Make popup appear on top
    messagebox.showinfo(title, message)
    root.destroy()

def execute_single_sequence():
    """Executes one iteration of the mouse and keyboard actions."""
    print("--- Running sequence ---")
    # 1. Generate random numbers
    rand_y1 = random.randint(900, 920)
    rand_x1 = random.randint(1723, 1740)
    rand_y2 = random.randint(737, 763)
    rand_x2 = random.randint(1715, 1745)

    # 2. Store current mouse position
    original_x, original_y = pyautogui.position()

    # 3. Press '1' key
    pyautogui.press('1')

    # 4. Move and click at the first random position
    time.sleep(0.02)
    pyautogui.moveTo(rand_x1, rand_y1)
    pyautogui.click()

    # 5. Move and click at the second random position
    time.sleep(0.02)
    pyautogui.moveTo(rand_x2, rand_y2)
    pyautogui.click()

    # 6. Return the mouse to its original position
    pyautogui.moveTo(original_x, original_y)
    print("Sequence complete. Returning mouse.")

def sequence_loop():
    """The main loop that repeatedly calls the sequence function."""
    while not stop_event.is_set():
        execute_single_sequence()
        print(f"--- Waiting for {WAIT_INTERVAL} seconds... (Press CTRL+SHIFT+S to stop) ---")
        for _ in range(int(WAIT_INTERVAL / 0.1)):
            if stop_event.is_set():
                break
            time.sleep(0.1)
    print("\nLoop has been stopped.")
    show_info_popup("Sequence Stopped", "The automated loop has been stopped successfully.")

def start_loop():
    """Starts the sequence loop in a new thread."""
    global execution_thread
    if execution_thread and execution_thread.is_alive():
        print("Loop is already running.")
    else:
        print("\nHotkey Detected: Starting loop...")
        stop_event.clear()
        execution_thread = threading.Thread(target=sequence_loop)
        execution_thread.start()
        show_info_popup("Sequence Started", "The loop has started.\nPress CTRL+SHIFT+S to stop.")

def stop_loop():
    """Signals the execution thread to stop."""
    if execution_thread and execution_thread.is_alive():
        print("\nHotkey Detected: Stopping loop...")
        stop_event.set()
    else:
        print("Loop is not currently running.")

def main():
    """Sets up the keyboard hotkeys and runs the script."""
    print("Script is running and listening for hotkeys.")
    print("---------------------------------------------")
    print("Press CTRL+SHIFT+R to START the sequence loop.")
    print("Press CTRL+SHIFT+S to STOP the sequence loop.")
    print("---------------------------------------------")
    print("Close this terminal window or press CTRL+C here to exit the script entirely.")

    # Register hotkeys using the keyboard library
    keyboard.add_hotkey(HOTKEY_START, start_loop)
    keyboard.add_hotkey(HOTKEY_STOP, stop_loop)

    try:
        keyboard.wait()  # Wait forever, listening for hotkeys
    except KeyboardInterrupt:
        print("\nExiting script.")

if __name__ == "__main__":
    main()