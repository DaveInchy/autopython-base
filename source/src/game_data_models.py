from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

@dataclass
class BoundingBox:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

@dataclass
class ActorDeathEvent:
    actorName: str
    boundingBox: BoundingBox = field(default_factory=BoundingBox)

@dataclass
class ActorPositionUpdateEvent:
    actorName: str
    actorId: int
    boundingBox: BoundingBox = field(default_factory=BoundingBox)

@dataclass
class ChatMessageEvent:
    type: str
    message: str
    name: str

@dataclass
class GameStateChangedEvent:
    gameState: str

@dataclass
class HitsplatAppliedEvent:
    actorName: str
    hitsplatType: int
    amount: int
    boundingBox: BoundingBox = field(default_factory=BoundingBox)

@dataclass
class ItemContainerChangedEvent:
    containerId: int
    itemCount: int

@dataclass
class NpcDespawnedEvent:
    npcId: int
    npcName: str

@dataclass
class NpcSpawnedEvent:
    npcId: int
    npcName: str
    boundingBox: BoundingBox = field(default_factory=BoundingBox)

@dataclass
class SessionClosedEvent:
    pass # No specific data

@dataclass
class SessionStartedEvent:
    pass # No specific data

@dataclass
class StatChangedEvent:
    level: int
    xp: int
    skill: str
    boostedLevel: int
