"""
This module provides a Player class to interact with the player character,
including health, prayer, and gear.
"""

import pyautogui
import time
import random

from .runelite_api import RuneLiteAPI
from .inventory import Inventory

class Player:
    """
    Represents the player and their actions.
    """

    def __init__(self, runeLite_api: RuneLiteAPI, inventory: Inventory):
        self.api = runeLite_api
        self.inventory = inventory

    def eat_food_if_needed(self, min_health: int, food_item_name: str = "Shark") -> bool:
        """
        Checks health via API and eats if below a threshold.
        """
        health = self.api.get_stats()["HITPOINTS"]['boostedLevel']
        if health is not None and health < min_health:
            print(f"Health is low ({health}), eating {food_item_name}.")
            food_slot = self.inventory.find_item(food_item_name)
            if food_slot:
                self.inventory.click_slot(food_slot)
                return True
            else:
                print(f"No {food_item_name} found in inventory!")
                return False
        return False

    def drink_prayer_potion_if_needed(self, min_prayer: int, potion_item_name: str = "Prayer potion") -> bool:
        """
        Checks prayer via API and drinks a prayer potion if below a threshold.
        """
        prayer_points = self.api.get_prayer_points()
        if prayer_points is not None and prayer_points < min_prayer:
            print(f"Prayer is low ({prayer_points}), drinking {potion_item_name}.")
            potion_slot = self.inventory.find_item(potion_item_name)
            if potion_slot:
                self.inventory.click_slot(potion_slot)
                return True
            else:
                print(f"No {potion_item_name} found in inventory!")
                return False
        return False

    def switch_prayer(self, prayer_name: str, prayer_coords: dict):
        """
        Switches to a specific prayer using screen coordinates.
        
        TODO: This should be updated to use the RuneLite API if possible, 
              or a more robust image recognition method.
        """
        coords = prayer_coords.get(prayer_name.upper().replace(' ', '_'))
        if coords:
            pyautogui.moveTo(coords[0], coords[1], duration=random.uniform(0.1, 0.3))
            pyautogui.click()
        else:
            print(f"Prayer {prayer_name} not found in coordinates mapping.")

    def switch_gear(self, gear_slots: list):
        """
        Equips gear by clicking a list of specified inventory slots.
        """
        self.inventory.client.bring_to_foreground()
        for slot in gear_slots:
            self.inventory.click_slot(slot, bring_to_foreground=False)
            time.sleep(random.uniform(0.05, 0.1))
