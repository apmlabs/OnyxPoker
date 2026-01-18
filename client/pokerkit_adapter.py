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


def run_hand(strategies, verbose=False, track_details=False):
    """Run single hand, return payoffs (or (payoffs, details) if track_details)."""
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
    
    details = {'holes': [deck[i*2:(i+1)*2] for i in range(n)], 'board': [], 'actions': []} if track_details else None
    opener = None
    
    for _ in range(100):
        if not state.status: break
        
        if state.actor_index is None:
            board_len = len([c for row in state.board_cards for c in row]) if state.board_cards else 0
            state.burn_card('??')
            if board_len == 0:
                for card in deck[n*2:n*2+3]: state.deal_board(card)
                if details: details['board'] = deck[n*2:n*2+3]
            elif board_len == 3:
                state.deal_board(deck[n*2+3])
                if details: details['board'].append(deck[n*2+3])
            elif board_len == 4:
                state.deal_board(deck[n*2+4])
                if details: details['board'].append(deck[n*2+4])
            continue
        
        idx = state.actor_index
        action, size = strategy_decision(state, idx, strategies[idx], opener == idx)
        to_call = float(state.checking_or_calling_amount or 0)
        
        if details:
            details['actions'].append((idx, strategies[idx], action, to_call, float(state.total_pot_amount)))
        
        if action == 'fold':
            if to_call > 0:
                state.fold()
            else:
                state.check_or_call()
        elif action in ('call', 'check'):
            state.check_or_call()
        elif action in ('raise', 'bet'):
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
    
    payoffs = list(state.payoffs)
    return (payoffs, details) if track_details else payoffs


def random_5nl_table():
    """Generate random 5-player table matching real 2NL composition.
    Updated Jan 18 2026 from analyze_table_composition.py (deep research):
    Real: 34% fish, 25% nit, 15% rock, 9% lag, 9% tag, 9% maniac
    """
    archetypes = ['fish', 'nit', 'rock', 'lag', 'tag', 'maniac']
    weights = [0.34, 0.25, 0.15, 0.09, 0.09, 0.09]
    return [random.choices(archetypes, weights)[0] for _ in range(5)]


def simulate(hero, num_hands=1000, show_progress=True):
    """Run simulation, return BB/100 and detailed stats for hero strategy."""
    results = []  # per-hand BB results
    
    for i in range(num_hands):
        opponents = random_5nl_table()
        table = [hero] + opponents
        random.shuffle(table)
        hero_idx = table.index(hero)
        
        try:
            payoffs = run_hand(table)
            bb_result = payoffs[hero_idx] / 0.02  # convert to BB
            results.append(bb_result)
        except:
            pass
        
        if show_progress and (i + 1) % 1000 == 0:
            print(f"  {i + 1}/{num_hands} hands...", flush=True)
    
    import statistics
    hands = len(results)
    total_bb = sum(results)
    bb100 = (total_bb / hands * 100) if hands else 0
    
    # Detailed stats
    stdev = statistics.stdev(results) if hands > 1 else 0
    wins = [r for r in results if r > 0]
    losses = [r for r in results if r < 0]
    
    return {
        'hands': hands,
        'bb100': bb100,
        'total_bb': total_bb,
        'stdev': stdev,
        'stdev_100': stdev * 10,  # stdev per 100 hands
        'win_rate': len(wins) / hands * 100 if hands else 0,
        'avg_win': sum(wins) / len(wins) if wins else 0,
        'avg_loss': sum(losses) / len(losses) if losses else 0,
        'max_win': max(results) if results else 0,
        'max_loss': min(results) if results else 0,
    }


def simulate_disasters(hero, num_hands=1000, top_n=10):
    """Run simulation and return worst hands with details."""
    from poker_logic import analyze_hand
    all_hands = []
    
    for i in range(num_hands):
        opponents = random_5nl_table()
        table = [hero] + opponents
        random.shuffle(table)
        hero_idx = table.index(hero)
        
        try:
            payoffs, details = run_hand(table, track_details=True)
            bb = payoffs[hero_idx] / 0.02
            details['hero_idx'] = hero_idx
            details['hero_pos'] = get_position(hero_idx, 6)
            all_hands.append((bb, details))
        except:
            pass
        
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{num_hands}...", flush=True)
    
    all_hands.sort(key=lambda x: x[0])
    
    print(f"\n{'='*60}")
    print(f"TOP {top_n} DISASTER HANDS ({hero})")
    print(f"{'='*60}\n")
    
    for i, (bb, d) in enumerate(all_hands[:top_n]):
        hero_hole = d['holes'][d['hero_idx']]
        board = d['board']
        hero_actions = [a for a in d['actions'] if a[0] == d['hero_idx']]
        
        print(f"{i+1}. Lost {abs(bb):.1f} BB | {d['hero_pos']}")
        print(f"   Hole: {' '.join(hero_hole)}")
        print(f"   Board: {' '.join(board) if board else '(preflop)'}")
        if board:
            analysis = analyze_hand(hero_hole, board)
            print(f"   Final: {analysis['desc']}")
        # Show actions with context
        action_strs = []
        for idx, strat, act, tc, pot in hero_actions:
            if tc > 0:
                action_strs.append(f"{act}(${tc:.2f}/{pot:.2f})")
            else:
                action_strs.append(act)
        print(f"   Actions: {' -> '.join(action_strs)}")
        print()
    
    total = sum(bb for bb, _ in all_hands)
    print(f"Overall: {total:+.1f} BB ({total/len(all_hands)*100:+.1f} BB/100)")


if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    
    # Parse --disasters flag
    disasters = '--disasters' in args
    if disasters:
        args.remove('--disasters')
    
    num = int(args[0]) if args else 1000
    strat = args[1] if len(args) > 1 else 'value_lord'
    
    if disasters:
        print(f"Running {num} hands, finding disasters for {strat}...\n")
        simulate_disasters(strat, num)
    else:
        strategies = [strat] if strat else ['value_lord', 'kiro_optimal', 'kiro_lord', 'sonnet']
        
        print(f"PokerKit simulation: {num} hands", flush=True)
        print("Opponents: random 2NL table (34% fish, 25% nit, 15% rock, 9% lag, 9% tag, 9% maniac)")
        print("=" * 50, flush=True)
        
        for bot in strategies:
            print(f"\nTesting {bot}...", flush=True)
            r = simulate(bot, num)
            print(f"\n  === {bot} Results ===")
            print(f"  BB/100:     {r['bb100']:+.2f}")
            print(f"  Total BB:   {r['total_bb']:+.1f}")
            print(f"  Hands:      {r['hands']}")
            print(f"  StdDev:     {r['stdev']:.2f} BB/hand ({r['stdev_100']:.1f} BB/100)")
            print(f"  Win Rate:   {r['win_rate']:.1f}% of hands")
            print(f"  Avg Win:    {r['avg_win']:+.2f} BB")
            print(f"  Avg Loss:   {r['avg_loss']:.2f} BB")
            print(f"  Max Win:    {r['max_win']:+.1f} BB")
            print(f"  Max Loss:   {r['max_loss']:.1f} BB")
