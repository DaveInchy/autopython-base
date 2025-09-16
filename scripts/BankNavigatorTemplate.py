from src.client_window import RuneLiteClientWindow
from src.ui_utils import MouseActionOCR
from src.xp_tracker import XPTracker
from src.runelite_api import RuneLiteAPI
import pyautogui
import time
from src.ui_utils import InventoryGrid, ResizableInventoryGrid

class BankNavigator:

    def execute_single_sequence(self):
        """
        Example: walk to bank (can be replaced with more complex logic).
        """
        self.client.bring_to_foreground()
        self.go_to_bank()

    def sequence_loop(self, stop_event=None, wait_interval=2):
        """
        Repeatedly go to bank until stopped (for testing or chaining with other scripts).
        """
        if stop_event is None:
            import threading
            stop_event = threading.Event()
        while not stop_event.is_set():
            self.execute_single_sequence()
            print(f"--- Waiting for {wait_interval} seconds before next bank run ---")
            for _ in range(int(wait_interval / 0.1)):
                if stop_event.is_set():
                    break
                time.sleep(0.1)
        print("\nBankNavigator loop stopped.")
    """
    Template for navigating to Edgeville bank from anywhere, using fastest available method.
    """
    def __init__(self):
        self.client = RuneLiteClientWindow()
        self.api = RuneLiteAPI()

    def has_item(self, item_name):
        """Check if the player has a specific item in inventory (RuneLite API)."""
        inventory = self.api.get_inventory()
        if not inventory:
            return False
        return any(item_name.lower() in (item['name'] or '').lower() for item in inventory)

    def use_item(self, item_name, action):
        self.client.bring_to_foreground()

        #1 first know where the item is in inventory by using the coordinates from ui_utils and the info we can get from the runelite API
        #2 then use pyautogui to move the mouse and right click on it
        #3 select the use action from the context menu based on standard pixel offsets
        #4 verify the "use" action is available by reading the menu with OCR
        #5 click the action

        """Simulate using an item (e.g., click on glory, ring of dueling, etc.)."""
        # call the api for inventory items
        inventory = self.api.get_inventory()
        if not inventory:
            print("[BankNavigator] Unable to read inventory from API.")
            return
        time.sleep(1)

        # check if item is in inventory
        hasItem = self.has_item(item_name)
        if hasItem:
            print(f"[BankNavigator] Using item: {item_name} with action: {action}")

        # get the items position in inventory
        item_index = next((i for i, item in enumerate(inventory) if item_name.lower() in (item['name'] or '').lower()), None)
        if item_index is None:
            print(f"[BankNavigator] Item {item_name} not found in inventory.")
            return
        
        # Calculate inventory slot position (assuming standard 4x7 grid, adjust as needed)
        row = item_index // 4
        col = item_index % 4
        slot_x, slot_y = ResizableInventoryGrid.get_slot_xy(item_index + 1, self.client.get_rect())
        pyautogui.moveTo(slot_x, slot_y, duration=0.2)
        pyautogui.rightClick()
        time.sleep(0.5)
        # Assuming the context menu opens below the cursor, click the action
        # This is a simplification; in practice, you'd want to read the menu with OCR
        action_offset_y = 20  # Adjust based on your menu layout
        pyautogui.moveRel(0, action_offset_y, duration=0.2)

        #verify the action was successful with ocr
        action_text = MouseActionOCR.get_primary_action_text(self.client.get_rect())
        if action_text and action.lower() in action_text.lower():
            print(f"[BankNavigator] Successfully initiated {action} on {item_name}.")
        else:
            print(f"[BankNavigator] Failed to verify {action} action on {item_name}. Detected action: {action_text}")
        
        time.sleep(1)

        pyautogui.click()


    def walk_to_bank(self):
        """Fallback: Simulate walking to Edgeville bank (stub)."""
        print("[BankNavigator] Walking to Edgeville bank...")
        # You would use minimap clicks, pathfinding, or color search here
        time.sleep(3)

    def go_to_bank(self):
        """
        Main method: chooses fastest method to Edgeville bank based on inventory.
        """
        # 1. Amulet of glory teleport
        if self.has_item('Amulet of glory'):
            print("[BankNavigator] Using Amulet of glory to teleport to Edgeville.")
            self.use_item('Amulet of glory', "Rub")
            # press 1, 2, 3, or 4 for Edgeville on your keyboard
            time.sleep(1)
            pyautogui.keyDown('1')

            return
        # 2. Ring of dueling to Ferox Enclave, then walk
        if self.has_item('Ring of dueling'):
            print("[BankNavigator] Using Ring of dueling to Ferox Enclave, then walking to Edgeville.")
            self.use_item('Ring of dueling', "Rub")
             # press 1, 2, 3, or 4 for Ferox Enclave on your keyboard
            time.sleep(1)
            

            self.walk_to_bank()
            return
        # 3. Home teleport to Edgeville (if available)
        if self.has_item('Teleport to house'):
            print("[BankNavigator] Using house teleport, then walking to Edgeville.")
            self.use_item('Teleport to house', "Break")
            self.walk_to_bank()
            return
        # 4. Fallback: walk from current location
        print("[BankNavigator] No fast travel items found, walking to Edgeville bank.")
        self.walk_to_bank()

if __name__ == "__main__":
    nav = BankNavigator()
    # Example: run a single bank trip
    nav.execute_single_sequence()
    # Example: run a loop (uncomment to use)
    # import threading
    # stop_event = threading.Event()
    # nav.sequence_loop(stop_event=stop_event, wait_interval=5)
