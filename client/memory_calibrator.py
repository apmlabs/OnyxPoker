"""
Memory Calibrator - Auto-find PokerStars memory offsets using GPT vision as oracle.

Workflow:
1. Screenshot + scan memory for card-like values (same instant)
2. Save candidate addresses with their values
3. Send screenshot to GPT-5.2 for card detection
4. Correlate: filter addresses that had the correct card values
5. Repeat across hands until stable offsets found

Usage:
    python memory_calibrator.py              # Run calibration mode
    python memory_calibrator.py --test       # Test with known offsets
    python memory_calibrator.py --status     # Show calibration progress
"""

import sys
import os
import json
import logging
from datetime import datetime

# Check for Windows
IS_WINDOWS = sys.platform == 'win32'

if IS_WINDOWS:
    import ctypes
    # Windows API constants
    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400

# Card encodings to search for
RANK_2_14 = {2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12, 13: 13, 14: 14}  # J=11, Q=12, K=13, A=14
RANK_0_12 = {2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 7, 10: 8, 11: 9, 12: 10, 13: 11, 14: 12}  # 2=0, A=12
SUIT_MAP = {'c': 0, 'd': 1, 'h': 2, 's': 3}  # clubs, diamonds, hearts, spades

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Calibration data file
CALIBRATION_FILE = 'memory_calibration.json'


def get_pokerstars_pid():
    """Find PokerStars.exe process ID."""
    if not IS_WINDOWS:
        logger.error("Memory reading only works on Windows")
        return None
    import subprocess
    try:
        output = subprocess.check_output('tasklist /FI "IMAGENAME eq PokerStars.exe" /FO CSV', shell=True)
        lines = output.decode().strip().split('\n')
        if len(lines) > 1:
            # Parse CSV: "PokerStars.exe","12345",...
            parts = lines[1].split(',')
            pid = int(parts[1].strip('"'))
            return pid
    except Exception as e:
        logger.error(f"Failed to find PokerStars.exe: {e}")
    return None


def open_process(pid):
    """Open process handle for memory reading."""
    if not IS_WINDOWS:
        return None
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        logger.error(f"Failed to open process {pid}")
    return handle


def read_memory(handle, address, size):
    """Read memory from process."""
    if not IS_WINDOWS:
        return None
    kernel32 = ctypes.windll.kernel32
    buffer = ctypes.create_string_buffer(size)
    bytes_read = ctypes.c_size_t()
    
    result = kernel32.ReadProcessMemory(
        handle,
        ctypes.c_void_p(address),
        buffer,
        size,
        ctypes.byref(bytes_read)
    )
    
    if result:
        return buffer.raw[:bytes_read.value]
    return None


def scan_for_card_values(handle, base_address, region_size=0x200000):
    """
    Scan memory region for values that could be card encodings.
    Returns dict of {address: value} for all card-like values found.
    """
    candidates = {}
    
    # Valid card values to search for
    valid_values = set()
    # Rank 2-14 encoding
    valid_values.update(range(2, 15))
    # Rank 0-12 encoding  
    valid_values.update(range(0, 13))
    # Combined 0-51 encoding
    valid_values.update(range(0, 52))
    # Suit values 0-3
    valid_values.update(range(0, 4))
    # ASCII: 2-9, T, J, Q, K, A
    valid_values.update([ord(c) for c in '23456789TJQKA'])
    # ASCII suits: c, d, h, s
    valid_values.update([ord(c) for c in 'cdhs'])
    
    # Read memory in chunks
    chunk_size = 4096
    for offset in range(0, region_size, chunk_size):
        data = read_memory(handle, base_address + offset, chunk_size)
        if not data:
            continue
            
        # Scan each byte
        for i, byte in enumerate(data):
            if byte in valid_values:
                addr = base_address + offset + i
                candidates[addr] = byte
    
    return candidates


def parse_card_string(card_str):
    """
    Parse card string like 'Ah' or 'Kd' into rank and suit values.
    Returns dict with multiple encoding possibilities.
    """
    if len(card_str) < 2:
        return None
    
    rank_char = card_str[0].upper()
    suit_char = card_str[1].lower()
    
    # Map rank character to numeric value
    rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    
    if rank_char not in rank_map or suit_char not in SUIT_MAP:
        return None
    
    rank = rank_map[rank_char]
    suit = SUIT_MAP[suit_char]
    
    return {
        'rank_2_14': rank,
        'rank_0_12': rank - 2,
        'combined_0_51': (rank - 2) * 4 + suit,
        'suit_0_3': suit,
        'ascii_rank': ord(rank_char),
        'ascii_suit': ord(suit_char),
    }


def correlate_candidates(candidates, gpt_cards):
    """
    Filter candidate addresses to those matching GPT-detected cards.
    
    candidates: {address: value} from memory scan
    gpt_cards: list of card strings like ['Ah', 'Kd']
    
    Returns addresses that matched any card encoding.
    """
    matches = []
    
    for card_str in gpt_cards:
        card_values = parse_card_string(card_str)
        if not card_values:
            continue
        
        # Check each candidate
        for addr, value in candidates.items():
            for encoding, expected in card_values.items():
                if value == expected:
                    matches.append({
                        'address': hex(addr),
                        'value': value,
                        'card': card_str,
                        'encoding': encoding
                    })
    
    return matches


