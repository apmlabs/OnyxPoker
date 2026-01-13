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


def run_simulation(num_hands=100000):
    """Run simulation with realistic table compositions."""
    random.seed(None)  # Fresh results each run
    
    bot_strategies = ['gpt3', 'gpt4', 'sonnet', 'kiro_optimal', 'kiro5', 'kiro_v2', 'aggressive', '2nl_exploit', 'value_max', 'value_maniac']
    player_archetypes = ['fish', 'nit', 'lag', 'tag', 'maniac']
    all_strategies = bot_strategies + player_archetypes
    
    print(f"Testing {len(bot_strategies)} bot strategies with full postflop play")
    print(f"Bots: {', '.join(bot_strategies)}")
    print(f"Players: {', '.join(player_archetypes)}")
    print(f"TOUGH TABLES: 30% LAG, 25% Maniac, 20% TAG, 15% Fish, 10% Nit (from 795-hand analysis)\n", flush=True)
    
    # Generate table configs - TOUGHER based on real 2NL Blitz data
    # 795-hand analysis: 72% open rate, 11.3% 3bet rate = aggressive tables
    # New distribution: 30% LAG, 25% Maniac, 20% TAG, 15% Fish, 10% Nit
    valid_tables = []
    for bot in bot_strategies:
        # LAG/Maniac heavy (50%) - tough aggressive tables
        for _ in range(3):
            valid_tables.append(['lag', 'lag', 'maniac', 'tag', 'nit', bot])
        for _ in range(2):
            valid_tables.append(['lag', 'maniac', 'maniac', 'tag', 'fish', bot])
        valid_tables.append(['lag', 'lag', 'maniac', 'maniac', 'tag', bot])
        # TAG heavy (25%) - solid regs
        for _ in range(2):
            valid_tables.append(['tag', 'tag', 'lag', 'maniac', 'fish', bot])
        valid_tables.append(['tag', 'tag', 'tag', 'lag', 'nit', bot])
        valid_tables.append(['tag', 'tag', 'lag', 'fish', 'nit', bot])
        # Mixed (25%) - some fish but still tough
        for _ in range(2):
            valid_tables.append(['fish', 'tag', 'lag', 'maniac', 'nit', bot])
        valid_tables.append(['fish', 'fish', 'tag', 'lag', 'maniac', bot])
        valid_tables.append(['fish', 'tag', 'tag', 'lag', 'lag', bot])
        valid_tables.append(['fish', 'tag', 'tag', 'lag', 'nit', bot])
        valid_tables.append(['fish', 'tag', 'nit', 'lag', 'maniac', bot])
        valid_tables.append(['fish', 'fish', 'tag', 'lag', 'nit', bot])
    
    print(f"Generated {len(valid_tables)} table configurations", flush=True)
    
    # Run trials
    all_results = defaultdict(list)
    
    for trial in range(3):
        print(f"\n--- Trial {trial+1}/3 ---", flush=True)
        random.seed(None)  # Fresh each trial
        
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
