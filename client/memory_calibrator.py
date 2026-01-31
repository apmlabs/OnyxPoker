"""
Memory Reader - Find PokerStars card data by scanning for known card values.

Since offsets change between PS versions, we scan memory for the actual card
values that GPT detected, then remember those addresses.

Usage:
    Integrated into helper_bar.py --calibrate
    python memory_calibrator.py --test       # Test memory access
"""

import sys
import os
import json
import time
from datetime import datetime

IS_WINDOWS = sys.platform == 'win32'

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    
    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400
    MEM_COMMIT = 0x1000
    PAGE_READABLE = 0x02 | 0x04 | 0x20 | 0x40 | 0x80

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]

# Card decoding - multiple possible encodings
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
SUITS = ['c', 'd', 'h', 's']

CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), 'memory_offsets.json')


def card_to_encodings(card_str):
    """Convert card like 'Ah' to all possible byte encodings."""
    if not card_str or len(card_str) < 2:
        return []
    
    rank_char = card_str[0].upper()
    suit_char = card_str[1].lower()
    
    if rank_char not in RANKS or suit_char not in SUITS:
        return []
    
    r = RANKS.index(rank_char)  # 0-12
    s = SUITS.index(suit_char)  # 0-3
    
    return [
        ('rank_0_12', r),           # 0-12
        ('rank_2_14', r + 2),       # 2-14
        ('combined_r4s', r * 4 + s),  # 0-51
        ('combined_s13r', s * 13 + r), # 0-51 alt
    ]


