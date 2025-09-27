import os
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import threading
import time
import logging
import numpy as np
import win32api

# --- OSRS Macro SDK Imports ---
from src.client_window import RuneLiteClientWindow

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s, %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class WindowOverlay:
    def __init__(self, title="Overlay", width=300, height=200, x=100, y=100, transparency=.2):
        self.client_window = RuneLiteClientWindow() # Initialize client_window
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.overrideredirect(True) # Remove window decorations
        self.root.attributes("-topmost", True) # Always on top
        # self.root.attributes("-alpha", 1) # Set transparency

        self.width = width
        self.height = height
        self.transparency = transparency # Store transparency
        self.text_color = (255, 255, 0) # Default text color
        self.transparent_color = '#FF00FF' # Magenta for transparency
        self.root.attributes("-transparentcolor", self.transparent_color)
        
        # Initialize font
        self.font_path = os.path.join(os.path.dirname(__file__), '..', '..', 'res', 'font', 'OpenRS.ttf') # Corrected path to OpenRS font
        try:
            self.font = ImageFont.truetype(self.font_path, 16) # Default font size
        except IOError:
            logger.warning(f"Font file not found at {self.font_path}. Using default font.")
            self.font = ImageFont.load_default()

        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height, highlightthickness=0.1)
        self.canvas.pack(fill="both", expand=True)

        # Initialize image and drawing context
        self.image = Image.new('RGBA', (self.width, self.height), (255, 0, 255, 255)) # Initialize with magenta
        self.draw = ImageDraw.Draw(self.image) # Initialize ImageDraw object
        self.tk_image = ImageTk.PhotoImage(self.image, master=self.root)
        self.image_on_canvas = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.canvas.image = self.tk_image # Keep a reference to prevent garbage collection

        self.active_highlights = [] # List to store highlight rectangles
        self.text_elements = [] # List to store text elements (not used in current update_overlay)

    def update_overlay(self):
        """
        Updates the overlay by redrawing all elements, including fading highlights.
        This method should be called continuously by a main loop.
        """
        # 1. Draw fading highlights
        current_time = time.time()
        highlights_to_keep = []
        for h in self.active_highlights:
            elapsed = current_time - h['start_time']
            if elapsed < h['duration']:
                progress = elapsed / h['duration']
                r = int(h['color_start'][0] * (1 - progress) + h['color_end'][0] * progress)
                g = int(h['color_start'][1] * (1 - progress) + h['color_end'][1] * progress)
                b = int(h['color_start'][2] * (1 - progress) + h['color_end'][2] * progress)
                alpha = int(255 * (1 - progress)) # Fade out alpha

                current_color = (r, g, b, alpha)
                
                self.draw.rectangle([h['top_left'], h['bottom_right']], fill=current_color)
                highlights_to_keep.append(h)
            
        self.active_highlights = highlights_to_keep

        # 2. Update the Tkinter PhotoImage and canvas
        if self.image is None:
            self.image = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))

        self.tk_image = ImageTk.PhotoImage(self.image, master=self.root)
        self.canvas.itemconfig(self.image_on_canvas, image=self.tk_image)
        self.root.update_idletasks()
        self.root.update()

    def clear(self):
        """Clears the overlay to be fully transparent."""
        self.draw.rectangle([(0, 0), (self.width, self.height)], fill=(255, 0, 255, 255)) # Fill with magenta

    def draw_text(self, text, position=(10, 10), font_size=None, color=None):
        """Draw text on the overlay's internal drawing buffer. update_overlay must be called to reflect changes."""
        if font_size:
            font = ImageFont.truetype(self.font_path, font_size) if self.font_path else ImageFont.load_default()
        else:
            font = self.font
        if color is None:
            color = self.text_color

        if len(color) == 3:
            color = color + (255,)

        self.draw.text(position, text, font=font, fill=color)

    def draw_rectangle(self, top_left, bottom_right, outline_color=(0, 0, 0), fill_color=None, width=1):
        """Draw a rectangle on the overlay's internal drawing buffer. update_overlay must be called to reflect changes."""
        if fill_color:
            self.draw.rectangle([top_left, bottom_right], outline=outline_color, fill=fill_color, width=width)
        else:
            self.draw.rectangle([top_left, bottom_right], outline=outline_color, width=width)

    def draw_image(self, image_path, position=(0, 0)):
        """Draw an image on the overlay's internal drawing buffer. update_overlay must be called to reflect changes."""
        logger.info(f"Attempting to draw image: {image_path} at position {position}")
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return
        try:
            img = Image.open(image_path).convert("RGBA")
            logger.info(f"Image loaded successfully. Mode: {img.mode}, Size: {img.size}")
            self.image.paste(img, position, img)
            logger.info(f"Image pasted onto overlay buffer.")
        except Exception as e:
            logger.error(f"Error loading or pasting image {image_path}: {e}")

    def draw_pil_image(self, pil_image: Image.Image, position=(0, 0)):
        """Draw a pre-loaded PIL Image object on the overlay's internal drawing buffer."""
        if pil_image is None:
            logger.warning("Attempted to draw a None PIL Image.")
            return
        try:
            self.image.paste(pil_image, position, pil_image)
            logger.info(f"PIL Image pasted onto overlay buffer at position {position}.")
        except Exception as e:
            logger.error(f"Error pasting PIL Image: {e}")

    def set_position(self, x, y):
        """Set the position of the overlay window."""
        self.root.geometry(f"+{x}+{y}")

    def set_size(self, width, height):
        """Set the size of the overlay window."""
        self.width = width
        self.height = height
        self.root.geometry(f"{width}x{height}")
        self.canvas.config(width=width, height=height)
        self.image = Image.new("RGBA", (width, height), (255, 0, 255, 255)) # Initialize with magenta
        self.draw = ImageDraw.Draw(self.image)
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.itemconfig(self.image_on_canvas, image=self.tk_image)

    def set_transparency(self, alpha):
        """Set the transparency of the overlay window."""
        if 0.0 <= alpha <= 1.0:
            self.transparency = alpha
            self.root.attributes("-alpha", alpha)
        else:
            logger.error("Transparency must be between 0.0 and 1.0")

    def add_highlight(self, top_left, bottom_right, color_start=(0, 255, 0), color_end=(255, 0, 0), duration=1.0):
        """Adds a highlight that fades over time."""
        self.active_highlights.append({
            'top_left': top_left,
            'bottom_right': bottom_right,
            'color_start': color_start,
            'color_end': color_end,
            'duration': duration,
            'start_time': time.time()
        })

    def show_click(self, pos, duration=0.5, size=5, color_start=(0, 255, 0), color_end=(255, 0, 0)):
        """
        Renders a temporary, fading box to visualize a click.
        pos: The (x, y) center of the click.
        duration: How long the visualization lasts, in seconds.
        size: The size of the square to draw.
        """
        half_size = size // 2
        top_left = (pos[0] - half_size, pos[1] - half_size)
        bottom_right = (pos[0] + half_size, pos[1] + half_size)
        self.add_highlight(top_left, bottom_right, color_start, color_end, duration)

    def close(self):
        """Close the overlay window."""
        self.root.destroy()

    def bring_to_foreground(self):
        """Bring the overlay window to the foreground."""
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after_idle(self.root.attributes, '-topmost', False)

def DrawCursorPosition(overlay: WindowOverlay, stop_event: threading.Event, color=(251, 252, 253)):
    """Thread function to continuously draw the mouse cursor position relative to the RuneLite client window (bottom-right origin)."""
    # Ensure the overlay has a client window instance
    client_window = overlay.client_window

    overlay.bring_to_foreground()
    
    while not stop_event.is_set():
        # Get absolute cursor position
        cursor_x, cursor_y = win32api.GetCursorPos()
        # Get client window position and size
        win_rect = client_window.get_rect()
        if not win_rect:
            time.sleep(0.1)
            continue
        win_left, win_top, win_width, win_height = win_rect['left'], win_rect['top'], win_rect['w'], win_rect['h']

        # Calculate cursor position relative to the client window (origin at bottom-right)
        rel_x = (cursor_x - win_left)
        rel_y = (cursor_y - win_top)
        offset_x = win_width - rel_x
        offset_y = win_height - rel_y

        overlay.clear()
        overlay.draw_text(
            f"X {offset_x} Y {offset_y}",
            position=(10, 40),
            font_size=32,
            color=color
        )
        overlay.update_overlay()
        time.sleep(1/10)