def load_calibration():
    """Load existing calibration data."""
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE, 'r') as f:
            return json.load(f)
    return {'hands': [], 'stable_offsets': None}


def save_calibration(data):
    """Save calibration data."""
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def analyze_calibration_data(data):
    """
    Analyze collected hands to find stable offsets.
    Returns offsets that appeared in >80% of hands.
    """
    if len(data['hands']) < 5:
        return None
    
    # Count address occurrences by encoding type
    address_counts = {}
    
    for hand in data['hands']:
        for match in hand.get('matches', []):
            key = (match['address'], match['encoding'])
            address_counts[key] = address_counts.get(key, 0) + 1
    
    # Find addresses that appear consistently
    threshold = len(data['hands']) * 0.8
    stable = []
    
    for (addr, encoding), count in address_counts.items():
        if count >= threshold:
            stable.append({
                'address': addr,
                'encoding': encoding,
                'hit_rate': count / len(data['hands'])
            })
    
    return stable if stable else None


def memory_snapshot(pid=None):
    """
    Take a snapshot of card-like values in PokerStars memory.
    Returns dict of {address: value} for correlation later.
    """
    if not IS_WINDOWS:
        logger.error("Memory reading only works on Windows")
        return None
        
    if pid is None:
        pid = get_pokerstars_pid()
    if not pid:
        return None
    
    handle = open_process(pid)
    if not handle:
        return None
    
    try:
        # Known base offset from poker-supernova (may need adjustment)
        # Start scanning from likely regions
        base_addresses = [
            0x133CAB0,  # poker-supernova client offset
            0x10000000,  # Common heap region
            0x20000000,
        ]
        
        all_candidates = {}
        for base in base_addresses:
            candidates = scan_for_card_values(handle, base, region_size=0x100000)
            all_candidates.update(candidates)
        
        logger.info(f"Found {len(all_candidates)} card-like values in memory")
        return all_candidates
        
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def calibration_step(screenshot_path, gpt_cards, candidates):
    """
    One step of calibration: correlate memory snapshot with GPT results.
    
    screenshot_path: path to screenshot (for logging)
    gpt_cards: list of cards detected by GPT, e.g. ['Ah', 'Kd']
    candidates: dict from memory_snapshot()
    
    Returns matches and updates calibration file.
    """
    matches = correlate_candidates(candidates, gpt_cards)
    
    # Load and update calibration data
    data = load_calibration()
    
    hand_record = {
        'timestamp': datetime.now().isoformat(),
        'screenshot': screenshot_path,
        'gpt_cards': gpt_cards,
        'num_candidates': len(candidates),
        'matches': matches
    }
    
    data['hands'].append(hand_record)
    
    # Check if we have enough data for stable offsets
    stable = analyze_calibration_data(data)
    if stable:
        data['stable_offsets'] = stable
        logger.info(f"Found {len(stable)} stable offsets!")
    
    save_calibration(data)
    
    return matches, stable


def show_status():
    """Show current calibration status."""
    data = load_calibration()
    
    print(f"\n=== Memory Calibration Status ===")
    print(f"Hands collected: {len(data['hands'])}")
    
    if data['stable_offsets']:
        print(f"\nStable offsets found:")
        for offset in data['stable_offsets']:
            print(f"  {offset['address']} ({offset['encoding']}) - {offset['hit_rate']*100:.0f}% hit rate")
    else:
        print(f"\nNo stable offsets yet. Need more hands.")
        if data['hands']:
            # Show most promising candidates
            address_counts = {}
            for hand in data['hands']:
                for match in hand.get('matches', []):
                    key = (match['address'], match['encoding'])
                    address_counts[key] = address_counts.get(key, 0) + 1
            
            if address_counts:
                print(f"\nTop candidates:")
                sorted_addrs = sorted(address_counts.items(), key=lambda x: -x[1])[:10]
                for (addr, enc), count in sorted_addrs:
                    print(f"  {addr} ({enc}) - {count}/{len(data['hands'])} hands")


if __name__ == '__main__':
    import sys
    
    if '--status' in sys.argv:
        show_status()
    elif '--test' in sys.argv:
        # Test mode: just check if we can read PokerStars memory
        pid = get_pokerstars_pid()
        if pid:
            print(f"Found PokerStars.exe (PID: {pid})")
            candidates = memory_snapshot(pid)
            if candidates:
                print(f"Successfully scanned memory: {len(candidates)} card-like values")
            else:
                print("Failed to scan memory")
        else:
            print("PokerStars.exe not running")
    else:
        print("Memory Calibrator")
        print("This script is called by helper_bar.py during calibration mode.")
        print("")
        print("Usage:")
        print("  python memory_calibrator.py --test    # Test memory reading")
        print("  python memory_calibrator.py --status  # Show calibration progress")
