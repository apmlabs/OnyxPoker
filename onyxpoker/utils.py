"""
Utility functions for the OnyxPoker project.

This module contains helper functions for card recognition and OCR.
Feel free to extend or replace these implementations to improve
performance and accuracy.  Many of the functions here are stubs
providing basic structure; they will need to be filled in with
actual image processing logic for a production bot.
"""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

from PIL import Image
import numpy as np
import pytesseract
import imagehash

# --- Card recognition via template matching ---------------------------------

CARD_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates', 'cards')

def load_card_templates() -> Dict[str, Image.Image]:
    """Load template images for all cards.

    Expects a directory structure like:

    ```
    onyxpoker/templates/cards/
      As.png  # Ace of spades
      Kc.png  # King of clubs
      ...
    ```

    The filenames should correspond to card codes (rank + suit initial,
    case sensitive).  For example, the king of hearts would be `Kh.png`.

    Returns a dictionary mapping card codes (e.g. 'As', 'Td') to PIL
    Image objects.  If the directory does not exist, an empty
    dictionary is returned.
    """
    templates: Dict[str, Image.Image] = {}
    if not os.path.isdir(CARD_TEMPLATES_DIR):
        return templates
    for filename in os.listdir(CARD_TEMPLATES_DIR):
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue
        code = os.path.splitext(filename)[0]
        path = os.path.join(CARD_TEMPLATES_DIR, filename)
        try:
            templates[code] = Image.open(path).convert('RGB')
        except Exception:
            continue
    return templates

_CARD_TEMPLATES = None

def get_card_from_image(img: Image.Image) -> str:
    """Identify a playing card from a cropped image.

    This function uses perceptual hashing (via the `imagehash` package)
    to compare the input image to a set of known templates.  The
    template images must be loaded via `load_card_templates()` and
    stored in the global `_CARD_TEMPLATES` variable.

    If no templates are available or no match is found within a
    reasonable Hamming distance, returns an empty string.
    """
    global _CARD_TEMPLATES
    if _CARD_TEMPLATES is None:
        _CARD_TEMPLATES = load_card_templates()
    if not _CARD_TEMPLATES:
        return ''
    img_hash = imagehash.phash(img)
    best_match = ''
    best_distance = 64  # maximum bits in a 64‑bit hash
    for code, template in _CARD_TEMPLATES.items():
        try:
            template_hash = imagehash.phash(template)
            dist = img_hash - template_hash
            if dist < best_distance:
                best_distance = dist
                best_match = code
        except Exception:
            continue
    # Accept the match only if the distance is small enough
    # (Threshold may need tuning; lower means stricter matching.)
    return best_match if best_distance <= 8 else ''

# --- OCR for numbers and text ----------------------------------------------

def ocr_text(img: Image.Image, whitelist: str = "0123456789" ) -> str:
    """Perform OCR on the provided image and return the recognized text.

    Uses pytesseract with a restricted character whitelist to improve
    accuracy.  You may need to preprocess the image (e.g. increase
    contrast or convert to black/white) before calling this function.

    Args:
        img: A PIL Image to be recognized.
        whitelist: A string of characters that Tesseract is allowed
            to output.  The default restricts output to digits.

    Returns:
        The raw OCR string stripped of whitespace.
    """
    # Convert to grayscale for better OCR performance
    gray = img.convert('L')
    # Tesseract configuration: psm 7 means a single text line
    custom_config = f"--psm 7 -c tessedit_char_whitelist={whitelist}"
    text = pytesseract.image_to_string(gray, config=custom_config)
    return text.strip()


def parse_int_from_ocr(img: Image.Image) -> int:
    """Recognize a number from an image and convert to int.

    Returns 0 if OCR fails or if the recognized string is not a valid
    integer.  This is used for pot sizes, stack counts and bet sizes.
    """
    s = ocr_text(img, whitelist="0123456789")
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def normalize_card_code(code: str) -> str:
    """Normalize card codes to ensure consistent formatting.

    For example, convert '10s' to 'Ts', '1S' to 'As' (if you use 1 for Ace),
    and uppercase suits.  Adjust this function to match your template names.
    """
    code = code.strip()
    if not code:
        return ''
    # Map rank synonyms
    rank_map = {
        '1': 'A', '14': 'A', '11': 'J', '12': 'Q', '13': 'K', '10': 'T',
    }
    rank = code[:-1]
    suit = code[-1].lower()
    rank = rank_map.get(rank, rank.upper())
    suit_map = {'s': 's', 'h': 'h', 'd': 'd', 'c': 'c', '♠': 's', '♥': 'h', '♦': 'd', '♣': 'c'}
    suit = suit_map.get(suit, suit)
    return f"{rank}{suit}"

## End of utils.py