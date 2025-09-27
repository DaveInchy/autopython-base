import sys
from pynput import mouse, keyboard
from PIL import ImageGrab
from src.phase_tracker import RotationManager

# --- Global Variables ---
TOLERANCE = 20
PHASE_COLORS = {}

def get_phase_from_color(clicked_color: tuple) -> str:
    """Compares a clicked color to the phase colors and returns the phase name."""
    for phase, colors in PHASE_COLORS.items():
        for color in colors:
            if all(abs(int(clicked_color[i]) - color[i]) <= TOLERANCE for i in range(3)):
                return phase
    return None

def on_click(x, y, button, pressed):
    """Callback function for mouse clicks."""
    if pressed and button == mouse.Button.left:
        try:
            pixel_color = ImageGrab.grab(bbox=(x, y, x+1, y+1)).getpixel((0, 0))
            phase = get_phase_from_color(pixel_color)
            if phase:
                print(f"Click at ({int(x)}, {int(y)}) with color {pixel_color} -> Phase Detected: {phase}")
            else:
                print(f"Click at ({int(x)}, {int(y)}) with color {pixel_color} -> Phase not recognized.")
        except Exception as e:
            print(f"Error processing click: {e}")

def on_press(key):
    """Callback function for key presses."""
    if key == keyboard.Key.esc:
        print("Exiting...")
        return False # Stop listener

def main():
    global PHASE_COLORS
    print("Starting click phase detector...")
    
    # Load phase color data from RotationManager
    try:
        rotation_manager = RotationManager()
        phase_data = rotation_manager._get_zulrah_rotations_data()['types']
        PHASE_COLORS = {phase_info['style']: phase_info['colors'] for _, phase_info in phase_data.items()}
        print("Phase colors loaded successfully.")
    except Exception as e:
        print(f"Failed to load phase colors: {e}")
        return

    print("Left-click on the boss to detect its phase.")
    print("Press 'Esc' to stop.")

    with mouse.Listener(on_click=on_click) as m_listener, keyboard.Listener(on_press=on_press) as k_listener:
        k_listener.join()

if __name__ == "__main__":
    main()