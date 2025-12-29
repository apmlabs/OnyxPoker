"""
Configuration for OnyxPoker bot
Screen regions and timing parameters
"""

# Table window region (x, y, width, height)
TABLE_REGION = (100, 100, 800, 600)

# Hero's hole cards
HOLE_CARD_REGIONS = [
    (350, 500, 50, 70),
    (420, 500, 50, 70),
]

# Community cards
COMMUNITY_CARD_REGIONS = [
    (300, 300, 50, 70),  # Flop 1
    (370, 300, 50, 70),  # Flop 2
    (440, 300, 50, 70),  # Flop 3
    (510, 300, 50, 70),  # Turn
    (580, 300, 50, 70),  # River
]

# Pot size region
POT_REGION = (450, 250, 100, 30)

# Stack sizes for each seat
STACK_REGIONS = [
    (200, 150, 80, 30),  # Seat 1
    (600, 150, 80, 30),  # Seat 2
    (700, 350, 80, 30),  # Seat 3 (hero)
    (600, 550, 80, 30),  # Seat 4
    (200, 550, 80, 30),  # Seat 5
    (100, 350, 80, 30),  # Seat 6
]

# Action buttons
BUTTON_REGIONS = {
    "fold": (300, 580, 80, 40),
    "call": (400, 580, 80, 40),
    "raise": (500, 580, 80, 40),
}

# Timing
POLL_INTERVAL = 0.5  # seconds between turn checks
ACTION_DELAY = 2.0   # seconds to wait after acting
