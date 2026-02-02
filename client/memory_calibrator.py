"""
Memory Calibrator v2 - Find cards by searching for UNIQUE values first.

Strategy: Card values (0-12) are too common. Instead:
1. GPT reads hand_id (12-digit number) from screenshot
2. Scan memory for hand_id - very few matches
3. Card data is at known offset from hand_id location

From poker-supernova offsets:
  table: hand_id at 0x40, card_values at 0x64, card_suits at 0x68
  seat: card_values at 0x9C, card_suits at 0xA0
"""

import sys
import os
import struct
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

LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', 'memory_scan.log')
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
SUITS = ['c', 'd', 'h', 's']


def log(msg):
    line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
    print(f"[MEM] {msg}")
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass


class MemoryScanner:
    def __init__(self):
        self.handle = None
        self.pid = None
    
    def find_pokerstars(self):
        if not IS_WINDOWS:
            return None
        import subprocess
        try:
            out = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq PokerStars.exe" /FO CSV',
                shell=True, stderr=subprocess.DEVNULL
            )
            for line in out.decode().strip().split('\n')[1:]:
                return int(line.split(',')[1].strip('"'))
        except:
            pass
        return None
    
    def open(self):
        if not IS_WINDOWS:
            return False
        self.pid = self.find_pokerstars()
        if not self.pid:
            log("PokerStars not found")
            return False
        self.handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, self.pid
        )
        if not self.handle:
            log("Could not open process")
            return False
        log(f"Attached to PID {self.pid}")
        return True
    
    def read(self, addr, size):
        if not self.handle:
            return None
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t()
        if ctypes.windll.kernel32.ReadProcessMemory(
            self.handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(read)
        ):
            return buf.raw[:read.value]
        return None
    
    def scan_for_bytes(self, pattern):
        """Scan all readable memory for byte pattern. Returns list of addresses."""
        if not self.handle:
            return []
        
        matches = []
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        regions_scanned = 0
        
        while ctypes.windll.kernel32.VirtualQueryEx(
            self.handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)
        ):
            if mbi.RegionSize is None or mbi.RegionSize <= 0:
                break
            
            # Only scan committed, readable memory
            if mbi.State == MEM_COMMIT and (mbi.Protect & PAGE_READABLE):
                base = mbi.BaseAddress or 0
                size = mbi.RegionSize
                
                # Skip huge regions
                if size <= 50 * 1024 * 1024:
                    data = self.read(base, size)
                    if data:
                        # Find all occurrences
                        idx = 0
                        while True:
                            idx = data.find(pattern, idx)
                            if idx == -1:
                                break
                            matches.append(base + idx)
                            idx += 1
                    regions_scanned += 1
                    if regions_scanned % 200 == 0:
                        log(f"Scanned {regions_scanned} regions, {len(matches)} matches so far")
            
            addr = (mbi.BaseAddress or 0) + mbi.RegionSize
            if addr <= (mbi.BaseAddress or 0):
                break
        
        return matches


