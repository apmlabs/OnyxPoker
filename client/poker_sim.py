#!/usr/bin/env python3
"""
Poker Strategy Simulator - Tests strategies with full postflop play.
Uses poker_logic.py for hand evaluation and decisions.
"""

import random
from collections import defaultdict
from poker_logic import (
    RANKS, SUITS, RANK_VAL, STRATEGIES, expand_range,
    hand_to_str, evaluate_hand, postflop_action, preflop_action
)

POSITIONS = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']

def make_deck():
    return [(r, s) for r in RANKS for s in SUITS]

class Player:
    def __init__(self, name, strategy):
        self.name = name
        self.strategy = strategy
        self.stack = 100.0
        self.stats = defaultdict(int)
        self.profit = 0.0
        self.cards = None
        self.hand_str = None

def simulate_hand(players, dealer_pos):
    """Simulate one hand with full postflop play."""
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
    
    invested = {p.name: 0.0 for p in players}
    active = {p.name: True for p in players}
    
    # Post blinds
    sb_player = next(p for p in players if positions[p.name] == 'SB')
    bb_player = next(p for p in players if positions[p.name] == 'BB')
    invested[sb_player.name] = 0.5
    invested[bb_player.name] = 1.0
    
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
    
    # No limpers in 2NL Blitz (0% from 407-hand analysis)
    
    for p in action_order:
        if not active[p.name]:
            continue
        pos = positions[p.name]
        p.stats['hands'] += 1
        base = p.base_strategy if hasattr(p, 'base_strategy') else p.name
        
        if opener is None:
            facing = 'none'
            action, _ = preflop_action(p.hand_str, pos, p.strategy, facing)
            
            # Fish limp removed - real 2NL Blitz has 0% limps (from 407 hand analysis)
            
            if action == 'raise':
                opener = p
                invested[p.name] = open_size
                p.stats['vpip'] += 1
                p.stats['pfr'] += 1
            elif pos != 'BB':
                active[p.name] = False
        else:
            facing = 'open'
            action, _ = preflop_action(p.hand_str, pos, p.strategy, facing, positions[opener.name])
            if action == 'raise':
                three_bettor = p
                # Maniacs use variable 3-bet sizing (3x to 5x the open)
                if base == 'maniac':
                    three_bet_mult = random.uniform(3.0, 5.0)
                    invested[p.name] = open_size * three_bet_mult
                else:
                    invested[p.name] = three_bet_size
                p.stats['vpip'] += 1
                p.stats['pfr'] += 1
            elif action == 'call':
                invested[p.name] = open_size
                p.stats['vpip'] += 1
            else:
                active[p.name] = False
    
    # Limpers removed - real 2NL Blitz has 0% limps
    
    # Handle 3-bet response
    if three_bettor and opener and active[opener.name]:
        action, _ = preflop_action(opener.hand_str, positions[opener.name], opener.strategy, '3bet')
        three_bet_amt = invested[three_bettor.name]
        if action == 'raise':
            invested[opener.name] = three_bet_amt * 2.5  # 4-bet
        elif action == 'call':
            invested[opener.name] = three_bet_amt
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
        
        active_players = [p for p in players if active[p.name]]
        if len(active_players) <= 1:
            break
        
        # Postflop betting - simplified single orbit
        pos_order = ['SB', 'BB', 'UTG', 'MP', 'CO', 'BTN']
        street_order = sorted(active_players, key=lambda p: pos_order.index(positions[p.name]))
        
        current_bet = 0
        round_invested = {p.name: 0 for p in players}
        
        for p in street_order:
            if not active[p.name]:
                continue
            
            to_call = current_bet - round_invested[p.name]
            is_ip = positions[p.name] in ['BTN', 'CO']
            is_agg = (p == opener) or (p == three_bettor)
            
            # Count active opponents
            num_opponents = len([x for x in active_players if x != p]) - 1
            
            # Determine archetype vs bot strategy
            base = p.base_strategy if hasattr(p, 'base_strategy') else p.name
            archetype = base if base in ['fish', 'nit', 'tag', 'lag'] else None
            strategy = base if base in ['gpt3', 'gpt4', 'sonnet', 'kiro_optimal'] else None
            
            action, bet_size, _ = postflop_action(
                list(p.cards), board, pot, to_call, street_name, is_ip, is_agg,
                archetype=archetype, strategy=strategy, num_opponents=num_opponents
            )
            
            if action == 'fold':
                active[p.name] = False
            elif action == 'call':
                round_invested[p.name] += to_call
                invested[p.name] += to_call
                pot += to_call
            elif action in ['bet', 'raise']:
                round_invested[p.name] += to_call + bet_size
                invested[p.name] += to_call + bet_size
                pot += to_call + bet_size
                current_bet = round_invested[p.name]
    
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
        rank, desc, kicker = evaluate_hand(list(p.cards), board)
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
    """Return realistic 2NL table compositions based on log analysis."""
    # REALISTIC 2NL BLITZ: Based on 886 hands of log analysis
    # - 73% check postflop (very passive)
    # - 21% c-bet (low aggression)  
    # - Estimated: 60% fish, 25% nit, 15% tag
    return [
        ['fish', 'fish', 'fish', 'nit', 'tag'],
        ['fish', 'fish', 'fish', 'fish', 'nit'],
        ['fish', 'fish', 'fish', 'nit', 'nit'],
        ['fish', 'fish', 'nit', 'tag', 'fish'],
    ]


def run_simulation(num_hands=100000):
    """Run simulation on realistic 2NL tables."""
    random.seed(None)
    
    bot_strategies = ['value_maniac', 'value_max', 'sonnet_max', 'sonnet', 'gpt4', 'gpt3', 
                      'kiro_optimal', 'kiro5', 'kiro_v2', '2nl_exploit', 'aggressive',
                      'fish', 'nit', 'tag', 'lag', 'maniac']
    tables = get_table_configs()
    
    print(f"Testing {len(bot_strategies)} strategies")
    print(f"Total hands: {num_hands:,}")
    print(f"Table: 60% fish, 25% nit, 15% tag (realistic 2NL)\n", flush=True)
    
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
