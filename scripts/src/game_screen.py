"""
This module provides a GameScreen class for interacting with the game screen,
including color detection, OCR, and other screen analysis tools.
"""

import pyautogui
import numpy as np
import cv2
from PIL import ImageGrab
import easyocr
import re
import os
import sys
import warnings

from .client_window import RuneLiteClientWindow

class GameScreen:
    """
    A class to handle screen interactions, including OCR and color detection.
    """

    def __init__(self):
        # Temporarily suppress stdout/stderr and warnings to hide the noisy
        # "CUDA not available" and "pin_memory" messages from easyocr/torch.
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            try:
                self.ocr_reader = easyocr.Reader(['en'])
            finally:
                # Restore stdout/stderr
                sys.stdout.close()
                sys.stderr.close()
                sys.stdout = original_stdout
                sys.stderr = original_stderr

    # --- Color Detection --- #

    def find_color(self, color: tuple, spectrum_range: list = None, region: tuple = None, size: tuple = None) -> tuple:
        """Find a color on the screen within the specified range."""
        if spectrum_range is None:
            r, g, b = color
            spectrum_range = [r, g, b, r, g, b]

        if region is None:
            client_rect = RuneLiteClientWindow().get_rect()
            if client_rect:
                region = (client_rect['left'], client_rect['top'], client_rect['right'], client_rect['bottom'])
            else:
                return None # No window found
        
        if size is not None:
            region = (region[0], region[1], region[0] + size[0], region[1] + size[1])

        screenshot = ImageGrab.grab(bbox=region)
        offset_x, offset_y = region[0], region[1]

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
        """Read text from a specific region of the screen with preprocessing."""
        try:
            # 1. Capture the region
            image_pil = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            if image_pil is None: return None
            
            # 2. Convert to OpenCV format
            image_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)

            # 3. Convert to grayscale
            gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)

            # 4. Apply a binary threshold to isolate the text
            _ , thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

            # 5. Invert the image for better OCR performance
            thresh = cv2.bitwise_not(thresh)

            # 6. Read text from the processed image
            result = self.ocr_reader.readtext(thresh, detail=0)
            
            if result:
                text = ' '.join(result)
                if clean_pattern:
                    # Allow hyphens and spaces in the cleaned text
                    clean_pattern = r'[^a-zA-Z0-9,.\- ]'
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
