"""
Configuration settings for the OnyxPoker bot.

This file defines the screen regions used for OCR, as well as
timing and model parameters.  You must adjust the pixel coordinates
to match your own table setup.  Use the same window size and theme
for every session to ensure the bot sees consistent images.

Coordinates are given as `(x, y, width, height)` tuples relative
to the top‑left corner of the screen.

To determine coordinates, run a Python REPL and import `pyautogui`.
Move your mouse to the corners of each region and note the values
returned by `pyautogui.position()`.  Subtract the table’s top‑left
corner to get the region’s relative coordinates.
"""

# Bounding box for the entire table window (x, y, width, height).
# Use this to crop the screenshot to reduce processing time.
TABLE_REGION = (100, 100, 800, 600)  # TODO: update these values

# Regions for the hero’s two hole cards.
# Each entry is (x, y, width, height) relative to the TABLE_REGION.
HOLE_CARD_REGIONS = [
    (350, 500, 50, 70),  # Card 1 – update these values
    (420, 500, 50, 70),  # Card 2 – update these values
]

# Regions for the community cards on flop, turn and river.
COMMUNITY_CARD_REGIONS = [
    (300, 300, 50, 70),  # Flop card 1 – update
    (370, 300, 50, 70),  # Flop card 2 – update
    (440, 300, 50, 70),  # Flop card 3 – update
    (510, 300, 50, 70),  # Turn card – update
    (580, 300, 50, 70),  # River card – update
]

# Region for the pot size display.
POT_REGION = (450, 250, 100, 30)  # update

# Regions for each player’s stack size.  Order should correspond to seat
# positions starting with the small blind and going clockwise.  You can
# leave unused positions at the end as `(0, 0, 0, 0)`.
STACK_REGIONS = [
    (200, 150, 80, 30),  # Seat 1
    (600, 150, 80, 30),  # Seat 2
    (700, 350, 80, 30),  # Seat 3 (your seat)
    (600, 550, 80, 30),  # Seat 4
    (200, 550, 80, 30),  # Seat 5
    (100, 350, 80, 30),  # Seat 6
]

# Regions for the Fold, Call/Check and Raise buttons.
BUTTON_REGIONS = {
    "fold": (300, 580, 80, 40),  # Fold button – update
    "call": (400, 580, 80, 40),  # Call/Check button – update
    "raise": (500, 580, 80, 40),  # Raise button – update
}

# GPT model configuration
GPT_MODEL = "gpt-4-0613"
GPT_TEMPERATURE = 0.0
GPT_TIMEOUT = 5  # seconds to wait for a response before folding

# Prompt template for GPT decisions.  The `{state}` placeholder will be
# replaced with a summary of the current game state by the backend.
GPT_PROMPT_TEMPLATE = (
    "You are a professional poker player playing 6‑max No‑Limit Texas Hold’em.\n"
    "Use optimal strategy to maximize expected value against average opponents.\n"
    "Here is the current game state:\n"
    "{state}\n\n"
    "Respond with one of: 'fold', 'call', or 'raise <amount>'."
)

## Optional features

# Whether to display GUI overlay windows showing what the bot sees.  Set
# to True for debugging.  Requires additional code (not implemented by
# default) and may slow down performance.
SHOW_GUI = False

## End of configuration