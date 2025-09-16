from src.client_window import RuneLiteClientWindow
from src.ui_utils import ResizableInventoryGrid
import pyautogui
import time

def shift_click_all_inventory_slots(delay=0.05):
    """
    Shift-click every inventory slot (1-28) as fast as possible in resizable mode.
    """
    client = RuneLiteClientWindow()
    client.bring_to_foreground()
    rect = client.get_rect()
    for slot in range(1, 29):
        x, y = ResizableInventoryGrid.get_slot_xy(slot, rect)
        print(f"Shift-clicking slot {slot} at ({x}, {y})")
        pyautogui.keyDown('shift')
        pyautogui.click(x, y)
        pyautogui.keyUp('shift')
        time.sleep(delay)

def click_inventory_slot(slot):
    """
    Click a specific inventory slot (1-28) in resizable mode.
    """
    if not (1 <= slot <= 28):
        raise ValueError("Slot must be between 1 and 28")
    client = RuneLiteClientWindow()
    client.bring_to_foreground()
    rect = client.get_rect()
    x, y = ResizableInventoryGrid.get_slot_xy(slot, rect)
    print(f"Clicking slot {slot} at ({x}, {y})")
    pyautogui.click(x, y)

def disable_user_mouse_input():
    """
    Disable user mouse input temporarily to prevent interference.
    """
    print("User mouse input disabled temporarily.")
    pyautogui.FAILSAFE = False  # Disable failsafe for uninterrupted operation

def enable_user_mouse_input():
    """
    Re-enable user mouse input after being disabled.
    """
    print("User mouse input re-enabled.")
    pyautogui.FAILSAFE = True  # Re-enable failsafe

def get_current_equipped_combat_style():
    return "MAGE" # or "RANGE";

def equip_mage_gear():
    """
    Example function to equip mage gear by clicking specific inventory slots.
    Adjust slot numbers as needed based on your inventory layout.
    """

    # Disable user mouse input to prevent interference
    disable_user_mouse_input()

    # Example slot numbers for mage gear (adjust as necessary)
    mage_gear_slots = [1, 2, 5, 6, 9, 10, 13]
    for slot in mage_gear_slots:
        click_inventory_slot(slot)
    
    enable_user_mouse_input()

def equip_range_gear():
    """
    Example function to equip range gear by clicking specific inventory slots.
    Adjust slot numbers as needed based on your inventory layout.
    """
    disable_user_mouse_input()
    
    range_gear_slots = [1, 2, 5, 6, 9, 10, 13]
    for slot in range_gear_slots:
        click_inventory_slot(slot)
    
    enable_user_mouse_input()

if __name__ == "__main__":
    equip_range_gear();
    equip_mage_gear();
