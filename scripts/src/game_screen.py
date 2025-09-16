"""
This module provides a GameScreen class for interacting with the game screen,
including color detection, OCR, and other screen analysis tools.
"""

import pyautogui
import numpy as np
from PIL import ImageGrab
import easyocr
import re

from .client_window import RuneLiteClientWindow

class GameScreen:
    """
    A class to handle screen interactions, including OCR and color detection.
    """

    def __init__(self):
        self.ocr_reader = easyocr.Reader(['en'])

    # --- Color Detection --- #

    def find_color(self, color: tuple, spectrum_range: list = None) -> tuple:
        """Find a color on the screen within the specified range."""
        if spectrum_range is None:
            r, g, b = color
            spectrum_range = [r, g, b, r, g, b]

        region = RuneLiteClientWindow().get_rect()
        x1, y1, x2, y2 = region[0], region[1], region[2], region[3]
        width, height = region["w"], region["h"]

        if region is not None:
            region = (x1, y1, x2, y2)
            if size is not None:
                region = (x1, y1, x1+size[0], y1+size[1])
                print(f"region: {region}")
                print(f"size: {size}")
            if size is None:
                region = (x1, y1, x2, y2)
                size = (width, height)
                print(f"region: {region}")
                print(f"size: {size}")
        
        screenshot = ImageGrab.grab(bbox=region)
        offset_x, offset_y = (region[0], region[1]) if region else (0, 0)
        
        img_array = np.array(screenshot)
        
        matches = np.where(
            (img_array[:, :, 0] >= spectrum_range[0]) & (img_array[:, :, 0] <= spectrum_range[1]) &
            (img_array[:, :, 1] >= spectrum_range[2]) & (img_array[:, :, 1] <= spectrum_range[3]) &
            (img_array[:, :, 2] >= spectrum_range[4]) & (img_array[:, :, 2] <= spectrum_range[5])
        )
        
        if len(matches[0]) > 0:
            y, x = matches[0][0], matches[1][0]
            return (x + offset_x, y + offset_y)
        
        return None

    def move_to_color(self, color: tuple, spectrum_range: list = None, region: tuple = None) -> tuple:
        """Move the mouse to a color on screen."""
        pos = self.find_color(color, spectrum_range, region)
        if pos:
            pyautogui.moveTo(pos[0], pos[1])
            return pos
        return None

    # --- OCR --- #

    def capture_region(self, x1, y1, x2, y2):
        """Capture a specific region of the screen."""
        try:
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            return np.array(screenshot)
        except Exception as e:
            print(f"Error capturing screen region: {str(e)}")
            return None

    def read_text_from_region(self, x1, y1, x2, y2, clean_pattern=r'[^a-zA-Z0-9,.]'):
        """Read text from a specific region of the screen."""
        try:
            image = self.capture_region(x1, y1, x2, y2)
            if image is None: return None
            
            result = self.ocr_reader.readtext(image, detail=0)
            
            if result:
                text = ' '.join(result)
                if clean_pattern:
                    text = re.sub(clean_pattern, '', text)
                return text.strip()
            
            return None
        except Exception as e:
            print(f"Error reading text: {str(e)}")
            return None

    def get_top_left_action_text(self, rect: dict) -> str:
        """Reads the primary action text at the top-left of the client."""
        x1 = rect[1] + 20
        y1 = rect[2] + 40
        x2 = x1 + 280
        y2 = y1 + 32
        return self.read_text_from_region(x1, y1, x2, y2)
