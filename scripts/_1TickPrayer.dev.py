import math # Not used directly for random, but kept if you have other math operations
import time
from src.hotkeys import HotkeyManager # Assuming this path is correct
import threading
import pyautogui
import random # Import the random module

tick = 0.4
max_deviation_percent = 0.0025 # 1.4% as per your 1.014, and 0.4% as per 0.996. Let's simplify
min_deviation_factor = 1 - max_deviation_percent # 0.986
max_deviation_factor = 1 + max_deviation_percent # 1.014

# Global variable to track the start time of the current synchronization period
# This helps us calculate the actual time elapsed more accurately
sync_period_start_time = time.time()

def main_loop(stop_event: threading.Event):
    global sync_period_start_time # Declare intent to modify global variable

    ticks_in_current_period = 0
    sync_period_start_time = time.time() # Initialize on loop start

    while not stop_event.is_set():
        current_tick_start_time = time.time()

        # Introduce random deviation for the current tick
        deviation_factor = random.uniform(min_deviation_factor, max_deviation_factor)
        sleep_duration = deviation_factor * tick
        time.sleep(sleep_duration)

        pyautogui.click() # Simulate a click for the current tick -> Off
        pyautogui.click() # Simulate a click for the current tick -> On

        ticks_in_current_period += 1

        # Check for synchronization point
        if ticks_in_current_period % 4 == 0:
            # Calculate ideal time for this period
            ideal_period_duration = ticks_in_current_period * tick

            # Calculate actual time elapsed since the start of this sync period
            actual_period_duration = time.time() - sync_period_start_time

            # Calculate the overall deviation for this period
            overall_deviation = actual_period_duration - ideal_period_duration

            print(f"Syncing after {ticks_in_current_period} ticks.")
            print(f"Ideal duration: {ideal_period_duration:.3f}s, Actual duration: {actual_period_duration:.3f}s")
            print(f"Overall deviation: {overall_deviation:.3f}s")

            # Adjust the *next* sleep to compensate for the deviation
            # If overall_deviation is positive, we are running fast, so wait longer
            # If overall_deviation is negative, we are running slow, so wait less (but not negative sleep)
            # A simple approach is to try and "catch up" or "wait for" the ideal time.

            # This part is crucial for synchronization.
            # Instead of sleeping *extra* at the end of the period,
            # we should aim to have the *next* tick start exactly on time.
            # The next tick's sleep duration will be adjusted.
            
            # To sync, we reset the start time for the next period.
            sync_period_start_time = time.time()
            ticks_in_current_period = 0 # Reset tick counter for the new period

            # You could also consider a more sophisticated catch-up:
            # If overall_deviation > 0 (we're ahead), wait for the remainder
            # time_to_wait = overall_deviation
            # if time_to_wait > 0:
            #     time.sleep(time_to_wait)
            # This would put you precisely back on schedule *after* the clicks of the current period.
            # However, your current desired behavior seems to be "occasionally sync up",
            # which implies resetting the *start* of the next sequence of ticks.

    return

if __name__ == "__main__":
    hk = "."
    hk = HotkeyManager(hk, f"ctrl+{hk}")
    hk.register_hotkeys(main_loop)
    hk.wait_for_exit()