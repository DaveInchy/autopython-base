import sys
import threading
from src.pathing import RoutePather
from src.hotkeys import HotkeyManager

def main():
    """
    Main function to initialize and run the RoutePather.
    
    Usage: python run_route.py [route_name]
    Example: python run_route.py route-1
    """
    # Default route name, can be overridden by command-line argument
    route_name = "route-1"
    if len(sys.argv) > 1:
        route_name = sys.argv[1]

    print(f"Preparing to run route: '{route_name}'")
    print("Press 'ctrl+.' to start the route.")
    print("Press 'ctrl+,' to stop the route.")
    print("Press Ctrl+C in the console to exit the script entirely.")

    try:
        # Initialize the RoutePather. For now, we are not using a visual overlay.
        pather = RoutePather(route_name=route_name, overlay=None)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error initializing RoutePather: {e}")
        return

    # The HotkeyManager will handle starting the pather.run method in a new thread.
    hotkey_manager = HotkeyManager(start_hotkey='ctrl+.', stop_hotkey='ctrl+,')
    hotkey_manager.register_hotkeys(pather.run)

    print("\nHotkeys registered. Waiting for start command...")
    hotkey_manager.wait_for_exit()
    print("Script finished.")


if __name__ == "__main__":
    main()

