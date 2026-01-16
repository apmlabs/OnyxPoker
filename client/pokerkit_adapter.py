#!/usr/bin/env python3
"""
Adapter to run OnyxPoker strategies in PokerKit simulation.
Uses PokerKit for game mechanics, our strategies make decisions.
"""

import random
from pokerkit import Automation, NoLimitTexasHoldem
from poker_logic import preflop_action, postflop_action


def get_street(board):
    n = len(board)
    if n == 0: return 'preflop'
    elif n == 3: return 'flop'
    elif n == 4: return 'turn'
    return 'river'


def get_position(idx, num_players):
    positions = ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO']
    return positions[idx % num_players]


def strategy_decision(state, player_idx, strategy, is_aggressor=True):
    """Get decision from our strategy."""
    # Convert PokerKit cards to our format
    hole = [f"{c.rank}{c.suit}" for c in state.hole_cards[player_idx]]
    board = [f"{c.rank}{c.suit}" for row in state.board_cards for c in row] if state.board_cards else []
    street = get_street(board)
    pot = float(state.total_pot_amount)
    to_call = float(state.checking_or_calling_amount or 0)
    position = get_position(player_idx, len(state.stacks))
    
    # Convert hole cards to hand string (e.g., "AKs" or "AKo")
    c1, c2 = hole[0], hole[1]
    r1, s1 = c1[0], c1[1]
    r2, s2 = c2[0], c2[1]
    rank_order = 'AKQJT98765432'
    if rank_order.index(r1) > rank_order.index(r2):
        r1, r2, s1, s2 = r2, r1, s2, s1
    suited = 's' if s1 == s2 else 'o'
    hand_str = r1 + r2 if r1 == r2 else r1 + r2 + suited
    
    archetypes = ['fish', 'nit', 'tag', 'lag', 'maniac']
    is_archetype = strategy in archetypes
    
    if street == 'preflop':
        if to_call <= 0.02: facing = 'none'
        elif to_call <= 0.08: facing = 'open'
        elif to_call <= 0.25: facing = '3bet'
        else: facing = '4bet'
        
        from poker_logic import STRATEGIES
        strat_dict = STRATEGIES.get(strategy, STRATEGIES.get('value_lord'))
        result = preflop_action(hand_str, position, strat_dict, facing)
        action = result[0]
        size = 0.66
    else:
        action, size, _ = postflop_action(
            hole, board, pot, to_call, street,
            is_ip=True, is_aggressor=is_aggressor,
            archetype=strategy if is_archetype else None,
            strategy=strategy if not is_archetype else None
        )
    return action, size


def run_hand(strategies, verbose=False):
    """Run single hand, return payoffs."""
    n = len(strategies)
    state = NoLimitTexasHoldem.create_state(
        automations=(
            Automation.ANTE_POSTING, Automation.BET_COLLECTION,
            Automation.BLIND_OR_STRADDLE_POSTING, Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
            Automation.HAND_KILLING, Automation.CHIPS_PUSHING, Automation.CHIPS_PULLING,
        ),
        ante_trimming_status=True, raw_antes=0,
        raw_blinds_or_straddles=(0.01, 0.02), min_bet=0.02,
        raw_starting_stacks=(2.0,) * n, player_count=n,
    )
    
    deck = [f"{r}{s}" for r in 'AKQJT98765432' for s in 'hdcs']
    random.shuffle(deck)
    for i in range(n):
        state.deal_hole(''.join(deck[i*2:(i+1)*2]))
    
    opener = None
    for _ in range(100):
        if not state.status: break
        
        if state.actor_index is None:
            board_len = len([c for row in state.board_cards for c in row]) if state.board_cards else 0
            state.burn_card('??')
            if board_len == 0:
                for card in deck[n*2:n*2+3]: state.deal_board(card)
            elif board_len == 3: state.deal_board(deck[n*2+3])
            elif board_len == 4: state.deal_board(deck[n*2+4])
            continue
        
        idx = state.actor_index
        action, size = strategy_decision(state, idx, strategies[idx], opener == idx)
        to_call = float(state.checking_or_calling_amount or 0)
        
        if action == 'fold':
            if to_call > 0:
                state.fold()
            else:
                state.check_or_call()
        elif action in ('call', 'check'):
            state.check_or_call()
        elif action == 'raise':
            pot = float(state.total_pot_amount)
            raise_to = to_call + (size if size > 0 else 0.66) * (pot + to_call)
            min_raise = getattr(state, 'min_completion_raising_to_amount', None)
            raise_to = max(raise_to, float(min_raise) if min_raise else 0.04)
            raise_to = min(raise_to, 2.0)
            try:
                state.complete_bet_or_raise_to(raise_to)
                if opener is None: opener = idx
            except:
                state.check_or_call()
        else:
            state.check_or_call()
    
    return list(state.payoffs)


def random_5nl_table():
    """Generate random 5-player table matching real 5NL composition.
    Target: 8.5% fish, 31% nit, 39% TAG, 22% LAG (from Session 43 Part 24)
    """
    archetypes = ['fish', 'nit', 'tag', 'lag']
    weights = [0.085, 0.31, 0.39, 0.22]
    return [random.choices(archetypes, weights)[0] for _ in range(5)]


def simulate(hero, num_hands=1000, show_progress=True):
    """Run simulation, return BB/100 for hero strategy."""
    total = 0.0
    hands = 0
    
    for i in range(num_hands):
        opponents = random_5nl_table()
        table = [hero] + opponents
        random.shuffle(table)
        hero_idx = table.index(hero)
        
        try:
            payoffs = run_hand(table)
            total += payoffs[hero_idx]
            hands += 1
        except:
            pass
        
        if show_progress and (i + 1) % 1000 == 0:
            print(f"  {i + 1}/{num_hands} hands...", flush=True)
    
    bb100 = (total / 0.02 / hands * 100) if hands else 0
    return {'total': total, 'hands': hands, 'bb100': bb100}


if __name__ == '__main__':
    import sys
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    
    print(f"PokerKit simulation: {num} hands per strategy", flush=True)
    print("Opponents: random 5NL table (8.5% fish, 31% nit, 39% TAG, 22% LAG)")
    print("=" * 50, flush=True)
    
    for bot in ['value_lord', 'kiro_optimal', 'kiro_lord', 'sonnet']:
        print(f"\nTesting {bot}...", flush=True)
        r = simulate(bot, num)
        print(f"  Result: {r['bb100']:+.1f} BB/100 ({r['hands']} hands)", flush=True)
