#!/usr/bin/env python3
"""Analyze all hands >=10BB won/lost and show what value_lord would do."""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from poker_logic import preflop_action, postflop_action, analyze_hand

RANK_MAP = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}
for i in range(2, 10): RANK_MAP[str(i)] = str(i)

def parse_card(s):
    s = s.strip()
    if len(s) == 2: return s[0].upper(), s[1].lower()
    if len(s) == 3: return '10', s[2].lower()
    return None, None

def parse_hand_history(text):
    """Parse a single hand from PokerStars format."""
    lines = text.strip().split('\n')
    if not lines: return None
    
    # Get hand ID and BB
    m = re.search(r'Hand #(\d+)', lines[0])
    hand_id = m.group(1) if m else 'unknown'
    m = re.search(r'€([\d.]+)/€([\d.]+)', lines[0])
    bb = float(m.group(2)) if m else 0.05
    
    # Find hero
    hero = None
    hero_cards = None
    for line in lines:
        m = re.match(r'Dealt to (\S+) \[(.+)\]', line)
        if m:
            hero = m.group(1)
            cards = m.group(2).split()
            hero_cards = [parse_card(c) for c in cards]
            break
    if not hero_cards: return None
    
    # Parse board
    board = []
    for line in lines:
        m = re.search(r'\*\*\* (FLOP|TURN|RIVER) \*\*\* \[([^\]]+)\]', line)
        if m:
            cards = m.group(2).replace('[', '').replace(']', '').split()
            board = [parse_card(c) for c in cards if c.strip()]
    
    # Calculate hero profit
    invested = 0
    won = 0
    for line in lines:
        if hero in line:
            # Posts
            m = re.search(rf'{re.escape(hero)}: posts (?:small |big )?blind €([\d.]+)', line)
            if m: invested += float(m.group(1))
            # Calls
            m = re.search(rf'{re.escape(hero)}: calls €([\d.]+)', line)
            if m: invested += float(m.group(1))
            # Raises/bets
            m = re.search(rf'{re.escape(hero)}: (?:raises|bets) €[\d.]+ to €([\d.]+)', line)
            if m: invested = float(m.group(1))  # Total invested
            m = re.search(rf'{re.escape(hero)}: bets €([\d.]+)', line)
            if m and 'to €' not in line: invested += float(m.group(1))
        # Uncalled bet returned
        m = re.search(rf'Uncalled bet \(€([\d.]+)\) returned to {re.escape(hero)}', line)
        if m: invested -= float(m.group(1))
        # Won pot
        m = re.search(rf'{re.escape(hero)} collected €([\d.]+)', line)
        if m: won += float(m.group(1))
    
    profit_bb = (won - invested) / bb
    
    # Get position
    positions = []
    in_seats = False
    for line in lines:
        if 'Seat ' in line and ': ' in line and '€' in line:
            m = re.match(r'Seat \d+: (\S+)', line)
            if m: positions.append(m.group(1))
        if '*** HOLE CARDS ***' in line: break
    
    # Find button
    btn_seat = None
    for line in lines:
        m = re.search(r'Seat #(\d+) is the button', line)
        if m:
            btn_seat = int(m.group(1))
            break
    
    # Determine hero position
    pos_names = ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO']
    hero_pos = 'BTN'
    if btn_seat and hero in positions:
        hero_idx = positions.index(hero)
        # Find button player index
        for i, line in enumerate(lines):
            if f'Seat {btn_seat}:' in line:
                m = re.match(r'Seat \d+: (\S+)', line)
                if m:
                    btn_player = m.group(1)
                    if btn_player in positions:
                        btn_idx = positions.index(btn_player)
                        offset = (hero_idx - btn_idx) % len(positions)
                        if offset < len(pos_names):
                            hero_pos = pos_names[offset]
                break
    
    return {
        'hand_id': hand_id,
        'hero': hero,
        'hero_cards': hero_cards,
        'board': board,
        'profit_bb': profit_bb,
        'position': hero_pos,
        'bb': bb,
        'text': text
    }

def get_value_lord_advice(hand):
    """Get value_lord advice for each street."""
    cards = hand['hero_cards']
    board = hand['board']
    pos = hand['position']
    
    # Convert cards to canonical notation (AA, AKs, AKo)
    from poker_logic import hand_to_str, STRATEGIES
    hand_str = hand_to_str(cards)
    
    advice = []
    
    # Preflop - need strategy dict from STRATEGIES
    strat = STRATEGIES.get('value_lord', STRATEGIES['value_maniac'])
    pf = preflop_action(hand_str, pos, strat, 'none')
    advice.append(f"Preflop: {pf[0].upper()} ({pf[1]})")
    
    # Postflop streets
    if len(board) >= 3:
        for street, n_cards in [('flop', 3), ('turn', 4), ('river', 5)]:
            if len(board) >= n_cards:
                b = board[:n_cards]
                # postflop_action(hole_cards, board, pot, to_call, street, is_ip, is_aggressor, archetype, strategy, num_opponents, bb_size)
                # First to act
                act, size, reason = postflop_action(cards, b, 1.0, 0, street, True, True, None, 'value_lord', 1, 0.05)
                advice.append(f"{street.title()} (1st): {act.upper()} ({reason})")
                # Facing 50% pot bet
                act2, size2, reason2 = postflop_action(cards, b, 1.0, 0.5, street, True, False, None, 'value_lord', 1, 0.05)
                advice.append(f"{street.title()} (vs 50%): {act2.upper()} ({reason2})")
                # Facing raise/shove (150% pot)
                act3, size3, reason3 = postflop_action(cards, b, 1.0, 1.5, street, True, False, None, 'value_lord', 1, 0.05)
                advice.append(f"{street.title()} (vs 150%): {act3.upper()} ({reason3})")
    
    return advice

def main():
    hh_dir = '../idealistslp_extracted'
    all_hands = []
    
    for fname in os.listdir(hh_dir):
        if not fname.endswith('.txt'): continue
        with open(os.path.join(hh_dir, fname), 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into hands
        hands = re.split(r'\n\n+(?=PokerStars)', content)
        for h in hands:
            if not h.strip(): continue
            parsed = parse_hand_history(h)
            if parsed and abs(parsed['profit_bb']) >= 10:
                all_hands.append(parsed)
    
    # Sort by profit
    all_hands.sort(key=lambda x: x['profit_bb'])
    
    print(f"=== HANDS WITH >=10BB SWING ({len(all_hands)} total) ===\n")
    
    for h in all_hands:
        cards_str = ''.join(f"{r}{s}" for r, s in h['hero_cards'])
        board_str = ' '.join(f"{r}{s}" for r, s in h['board']) if h['board'] else 'no showdown'
        sign = '+' if h['profit_bb'] > 0 else ''
        
        print(f"Hand #{h['hand_id']}: {cards_str} | {h['position']} | Board: {board_str}")
        print(f"Result: {sign}{h['profit_bb']:.1f} BB")
        print("value_lord advice:")
        for a in get_value_lord_advice(h):
            print(f"  {a}")
        print()

if __name__ == '__main__':
    main()