class MemoryReader:
    def __init__(self):
        self.pid = None
        self.handle = None
        self.card1_addr = None  # Address of first hero card
        self.card1_encoding = None
        self.card1_gap = 1  # Gap between card1 and card2
        
    def find_pokerstars(self):
        """Find PokerStars.exe PID."""
        if not IS_WINDOWS:
            return None
        import subprocess
        try:
            out = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq PokerStars.exe" /FO CSV',
                shell=True, stderr=subprocess.DEVNULL
            )
            lines = out.decode().strip().split('\n')
            if len(lines) > 1:
                return int(lines[1].split(',')[1].strip('"'))
        except:
            pass
        return None
    
    def open_process(self, pid):
        """Open process for reading."""
        if not IS_WINDOWS:
            return None
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid
        )
        return handle if handle else None
    
    def close(self):
        """Close process handle."""
        if IS_WINDOWS and self.handle:
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None
    
    def read_bytes(self, address, size):
        """Read bytes from memory."""
        if not IS_WINDOWS or not self.handle:
            return None
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t()
        if ctypes.windll.kernel32.ReadProcessMemory(
            self.handle, ctypes.c_void_p(address), buf, size, ctypes.byref(read)
        ):
            return buf.raw[:read.value]
        return None
    
    def enumerate_regions(self):
        """Get all readable memory regions."""
        if not IS_WINDOWS or not self.handle:
            return []
        regions = []
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        while ctypes.windll.kernel32.VirtualQueryEx(
            self.handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)
        ):
            base = mbi.BaseAddress
            size = mbi.RegionSize
            # Safety: size must be positive
            if size is None or size <= 0:
                break
            if mbi.State == MEM_COMMIT and (mbi.Protect & PAGE_READABLE):
                regions.append((base, size))
            # Move to next region (base can be 0 for first region)
            if base is None:
                base = 0
            addr = base + size
            if addr <= base:  # Overflow check
                break
        return regions
    
    def scan_for_card_pair(self, card1, card2):
        """
        Scan memory for two cards appearing close together.
        Returns list of (address, encoding) candidates.
        """
        enc1_list = card_to_encodings(card1)
        enc2_list = card_to_encodings(card2)
        
        if not enc1_list or not enc2_list:
            return []
        
        candidates = []
        regions = self.enumerate_regions()
        print(f"[MEM] Scanning {len(regions)} regions...")
        
        scanned = 0
        for base, size in regions:
            if size is None or size <= 0:
                continue
            if size > 10 * 1024 * 1024:  # Skip >10MB
                continue
            if base is None:
                base = 0
            
            scanned += 1
            if scanned % 100 == 0:
                print(f"[MEM] Scanned {scanned} regions, {len(candidates)} candidates...")
            
            # Read in chunks
            chunk_size = 65536
            for offset in range(0, size, chunk_size):
                read_size = min(chunk_size + 16, size - offset)  # +16 for card pair
                data = self.read_bytes(base + offset, read_size)
                if not data:
                    continue
                
                # Search for card1 followed by card2 within 8 bytes
                for enc1_name, enc1_val in enc1_list:
                    for i, byte in enumerate(data[:-8]):
                        if byte == enc1_val:
                            # Check if card2 is nearby (1-8 bytes after)
                            for enc2_name, enc2_val in enc2_list:
                                if enc1_name == enc2_name:  # Same encoding type
                                    for gap in range(1, 8):
                                        if i + gap < len(data) and data[i + gap] == enc2_val:
                                            addr = base + offset + i
                                            candidates.append({
                                                'addr': addr,
                                                'encoding': enc1_name,
                                                'gap': gap,
                                                'card1': card1,
                                                'card2': card2
                                            })
        
        print(f"[MEM] Scan complete: {scanned} regions, {len(candidates)} candidates")
        return candidates
    
    def scan_for_single_card(self, card):
        """
        Scan memory for a single card value.
        Returns list of {addr, encoding} for all matches.
        """
        enc_list = card_to_encodings(card)
        if not enc_list:
            return []
        
        candidates = []
        regions = self.enumerate_regions()
        print(f"[MEM] Scanning {len(regions)} regions for {card}...")
        
        scanned = 0
        for base, size in regions:
            if size is None or size <= 0:
                continue
            if size > 10 * 1024 * 1024:  # Skip >10MB
                continue
            if base is None:
                base = 0
            
            scanned += 1
            if scanned % 100 == 0:
                print(f"[MEM] Scanned {scanned} regions, {len(candidates)} candidates...")
            
            # Read in chunks
            chunk_size = 65536
            for offset in range(0, size, chunk_size):
                read_size = min(chunk_size, size - offset)
                data = self.read_bytes(base + offset, read_size)
                if not data:
                    continue
                
                # Search for card value in all encodings
                for enc_name, enc_val in enc_list:
                    for i, byte in enumerate(data):
                        if byte == enc_val:
                            addr = base + offset + i
                            candidates.append({
                                'addr': addr,
                                'encoding': enc_name
                            })
        
        print(f"[MEM] Scan complete: {scanned} regions, {len(candidates)} candidates")
        return candidates
    
    def read_card(self, address, encoding):
        """Read a card from memory using known encoding. Returns full card like 'As'."""
        data = self.read_bytes(address, 1)
        if not data:
            return None
        
        val = data[0]
        
        # For rank-only encodings, we can only return the rank
        # These won't work for our purposes - need combined encoding
        if encoding == 'rank_0_12':
            if 0 <= val <= 12:
                return RANKS[val]  # Just rank, no suit
        elif encoding == 'rank_2_14':
            if 2 <= val <= 14:
                return RANKS[val - 2]  # Just rank, no suit
        elif encoding == 'combined_r4s':
            if 0 <= val <= 51:
                r = val // 4
                s = val % 4
                return RANKS[r] + SUITS[s]
        elif encoding == 'combined_s13r':
            if 0 <= val <= 51:
                s = val // 13
                r = val % 13
                return RANKS[r] + SUITS[s]
        
        return None


# Global instance
_reader = None
_last_snapshot = None  # Memory snapshot taken at screenshot time

def get_reader():
    global _reader
    if _reader is None:
        _reader = MemoryReader()
    return _reader


def scan_memory_snapshot():
    """
    Scan memory NOW and save snapshot. Called at screenshot time.
    Returns dict of {addr: byte_value} for all card-like values.
    """
    global _last_snapshot
    reader = get_reader()
    
    if not reader.handle:
        reader.pid = reader.find_pokerstars()
        if not reader.pid:
            return None
        reader.handle = reader.open_process(reader.pid)
        if not reader.handle:
            return None
    
    # Scan for all possible card values (0-51 for combined encodings)
    snapshot = {}
    regions = reader.enumerate_regions()
    
    for base, size in regions:
        if size is None or size <= 0 or size > 10 * 1024 * 1024:
            continue
        if base is None:
            base = 0
        
        chunk_size = 65536
        for offset in range(0, size, chunk_size):
            read_size = min(chunk_size, size - offset)
            data = reader.read_bytes(base + offset, read_size)
            if not data:
                continue
            
            for i, byte in enumerate(data):
                # Keep bytes that could be cards (0-51 range covers most encodings)
                if byte <= 51:
                    snapshot[base + offset + i] = byte
    
    _last_snapshot = snapshot
    print(f"[MEM] Snapshot: {len(snapshot)} card-like addresses")
    return snapshot


