
import time
from src.phase_tracker import RotationManager, PhaseDetector
from src.client_window import RuneLiteClientWindow

def on_phase_change(phase, confidence):
    """Callback function for when a phase change is detected."""
    print(f"[Phase Change] New Phase: {phase} (Confidence: {confidence:.2f}%)")

def test_phase_detection():
    """Tests the phase detection system."""
    rotation_manager = RotationManager()
    phase_data = rotation_manager._get_zulrah_rotations_data()['types']

    phase_detector = PhaseDetector(phase_data, on_phase_change=on_phase_change)

    # Define the precise game view and player exclusion regions
    game_view_region = (258, 174, 769, 509)
    player_mask_region = (471, 292, 565, 399)

    print(f"Starting phase detection in region: {game_view_region}")
    print(f"Excluding region: {player_mask_region}")
    phase_detector.start(game_view_region, exclude_region=player_mask_region, interval=0.2)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping phase detection.")
        phase_detector.stop()

if __name__ == "__main__":
    test_phase_detection()
