#!/usr/bin/env python3
"""
Poker Strategy Simulator - Tests strategies with full postflop play.
Uses poker_logic.py for hand evaluation and decisions.
"""

import random
from collections import defaultdict
from poker_logic import (
    RANKS, SUITS, RANK_VAL, STRATEGIES, expand_range,
    hand_to_str, analyze_hand, postflop_action, preflop_action
)

POSITIONS = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']

def make_deck():
    return [(r, s) for r in RANKS for s in SUITS]

STACK_SIZE = 100.0  # 100 BB stacks

class Player:
    def __init__(self, name, strategy):
        self.name = name
        self.strategy = strategy
        self.stats = defaultdict(int)
        self.profit = 0.0
        self.cards = None
        self.hand_str = None

def simulate_hand(players, dealer_pos):
    """Simulate one hand with full postflop play and proper stack limits."""
    deck = make_deck()
    random.shuffle(deck)
    
    # Deal hole cards
    for p in players:
        p.cards = (deck.pop(), deck.pop())
        p.hand_str = hand_to_str(p.cards)
    
    # Assign positions
    positions = {}
    for i, pos in enumerate(POSITIONS):
        idx = (dealer_pos + i + 1) % 6
        positions[players[idx].name] = pos
    
    # Each player starts with STACK_SIZE BB
    stacks = {p.name: STACK_SIZE for p in players}
    invested = {p.name: 0.0 for p in players}
    active = {p.name: True for p in players}
    all_in = {p.name: False for p in players}
    
    # Post blinds
    sb_player = next(p for p in players if positions[p.name] == 'SB')
    bb_player = next(p for p in players if positions[p.name] == 'BB')
    invested[sb_player.name] = min(0.5, stacks[sb_player.name])
    invested[bb_player.name] = min(1.0, stacks[bb_player.name])
    stacks[sb_player.name] -= invested[sb_player.name]
    stacks[bb_player.name] -= invested[bb_player.name]
    
    # Preflop action
    opener = None
    three_bettor = None
    open_size = 2.5
    three_bet_size = 8.0
    
    action_order = []
    for pos in POSITIONS:
        for p in players:
            if positions[p.name] == pos:
                action_order.append(p)
                break
    
    def bet_amount(player, amount):
        """Bet up to amount, limited by stack. Returns actual bet."""
        actual = min(amount, stacks[player.name] + invested[player.name])
        add = actual - invested[player.name]
        if add > 0:
            stacks[player.name] -= add
            invested[player.name] = actual
            if stacks[player.name] <= 0:
                all_in[player.name] = True
        return actual
    
    for p in action_order:
        if not active[p.name] or all_in[p.name]:
            continue
        pos = positions[p.name]
        p.stats['hands'] += 1
        base = p.base_strategy if hasattr(p, 'base_strategy') else p.name
        
        if opener is None:
            facing = 'none'
            action, _ = preflop_action(p.hand_str, pos, p.strategy, facing)
            
            # Fish limp ~8% of hands they play
            if base == 'fish' and action == 'raise' and random.random() < 0.15:
                bet_amount(p, 1.0)  # Limp
                p.stats['vpip'] += 1
                continue
            
            if action == 'raise':
                opener = p
                bet_amount(p, open_size)
                p.stats['vpip'] += 1
                p.stats['pfr'] += 1
            elif pos != 'BB':
                active[p.name] = False
        else:
            facing = 'open'
            action, _ = preflop_action(p.hand_str, pos, p.strategy, facing, positions[opener.name])
            if action == 'raise':
                three_bettor = p
                if base == 'maniac':
                    three_bet_mult = random.uniform(3.0, 5.0)
                    bet_amount(p, open_size * three_bet_mult)
                else:
                    bet_amount(p, three_bet_size)
                p.stats['vpip'] += 1
                p.stats['pfr'] += 1
            elif action == 'call':
                bet_amount(p, invested[opener.name])
                p.stats['vpip'] += 1
            else:
                active[p.name] = False
    
    # Handle 3-bet response
    if three_bettor and opener and active[opener.name] and not all_in[opener.name]:
        action, _ = preflop_action(opener.hand_str, positions[opener.name], opener.strategy, '3bet')
        three_bet_amt = invested[three_bettor.name]
        if action == 'raise':
            bet_amount(opener, three_bet_amt * 2.5)  # 4-bet
        elif action == 'call':
            bet_amount(opener, three_bet_amt)
        else:
            active[opener.name] = False
    
    pot = sum(invested.values())
    active_players = [p for p in players if active[p.name]]
    
    # Everyone folded
    if len(active_players) == 1:
        winner = active_players[0]
        winner.stats['steals'] += 1
        for p in players:
            p.profit += (pot - invested[p.name]) if p == winner else -invested[p.name]
        return
    
    if len(active_players) == 0:
        for p in players:
            p.profit -= invested[p.name]
        bb_player.profit += pot
        return
    
    # Deal board and play postflop
    board = []
    streets = [('flop', 3), ('turn', 1), ('river', 1)]
    
    for street_name, num_cards in streets:
        for _ in range(num_cards):
            board.append(deck.pop())
        
        active_players = [p for p in players if active[p.name] and not all_in[p.name]]
        if len([p for p in players if active[p.name]]) <= 1:
            break
        # If everyone is all-in, just deal remaining cards
        if len(active_players) == 0:
            continue
        
        # Postflop betting round
        pos_order = ['SB', 'BB', 'UTG', 'MP', 'CO', 'BTN']
        
        current_bet = 0
        round_invested = {p.name: 0 for p in players}
        bet_count = 0  # capped at 4
        
        needs_action = {p.name: True for p in players if active[p.name] and not all_in[p.name]}
        
        while any(needs_action.values()):
            street_order = sorted([p for p in players if active[p.name] and not all_in[p.name]], 
                                  key=lambda p: pos_order.index(positions[p.name]))
            
            acted_this_orbit = False
            for p in street_order:
                if not active[p.name] or not needs_action[p.name] or all_in[p.name]:
                    continue
                
                to_call = min(current_bet - round_invested[p.name], stacks[p.name])
                is_ip = positions[p.name] in ['BTN', 'CO']
                is_agg = (p == opener) or (p == three_bettor)
                num_opponents = len([x for x in players if active[x.name] and x != p])
                
                base = p.base_strategy if hasattr(p, 'base_strategy') else p.name
                archetype = base if base in ['fish', 'nit', 'tag', 'lag', 'maniac'] else None
                strategy = base if base not in ['fish', 'nit', 'tag', 'lag', 'maniac'] else None
                
                action, bet_size, _ = postflop_action(
                    list(p.cards), board, pot, to_call, street_name, is_ip, is_agg,
                    archetype=archetype, strategy=strategy, num_opponents=num_opponents
                )
                
                needs_action[p.name] = False
                acted_this_orbit = True
                
                if action == 'fold':
                    active[p.name] = False
                elif action == 'call':
                    # Call limited by stack
                    actual_call = min(to_call, stacks[p.name])
                    round_invested[p.name] += actual_call
                    invested[p.name] += actual_call
                    stacks[p.name] -= actual_call
                    pot += actual_call
                    if stacks[p.name] <= 0:
                        all_in[p.name] = True
                elif action in ['bet', 'raise']:
                    if bet_count < 4:  # Can still raise
                        # Limit bet to remaining stack
                        total_wanted = to_call + bet_size
                        actual_add = min(total_wanted, stacks[p.name])
                        round_invested[p.name] += actual_add
                        invested[p.name] += actual_add
                        stacks[p.name] -= actual_add
                        pot += actual_add
                        current_bet = round_invested[p.name]
                        bet_count += 1
                        if stacks[p.name] <= 0:
                            all_in[p.name] = True
                        # Everyone else needs to act again (if not all-in)
                        for other in players:
                            if active[other.name] and other != p and not all_in[other.name]:
                                needs_action[other.name] = True
                    else:
                        # Betting capped - just call
                        actual_call = min(to_call, stacks[p.name])
                        round_invested[p.name] += actual_call
                        invested[p.name] += actual_call
                        stacks[p.name] -= actual_call
                        pot += actual_call
                        if stacks[p.name] <= 0:
                            all_in[p.name] = True
            
            # Safety: if no one acted, we're done
            if not acted_this_orbit:
                break
            # Safety: if only one active non-all-in player, stop betting
            if len([p for p in players if active[p.name] and not all_in[p.name]]) <= 1:
                break
    
    # Showdown
    active_players = [p for p in players if active[p.name]]
    
    if len(active_players) <= 1:
        winner = active_players[0] if active_players else bb_player
        for p in players:
            p.profit += (pot - invested[p.name]) if p == winner else -invested[p.name]
        return
    
    # Evaluate hands
    best_rank = -1
    best_kicker = -1
    winners = []
    
    for p in active_players:
        info = analyze_hand(list(p.cards), board)
        rank, kicker = info['strength'], info['kicker']
        if rank > best_rank or (rank == best_rank and kicker > best_kicker):
            best_rank = rank
            best_kicker = kicker
            winners = [p]
        elif rank == best_rank and kicker == best_kicker:
            winners.append(p)
    
    if not winners:
        winners = active_players  # Fallback
    
    # Split pot among winners
    share = pot / len(winners)
    for p in players:
        if p in winners:
            p.profit += share - invested[p.name]
            p.stats['wins'] += 1
        else:
            p.profit -= invested[p.name]


