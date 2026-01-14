#!/usr/bin/env python3
"""
Postflop strategy tester - tests edge cases and detects leaks.
Usage: python3 test_postflop.py [strategy_name]
Default strategy: value_max
"""

import sys
from poker_logic import postflop_action, analyze_hand, calculate_equity, count_outs

# Test scenarios: (hole_cards, board, street, to_call, pot, description)
SCENARIOS = [
    # === MONSTERS ===
    (["As", "Ah"], ["Ac", "Ad", "7h"], "flop", 0, 10, "Quads"),
    (["Ks", "Kh"], ["Kc", "7d", "7h"], "flop", 0, 10, "Full house"),
    (["As", "Ks"], ["Qs", "Js", "Ts"], "flop", 0, 10, "Royal flush"),
    (["As", "Ah"], ["Ac", "Ad", "7h"], "flop", 5, 10, "Quads facing bet"),
    (["Ks", "Kh"], ["Kc", "7d", "7h"], "flop", 5, 10, "Full house facing bet"),
    
    # === OVERPAIRS ===
    (["As", "Ah"], ["Kc", "7d", "2h"], "flop", 0, 10, "AA overpair"),
    (["Ks", "Kh"], ["Qc", "7d", "2h"], "flop", 0, 10, "KK overpair"),
    (["Qs", "Qh"], ["Jc", "7d", "2h"], "flop", 0, 10, "QQ overpair"),
    (["As", "Ah"], ["Kc", "7d", "2h"], "flop", 5, 10, "AA overpair facing bet"),
    (["Ks", "Kh"], ["Qc", "7d", "2h"], "turn", 10, 20, "KK overpair facing turn bet"),
    (["As", "Ah"], ["Kc", "7d", "2h"], "river", 15, 30, "AA overpair river facing bet"),
    
    # === UNDERPAIRS ===
    (["Ks", "Kh"], ["Ac", "7d", "2h"], "flop", 0, 10, "KK underpair to ace"),
    (["Qs", "Qh"], ["Ac", "Kd", "2h"], "flop", 0, 10, "QQ underpair to AK"),
    (["Ks", "Kh"], ["Ac", "7d", "2h"], "flop", 5, 10, "KK underpair facing bet"),
    (["Js", "Jh"], ["Ac", "7d", "2h"], "flop", 5, 10, "JJ underpair facing bet"),
    (["Js", "Jh"], ["9c", "8d", "Th"], "flop", 0, 10, "JJ overpair + OESD"),
    (["Js", "Jh"], ["9c", "8d", "Ah", "Tc"], "turn", 10, 20, "JJ underpair + draw turn"),
    
    # === TOP PAIR ===
    (["As", "Kh"], ["Ac", "7d", "2h"], "flop", 0, 10, "TPTK"),
    (["As", "Qh"], ["Ac", "7d", "2h"], "flop", 0, 10, "Top pair good kicker"),
    (["As", "5h"], ["Ac", "7d", "2h"], "flop", 0, 10, "Top pair weak kicker"),
    (["As", "Kh"], ["Ac", "7d", "2h"], "flop", 5, 10, "TPTK facing bet"),
    (["As", "Kh"], ["Ac", "7d", "2h"], "turn", 10, 20, "TPTK facing turn bet"),
    (["As", "Kh"], ["Ac", "7d", "2h", "3c"], "river", 15, 30, "TPTK facing river bet"),
    (["As", "5h"], ["Ac", "7d", "2h"], "river", 15, 30, "TPWK river facing bet"),
    
    # === TWO PAIR ===
    (["As", "7h"], ["Ac", "7d", "2h"], "flop", 0, 10, "Two pair"),
    (["As", "7h"], ["Ac", "7d", "2h"], "flop", 5, 10, "Two pair facing bet"),
    (["As", "7h"], ["Ac", "7d", "2h", "2c"], "turn", 0, 20, "Two pair board paired turn"),
    (["As", "7h"], ["Ac", "7d", "2h", "2c"], "turn", 10, 20, "Two pair board paired facing bet"),
    (["As", "7h"], ["Ac", "7d", "2h", "2c"], "river", 15, 30, "Two pair board paired river facing bet"),
    
    # === SETS ===
    (["7s", "7h"], ["Ac", "7d", "2h"], "flop", 0, 10, "Set"),
    (["7s", "7h"], ["Ac", "7d", "2h"], "flop", 5, 10, "Set facing bet"),
    (["7s", "7h"], ["Ac", "7d", "2h", "2c"], "turn", 10, 20, "Set board paired facing bet"),
    (["2s", "2h"], ["Ac", "7d", "2c"], "flop", 0, 10, "Bottom set"),
    
    # === STRAIGHTS ===
    (["Js", "Th"], ["9c", "8d", "7h"], "flop", 0, 10, "Straight"),
    (["Js", "Th"], ["9c", "8d", "7h", "7c"], "turn", 10, 20, "Straight board paired facing bet"),
    (["Js", "Th"], ["9c", "8d", "7h", "7c", "9d"], "river", 15, 30, "Straight double paired river"),
    
    # === FLUSHES ===
    (["As", "Ks"], ["Qs", "7s", "2s"], "flop", 0, 10, "Nut flush"),
    (["7s", "6s"], ["Qs", "Js", "2s"], "flop", 0, 10, "Small flush"),
    (["7s", "6s"], ["Qs", "Js", "2s", "Qc"], "turn", 10, 20, "Small flush board paired"),
    
    # === FLUSH DRAWS ===
    (["As", "Ks"], ["Qs", "7s", "2h"], "flop", 0, 10, "Nut flush draw"),
    (["As", "Ks"], ["Qs", "7s", "2h"], "flop", 5, 10, "Nut flush draw facing 50% pot"),
    (["As", "Ks"], ["Qs", "7s", "2h"], "flop", 8, 10, "Nut flush draw facing 80% pot"),
    (["As", "Ks"], ["Qs", "7s", "2h", "3c"], "turn", 10, 20, "Flush draw turn facing bet"),
    (["As", "Ks"], ["Qs", "7s", "2h", "3c", "4d"], "river", 15, 30, "Missed flush draw river"),
    
    # === STRAIGHT DRAWS ===
    (["Js", "Th"], ["9c", "8d", "2h"], "flop", 0, 10, "OESD"),
    (["Js", "Th"], ["9c", "8d", "2h"], "flop", 5, 10, "OESD facing 50% pot"),
    (["Js", "Th"], ["9c", "8d", "2h"], "flop", 10, 10, "OESD facing pot bet"),
    (["Ks", "Qh"], ["Jc", "Td", "2h"], "flop", 0, 10, "OESD + overcards"),
    
    # === GUTSHOTS ===
    (["As", "Kh"], ["Qc", "Td", "2h"], "flop", 0, 10, "Gutshot + overcards"),
    (["Js", "9h"], ["Qc", "Td", "2h"], "flop", 5, 10, "Gutshot facing bet"),
    
    # === HIGH CARD / AIR ===
    (["As", "Kh"], ["Qc", "7d", "2h"], "flop", 0, 10, "AK high card"),
    (["As", "Kh"], ["Qc", "7d", "2h"], "flop", 3, 10, "AK high card facing 30% pot"),
    (["As", "Kh"], ["Qc", "7d", "2h"], "flop", 8, 10, "AK high card facing 80% pot"),
    (["7s", "6h"], ["Ac", "Kd", "Qh"], "flop", 0, 10, "Air on scary board"),
    (["7s", "6h"], ["Ac", "Kd", "Qh"], "flop", 5, 10, "Air facing bet"),
    (["7s", "6h"], ["Ac", "Kd", "Qh", "Jc", "2s"], "river", 15, 30, "Air river facing bet"),
    
    # === MIDDLE/BOTTOM PAIR ===
    (["Ks", "7h"], ["Ac", "7d", "2h"], "flop", 0, 10, "Middle pair"),
    (["Ks", "7h"], ["Ac", "7d", "2h"], "flop", 3, 10, "Middle pair facing small bet"),
    (["Ks", "7h"], ["Ac", "7d", "2h"], "flop", 8, 10, "Middle pair facing big bet"),
    (["Ks", "7h"], ["Ac", "7d", "2h"], "river", 15, 30, "Middle pair river facing bet"),
    
    # === COMBO DRAWS ===
    (["As", "5s"], ["4s", "3s", "2h"], "flop", 0, 10, "Flush draw + gutshot wheel"),
    (["Ks", "Qs"], ["Js", "Ts", "2h"], "flop", 0, 10, "Flush draw + OESD"),
    (["Ks", "Qs"], ["Js", "Ts", "2h"], "flop", 5, 10, "Flush draw + OESD facing bet"),
    (["Ks", "Qs"], ["Js", "Ts", "2h"], "flop", 10, 10, "Flush draw + OESD facing pot"),
    
    # === BOARD TEXTURE ===
    (["As", "Ah"], ["Ks", "Qs", "Js"], "flop", 0, 10, "AA on monotone board"),
    (["As", "Ah"], ["2c", "7d", "Qh"], "flop", 0, 10, "AA on dry board"),
    
    # === RIVER VALUE ===
    (["As", "Kh"], ["Ac", "7d", "2h", "3c", "4s"], "river", 0, 30, "TPTK river value bet"),
    
    # === RIVER RAISE DEFENSE (critical leak test) ===
    (["As", "Qh"], ["6s", "4s", "Jh", "9d", "Qc"], "river", 15, 30, "TPGK facing river raise - FOLD"),
    (["Ks", "Jh"], ["Jc", "7d", "2h", "3c", "4s"], "river", 20, 25, "TPWK facing river raise - FOLD"),
    (["7s", "7h"], ["Ac", "Kd", "2h", "3c", "4s"], "river", 15, 30, "Pocket pair facing river raise - FOLD"),
]


