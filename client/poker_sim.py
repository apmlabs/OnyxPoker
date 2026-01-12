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
    
    for p in action_order:
        if not active[p.name]:
            continue
        pos = positions[p.name]
        p.stats['hands'] += 1
        
        if opener is None:
            facing = 'none'
            action, _ = preflop_action(p.hand_str, pos, p.strategy, facing)
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
                invested[p.name] = three_bet_size
                p.stats['vpip'] += 1
                p.stats['pfr'] += 1
            elif action == 'call':
                invested[p.name] = open_size
                p.stats['vpip'] += 1
            else:
                active[p.name] = False
    
    # Handle 3-bet response
    if three_bettor and opener and active[opener.name]:
        action, _ = preflop_action(opener.hand_str, positions[opener.name], opener.strategy, '3bet')
        if action == 'raise':
            invested[opener.name] = 20.0
        elif action == 'call':
            invested[opener.name] = three_bet_size
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
            
            action, bet_size, _ = postflop_action(
                list(p.cards), board, pot, to_call, street_name, is_ip, is_agg,
                archetype=p.base_strategy if hasattr(p, 'base_strategy') else p.name
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


def run_simulation(num_hands=100000):
    """Run simulation with realistic table compositions."""
    random.seed(42)
    
    bot_strategies = ['gpt3', 'gpt4', 'sonnet', 'kiro_optimal']
    player_archetypes = ['fish', 'nit', 'lag', 'tag']
    all_strategies = bot_strategies + player_archetypes
    
    print(f"Testing {len(bot_strategies)} bot strategies with full postflop play")
    print(f"Bots: {', '.join(bot_strategies)}")
    print(f"Players: {', '.join(player_archetypes)}")
    print(f"~40% fish, ~25% TAG, ~20% nit, ~10% LAG per table\n", flush=True)
    
    # Generate table configs
    valid_tables = []
    for bot in bot_strategies:
        # Soft tables (50%)
        for _ in range(3):
            valid_tables.append(['fish', 'fish', 'fish', 'tag', 'nit', bot])
        for _ in range(3):
            valid_tables.append(['fish', 'fish', 'tag', 'tag', 'nit', bot])
        for _ in range(2):
            valid_tables.append(['fish', 'fish', 'tag', 'nit', 'nit', bot])
        # Standard with LAG (35%)
        for _ in range(3):
            valid_tables.append(['fish', 'fish', 'tag', 'nit', 'lag', bot])
        for _ in range(2):
            valid_tables.append(['fish', 'fish', 'tag', 'tag', 'lag', bot])
        valid_tables.append(['fish', 'fish', 'fish', 'tag', 'lag', bot])
        # Tougher (15%)
        valid_tables.append(['fish', 'tag', 'tag', 'nit', 'lag', bot])
        valid_tables.append(['fish', 'tag', 'tag', 'nit', 'nit', bot])
        valid_tables.append(['fish', 'tag', 'nit', 'nit', 'lag', bot])
    
    print(f"Generated {len(valid_tables)} table configurations", flush=True)
    
    # Run trials
    all_results = defaultdict(list)
    
    for trial in range(3):
        print(f"\n--- Trial {trial+1}/3 ---", flush=True)
        random.seed(trial * 1000 + 42)
        
        total_profit = {name: 0.0 for name in all_strategies}
        total_hands = {name: 0 for name in all_strategies}
        
        hands_per_table = num_hands // len(valid_tables)
        
        for idx, table_strats in enumerate(valid_tables):
            name_counts = {}
            players = []
            for strat in table_strats:
                name_counts[strat] = name_counts.get(strat, 0) + 1
                unique_name = f"{strat}_{name_counts[strat]}" if table_strats.count(strat) > 1 else strat
                p = Player(unique_name, STRATEGIES[strat])
                p.base_strategy = strat
                players.append(p)
            
            for i in range(hands_per_table):
                simulate_hand(players, i % 6)
            
            for p in players:
                strat = p.base_strategy
                total_profit[strat] += p.profit
                total_hands[strat] += p.stats['hands']
            
            if (idx + 1) % 20 == 0:
                print(f"  Table {idx+1}/{len(valid_tables)} complete...", flush=True)
        
        for name in all_strategies:
            if total_hands[name] > 0:
                bb100 = (total_profit[name] / total_hands[name]) * 100
                all_results[name].append(bb100)
        
        print(f"Trial {trial+1} complete!", flush=True)
    
    # Final results
    print("\n" + "="*80)
    print(f"FINAL RESULTS (Average of 3 trials, {num_hands} hands each)")
    print("="*80, flush=True)
    
    final = []
    for name in all_strategies:
        if all_results[name]:
            avg = sum(all_results[name]) / len(all_results[name])
            std = (sum((x - avg)**2 for x in all_results[name]) / len(all_results[name])) ** 0.5
            is_bot = name in bot_strategies
            final.append((name, avg, std, all_results[name], is_bot))
    
    final.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n{'Strategy':<15} {'Type':<8} {'Avg BB/100':>12} {'StdDev':>10}")
    print("-"*50)
    
    for name, avg, std, trials, is_bot in final:
        type_str = "BOT" if is_bot else "PLAYER"
        print(f"{name:<15} {type_str:<8} {avg:>+12.2f} {std:>10.2f}")
    
    print("\n" + "="*80)
    print("BOT RANKING")
    print("="*80)
    bot_results = [(n, a, s) for n, a, s, _, is_bot in final if is_bot]
    for i, (name, avg, std) in enumerate(bot_results, 1):
        print(f"{i}. {name}: {avg:+.2f} BB/100 (+/- {std:.2f})")


if __name__ == '__main__':
    import sys
    num_hands = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    print("="*80)
    print("POKER STRATEGY SIMULATOR (with postflop)")
    print("="*80)
    print(flush=True)
    run_simulation(num_hands)