SAMPLES_FILE = os.path.join(os.path.dirname(__file__), 'memory_samples.json')

def calibrate_with_gpt(gpt_cards, snapshot=None):
    """
    Use snapshot (taken at screenshot time) to find card addresses.
    """
    global _last_snapshot
    
    if snapshot is None:
        snapshot = _last_snapshot
    
    if not snapshot:
        return "No memory snapshot - scan failed?"
    
    if not gpt_cards or len(gpt_cards) < 2:
        return "Need 2 cards"
    
    card1, card2 = gpt_cards[0], gpt_cards[1]
    
    # Log encodings for debugging
    enc1_list = card_to_encodings(card1)
    enc2_list = card_to_encodings(card2)
    print(f"[MEM] calibrate: {card1}={enc1_list} {card2}={enc2_list}")
    print(f"[MEM] snapshot has {len(snapshot)} addresses")
    
    # Get expected byte values for both cards
    enc1_map = {enc: val for enc, val in card_to_encodings(card1)}
    enc2_map = {enc: val for enc, val in card_to_encodings(card2)}
    
    # Load existing tracking data
    tracking = {'addrs': {}, 'hands': 0}
    if os.path.exists(SAMPLES_FILE):
        try:
            with open(SAMPLES_FILE) as f:
                loaded = json.load(f)
            if isinstance(loaded.get('hands'), int) and isinstance(loaded.get('addrs'), dict):
                tracking = loaded
            else:
                os.remove(SAMPLES_FILE)
        except:
            pass
    
    if tracking['hands'] == 0:
        # First hand: find pairs in snapshot
        print(f"[MEM] Hand 1 - finding {card1} {card2} pairs in snapshot...")
        
        candidates = {}
        snapshot_addrs = sorted(snapshot.keys())
        
        for enc_name in enc1_map:
            if enc_name not in enc2_map:
                continue
            val1 = enc1_map[enc_name]
            val2 = enc2_map[enc_name]
            
            for addr in snapshot_addrs:
                if snapshot[addr] == val1:
                    # Check if card2 is nearby (gap 1-8)
                    for gap in range(1, 9):
                        addr2 = addr + gap
                        if addr2 in snapshot and snapshot[addr2] == val2:
                            candidates[str(addr)] = {'enc': enc_name, 'gap': gap}
        
        print(f"[MEM] Found {len(candidates)} pair candidates")
        
        if not candidates:
            return f"No pairs found for {card1} {card2}"
        
        tracking['addrs'] = candidates
        tracking['hands'] = 1
        
        with open(SAMPLES_FILE, 'w') as f:
            json.dump(tracking, f)
        
        print(f"[MEM] Hand 1 done. Tracking {len(candidates)} addresses.")
        return None
    
    else:
        # Subsequent hands: filter to addresses that have new cards in snapshot
        print(f"[MEM] Hand {tracking['hands'] + 1} - checking {card1} {card2}...")
        print(f"[MEM] Expected values: card1={enc1_map}, card2={enc2_map}")
        
        surviving = {}
        checked = 0
        for addr_str, info in tracking['addrs'].items():
            addr = int(addr_str)
            enc = info['enc']
            gap = info['gap']
            
            if enc not in enc1_map or enc not in enc2_map:
                continue
            
            checked += 1
            expected1 = enc1_map[enc]
            expected2 = enc2_map[enc]
            
            # Check snapshot for both cards
            if addr in snapshot and (addr + gap) in snapshot:
                actual1 = snapshot[addr]
                actual2 = snapshot[addr + gap]
                if actual1 == expected1 and actual2 == expected2:
                    surviving[addr_str] = info
                elif checked <= 5:  # Log first few mismatches
                    print(f"[MEM] Addr {hex(addr)}: expected {expected1},{expected2} got {actual1},{actual2}")
            elif checked <= 5:
                in1 = addr in snapshot
                in2 = (addr + gap) in snapshot
                print(f"[MEM] Addr {hex(addr)}: not in snapshot (in1={in1}, in2={in2})")
        
        print(f"[MEM] {len(surviving)} survived (was {len(tracking['addrs'])})")
        
        tracking['addrs'] = surviving
        tracking['hands'] += 1
        
        if len(surviving) == 0:
            print("[MEM] No addresses survived - starting over")
            os.remove(SAMPLES_FILE)
            return None
        
        if len(surviving) <= 5 and tracking['hands'] >= 3:
            addr_str = list(surviving.keys())[0]
            info = surviving[addr_str]
            print(f"[MEM] FOUND! Address {hex(int(addr_str))}, enc={info['enc']}, gap={info['gap']}")
            
            save_calibration({
                'card1_addr': int(addr_str),
                'encoding': info['enc'],
                'gap': info['gap'],
                'hands_to_calibrate': tracking['hands'],
                'timestamp': datetime.now().isoformat()
            })
            os.remove(SAMPLES_FILE)
            return None
        
        with open(SAMPLES_FILE, 'w') as f:
            json.dump(tracking, f)
        
        print(f"[MEM] Hand {tracking['hands']} done. {len(surviving)} remain.")
        return None


