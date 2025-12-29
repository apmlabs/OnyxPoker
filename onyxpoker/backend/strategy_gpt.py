"""
GPT‑based decision engine for OnyxPoker.

This module defines a function `decide_action(state)` which takes a
structured game state dictionary (as returned by
`frontend.screen_reader.ScreenReader.parse_game_state()`) and
returns a decision on what action the bot should take.  It uses the
OpenAI API to query a large language model (GPT‑4 or compatible) for
advice.

The design is intentionally simple: the game state is turned into a
prompt using a template from `config.py`, the model is invoked, and
the response is parsed to extract the action.  You can replace this
function with your own logic or models (e.g. Monte Carlo simulations
or CFR) without changing the rest of the code.
"""

from __future__ import annotations

import os
from typing import Dict, Any, Tuple

import openai

from .. import config


def serialize_state(state: Dict[str, Any]) -> str:
    """Serialize the game state dict into a human‑readable summary.

    This function turns the internal state representation into a
    description string that can be understood by a language model.
    Feel free to modify the formatting to provide more or less
    information.  The ordering and clarity of the summary can affect
    how well the model understands the context.
    """
    hero_cards = state.get('hero_cards', [])
    community_cards = state.get('community_cards', [])
    pot = state.get('pot', 0)
    stacks = state.get('stacks', [])
    actions = state.get('actions', {})
    # Describe cards; use '?' for unknown
    hero_str = ', '.join(card or '?' for card in hero_cards)
    board_str = ', '.join(card or '?' for card in community_cards)
    # Describe actions
    act_descriptions = []
    for name, label in actions.items():
        if label:
            act_descriptions.append(f"{name}={label}")
    actions_str = ', '.join(act_descriptions)
    # Describe stacks: show hero’s stack plus approximate others
    stacks_str = ' / '.join(str(s) for s in stacks)
    summary = (
        f"Hero cards: {hero_str}\n"
        f"Board: {board_str}\n"
        f"Pot: {pot}\n"
        f"Stacks: {stacks_str}\n"
        f"Available actions: {actions_str}\n"
    )
    return summary


def decide_action(state: Dict[str, Any]) -> Dict[str, Any]:
    """Determine the bot’s next action using GPT.

    The return value is a dict with at least the key `action`,
    containing one of `'fold'`, `'call'` or `'raise'`.  If the action
    is `'raise'`, a second key `amount` will specify the raise amount
    as an integer.  If the GPT call fails or cannot be parsed, the bot
    defaults to folding.
    """
    prompt = config.GPT_PROMPT_TEMPLATE.format(state=serialize_state(state))
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        # Without an API key, we cannot query GPT; fold to be safe
        print("OPENAI_API_KEY not set; defaulting to fold.")
        return {'action': 'fold'}
    openai.api_key = api_key
    try:
        response = openai.ChatCompletion.create(
            model=config.GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert poker assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=config.GPT_TEMPERATURE,
            timeout=config.GPT_TIMEOUT,
        )
        content = response['choices'][0]['message']['content'].strip().lower()
    except Exception as exc:
        print(f"GPT request failed ({exc}); defaulting to fold.")
        return {'action': 'fold'}
    # Parse the model’s reply
    action, amount = _parse_gpt_reply(content)
    return {'action': action, 'amount': amount} if action == 'raise' else {'action': action}


def _parse_gpt_reply(reply: str) -> Tuple[str, int]:
    """Parse the GPT model’s reply into an action and amount.

    The model is instructed to return one of: `fold`, `call`, or
    `raise <amount>`.  This helper extracts the first keyword and any
    numeric value that follows.  If the reply is not understood, it
    returns `('fold', 0)`.
    """
    tokens = reply.split()
    if not tokens:
        return 'fold', 0
    first = tokens[0]
    if first.startswith('f'):  # fold
        return 'fold', 0
    if first.startswith('c'):  # call or check
        return 'call', 0
    if first.startswith('r'):  # raise
        # Attempt to find a number in the rest of the reply
        amt = 0
        for tok in tokens[1:]:
            try:
                amt = int(tok)
                break
            except ValueError:
                continue
        # Fallback: if no amount found, raise minimum (treated as call)
        return 'raise', amt
    # Otherwise default to fold
    return 'fold', 0