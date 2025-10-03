import requests
import json
import time
from typing import Optional, Dict, Any, List, Tuple
import logging
from .osrs_items import OSRSItems, OSRSItemID

class RuneLiteAPI:
    def __init__(self, auth_token=None):
        """
        Initialize RuneLite API client
        :param auth_token: The RuneLite API authentication token from Settings > Enable API
        """
        self.base_url = "http://localhost:8080"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        })
        
        if auth_token:
            self.session.headers.update({
                'RUNELITE-AUTH': auth_token
            })
            
        self._last_request_time = 0
        self._request_delay = 0.05  # Minimum delay between requests
        
        # Initialize item database
        self.items_db = OSRSItems()
        
    def _rate_limit(self):
        """Ensure minimum delay between requests"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._request_delay:
            time.sleep(self._request_delay - time_since_last)
        self._last_request_time = time.time()

    def _make_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make a request to the RuneLite API with rate limiting"""
        try:
            self._rate_limit()
            url = f"{self.base_url}/{endpoint}"
            response = self.session.get(url, timeout=2)
            if response.status_code == 200:
                return response.json()
            return None
        except (requests.RequestException, json.JSONDecodeError) as e:
            logging.debug(f"Failed to fetch {endpoint}: {str(e)}")
            return None

    def get_xp(self) -> Optional[Dict[str, int]]:
        """Get XP for all skills"""
        data = self._make_request("xp")
        if data and isinstance(data, dict):
            return data
        return None

    def get_skill_xp(self, skill: str) -> Optional[int]:
        """Get XP for a specific skill"""
        stats = self.get_stats()
        if stats and skill.upper() in stats:
            return stats[skill.upper()]['xp']
        return None

    def get_inventory(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get inventory contents with item names
        Returns list of items with their IDs, names, and quantities
        Example: [{"id": 556, "name": "Air rune", "quantity": 1000}, ...]
        """
        items = self._make_request("inventory")
        if not items:
            return None
            
        # Add item names to the data
        for item in items:
            item_info = self.items_db.get_item_info(item['id'])
            if item_info:
                item['name'] = item_info['name']
                item['examine'] = item_info.get('examine')
                item['tradeable'] = item_info.get('tradeable', False)
                item['members'] = item_info.get('members', False)
            else:
                item['name'] = f"Unknown item ({item['id']})"
                
        return items
    
    def get_equipment(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get equipped items with names
        Returns list of equipped items with their IDs, names, and quantities
        Empty slots have id=-1
        """
        items = self._make_request("equipment")
        if not items:
            return None
            
        # Add item names to the data
        for item in items:
            if item['id'] != -1:
                item_info = self.items_db.get_item_info(item['id'])
                if item_info:
                    item['name'] = item_info['name']
                    item['examine'] = item_info.get('examine')
                    item['tradeable'] = item_info.get('tradeable', False)
                    item['members'] = item_info.get('members', False)
                else:
                    item['name'] = f"Unknown item ({item['id']})"
            else:
                item['name'] = "Empty slot"
                
        return items
        
    def has_item_in_inventory(self, item_id: int) -> Optional[bool]:
        """Check if a specific item is in the inventory"""
        inventory = self.get_inventory()
        if not inventory:
            return None
        return any(item['id'] == item_id for item in inventory)
        
    def get_item_quantity_in_inventory(self, item_id: int) -> Optional[int]:
        """Get the quantity of a specific item in inventory"""
        inventory = self.get_inventory()
        if not inventory:
            return None
        for item in inventory:
            if item['id'] == item_id:
                return item['quantity']
        return 0

    def get_all_runes_in_inventory(self) -> Dict[str, int]:
        """Get all runes in inventory with their quantities"""
        rune_ids = [
            OSRSItemID.AIR_RUNE, OSRSItemID.WATER_RUNE, OSRSItemID.EARTH_RUNE,
            OSRSItemID.FIRE_RUNE, OSRSItemID.MIND_RUNE, OSRSItemID.CHAOS_RUNE,
            OSRSItemID.DEATH_RUNE, OSRSItemID.BLOOD_RUNE, OSRSItemID.NATURE_RUNE,
            OSRSItemID.LAW_RUNE, OSRSItemID.COSMIC_RUNE, OSRSItemID.BODY_RUNE,
            OSRSItemID.SOUL_RUNE, OSRSItemID.ASTRAL_RUNE, OSRSItemID.WRATH_RUNE
        ]
        
        runes = {}
        inventory = self.get_inventory()
        if inventory:
            for item in inventory:
                if item['id'] in rune_ids:
                    runes[self.items_db.get_item_name(item['id'])] = item['quantity']
        
        return runes

    def get_coins_in_inventory(self) -> Optional[int]:
        """Get total coins in inventory"""
        return self.get_item_quantity_in_inventory(OSRSItemID.COINS)

    def find_items_in_inventory(self, search: str) -> List[Dict[str, Any]]:
        """Search for items in inventory by name"""
        inventory = self.get_inventory()
        if not inventory:
            return []
            
        search = search.lower()
        return [
            item for item in inventory 
            if search in item.get('name', '').lower()
        ]

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get all player stats including boosts"""
        data = self._make_request("stats")
        if not data:
            return None
        
        # Convert list of stats to a more usable dictionary
        stats_dict = {}
        for stat in data:
            stats_dict[stat['stat'].upper()] = {
                'level': stat['level'],
                'boostedLevel': stat['boostedLevel'],
                'xp': stat['xp']
            }
        return stats_dict

    def get_health_points(self) -> Optional[int]:
        """Get current health points"""
        stats = self.get_stats()
        if stats and 'HITPOINTS' in stats:
            return stats['HITPOINTS']['boostedLevel']
        return None

    def get_prayer_points(self) -> Optional[int]:
        """Get current prayer points"""
        stats = self.get_stats()
        if stats and 'PRAYER' in stats:
            return stats['PRAYER']['boostedLevel']
        return None

    def get_energy(self) -> Optional[int]:
        """Get current run energy percentage"""
        stats = self.get_stats()
        if stats and 'RUN_ENERGY' in stats:
            return stats['RUN_ENERGY']['boostedLevel']
        return None
        
    def get_combat_stats(self) -> Optional[Dict[str, Dict[str, int]]]:
        """Get all combat-related stats"""
        stats = self.get_stats()
        if not stats:
            return None
            
        combat_skills = ['ATTACK', 'STRENGTH', 'DEFENCE', 'RANGED', 'MAGIC', 'HITPOINTS', 'PRAYER']
        return {skill: stats[skill] for skill in combat_skills if skill in stats}

    def get_world(self) -> Optional[int]:
        """Get current game world number"""
        return self._make_request("world")

    def get_npcs(self) -> Optional[List[Dict[str, Any]]]:
        """Get all NPCs in the scene"""
        return self._make_request("npcs")

    def is_logged_in(self) -> bool:
        """Check if player is logged in"""
        return self.get_stats() is not None