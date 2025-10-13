import random
import time
import pyautogui
from src.client_window import RuneLiteClientWindow
from src.ui_utils import MouseActionOCR

# --- Configuration ---
WAIT_INTERVAL = 1.5  # seconds between actions

# Example actions to randomly perform
ACTIONS = [
    'Open Magic Tab',
    'Open Inventory',
    'Move Mouse Randomly',
    'Check Primary Action',
]

def random_player_pattern():
    """
    Simulates random player-like actions using client window offsets and OCR.
    """
    client = RuneLiteClientWindow()
    client.bring_to_foreground()
    rect = client.get_rect()
    for _ in range(10):  # Perform 10 random actions
        action = random.choice(ACTIONS)
        if action == 'Open Magic Tab':
            pyautogui.press('1')
            print('Pressed 1 (Magic Tab)')
        elif action == 'Open Inventory':
            pyautogui.press('2')
            print('Pressed 2 (Inventory)')
        elif action == 'Move Mouse Randomly':
            x = rect[1] + random.randint(50, rect['w'] - 50)
            y = rect[2] + random.randint(50, rect['h'] - 50)
            pyautogui.moveTo(x, y, duration=random.uniform(0.1, 0.4))
            print(f'Moved mouse to ({x}, {y})')
        elif action == 'Check Primary Action':
            text = MouseActionOCR.get_primary_action_text(rect)
            print(f'Primary action text: {text}')
        time.sleep(WAIT_INTERVAL)

if __name__ == "__main__":
    print("Starting Random Player Patterns...")
    random_player_pattern()
    print("Done.")
