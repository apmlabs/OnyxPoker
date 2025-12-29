"""
Screen reading and game state extraction for OnyxPoker.

The `ScreenReader` class encapsulates all logic for capturing the
poker table window from the screen, extracting relevant regions, and
interpreting the game state.  It uses PyAutoGUI to take screenshots
and the utility functions in `onyxpoker.utils` to perform OCR and
template matching.

Note: This code is a template.  You will need to adjust the
configuration values (see `config.py`) and may need to refine the
image processing steps to achieve reliable card and number
recognition on your specific table theme and resolution.
"""

from __future__ import annotations

import time
from typing import Dict, List, Tuple

import pyautogui
from PIL import Image

from .. import config
from .. import utils


class ScreenReader:
    """Encapsulates screen capture and OCR for the poker table."""

    def __init__(self):
        # Preload card templates to avoid repeated disk access
        self._card_templates = utils.load_card_templates()
        # Warm up pytesseract if desired (no op here but reserved)

    def _capture_region(self, region: Tuple[int, int, int, int]) -> Image.Image:
        """Capture a specific region relative to the table region.

        The region tuple is (x, y, width, height) relative to the table
        window.  We adjust these coordinates by adding the table’s
        absolute screen offset.
        """
        # Offset the region by the TABLE_REGION’s origin
        table_x, table_y, _, _ = config.TABLE_REGION
        x, y, w, h = region
        abs_region = (table_x + x, table_y + y, w, h)
        # Use PyAutoGUI to capture the specified region
        return pyautogui.screenshot(region=abs_region)

    def _crop_cards(self, img: Image.Image, regions: List[Tuple[int, int, int, int]]) -> List[Image.Image]:
        """Return a list of cropped card images from the given table image."""
        cards: List[Image.Image] = []
        for reg in regions:
            cards.append(self._capture_region(reg))
        return cards

    def get_hole_cards(self) -> List[str]:
        """Detect and return the hero’s two hole cards as strings.

        If a card cannot be recognized, an empty string is returned in its
        place.  The order of cards corresponds to the order of
        `config.HOLE_CARD_REGIONS`.
        """
        card_images = [self._capture_region(reg) for reg in config.HOLE_CARD_REGIONS]
        codes: List[str] = []
        for img in card_images:
            code = utils.get_card_from_image(img)
            codes.append(utils.normalize_card_code(code))
        return codes

    def get_community_cards(self) -> List[str]:
        """Detect and return the community cards on the board.

        A list of card codes is returned.  If no card is present in a
        slot, an empty string is returned for that slot.  This method
        always returns a list of length equal to
        `len(config.COMMUNITY_CARD_REGIONS)`.
        """
        cards: List[str] = []
        for reg in config.COMMUNITY_CARD_REGIONS:
            img = self._capture_region(reg)
            code = utils.get_card_from_image(img)
            cards.append(utils.normalize_card_code(code))
        return cards

    def get_pot_size(self) -> int:
        """OCR the pot size displayed on the table."""
        img = self._capture_region(config.POT_REGION)
        return utils.parse_int_from_ocr(img)

    def get_stack_sizes(self) -> List[int]:
        """OCR the chip stack for each player seat.

        Returns a list of integers corresponding to the values in
        `config.STACK_REGIONS`.  If a seat is empty or OCR fails, 0
        will be returned for that seat.
        """
        stacks: List[int] = []
        for reg in config.STACK_REGIONS:
            if reg == (0, 0, 0, 0):
                stacks.append(0)
                continue
            img = self._capture_region(reg)
            stacks.append(utils.parse_int_from_ocr(img))
        return stacks

    def get_action_buttons(self) -> Dict[str, str]:
        """Check which action buttons (fold, call/check, raise) are available.

        Returns a dictionary mapping button names to strings describing
        their labels, as read via OCR.  If a button region contains no
        text (e.g. because it is disabled), an empty string is returned.

        Example return value:
        ```
        {
            "fold": "Fold",
            "call": "Call 20",
            "raise": "Raise to 40"
        }
        ```
        """
        actions: Dict[str, str] = {}
        for name, reg in config.BUTTON_REGIONS.items():
            img = self._capture_region(reg)
            # OCR using a broader whitelist to capture words and numbers
            label = utils.ocr_text(img, whitelist="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ")
            actions[name] = label
        return actions

    def is_hero_turn(self) -> bool:
        """Determine if it is the hero’s turn to act.

        This implementation checks whether the call/check button has
        non‑empty text.  Depending on the table theme, you may want to
        refine this logic, for example by checking color highlights or
        a timer indicator.
        """
        actions = self.get_action_buttons()
        label = actions.get('call', '')
        return bool(label.strip())

    def parse_game_state(self) -> Dict[str, object]:
        """Capture the current game state and return a structured dict.

        The returned dict contains at least the following keys:

        * `hero_cards`: list of two strings (e.g. ['As', 'Kd'])
        * `community_cards`: list of strings for the flop/turn/river
        * `pot`: integer pot size
        * `stacks`: list of stack sizes for each seat
        * `actions`: dict mapping 'fold', 'call' and 'raise' to button text
        """
        state = {
            'hero_cards': self.get_hole_cards(),
            'community_cards': self.get_community_cards(),
            'pot': self.get_pot_size(),
            'stacks': self.get_stack_sizes(),
            'actions': self.get_action_buttons(),
        }
        return state


def demo_once(delay: float = 0.5) -> None:
    """Demonstrate a single parse of the game state (for debugging).

    Waits for the specified delay, captures the table state, prints it
    to the console, and exits.  Useful for testing coordinate
    configuration.
    """
    print("Waiting for", delay, "seconds…")
    time.sleep(delay)
    reader = ScreenReader()
    state = reader.parse_game_state()
    print("Game state:")
    for k, v in state.items():
        print(f"  {k}: {v}")