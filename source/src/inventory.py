"""
This module provides a centralized SDK for all inventory-related actions in OSRS,
including interacting with the inventory grid, finding items, and performing clicks.
"""

import pyautogui
import time
from typing import Optional, Tuple

from .client_window import RuneLiteClientWindow
from .runelite_api import RuneLiteAPI
from .ui_utils import ResizableInventoryGrid

class Inventory:
    """
    Provides high-level functions for interacting with the player's inventory.
    """
    def __init__(self, client_window: RuneLiteClientWindow, runeLite_api: RuneLiteAPI):
        self.client = client_window
        self.api = runeLite_api

    def get_slot_coords(self, slot_number: int) -> Optional[Tuple[int, int]]:
        """
        Calculates the screen coordinates for a given inventory slot number (1-28).
        """
        if not (1 <= slot_number <= 28):
            print(f"Invalid inventory slot number: {slot_number}")
            return None
        
        rect = self.client.get_rect()
        return ResizableInventoryGrid.get_slot_xy(slot_number, rect)

    def click_slot(self, slot_number: int, bring_to_foreground: bool = True):
        """
        Clicks a specific inventory slot.
        """
        if bring_to_foreground:
            self.client.bring_to_foreground()
        
        coords = self.get_slot_coords(slot_number)
        if coords:
            print(f"Clicking slot {slot_number} at {coords}")
            pyautogui.click(coords[0], coords[1])

    def shift_click_slot(self, slot_number: int, bring_to_foreground: bool = True):
        """
        Shift-clicks a specific inventory slot.
        """
        if bring_to_foreground:
            self.client.bring_to_foreground()
            
        coords = self.get_slot_coords(slot_number)
        if coords:
            print(f"Shift-clicking slot {slot_number} at {coords}")
            pyautogui.keyDown('shift')
            pyautogui.click(coords[0], coords[1])
            pyautogui.keyUp('shift')

    def shift_click_all_slots(self, delay_between_clicks: float = 0.05):
        """
        Shift-clicks every inventory slot (1-28).
        """
        self.client.bring_to_foreground()
        for slot in range(1, 29):
            self.shift_click_slot(slot, bring_to_foreground=False)
            time.sleep(delay_between_clicks)

    def find_item(self, item_name: str) -> Optional[int]:
        """
        Finds an item in the inventory by name and returns its slot number.
        Returns None if the item is not found.
        """
        inventory_data = self.api.get_inventory()
        if not inventory_data:
            return None
        
        for i, item in enumerate(inventory_data):
            if item and item.get('name', '').lower() == item_name.lower():
                return i + 1 # Slots are 1-indexed
        return None

    def use_item(self, item_name: str):
        """
        Finds an item by name and clicks it.
        """
        slot = self.find_item(item_name)
        if slot:
            self.click_slot(slot)
