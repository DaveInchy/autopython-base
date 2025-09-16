import sys
from pynput import mouse
import pyautogui

def on_click(x, y, button, pressed):
    """
    Callback function to handle mouse click events.
    """
    if pressed and button == mouse.Button.left:
        # Get the color of the clicked pixel
        rgb_color = pyautogui.pixel(x, y)
        
        # Format the color and command
        color_str = f"{rgb_color[0]},{rgb_color[1]},{rgb_color[2]}"
        
        print("\nPixel selected!")
        print(f"Coordinates: ({x}, {y})")
        print(f"RGB Color: {rgb_color}")
        
        # Stop the listener
        return False

def main():
    """
    Main function to set up and start the mouse listener.
    """
    print("Waiting for you to click on the desired color...")
    print("Click the left mouse button on any pixel on the screen.")

    # Create and start the mouse listener
    with mouse.Listener(on_click=on_click) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print("\nExiting script.")
            sys.exit(0)

if __name__ == "__main__":
    main()