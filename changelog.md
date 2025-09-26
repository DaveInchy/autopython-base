# Changelog

## [Unreleased] - 2025-09-19

### Added
- **Ancient Magic Spellbook Grid**: Added support for the Ancient Magic spellbook grid, allowing for more accurate and flexible interaction with Ancient spells.
- **Hybrid UI Interaction**: Implemented an optional image recognition system for clicking UI elements (inventory, prayer, magic, equipment slots). Users can now toggle between image-based detection and the existing grid-based coordinate system via a new `use_image_recognition` setting.
- **Dynamic UI Sizing**: Integrated a mechanism to extract UI element dimensions from RuneLite resource packs. These dimensions are used to dynamically update `user-interface.jsonc`, ensuring more accurate grid-based calculations that adapt to different UI scales.
- **Confidence Scoring for Phase Detection**: The color-based phase detection now calculates a confidence score (0-100%) for each potential phase, making detection more robust and less prone to false positives from minions.
- **Synchronized Combat Loop**: The main combat loop now runs at a consistent 0.4-second interval, ensuring more predictable timing for actions.

### Changed
- **Refactored UI Interaction**: The `UIInteraction` class in `ui_utils.py` was refactored to support both image-based and grid-based interaction methods, providing a more resilient and adaptable framework.
- **Scoped Action Hotkeys**: The gear (`q`, `w`, `e`) and spell (`r`) hotkeys are now "scoped" and will only function when the main combat loop is active.
- **Refactored Hotkey System**: Replaced the inefficient use of multiple `HotkeyManager` instances with a single manager for the main loop and direct registration for action keys, simplifying the threading model.

### Fixed
- Fixed a `TypeError` crash when calling `GameScreen.find_color()` by providing a required (but unused) `color` argument.
- Fixed a `TypeError` crash in the hotkey system by correctly handling arguments passed to callbacks.

### Removed
- Removed the old, inefficient, and threaded `await_phase_detection` logic in favor of a synchronous function integrated into the main combat loop.

### Deprecated
- The `detect_and_update_phase` function has been temporarily disabled (commented out) by user request to improve performance.