def get_table_configs():
    """Return realistic 5NL table compositions based on REAL data analysis.
    
    Real 5NL data (1209 hands, 71 players with 20+ hands):
    - FISH: 8.5%
    - NIT: 30.9%
    - TAG: 38.6%
    - LAG: 22.0%
    - MANIAC: 0%
    
    This is MUCH tighter than previously assumed!
    """
    # 5 opponents per table, weighted by real distribution
    # Target: ~10% fish, ~30% nit, ~40% tag, ~20% lag
    return [
        ['nit', 'tag', 'tag', 'lag', 'tag'],         # 20% nit, 60% tag, 20% lag
        ['fish', 'nit', 'tag', 'tag', 'lag'],        # 20% fish, 20% nit, 40% tag, 20% lag
        ['nit', 'nit', 'tag', 'tag', 'lag'],         # 40% nit, 40% tag, 20% lag
        ['nit', 'tag', 'tag', 'lag', 'lag'],         # 20% nit, 40% tag, 40% lag
        ['fish', 'nit', 'nit', 'tag', 'tag'],        # 20% fish, 40% nit, 40% tag
        ['nit', 'tag', 'lag', 'lag', 'tag'],         # 20% nit, 40% tag, 40% lag
    ]


def run_simulation(num_hands=100000):
    """Run simulation on realistic 2NL tables."""
    random.seed(None)
    
    bot_strategies = ['optimal_stats', 'value_lord', 'kiro_optimal', 'kiro_lord', 'sonnet']
    tables = get_table_configs()
    
    print(f"Testing {len(bot_strategies)} strategies")
    print(f"Total hands: {num_hands:,}")
    print(f"Table: ~10% fish, ~30% nit, ~40% tag, ~20% lag (REAL 5NL data)\n", flush=True)
    
    results = {bot: [] for bot in bot_strategies}
    
    for trial in range(3):
        print(f"--- Trial {trial+1}/3 ---", flush=True)
        
        hands_per_table = num_hands // (len(tables) * len(bot_strategies))
        
        for bot in bot_strategies:
            profit = 0.0
            hands = 0
            
            for table_comp in tables:
                strats = table_comp + [bot]
                name_counts = {}
                players = []
                for strat in strats:
                    name_counts[strat] = name_counts.get(strat, 0) + 1
                    unique_name = f"{strat}_{name_counts[strat]}" if strats.count(strat) > 1 else strat
                    p = Player(unique_name, STRATEGIES[strat])
                    p.base_strategy = strat
                    players.append(p)
                
                for i in range(hands_per_table):
                    simulate_hand(players, i % 6)
                
                bot_player = players[-1]
                profit += bot_player.profit
                hands += bot_player.stats['hands']
            
            bb100 = (profit / hands) * 100 if hands > 0 else 0
            results[bot].append(bb100)
        
        print("  Complete", flush=True)
    
    # Print results
    print("\n" + "=" * 60)
    print(f"RESULTS ({num_hands:,} hands, 3 trials avg)")
    print("=" * 60)
    print(f"\n{'Rank':<6} {'Strategy':<15} {'BB/100':>10} {'StdDev':>10}")
    print("-" * 45)
    
    final = []
    for bot in bot_strategies:
        avg = sum(results[bot]) / len(results[bot])
        std = (sum((x - avg) ** 2 for x in results[bot]) / len(results[bot])) ** 0.5
        final.append((bot, avg, std))
    
    for rank, (bot, avg, std) in enumerate(sorted(final, key=lambda x: -x[1]), 1):
        print(f"{rank:<6} {bot:<15} {avg:>+10.2f} {std:>10.2f}")


if __name__ == '__main__':
    import sys
    num_hands = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    print("="*80)
    print("POKER STRATEGY SIMULATOR (with postflop)")
    print("="*80)
    print(flush=True)
    run_simulation(num_hands)