def read_cards_fast():
    """
    Read hero cards using calibrated address.
    Returns [card1, card2] or None.
    """
    reader = get_reader()
    
    # Load calibration if needed
    if not reader.card1_addr:
        cal = load_calibration()
        if not cal:
            return None
        if not cal.get('card1_addr'):
            return None
        reader.card1_addr = cal['card1_addr']
        reader.card1_encoding = cal.get('encoding')
        reader.card1_gap = cal.get('gap', 1)
    
    # Safety check
    if not reader.card1_addr or not reader.card1_encoding:
        return None
    
    # Open process if needed
    if not reader.handle:
        reader.pid = reader.find_pokerstars()
        if not reader.pid:
            return None
        reader.handle = reader.open_process(reader.pid)
        if not reader.handle:
            return None
    
    # Read cards
    c1 = reader.read_card(reader.card1_addr, reader.card1_encoding)
    c2 = reader.read_card(reader.card1_addr + reader.card1_gap, reader.card1_encoding)
    
    if c1 and c2:
        return [c1, c2]
    return None


def load_calibration():
    """Load saved calibration."""
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE) as f:
                return json.load(f)
        except:
            pass
    return None


def save_calibration(data):
    """Save calibration."""
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def is_calibrated():
    """Check if memory reader is calibrated."""
    cal = load_calibration()
    if not cal:
        return False
    # Must have card1_addr AND encoding (new format)
    if cal.get('card1_addr') and cal.get('encoding'):
        return True
    # Delete any invalid/old calibration files
    try:
        os.remove(CALIBRATION_FILE)
    except:
        pass
    return False


if __name__ == '__main__':
    if '--test' in sys.argv:
        print("Testing memory access...")
        reader = MemoryReader()
        reader.pid = reader.find_pokerstars()
        
        if not reader.pid:
            print("PokerStars not running")
            sys.exit(1)
        
        print(f"Found PokerStars PID: {reader.pid}")
        reader.handle = reader.open_process(reader.pid)
        
        if not reader.handle:
            print("Could not open process (try running as admin?)")
            sys.exit(1)
        
        regions = reader.enumerate_regions()
        total_mb = sum(r[1] for r in regions) / 1024 / 1024
        print(f"Found {len(regions)} memory regions ({total_mb:.1f} MB)")
        print("Memory access OK!")
        
        reader.close()
    else:
        print("Memory Calibrator")
        print("")
        print("Usage:")
        print("  python memory_calibrator.py --test  # Test memory access")
        print("")
        print("Calibration: python helper_bar.py --calibrate")
        print("Press F9 with cards visible - we find them in memory.")
        print("After calibration, cards read instantly (<1ms).")
