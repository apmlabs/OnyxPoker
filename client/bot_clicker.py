"""
Bot clicker for PokerStars Zoom tables.
Detects buttons via pixel color at known relative positions, clicks them.
All coordinates are relative (% of window) so any window size works.

Button layouts detected:
  1. FOLD/CALL/RAISE  - facing a bet (3 red buttons)
  2. CHECK/BET        - checked to us (2 red buttons)
  3. FAST_FOLD        - preflop Zoom (1 red button + checkboxes)
  4. NONE             - not our turn (no red buttons)
"""

import pyautogui
import time

# Disable pyautogui's built-in pause and failsafe for speed
pyautogui.PAUSE = 0.03
pyautogui.FAILSAFE = True  # Move mouse to corner to abort

# Button centers as (x%, y%) of window — measured from 3018 screenshots at 1938x1392
# These are the CENTER of each clickable button
BUTTONS = {
    # Main action buttons (big red)
    'fold':       (0.573, 0.932),
    'call':       (0.739, 0.936),
    'raise':      (0.905, 0.926),
    'check':      (0.739, 0.924),
    'bet':        (0.905, 0.936),
    'fast_fold':  (0.573, 0.936),
    # Sizing presets (small red above bet input)
    'min':        (0.699, 0.810),
    '50pct':      (0.781, 0.810),
    'pot':        (0.863, 0.810),
    'max':        (0.945, 0.810),
    # Bet input box (click to focus, then type amount)
    'bet_input':  (0.695, 0.855),
}

# Red button detection: sample these points to determine which layout is active
# We check if the pixel at each button center is red (R>150, G<80, B<80)
DETECT_POINTS = {
    'fold_or_ff': (0.573, 0.932),  # Fold button OR Fast Fold (same position)
    'call':       (0.739, 0.936),  # Call button (only in 3-btn layout)
    'raise_or_bet': (0.905, 0.930),  # Raise or Bet button
    'check':      (0.739, 0.924),  # Check button (only in 2-btn layout)
}


def _abs(pct_x, pct_y, win_left, win_top, win_w, win_h):
    """Convert relative % to absolute screen coordinates."""
    return int(win_left + pct_x * win_w), int(win_top + pct_y * win_h)


def _is_red(img, pct_x, pct_y):
    """Check if pixel at relative position is red (button present)."""
    w, h = img.size
    x, y = int(pct_x * w), int(pct_y * h)
    x = min(x, w - 1)
    y = min(y, h - 1)
    r, g, b = img.getpixel((x, y))[:3]
    return r > 150 and g < 80 and b < 80


def detect_layout(screenshot):
    """Detect which button layout is currently visible.
    
    Returns: 'fold_call_raise' | 'check_bet' | 'fast_fold' | None
    """
    has_left = _is_red(screenshot, *DETECT_POINTS['fold_or_ff'])
    has_call = _is_red(screenshot, *DETECT_POINTS['call'])
    has_right = _is_red(screenshot, *DETECT_POINTS['raise_or_bet'])
    has_check = _is_red(screenshot, *DETECT_POINTS['check'])

    if has_left and has_call and has_right:
        return 'fold_call_raise'
    if has_check and has_right:
        return 'check_bet'
    if has_left and not has_call and not has_right:
        return 'fast_fold'
    return None


def click_button(button_name, win_rect, logger=None):
    """Click a button by name. win_rect = (left, top, width, height)."""
    if button_name not in BUTTONS:
        if logger:
            logger(f"[BOT] Unknown button: {button_name}", "ERROR")
        return False
    pct_x, pct_y = BUTTONS[button_name]
    ax, ay = _abs(pct_x, pct_y, *win_rect)
    if logger:
        logger(f"[BOT] Click {button_name} at ({ax},{ay})", "DEBUG")
    pyautogui.click(ax, ay)
    return True


def type_bet_amount(amount, win_rect, logger=None):
    """Click bet input box, clear it, type the amount, then click Raise/Bet."""
    # Click the bet input box
    pct_x, pct_y = BUTTONS['bet_input']
    ax, ay = _abs(pct_x, pct_y, *win_rect)
    if logger:
        logger(f"[BOT] Typing bet {amount:.2f}", "DEBUG")
    # Triple-click to select all text in input
    pyautogui.click(ax, ay, clicks=3)
    time.sleep(0.05)
    # Type the amount
    pyautogui.typewrite(f"{amount:.2f}", interval=0.02)
    time.sleep(0.05)


def execute_action(action, bet_size, screenshot, win_rect, logger=None):
    """Execute a poker action by clicking the appropriate button.
    
    action: 'fold' | 'call' | 'raise' | 'bet' | 'check'
    bet_size: float amount for raise/bet (ignored for fold/call/check)
    screenshot: PIL Image of current window (for layout detection)
    win_rect: (left, top, width, height) of poker window
    
    Returns: True if action was executed, False if couldn't (not our turn, etc.)
    """
    layout = detect_layout(screenshot)
    if logger:
        logger(f"[BOT] Layout: {layout}, Action: {action}, Bet: {bet_size}", "INFO")

    if layout is None:
        if logger:
            logger("[BOT] No buttons visible - not our turn", "DEBUG")
        return False

    if layout == 'fast_fold':
        # Preflop Zoom: only Fast Fold available as a button
        if action == 'fold':
            return click_button('fast_fold', win_rect, logger)
        else:
            # For call/raise in Zoom preflop, we need the full button layout
            # which appears when we DON'T pre-check Fast Fold.
            # If only Fast Fold is showing, we can't raise — just skip this cycle
            # and wait for the full layout to appear.
            if logger:
                logger(f"[BOT] Fast Fold layout but want {action} - waiting for full buttons", "DEBUG")
            return False

    if layout == 'check_bet':
        if action in ('fold', 'call'):
            # Facing no bet — check instead of fold/call
            return click_button('check', win_rect, logger)
        if action == 'check':
            return click_button('check', win_rect, logger)
        if action in ('bet', 'raise'):
            if bet_size and bet_size > 0:
                type_bet_amount(bet_size, win_rect, logger)
            return click_button('bet', win_rect, logger)

    if layout == 'fold_call_raise':
        if action == 'fold':
            return click_button('fold', win_rect, logger)
        if action == 'call':
            return click_button('call', win_rect, logger)
        if action in ('raise', 'bet'):
            if bet_size and bet_size > 0:
                type_bet_amount(bet_size, win_rect, logger)
            return click_button('raise', win_rect, logger)
        if action == 'check':
            # Shouldn't happen in fold/call/raise layout, but call is safest
            return click_button('call', win_rect, logger)

    return False