def calibrate_with_hand_id(hand_id, hero_cards=None):
    """
    Find card memory location using hand_id as anchor.
    
    hand_id: string like "234567890123" (12 digits)
    hero_cards: optional ["Ah", "Kd"] to verify we found the right spot
    """
    log(f"=== Calibrating with hand_id={hand_id} ===")
    
    scanner = MemoryScanner()
    if not scanner.open():
        return None
    
    # Try different encodings of hand_id
    patterns = []
    
    # As ASCII string
    patterns.append(('ascii', hand_id.encode('ascii')))
    
    # As int64
    try:
        patterns.append(('int64', struct.pack('<Q', int(hand_id))))
    except:
        pass
    
    # As UTF-16
    patterns.append(('utf16', hand_id.encode('utf-16-le')))
    
    all_matches = {}
    for name, pattern in patterns:
        log(f"Searching for {name}: {pattern.hex()}")
        matches = scanner.scan_for_bytes(pattern)
        log(f"  Found {len(matches)} matches")
        if matches:
            all_matches[name] = matches
    
    if not all_matches:
        log("No matches for hand_id - try a different hand")
        return None
    
    # For each match, look for card data nearby
    # poker-supernova: hand_id at 0x40, cards at 0x64/0x68 (table) or 0x9C/0xA0 (seat)
    # So cards could be at offset +0x24 to +0x60 from hand_id
    
    log("\n=== Exploring nearby memory for card patterns ===")
    
    for encoding, addrs in all_matches.items():
        for addr in addrs[:10]:  # Check first 10 matches
            # Read 256 bytes around the match
            data = scanner.read(addr - 64, 256)
            if not data:
                continue
            
            # Look for card-like patterns (two bytes 0-12 followed by two bytes 0-3)
            for offset in range(len(data) - 6):
                r1, r2 = data[offset], data[offset+1]
                # Check various gaps for suits
                for gap in [2, 3, 4]:  # suits might be 2-4 bytes after ranks
                    if offset + gap + 2 > len(data):
                        continue
                    s1, s2 = data[offset+gap], data[offset+gap+1]
                    
                    if 0 <= r1 <= 12 and 0 <= r2 <= 12 and 0 <= s1 <= 3 and 0 <= s2 <= 3:
                        card1 = RANKS[r1] + SUITS[s1]
                        card2 = RANKS[r2] + SUITS[s2]
                        real_addr = addr - 64 + offset
                        
                        # If we have hero_cards, check if this matches
                        if hero_cards:
                            if card1 == hero_cards[0] and card2 == hero_cards[1]:
                                log(f"MATCH! {card1} {card2} at {hex(real_addr)} (gap={gap})")
                                return {'addr': real_addr, 'gap': gap}
                        else:
                            log(f"Candidate: {card1} {card2} at {hex(real_addr)} (gap={gap})")
    
    return None


def calibrate_with_player_name(name, hero_cards=None):
    """Find card memory using player name as anchor."""
    log(f"=== Calibrating with player_name={name} ===")
    
    scanner = MemoryScanner()
    if not scanner.open():
        return None
    
    # Player names are usually UTF-16 in Windows
    patterns = [
        ('utf16', name.encode('utf-16-le')),
        ('ascii', name.encode('ascii')),
    ]
    
    for enc_name, pattern in patterns:
        log(f"Searching for {enc_name}: {pattern[:20].hex()}...")
        matches = scanner.scan_for_bytes(pattern)
        log(f"  Found {len(matches)} matches")
        
        if not matches:
            continue
        
        # seat base is at name offset 0x00, cards at 0x9C/0xA0
        # So cards are ~156 bytes after name start
        
        for addr in matches[:20]:
            # Read memory after the name
            data = scanner.read(addr, 256)
            if not data:
                continue
            
            # Look for card pattern around offset 0x9C (156 bytes)
            for offset in range(140, 180):
                if offset + 6 > len(data):
                    continue
                r1, r2 = data[offset], data[offset+1]
                for gap in [2, 3, 4]:
                    if offset + gap + 2 > len(data):
                        continue
                    s1, s2 = data[offset+gap], data[offset+gap+1]
                    
                    if 0 <= r1 <= 12 and 0 <= r2 <= 12 and 0 <= s1 <= 3 and 0 <= s2 <= 3:
                        card1 = RANKS[r1] + SUITS[s1]
                        card2 = RANKS[r2] + SUITS[s2]
                        
                        if hero_cards:
                            if card1 == hero_cards[0] and card2 == hero_cards[1]:
                                log(f"MATCH! {card1} {card2} at name+{offset} (gap={gap})")
                                return {'name_addr': addr, 'card_offset': offset, 'gap': gap}
                        else:
                            log(f"Candidate: {card1} {card2} at name+{offset}")
    
    return None


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--hand-id', help='12-digit hand ID from table')
    parser.add_argument('--name', help='Your player name')
    parser.add_argument('--cards', help='Your hole cards, e.g. "Ah,Kd"')
    args = parser.parse_args()
    
    hero_cards = None
    if args.cards:
        hero_cards = [c.strip() for c in args.cards.split(',')]
    
    if args.hand_id:
        result = calibrate_with_hand_id(args.hand_id, hero_cards)
        if result:
            print(f"\nSUCCESS: {result}")
    elif args.name:
        result = calibrate_with_player_name(args.name, hero_cards)
        if result:
            print(f"\nSUCCESS: {result}")
    else:
        print("Usage:")
        print("  python memory_calibrator.py --hand-id 234567890123 --cards Ah,Kd")
        print("  python memory_calibrator.py --name idealistslp --cards Ah,Kd")
