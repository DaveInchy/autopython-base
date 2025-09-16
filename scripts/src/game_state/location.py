from typing import Optional, Dict, List, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..api.runelite_api import RuneLiteAPI


@dataclass
class Coordinate:
    x: int
    y: int
    plane: int = 0  # Game level/floor
    
@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int
    
@dataclass
class WorldPoint:
    x: int
    y: int
    plane: int
    
@dataclass
class LocalPoint:
    x: int
    y: int

@dataclass
class GameObject:
    """Represents an interactable game object with its location and bounds"""
    id: int
    name: str
    location: WorldPoint
    local_location: LocalPoint
    canvas_location: Tuple[int, int]  # (x, y) on screen
    bounding_box: BoundingBox
    orientation: int
    distance: float  # Distance from player

@dataclass
class NPC:
    """Represents an NPC with its location and animation state"""
    id: int
    name: str
    location: WorldPoint
    local_location: LocalPoint
    canvas_location: Tuple[int, int]
    bounding_box: BoundingBox
    animation: int
    orientation: int
    distance: float
    combat_level: int
    health_ratio: int
    health_scale: int
    
class GameState:
    """Access game world state including locations and objects"""
    
    def __init__(self, api: 'RuneLiteAPI'):
        self.api = api
        
    def get_player_location(self) -> Optional[WorldPoint]:
        """Get the player's current world location"""
        data = self.api._make_request("worldLocation")
        if not data:
            return None
        return WorldPoint(
            x=data['x'],
            y=data['y'],
            plane=data.get('plane', 0)
        )
        
    def get_local_location(self) -> Optional[LocalPoint]:
        """Get player's local coordinates (relative to current region)"""
        data = self.api._make_request("localLocation")
        if not data:
            return None
        return LocalPoint(
            x=data['x'],
            y=data['y']
        )
        
    def get_camera_angle(self) -> Optional[float]:
        """Get current camera angle in degrees"""
        data = self.api._make_request("camera")
        if not data:
            return None
        return data.get('yaw')
        
    def get_objects_in_vicinity(self, max_distance: int = 10) -> List[GameObject]:
        """Get all game objects within specified tiles of player"""
        data = self.api._make_request(f"objects?distance={max_distance}")
        if not data:
            return []
            
        objects = []
        for obj in data:
            objects.append(GameObject(
                id=obj['id'],
                name=obj.get('name', 'Unknown'),
                location=WorldPoint(
                    x=obj['worldLocation']['x'],
                    y=obj['worldLocation']['y'],
                    plane=obj['worldLocation'].get('plane', 0)
                ),
                local_location=LocalPoint(
                    x=obj['localLocation']['x'],
                    y=obj['localLocation']['y']
                ),
                canvas_location=(
                    obj['canvasLocation']['x'],
                    obj['canvasLocation']['y']
                ),
                bounding_box=BoundingBox(
                    x=obj['bounds']['x'],
                    y=obj['bounds']['y'],
                    width=obj['bounds']['width'],
                    height=obj['bounds']['height']
                ),
                orientation=obj.get('orientation', 0),
                distance=obj.get('distance', 0.0)
            ))
        return objects
        
    def get_npcs_in_vicinity(self, max_distance: int = 10) -> List[NPC]:
        """Get all NPCs within specified tiles of player"""
        data = self.api._make_request(f"npcs?distance={max_distance}")
        if not data:
            return []
            
        npcs = []
        for npc in data:
            npcs.append(NPC(
                id=npc['id'],
                name=npc.get('name', 'Unknown'),
                location=WorldPoint(
                    x=npc['worldLocation']['x'],
                    y=npc['worldLocation']['y'],
                    plane=npc['worldLocation'].get('plane', 0)
                ),
                local_location=LocalPoint(
                    x=npc['localLocation']['x'],
                    y=npc['localLocation']['y']
                ),
                canvas_location=(
                    npc['canvasLocation']['x'],
                    npc['canvasLocation']['y']
                ),
                bounding_box=BoundingBox(
                    x=npc['bounds']['x'],
                    y=npc['bounds']['y'],
                    width=npc['bounds']['width'],
                    height=npc['bounds']['height']
                ),
                orientation=npc.get('orientation', 0),
                distance=npc.get('distance', 0.0),
                combat_level=npc.get('combatLevel', 0),
                health_ratio=npc.get('healthRatio', 0),
                health_scale=npc.get('healthScale', 0)
            ))
        return npcs
        
    def get_ground_items_in_vicinity(self, max_distance: int = 10) -> List[Dict[str, Any]]:
        """Get all ground items within specified tiles of player"""
        return self.api._make_request(f"groundItems?distance={max_distance}") or []
        
    def is_point_on_screen(self, x: int, y: int) -> bool:
        """Check if a canvas point is currently visible on screen"""
        data = self.api._make_request(f"pointOnScreen?x={x}&y={y}")
        return bool(data and data.get('onScreen', False))