def test_strategy(strategy_name="value_max"):
    """Test a strategy against all edge cases."""
    print("=" * 95)
    print(f"POSTFLOP EDGE CASE TESTER - Strategy: {strategy_name}")
    print("=" * 95)
    
    issues = []
    
    for hole, board, street, to_call, pot, desc in SCENARIOS:
        info = analyze_hand(hole, board)
        strength, hand_desc = info['strength'], info['desc']
        equity = calculate_equity(hole, board)
        outs, draws = count_outs(hole, board)
        facing_bet = to_call > 0
        pot_odds = (to_call / (pot + to_call)) * 100 if to_call > 0 else 0
        
        action, sizing, reason = postflop_action(
            hole, board, pot, to_call, street,
            is_ip=True, is_aggressor=True,
            strategy=strategy_name
        )
        
        # Detect issues - STRICT checks
        issue = ""
        act = action.upper()
        
        # Strong hands should bet/raise
        if strength >= 7 and act == "CHECK" and not facing_bet:
            issue = "LEAK: Monster checking"
        elif strength >= 7 and act == "FOLD":
            issue = "LEAK: Monster folding"
        elif strength >= 5 and act == "FOLD":
            issue = f"LEAK: Strong hand (str={strength}) folding"
        
        # Sets should raise when facing bet
        if strength == 4 and facing_bet and act == "CALL":
            issue = "QUESTIONABLE: Set just calling (should raise?)"
        
        # Overpairs shouldn't fold or just call small bets
        if "overpair" in hand_desc.lower():
            if act == "FOLD":
                issue = "LEAK: Overpair folding"
            elif not facing_bet and act == "CHECK":
                issue = "LEAK: Overpair checking (should bet)"
        
        # Two pair+ should raise when facing bet (not just call)
        if strength >= 3 and facing_bet and act == "CALL" and equity > 80:
            issue = f"QUESTIONABLE: {hand_desc} just calling with {equity:.0f}% equity"
        
        # Equity vs pot odds - should call if equity > pot_odds
        if facing_bet and equity > pot_odds + 10 and act == "FOLD":
            issue = f"LEAK: Folding {equity:.0f}% equity vs {pot_odds:.0f}% odds"
        
        # Calling when equity < pot odds (over-calling)
        if facing_bet and equity < pot_odds - 5 and act == "CALL":
            issue = f"LEAK: Over-calling {equity:.0f}% equity vs {pot_odds:.0f}% odds"
        
        # Bluffing with no equity
        if strength <= 1 and act == "BET" and equity < 30 and outs == 0:
            issue = f"LEAK: Bluffing with {equity:.0f}% equity, no outs"
        
        # Not value betting strong hands
        if not facing_bet and strength >= 3 and act == "CHECK":
            issue = f"LEAK: Checking {hand_desc} (should value bet)"
        
        # Draws - should semi-bluff or call with odds
        if outs >= 8 and not facing_bet and act == "CHECK" and equity > 45:
            issue = f"QUESTIONABLE: Checking draw with {outs} outs, {equity:.0f}% equity"
        
        # River - no more draws, should fold weak hands
        if street == "river" and strength <= 1 and outs > 0 and act == "CALL":
            issue = f"LEAK: Calling river with missed draw"
        
        # Print result
        act_str = f"{action}"
        if sizing:
            act_str += f" {sizing}"
        
        status = "OK" if not issue else "ISSUE"
        
        print(f"\n[{status}] {desc}")
        print(f"  {hole} | {board} | {street} | to_call={to_call}")
        print(f"  {hand_desc} (str={strength}) | Equity: {equity:.0f}% | Outs: {outs} | PotOdds: {pot_odds:.0f}%")
        print(f"  >>> {act_str}")
        print(f"  Reason: {reason}")
        if issue:
            print(f"  *** {issue} ***")
            issues.append((desc, issue, equity, pot_odds, action))
    
    # Summary
    print("\n" + "=" * 95)
    print(f"SUMMARY: {len(issues)} issues found out of {len(SCENARIOS)} scenarios")
    print("=" * 95)
    if issues:
        for desc, issue, eq, odds, act in issues:
            print(f"  - {desc}: {issue}")
    else:
        print("  All scenarios passed!")
    
    return len(issues)


if __name__ == "__main__":
    strategy = sys.argv[1] if len(sys.argv) > 1 else "value_max"
    test_strategy(strategy)
