import json
import os
import requests
from typing import Optional, Dict, List, Any
import time
import logging
from enum import IntEnum

class OSRSItems:
    def __init__(self):
        self.items_db: Dict[str, Dict[str, Any]] = {}
        self.name_to_id: Dict[str, str] = {}
        self.metadata_cache: Dict[int, Optional[Dict[str, Any]]] = {}
        self.db_path = os.path.join(os.path.dirname(__file__), 'data', 'items.json')
        self.last_update_path = os.path.join(os.path.dirname(__file__), 'data', 'last_update')
        self._load_or_fetch_database()
        
    def _load_or_fetch_database(self):
        """Load item database from file or fetch from OSRS Wiki API if not exists or outdated"""
        needs_update = True
        
        if os.path.exists(self.db_path) and os.path.exists(self.last_update_path):
            try:
                # Check if cache is still valid (less than 24 hours old)
                with open(self.last_update_path, 'r') as f:
                    last_update = int(f.read().strip())
                    if time.time() - last_update < 86400:
                        with open(self.db_path, 'r') as f:
                            self.items_db = json.load(f)
                            self._build_name_index()
                            needs_update = False
            except:
                logging.warning("Failed to load items database or cache expired, fetching fresh data...")
                
        if needs_update:
            self._fetch_and_save_database()

    def _fetch_and_save_database(self):
        """Fetch items from OSRS Wiki API and save to local file"""
        try:
            # OSRS Wiki API endpoint for item mapping
            url = "https://prices.runescape.wiki/api/v1/osrs/mapping"
            headers = {
                'User-Agent': 'OSRSMacroSDK/1.0 ItemDB',
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            items = response.json()
            
            # Convert list to dictionary with item ID as key and add additional fields
            self.items_db = {
                str(item['id']): {
                    'id': item['id'],
                    'name': item['name'],
                    'examine': item.get('examine'),
                    'members': item.get('members', False),
                    'tradeable': item.get('tradeable', False),
                    'tradeable_on_ge': item.get('tradeable_on_ge', False),
                    'stackable': item.get('stackable', False),
                    'noted': item.get('noted', False),
                    'noteable': item.get('noteable', False),
                    'linked_id_item': item.get('linked_id_item'),
                    'linked_id_noted': item.get('linked_id_noted'),
                    'linked_id_placeholder': item.get('linked_id_placeholder')
                } 
                for item in items
            }
            
            # Build the name to ID index
            self._build_name_index()
            
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Save to file
            with open(self.db_path, 'w') as f:
                json.dump(self.items_db, f)
                
            # Update timestamp
            with open(self.last_update_path, 'w') as f:
                f.write(str(int(time.time())))
                
        except Exception as e:
            logging.error(f"Error fetching items database: {str(e)}")
            
    def _build_name_index(self):
        """Build an index of item names to IDs for faster lookups"""
        self.name_to_id = {
            item['name'].lower(): item_id 
            for item_id, item in self.items_db.items()
        }

    def get_item_info(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Get full item information by ID"""
        return self.items_db.get(str(item_id))

    def get_item_name(self, item_id: int) -> Optional[str]:
        """Get item name by ID"""
        item = self.get_item_info(item_id)
        return item.get('name') if item else None

    def get_item_examine(self, item_id: int) -> Optional[str]:
        """Get item examine text by ID"""
        item = self.get_item_info(item_id)
        return item.get('examine') if item else None

    def is_tradeable(self, item_id: int) -> bool:
        """Check if item is tradeable"""
        item = self.get_item_info(item_id)
        return bool(item and item.get('tradeable'))

    def get_item_members(self, item_id: int) -> bool:
        """Check if item is members-only"""
        item = self.get_item_info(item_id)
        return bool(item and item.get('members'))
        
    def get_item_id(self, name: str) -> Optional[int]:
        """Get item ID by exact name match"""
        item_id = self.name_to_id.get(name.lower())
        return int(item_id) if item_id else None

    def search_items(self, name: str) -> List[Dict[str, Any]]:
        """Search items by name (case-insensitive partial match)"""
        name = name.lower()
        return [
            item for item in self.items_db.values()
            if name in item['name'].lower()
        ]
        
    def get_tradeable_items(self) -> List[Dict[str, Any]]:
        """Get all tradeable items"""
        return [
            item for item in self.items_db.values()
            if item.get('tradeable', False)
        ]
        
    def get_members_items(self) -> List[Dict[str, Any]]:
        """Get all members-only items"""
        return [
            item for item in self.items_db.values()
            if item.get('members', False)
        ]
        
    def get_stackable_items(self) -> List[Dict[str, Any]]:
        """Get all stackable items"""
        return [
            item for item in self.items_db.values()
            if item.get('stackable', False)
        ]

    def get_item_metadata(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed item metadata from the local 'data/items/{id}.json' files."""
        # Check cache first
        if item_id in self.metadata_cache:
            return self.metadata_cache[item_id]

        # Construct file path
        metadata_path = os.path.join(os.path.dirname(__file__), 'data', 'items', f'{item_id}.json')

        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                self.metadata_cache[item_id] = metadata # Cache the loaded data
                return metadata
        except FileNotFoundError:
            self.metadata_cache[item_id] = None # Cache the miss
            return None
        except Exception as e:
            logging.error(f"Error loading metadata for item {item_id}: {str(e)}")
            self.metadata_cache[item_id] = None # Cache the miss
            return None


# Common OSRS item IDs
class OSRSItemID:
    # Runes
    AIR_RUNE = 556
    WATER_RUNE = 555
    EARTH_RUNE = 557
    FIRE_RUNE = 554
    MIND_RUNE = 558
    CHAOS_RUNE = 562
    DEATH_RUNE = 560
    BLOOD_RUNE = 565
    NATURE_RUNE = 561
    LAW_RUNE = 563
    COSMIC_RUNE = 564
    BODY_RUNE = 559
    SOUL_RUNE = 566
    ASTRAL_RUNE = 9075
    WRATH_RUNE = 21880

    # Currency
    COINS = 995
    PLATINUM_TOKEN = 13204

    # Common items
    BONES = 526
    DRAGON_BONES = 536
    PURE_ESSENCE = 7936
    SPADE = 952
    BUCKET = 1925
    ROPE = 954
    TINDERBOX = 590
    
    # Potions
    PRAYER_POTION_4 = 2434
    SUPER_RESTORE_4 = 3024
    STAMINA_POTION_4 = 12625
    
    # Basic combat equipment
    BRONZE_DAGGER = 1205
    IRON_DAGGER = 1203
    STEEL_DAGGER = 1207
    BLACK_DAGGER = 1217
    MITHRIL_DAGGER = 1209
    ADAMANT_DAGGER = 1211
    RUNE_DAGGER = 1213
    DRAGON_DAGGER = 1215
    
    # Basic arrows
    BRONZE_ARROW = 882
    IRON_ARROW = 884
    STEEL_ARROW = 886
    MITHRIL_ARROW = 888
    ADAMANT_ARROW = 890
    RUNE_ARROW = 892
    DRAGON_ARROW = 11212
    
    # Food
    SHRIMP = 315
    COOKED_CHICKEN = 2140
    BREAD = 2309
    SALMON = 329
    LOBSTER = 379
    SWORDFISH = 373
    SHARK = 385
    
    # Basic armor
    BRONZE_PLATEBODY = 1117
    IRON_PLATEBODY = 1115
    STEEL_PLATEBODY = 1119
    BLACK_PLATEBODY = 1125
    MITHRIL_PLATEBODY = 1121
    ADAMANT_PLATEBODY = 1123
    RUNE_PLATEBODY = 1127
    
    # Tools
    BRONZE_PICKAXE = 1265
    IRON_PICKAXE = 1267
    STEEL_PICKAXE = 1269
    BLACK_PICKAXE = 12297
    MITHRIL_PICKAXE = 1273
    ADAMANT_PICKAXE = 1271
    RUNE_PICKAXE = 1275
    DRAGON_PICKAXE = 11920
    
    BRONZE_AXE = 1351
    IRON_AXE = 1349
    STEEL_AXE = 1353
    BLACK_AXE = 1361
    MITHRIL_AXE = 1355
    ADAMANT_AXE = 1357
    RUNE_AXE = 1359
    DRAGON_AXE = 6739
