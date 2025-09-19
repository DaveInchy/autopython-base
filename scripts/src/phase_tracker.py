"""
This module handles the tracking of Zulrah's phases using the RuneLite API.
"""

class RotationManager:
    def __init__(self):
        # Hardcoded phase data, now internal to the class or loaded once.
        # This function encapsulates the data for clarity.
        self._ZULRAH_DATA = self._get_zulrah_rotations_data()

        self.current_zulrah_history = []  # Stores observed phases (NPC ID and position)
        self.identified_rotation = None     # Stores the confirmed rotation name (e.g., "rotation_1")

        # Reverse maps coordinates to keys for efficient lookup
        self._pos_key_to_coords = {
            "ZulrahPosCenter": {"x": 6720, "y": 7616},
            "ZulrahPosWest": {"x": 8000, "y": 7360},
            "ZulrahPosEast": {"x": 5440, "y": 7360},
            "ZulrahPosNorth": {"x": 6720, "y": 6208}
        }
        self._coords_to_pos_key = {
            (v["x"], v["y"]): k for k, v in self._pos_key_to_coords.items()
        }

        self._player_tile_key_to_coords = {
            "SWCornerTile": {"x": 7488, "y": 7872},
            "SWCornerTileMelee": {"x": 7232, "y": 8000},
            "WPillar": {"x": 7232, "y": 7232},
            "WPillarN": {"x": 7232, "y": 7104},
            "EPillar": {"x": 6208, "y": 7232},
            "EPillarN": {"x": 6208, "y": 7104},
            "SECornerTile": {"x": 6208, "y": 8000},
            "SECornerTileMelee": {"x": 5952, "y": 7744},
            "Middle": {"x": 6720, "y": 6848}
        }

    def _get_zulrah_rotations_data(self) -> dict:
        """
        Hardcoded Zulrah rotation data.
        """
        return {
            "types": {
                2042: {
                    "name": "Green",
                    "style": "RANGE", # The original Java code mapped 2042 (Green) to P_FROM_MISSILES, indicating RANGE.
                    "rgb": [
                        {"min": [82-4, 85-4, 30-4], "max": [82+4, 85+4, 30+4]}, # Example placeholder, requires tuning
                        {"min": [196-4, 202-4, 133-4], "max": [196+4, 202+4, 133+4]},
                        {"min": [163-4, 182-4, 22-4], "max": [163+4, 182+4, 22+4]},
                        {"min": [146-4, 149-4, 56-4], "max": [146+4, 149+4, 56+4]},
                        {"min": [128-4, 137-4, 31-4], "max": [128+4, 137+4, 31+4]},
                        {"min": [33-4, 39, 23-4], "max": [33+4, 39+4, 23+4]}
                    ]
                },
                2043: {
                    "name": "Red",
                    "style": "MELEE",
                    "rgb": [
                        {"min": [86-4, 68-4, 63-4], "max": [86+4, 68+4, 63+4]}, # Example placeholder, requires tuning
                        {"min": [205-4, 98-4, 27-4], "max": [205+4, 98+4, 27+4]},
                        {"min": [164-4, 74-4, 27-4], "max": [164+4, 74+4, 27+4]},
                        {"min": [37-4, 30-4, 26-4], "max": [37+4, 30+4, 26+4]}
                    ]
                },
                2044: {
                    "name": "Blue",
                    "style": "MAGIC", # The original Java code mapped 2044 (Blue) to P_FROM_MAGIC, indicating MAGIC.
                    "rgb": [
                        {"min": [11-4, 46-4, 56-4], "max": [11+4, 46+4, 56+4]}, # Example placeholder, requires tuning
                        {"min": [12-4, 87-4, 87-4], "max": [28+4, 192+4, 160+4]},
                        {"min": [96-4, 14-4, 149-4], "max": [118+4, 21+4, 185+4]},
                        {"min": [96-4, 14-4, 149-4], "max": [96+4, 14+4, 149+4]},
                        {"min": [12-4, 87-4, 87-4], "max": [12+4, 87+4, 87+4]}
                    ]
                },
            },
            "rotations": {
                "rotation_1": {
                    "types": [2042, 2043, 2044, 2042, 2044, 2043, 2042, 2044, 2042, 2043],
                    "positions": [
                        "ZulrahPosCenter", "ZulrahPosCenter", "ZulrahPosCenter", "ZulrahPosEast",
                        "ZulrahPosNorth", "ZulrahPosCenter", "ZulrahPosWest", "ZulrahPosNorth",
                        "ZulrahPosEast", "ZulrahPosCenter"
                    ],
                    "player_tiles": [
                        "SWCornerTile", "SWCornerTile", "SWCornerTile", "EPillar",
                        "EPillarN", "EPillar", "Middle", "EPillar",
                        "EPillar", "SWCornerTile"
                    ],
                    "jad": 9,
                    "ticks": [28, 20, 18, 28, 39, 22, 20, 36, 48, 20] # Adjusted to be 0-indexed for phase 0 to N-1
                },
                "rotation_2": {
                    "types": [2042, 2043, 2044, 2042, 2043, 2044, 2042, 2044, 2042, 2043],
                    "positions": [
                        "ZulrahPosCenter", "ZulrahPosCenter", "ZulrahPosCenter", "ZulrahPosNorth",
                        "ZulrahPosCenter", "ZulrahPosEast", "ZulrahPosNorth", "ZulrahPosNorth",
                        "ZulrahPosEast", "ZulrahPosCenter"
                    ],
                    "player_tiles": [
                        "SWCornerTile", "SWCornerTile", "SWCornerTile", "EPillar",
                        "EPillar", "EPillar", "WPillar", "WPillarN",
                        "EPillar", "SWCornerTile"
                    ],
                    "jad": 9,
                    "ticks": [28, 20, 17, 39, 22, 20, 28, 36, 48, 21] # Adjusted to be 0-indexed for phase 0 to N-1
                },
                "rotation_3": {
                    "types": [2042, 2042, 2043, 2044, 2042, 2044, 2042, 2042, 2044, 2042, 2044],
                    "positions": [
                        "ZulrahPosCenter", "ZulrahPosWest", "ZulrahPosCenter", "ZulrahPosEast",
                        "ZulrahPosNorth", "ZulrahPosWest", "ZulrahPosCenter", "ZulrahPosEast",
                        "ZulrahPosCenter", "ZulrahPosWest", "ZulrahPosCenter"
                    ],
                    "player_tiles": [
                        "SWCornerTile", "SWCornerTile", "SECornerTile", "EPillar",
                        "WPillar", "WPillar", "EPillar", "EPillar",
                        "WPillar", "WPillar", "SWCornerTile"
                    ],
                    "jad": 10,
                    "ticks": [28, 30, 40, 20, 20, 20, 25, 20, 36, 35, 18] # Adjusted to be 0-indexed for phase 0 to N-1
                },
                "rotation_4": {
                    "types": [2042, 2044, 2042, 2044, 2043, 2042, 2042, 2044, 2042, 2044, 2042, 2044],
                    "positions": [
                        "ZulrahPosCenter", "ZulrahPosWest", "ZulrahPosNorth", "ZulrahPosEast",
                        "ZulrahPosCenter", "ZulrahPosWest", "ZulrahPosNorth", "ZulrahPosEast",
                        "ZulrahPosCenter", "ZulrahPosCenter", "ZulrahPosWest", "ZulrahPosCenter"
                    ],
                    "player_tiles": [
                        "SWCornerTile", "SWCornerTile", "EPillar", "EPillar",
                        "WPillar", "WPillar", "WPillar", "EPillar",
                        "WPillar", "WPillar", "WPillar", "SWCornerTile"
                    ],
                    "jad": 11,
                    "ticks": [28, 36, 24, 30, 28, 17, 34, 33, 20, 27, 29, 18] # Adjusted to be 0-indexed for phase 0 to N-1
                }
            }
        }

    def _get_position_key(self, local_point_x: int, local_point_y: int) -> str | None:
        """
        Reverse-maps LocalPoint coordinates to their string key in the zulrah_positions.
        """
        return self._coords_to_pos_key.get((local_point_x, local_point_y))

    def reset(self):
        """Resets the tracker for a new Zulrah fight."""
        self.current_zulrah_history = []
        self.identified_rotation = None

    def add_observed_phase(self, zulrah_id: int, local_point_x: int, local_point_y: int):
        """
        Adds a new observed Zulrah phase to the history.

        Args:
            zulrah_id: The NPC ID of Zulrah (e.g., 2042, 2043, 2044).
            local_point_x: The X coordinate of Zulrah's local position.
            local_point_y: The Y coordinate of Zulrah's local position.
        """
        self.current_zulrah_history.append({
            "id": zulrah_id,
            "position": {"x": local_point_x, "y": local_point_y}
        })

    def get_next_zulrah_phase_info(self) -> dict:
        """
        Determines the current Zulrah rotation, phase index, and the *next* expected
        Zulrah combat style and player position.

        Returns:
            A dictionary containing:
                "identified_rotation": The name of the identified rotation (e.g., "rotation_1"), or None.
                "current_phase_index": The 0-indexed position of the *last observed* phase in the rotation.
                "next_combat_style": The combat style of the *next* Zulrah phase ("RANGE", "MELEE", "MAGIC"), or None.
                "next_zulrah_position": Dictionary {"x": int, "y": int} of the next Zulrah position, or None.
                "next_player_tile": Dictionary {"x": int, "y": int} of the next recommended player tile, or None.
                "next_phase_ticks": The tick duration of the *upcoming* phase, or None.
                "is_last_phase_in_rotation": True if the last observed phase was the final one in its rotation.
                "possible_rotations": List of rotation names that still match (useful if not uniquely identified).
                "error": An error message if something went wrong, otherwise None.
        """
        if not self.current_zulrah_history:
            return {
                "identified_rotation": None,
                "current_phase_index": -1,
                "next_combat_style": None,
                "next_zulrah_position": None,
                "next_player_tile": None,
                "next_phase_ticks": None,
                "is_last_phase_in_rotation": False,
                "possible_rotations": list(self._ZULRAH_DATA["rotations"].keys()),
                "error": None
            }

        processed_history = []
        for obs in self.current_zulrah_history:
            pos_key = self._get_position_key(obs["position"]["x"], obs["position"]["y"])
            if pos_key is None:
                return {
                    "identified_rotation": None,
                    "current_phase_index": -1,
                    "next_combat_style": None,
                    "next_zulrah_position": None,
                    "next_player_tile": None,
                    "next_phase_ticks": None,
                    "is_last_phase_in_rotation": False,
                    "possible_rotations": [],
                    "error": f"Observed Zulrah position {obs['position']} not found in known positions."
                }
            processed_history.append({"id": obs["id"], "position_key": pos_key})

        num_observed_phases = len(processed_history)
        
        # Determine which rotations to check: all if not identified, else only the identified one.
        rotations_to_check = [self.identified_rotation] if self.identified_rotation else self._ZULRAH_DATA["rotations"].keys()
        
        matching_rotations = []

        for rotation_name in rotations_to_check:
            rotation_data = self._ZULRAH_DATA["rotations"].get(rotation_name)
            if not rotation_data:
                continue

            # Check if observed history can possibly match this rotation's length
            if num_observed_phases > len(rotation_data["types"]):
                continue

            is_match = True
            for i in range(num_observed_phases):
                observed_type = processed_history[i]["id"]
                observed_pos_key = processed_history[i]["position_key"]
                
                expected_type = rotation_data["types"][i]
                expected_pos_key = rotation_data["positions"][i]

                if observed_type != expected_type or observed_pos_key != expected_pos_key:
                    is_match = False
                    break
            
            if is_match:
                matching_rotations.append(rotation_name)

        # Update identified_rotation if a unique match is found
        if len(matching_rotations) == 1:
            self.identified_rotation = matching_rotations[0]
        elif len(matching_rotations) == 0:
            return {
                "identified_rotation": None,
                "current_phase_index": num_observed_phases - 1,
                "next_combat_style": None,
                "next_zulrah_position": None,
                "next_player_tile": None,
                "next_phase_ticks": None,
                "is_last_phase_in_rotation": False,
                "possible_rotations": [],
                "error": "Observed sequence does not match any known rotation."
            }
        # If multiple matches, self.identified_rotation remains what it was, or None if still ambiguous.

        current_phase_index = num_observed_phases - 1 # 0-indexed position of the *last observed* phase
        
        next_combat_style = None
        next_zulrah_position = None
        next_player_tile = None
        next_phase_ticks = None
        is_last_phase = False

        if self.identified_rotation:
            rotation_data = self._ZULRAH_DATA["rotations"][self.identified_rotation]
            
            # Check if the *current observed phase* is the final phase in the rotation.
            if current_phase_index >= len(rotation_data["types"]) - 1:
                is_last_phase = True
                # No next phase info to provide as the rotation is complete.
            else:
                next_phase_index = current_phase_index + 1
                next_zulrah_type_id = rotation_data["types"][next_phase_index]
                
                # Get combat style from zulrah_forms
                next_combat_style = self._ZULRAH_DATA["types"].get(next_zulrah_type_id, {}).get("style")

                # Get next Zulrah position
                next_zulrah_pos_key = rotation_data["positions"][next_phase_index]
                next_zulrah_position = self._pos_key_to_coords.get(next_zulrah_pos_key)

                # Get next player tile
                next_player_tile_key = rotation_data["player_tiles"][next_phase_index]
                next_player_tile = self._player_tile_key_to_coords.get(next_player_tile_key)

                # Get the ticks for the *upcoming* phase
                if next_phase_index < len(rotation_data["ticks"]):
                    next_phase_ticks = rotation_data["ticks"][next_phase_index]
                
        return {
            "identified_rotation": self.identified_rotation,
            "current_phase_index": current_phase_index,
            "next_combat_style": next_combat_style,
            "next_zulrah_position": next_zulrah_position,
            "next_player_tile": next_player_tile,
            "next_phase_ticks": next_phase_ticks,
            "is_last_phase_in_rotation": is_last_phase,
            "possible_rotations": matching_rotations,
            "error": None
        }
