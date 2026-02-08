#!/usr/bin/env python3
"""
OnyxPoker Test Runner - Run all Linux-compatible tests.

Usage:
    python3 run_tests.py          # Run core tests (fast)
    python3 run_tests.py --all    # Run all tests including postflop leaks
    python3 run_tests.py --quick  # Just poker rules + audit (fastest)
"""

import subprocess
import sys
import time
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

TESTS = {
    'core': [
        ('Poker Rules (24 tests)', 'python3 test_poker_rules.py', 'All poker rules verified'),
        ('Strategy Audit (30 tests)', 'python3 audit_strategies.py', 'All tests pass'),
        ('Strategy Engine (55 tests)', 'python3 test_strategy_engine.py', None),
    ],
    'extended': [
        ('Postflop value_lord', 'python3 test_postflop.py value_lord', None),
        ('Postflop the_lord', 'python3 test_postflop.py the_lord', None),
    ],
}


def run_test(name, cmd, success_marker=None):
    t = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    elapsed = time.time() - t
    output = result.stdout + result.stderr

    passed = result.returncode == 0
    if success_marker:
        passed = passed and success_marker in output

    # Extract summary line
    lines = output.strip().split('\n')
    summary = lines[-1] if lines else '(no output)'
    for line in reversed(lines):
        if 'Total:' in line or 'PASS' in line or 'FAIL' in line:
            summary = line.strip()
            break

    status = 'PASS' if passed else 'FAIL'
    print(f"  [{status}] {name} ({elapsed:.1f}s) - {summary}")
    return passed, output


def main():
    mode = 'core'
    if '--all' in sys.argv:
        mode = 'all'
    elif '--quick' in sys.argv:
        mode = 'quick'

    print(f"OnyxPoker Test Suite ({mode})")
    print("=" * 60)

    total_pass = 0
    total_fail = 0
    start = time.time()

    test_groups = ['core'] if mode != 'all' else ['core', 'extended']
    if mode == 'quick':
        test_groups = ['core']
        TESTS['core'] = TESTS['core'][:2]  # Just rules + audit

    for group in test_groups:
        print(f"\n{group.upper()} TESTS:")
        for name, cmd, marker in TESTS[group]:
            try:
                passed, _ = run_test(name, cmd, marker)
                if passed:
                    total_pass += 1
                else:
                    total_fail += 1
            except subprocess.TimeoutExpired:
                print(f"  [TIMEOUT] {name}")
                total_fail += 1

    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"Results: {total_pass} passed, {total_fail} failed ({elapsed:.1f}s)")

    if total_fail > 0:
        print("SOME TESTS FAILED")
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == '__main__':
    sys.exit(main())
