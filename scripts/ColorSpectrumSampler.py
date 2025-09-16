import sys
import pyautogui
from pynput import mouse, keyboard

def get_pixel_color(x, y):
    screenshot = pyautogui.screenshot(region=(x, y, 1, 1))
    return screenshot.getpixel((0, 0))

def expand_spectrum(spectrum, color):
    r, g, b = color
    if spectrum is None:
        return [r, r, g, g, b, b], True
    r_min, r_max, g_min, g_max, b_min, b_max = spectrum
    changed = False
    if r < r_min or r > r_max:
        changed = True
    if g < g_min or g > g_max:
        changed = True
    if b < b_min or b > b_max:
        changed = True
    r_min = min(r_min, r)
    r_max = max(r_max, r)
    g_min = min(g_min, g)
    g_max = max(g_max, g)
    b_min = min(b_min, b)
    b_max = max(b_max, b)
    new_spectrum = [r_min, r_max, g_min, g_max, b_min, b_max]
    return new_spectrum, changed

def main():
    print("Spectrum Sampler")
    print("Click the left mouse button on any pixel to sample its color.")
    print("Press ESC to finish and print the spectrum.")
    print("You need at least two samples to define a spectrum.")
    print("---------------------------------------------------")

    spectrum = None
    samples = []
    finished = [False]

    def on_click(x, y, button, pressed):
        nonlocal spectrum
        if pressed and button == mouse.Button.left:
            color = get_pixel_color(x, y)
            samples.append(color)
            if spectrum is None:
                spectrum, _ = expand_spectrum(None, color)
                print(f"Sampled color at ({x}, {y}): {color}")
                print(f"Initialized spectrum: {spectrum}")
            else:
                new_spectrum, changed = expand_spectrum(spectrum, color)
                print(f"Sampled color at ({x}, {y}): {color}")
                if changed:
                    print(f"Spectrum expanded to: {new_spectrum}")
                else:
                    print("Spectrum unchanged.")
                spectrum = new_spectrum
            if len(set(samples)) >= 2 and len(spectrum) == 6:
                print("Spectrum defined from samples.")
                print(f"Final spectrum: {spectrum}")
        return not finished[0]

    def on_press(key):
        if key == keyboard.Key.esc:
            finished[0] = True
            # Stop listener
            return False

    # Start mouse and keyboard listeners
    mouse_listener = mouse.Listener(on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_press)
    mouse_listener.start()
    keyboard_listener.start()
    mouse_listener.join()
    keyboard_listener.join()

    if spectrum and len(set(samples)) >= 2:
        print("\nYou can use this spectrum in your search:")
        print(f"--spectrum {spectrum[0]} {spectrum[1]} {spectrum[2]} {spectrum[3]} {spectrum[4]} {spectrum[5]}")
    else:
        print("\nNo valid spectrum was sampled.")

if __name__ == "__main__":
    main()