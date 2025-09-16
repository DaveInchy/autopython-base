from typing import Literal, TypedDict

type ATTACK_TYPES = Literal["MELEE", "RANGE", "MAGIC"] | None
type SNAKE_POSITIONS = Literal["CENTER", "LEFT", "RIGHT", "TOP"]
type TARGET_POSITIONS = Literal["BOTTOMLEFT", "TOPLEFT", "BOTTOMRIGHT", "TOPRIGHT", "MIDDLE"]
type SNAKE_PHASES = Literal["MELEE", "RANGE", "MAGIC", "JAD"]

class PHASE_TYPE(TypedDict):
    snake_type: SNAKE_PHASES
    protect_prayer: ATTACK_TYPES
    offense_prayer: ATTACK_TYPES
    equipment: ATTACK_TYPES

type PHASES = dict[int, {
    "snake_type": "RANGE",
    "protect_prayer": "RANGE",
    "offense_prayer": "MAGIC",
    "equipment": "MAGIC",
} | {

} | {

}]

JAD_PHASE_NUM = 9

ZULRAH_ONE: dict[int, PHASE_TYPE] = {
    1: {
        "snake_position": "CENTER",
        "player_target_position": "BOTTOMLEFT",
        
    },
    2: {
        "snake_position": "CENTER",
        "player_target_position": "BOTTOMLEFT",
        "snake_type": "MELEE",
        "protect_prayer": None,
        "offense_prayer": "RANGE",
        "equipment": "RANGE",
    },
    3: {
        "snake_position": "CENTER",
        "player_target_position": "BOTTOMLEFT",
        "snake_type": "MAGIC",
        "protect_prayer": "MAGIC",
        "offense_prayer": "RANGE",
        "equipment": "RANGE",
    }
}

ZULRAH_TWO = {
    1: {
        "snake_position": "CENTER",
        "player_target_position": "BOTTOMLEFT",
        "snake_type": "RANGE",
        "protect_prayer": "RANGE",
        "offense_prayer": "MAGE",
        "equipment": "MAGE",
    },
    2: {
        "snake_position": "CENTER",
        "player_target_position": "BOTTOMLEFT",
        "snake_type": "MELEE",
        "protect_prayer": None,
        "offense_prayer": "RANGE",
        "equipment": "RANGE",
    },
    3: {
        "snake_position": "CENTER",
        "player_target_position": "BOTTOMLEFT",
        "snake_type": "MAGIC",
        "protect_prayer": "MAGIC",
        "offense_prayer": "RANGE",
        "equipment": "RANGE",
    }
}

ZULRAH_THREE = {
    1: {
        "snake_position": "CENTER",
        "player_target_position": "BOTTOMLEFT",
        "snake_type": "RANGE",
        "protect_prayer": "RANGE",
        "offense_prayer": "MAGE",
        "equipment": "MAGE",
    },
    2: {
        "snake_position": "LEFT",
        "player_target_position": "BOTTOMLEFT",
        "snake_type": "RANGE",
        "protect_prayer": "RANGE",
        "offense_prayer": "MAGE",
        "equipment": "MAGE",
    },
    3: {
        "snake_position": "CENTER",
        "player_target_position": "BOTTOMRIGHT",
        "snake_type": "MELEE",
        "protect_prayer": None,
        "offense_prayer": "RANGE",
        "equipment": "RANGE",
    },
}

ZULRAH_STATE = {
    "started": False,
    "paths": {
        1: ZULRAH_ONE,
        2: ZULRAH_TWO,
        3: ZULRAH_THREE,
        4: {
            "type": "limbo",
        }
    }
}

def get_phase(path: int, phase: int):
    return ZULRAH_STATE["paths"][path][phase]

def get_path(path: int):
    return ZULRAH_STATE["paths"][path]

def is_started():
    return ZULRAH_STATE["started"]

def set_started(started: bool):
    ZULRAH_STATE["started"] = started