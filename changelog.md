# Changelog

## [Unreleased] - 2025-09-19

### Added
- **Confidence Scoring for Phase Detection**: The color-based phase detection now calculates a confidence score (0-100%) for each potential phase, making detection more robust and less prone to false positives from minions.
- **Synchronized Combat Loop**: The main combat loop now runs at a consistent 0.4-second interval, ensuring more predictable timing for actions.

### Changed
- **Scoped Action Hotkeys**: The gear (`q`, `w`, `e`) and spell (`r`) hotkeys are now "scoped" and will only function when the main combat loop is active.
- **Refactored Hotkey System**: Replaced the inefficient use of multiple `HotkeyManager` instances with a single manager for the main loop and direct registration for action keys, simplifying the threading model.

### Fixed
- Fixed a `TypeError` crash when calling `GameScreen.find_color()` by providing a required (but unused) `color` argument.
- Fixed a `TypeError` crash in the hotkey system by correctly handling arguments passed to callbacks.

### Removed
- Removed the old, inefficient, and threaded `await_phase_detection` logic in favor of a synchronous function integrated into the main combat loop.

### Deprecated
- The `detect_and_update_phase` function has been temporarily disabled (commented out) by user request to improve performance.
