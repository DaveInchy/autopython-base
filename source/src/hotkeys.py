"""
This module provides a simple framework for managing global hotkeys for scripts.
"""

import keyboard
import threading
import time

class HotkeyManager:
    """
    Manages the lifecycle of a script through global hotkeys.
    """

    def __init__(self, start_hotkey: str, stop_hotkey: str):
        self.start_hotkey = start_hotkey
        self.stop_hotkey = stop_hotkey
        self.stop_event = threading.Event()
        self.execution_thread = None
        self.loop_function = None

    def set_stop_event(self, stop_event: threading.Event):
        self.stop_event = stop_event

    def _start_loop(self):
        """Internal method to start the execution loop."""
        if self.execution_thread and self.execution_thread.is_alive():
            print("Loop is already running.")
            return

        print(f"Hotkey '{self.start_hotkey}' detected. Starting loop...")
        self.stop_event.clear()
        self.execution_thread = threading.Thread(target=self.loop_function, args=(self.stop_event,))
        self.execution_thread.start()
        print("Loop started.")

    def _stop_loop(self):
        """Internal method to stop the execution loop."""
        if self.execution_thread and self.execution_thread.is_alive():
            print(f"Hotkey '{self.stop_hotkey}' detected. Stopping loop...")
            self.stop_event.set()
            # self.execution_thread.join() # Avoid joining here to make the stop action non-blocking
            print("Loop stop signal sent.")
        else:
            print("Loop is not currently running.")

    def register_hotkeys(self, loop_function):
        """
        Registers the hotkeys and the main loop function.

        Args:
            loop_function: The function to be executed in a loop. 
                           It must accept a threading.Event as its first argument, 
                           which will be used to signal when to stop.
        """
        self.loop_function = loop_function
        keyboard.add_hotkey(self.start_hotkey, self._start_loop)
        keyboard.add_hotkey(self.stop_hotkey, self._stop_loop)
        print(f"Hotkeys registered. Press '{self.start_hotkey}' to start and '{self.stop_hotkey}' to stop.")

    def wait_for_exit(self):
        """
        Waits for a keyboard interrupt to exit the script gracefully.
        """
        try:
            print("Listening for hotkeys. Press Ctrl+C to exit.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nExiting script.")
            self._stop_loop() # Ensure the loop is stopped on exit
