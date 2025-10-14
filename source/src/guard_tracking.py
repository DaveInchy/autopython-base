from typing import List, Optional, Tuple
from dataclasses import dataclass
from .runelite_api import RuneLiteAPI
from .game_state import GameState, WorldPoint, NPC

@dataclass
class BoundaryArea:
    min_x: int
    min_y: int
    max_x: int
    max_y: int
    allowed_plane: int = 0
    
    def contains_point(self, x: int, y: int, plane: int = 0) -> bool:
        """Check if a point is within the boundary"""
        return (
            self.min_x <= x <= self.max_x and
            self.min_y <= y <= self.max_y and
            plane == self.allowed_plane
        )
        
    def get_nearest_valid_point(self, x: int, y: int) -> Tuple[int, int]:
        """Get nearest point inside boundary if outside"""
        return (
            min(max(x, self.min_x), self.max_x),
            min(max(y, self.min_y), self.max_y)
        )
        
    @classmethod
    def from_center(cls, center_x: int, center_y: int, radius: int, plane: int = 0) -> 'BoundaryArea':
        """Create boundary area from center point and radius"""
        return cls(
            min_x=center_x - radius,
            max_x=center_x + radius,
            min_y=center_y - radius,
            max_y=center_y + radius,
            allowed_plane=plane
        )

class GuardTracker:
    """Track guards and maintain boundary restrictions"""
    
    def __init__(self, api: RuneLiteAPI, boundary: BoundaryArea = None):
        self.api = api
        self.game_state = GameState(api)
        self.boundary = boundary
        self.tracked_guards: List[NPC] = []
        
    def set_boundary_from_current_location(self, radius: int = 20):
        """Set boundary area centered on current location"""
        loc = self.game_state.get_player_location()
        if loc:
            self.boundary = BoundaryArea.from_center(
                center_x=loc.x,
                center_y=loc.y,
                radius=radius,
                plane=loc.plane
            )
            return True
        return False
        
    def is_within_boundary(self) -> bool:
        """Check if player is within boundary"""
        if not self.boundary:
            return True
            
        loc = self.game_state.get_player_location()
        if not loc:
            return False
            
        return self.boundary.contains_point(loc.x, loc.y, loc.plane)
        
    def get_nearby_guards(self, max_distance: int = 15) -> List[NPC]:
        """Get all guard NPCs in vicinity"""
        npcs = self.game_state.get_npcs_in_vicinity(max_distance)
        
        # Filter for guard NPCs (common guard NPC IDs)
        guard_ids = {
            3010,  # Guard
            3011,  # Guard
            3094,  # Guard (Falador)
            5919,  # Guard (Varrock)
            3408,  # Guard (Ardougne)
            3252,  # Guard (Al Kharid)
        }
        
        guards = [
            npc for npc in npcs
            if npc.id in guard_ids or 'guard' in npc.name.lower()
        ]
        
        # If boundary is set, only include guards within it
        if self.boundary:
            guards = [
                guard for guard in guards
                if self.boundary.contains_point(
                    guard.location.x,
                    guard.location.y,
                    guard.location.plane
                )
            ]
            
        self.tracked_guards = guards
        return guards
        
    def get_nearest_guard(self) -> Optional[NPC]:
        """Get nearest guard from tracked guards"""
        if not self.tracked_guards:
            return None
            
        return min(self.tracked_guards, key=lambda g: g.distance)
        
    def get_guard_threat_level(self) -> float:
        """Calculate threat level based on guard proximity (0.0 - 1.0)"""
        if not self.tracked_guards:
            return 0.0
            
        # Consider closest 3 guards
        closest_guards = sorted(self.tracked_guards, key=lambda g: g.distance)[:3]
        
        # Weight based on distance (closer = more threatening)
        threat = sum(1.0 / (g.distance + 1) for g in closest_guards)
        
        # Normalize to 0.0 - 1.0 range (assuming max threat at distance 1)
        return min(threat / 3.0, 1.0)
        
    def get_safe_spots(self) -> List[WorldPoint]:
        """Find potential safe spots (areas far from guards)"""
        if not self.boundary or not self.tracked_guards:
            return []
            
        safe_spots = []
        step = 2  # Check every 2 tiles
        
        for x in range(self.boundary.min_x, self.boundary.max_x + 1, step):
            for y in range(self.boundary.min_y, self.boundary.max_y + 1, step):
                # Calculate minimum distance to any guard
                min_distance = min(
                    ((g.location.x - x) ** 2 + (g.location.y - y) ** 2) ** 0.5
                    for g in self.tracked_guards
                )
                
                # If spot is far enough from all guards, consider it safe
                if min_distance > 5:  # More than 5 tiles from any guard
                    safe_spots.append(WorldPoint(x, y, self.boundary.allowed_plane))
                    
        return safe_spots
