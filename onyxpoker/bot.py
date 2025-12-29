"""
Main entry point for the OnyxPoker bot.

This script glues together the frontend screen reader and the backend
decision engine to play a 6‑max No‑Limit Texas Hold’em table.  It
assumes the poker client window is positioned and sized according to
the coordinates specified in `config.py`.  When it detects that it is
the hero’s turn, it will parse the current game state, ask the
decision engine for a recommended action, and then perform that
action via mouse/keyboard automation.

**Warning**: Automating actions on real money poker sites can
violate terms of service and may lead to account suspension or legal
consequences.  Use this code for educational and research purposes
only, and only on play money or private simulations.
"""

from __future__ import annotations

import time
from typing import Dict, Any

import pyautogui

from .frontend.screen_reader import ScreenReader
from .backend.strategy_gpt import decide_action
from . import config


def perform_action(action_dict: Dict[str, Any]) -> None:
    """Execute the given action by clicking the appropriate button and typing.

    Args:
        action_dict: dictionary returned by the backend decision engine.
            Contains at least 'action' key and optionally an 'amount'.
    """
    action = action_dict.get('action')
    amount = action_dict.get('amount', 0)
    if action == 'fold':
        x, y, w, h = config.BUTTON_REGIONS['fold']
        pyautogui.click(config.TABLE_REGION[0] + x + w // 2,
                        config.TABLE_REGION[1] + y + h // 2)
        print("Clicked Fold.")
    elif action == 'call':
        x, y, w, h = config.BUTTON_REGIONS['call']
        pyautogui.click(config.TABLE_REGION[0] + x + w // 2,
                        config.TABLE_REGION[1] + y + h // 2)
        print("Clicked Call/Check.")
    elif action == 'raise':
        x, y, w, h = config.BUTTON_REGIONS['raise']
        # Click raise button to focus the bet input
        pyautogui.click(config.TABLE_REGION[0] + x + w // 2,
                        config.TABLE_REGION[1] + y + h // 2)
        # If an amount is specified, type it
        if amount and amount > 0:
            # Select any prefilled number (Ctrl+A) and type new amount
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.typewrite(str(amount), interval=0.02)
            # Press Enter to confirm if needed (depends on client)
            pyautogui.press('enter')
        print(f"Clicked Raise with amount {amount}.")
    else:
        print(f"Unknown action '{action}', doing nothing.")


def main_loop() -> None:
    """Run the bot until interrupted by the user.

    Continuously monitors the table.  When it is our turn, it parses
    the state, calls the decision engine and performs the returned
    action.  It waits a short period after acting to avoid double
    actions.  Use Ctrl+C in the terminal to quit.
    """
    reader = ScreenReader()
    print("OnyxPoker bot started.  Waiting for your turn…")
    try:
        while True:
            # Poll every 0.5 seconds to see if it’s our turn
            if not reader.is_hero_turn():
                time.sleep(0.5)
                continue
            # Parse game state
            state = reader.parse_game_state()
            print("Parsed state:", state)
            # Decide action
            decision = decide_action(state)
            print("Decision:", decision)
            # Perform the action
            perform_action(decision)
            # After acting, wait a few seconds to avoid acting again in the same hand
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nBot stopped by user.")


if __name__ == '__main__':
    main_loop()