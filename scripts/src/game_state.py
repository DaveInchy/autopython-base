"""
This module defines data classes for representing game state.
"""

from dataclasses import dataclass

@dataclass
class WorldPoint:
    x: int
    y: int
    plane: int

@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int

@dataclass
class NPC:
    id: int
    name: str
    bounding_box: BoundingBox
