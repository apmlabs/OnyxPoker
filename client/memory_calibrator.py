"""
Memory Calibrator v3 - Dump + Offline Search + Pointer Chain

Key insight from poker-supernova: PokerStars stores table data behind a
multi-level pointer chain from the module base. The struct layout is:

  table_base + 0x40 = hand_id (8 bytes)
  table_base + 0x58 = num_community_cards
  table_base + 0x64 = community card_values (spaced 0x08 apart)
  table_base + 0x68 = community card_suits  (spaced 0x08 apart)
  table_base + 0x0218 + seat_idx*0x0160 = seat base
    seat_base + 0x00 = name (string, 20 bytes)
    seat_base + 0x9C = card_values (2 cards, spaced 0x08 apart)
    seat_base + 0xA0 = card_suits  (2 cards, spaced 0x08 apart)

Strategy:
  1. dump  - Save all readable memory to disk for offline analysis
  2. find  - Search dump for hand_id, verify table struct around it
  3. chain - Find pointer chain from module base to table struct
  4. read  - Use saved chain for instant card reads

Usage:
  python memory_calibrator.py dump              # Dump PS memory to file
  python memory_calibrator.py find <hand_id> <cards>  # Search dump
  python memory_calibrator.py scan <hand_id> <cards>  # Live scan (no dump)
  python memory_calibrator.py read              # Read cards from saved chain

Examples:
  python memory_calibrator.py dump
  python memory_calibrator.py find 259643889546 Ah,Kd
  python memory_calibrator.py scan 259643889546 Ah,Kd
  python memory_calibrator.py read
"""

import sys
import os
import json
import struct
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

DUMP_DIR = os.path.join(os.path.dirname(__file__), 'memory_dumps')
CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), 'memory_offsets.json')

RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
SUITS = ['c', 'd', 'h', 's']

# Known struct offsets from poker-supernova (stable across versions)
TABLE = {
    'hand_id': 0x40,
    'num_cards': 0x58,
    'card_values': 0x64,
    'card_suits': 0x68,
}
SEAT = {
    'base': 0x0218,
    'interval': 0x0160,
    'name': 0x00,
    'card_values': 0x9C,
    'card_suits': 0xA0,
}


def log(msg):
    print(f"[MEM] {msg}")


def card_to_rank_suit(card_str):
    """Convert 'Ah' to (rank_idx=12, suit_idx=2). Returns (None,None) on error."""
    if not card_str or len(card_str) < 2:
        return None, None
    r, s = card_str[0].upper(), card_str[1].lower()
    if r not in RANKS or s not in SUITS:
        return None, None
    return RANKS.index(r), SUITS.index(s)


# ── Windows Process Helpers ──────────────────────────────────────────

class ProcessReader:
    """Read memory from a Windows process."""
    def __init__(self):
        self.handle = None
        self.pid = None
        self.module_base = None

    def attach(self):
        if not IS_WINDOWS:
            log("Windows only"); return False
        self.pid = self._find_pid()
        if not self.pid:
            log("PokerStars not found"); return False
        self.handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, self.pid)
        if not self.handle:
            log("Cannot open process"); return False
        self.module_base = self._get_module_base()
        log(f"Attached PID={self.pid} module_base={hex(self.module_base or 0)}")
        return True

    def _find_pid(self):
        import subprocess
        try:
            out = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq PokerStars.exe" /FO CSV',
                shell=True, stderr=subprocess.DEVNULL)
            for line in out.decode().strip().split('\n')[1:]:
                return int(line.split(',')[1].strip('"'))
        except:
            pass
        return None

    def _get_module_base(self):
        """Get base address of PokerStars.exe module."""
        try:
            import win32process
            modules = win32process.EnumProcessModules(self.handle)
            return modules[0] if modules else None
        except ImportError:
            # Fallback: use ctypes EnumProcessModulesEx
            try:
                hMods = (ctypes.c_void_p * 1024)()
                needed = ctypes.c_ulong()
                ctypes.windll.psapi.EnumProcessModulesEx(
                    self.handle, hMods, ctypes.sizeof(hMods),
                    ctypes.byref(needed), 0x03)
                return hMods[0] if needed.value > 0 else None
            except:
                return None

    def read(self, addr, size):
        if not self.handle:
            return None
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t()
        ok = ctypes.windll.kernel32.ReadProcessMemory(
            self.handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(read))
        return buf.raw[:read.value] if ok and read.value > 0 else None

    def read_int(self, addr, size=4):
        data = self.read(addr, size)
        if not data or len(data) < size:
            return None
        return int.from_bytes(data, 'little')

    def iter_regions(self):
        """Yield (base_addr, size) for each readable committed region."""
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        while ctypes.windll.kernel32.VirtualQueryEx(
            self.handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            if mbi.RegionSize is None or mbi.RegionSize <= 0:
                break
            if mbi.State == MEM_COMMIT and (mbi.Protect & PAGE_READABLE):
                yield (mbi.BaseAddress or 0, mbi.RegionSize)
            addr = (mbi.BaseAddress or 0) + mbi.RegionSize
            if addr <= (mbi.BaseAddress or 0):
                break

    def resolve_pointer(self, base, offsets):
        """Follow a pointer chain: base+off[0] -> deref+off[1] -> ... """
        ptr = base + offsets[0]
        for off in offsets[1:]:
            val = self.read_int(ptr)
            if val is None:
                return None
            ptr = val + off
        return ptr


# ── Memory Dump (Phase 1) ───────────────────────────────────────────

def cmd_dump():
    """Dump all readable memory of PokerStars to disk."""
    reader = ProcessReader()
    if not reader.attach():
        return

    os.makedirs(DUMP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dump_path = os.path.join(DUMP_DIR, f'ps_dump_{ts}.bin')
    index_path = os.path.join(DUMP_DIR, f'ps_dump_{ts}.json')

    regions = []
    total_bytes = 0
    log("Scanning memory regions...")
    for base, size in reader.iter_regions():
        if size <= 100 * 1024 * 1024:  # skip >100MB regions
            regions.append((base, size))
            total_bytes += size

    log(f"{len(regions)} regions, {total_bytes / 1024 / 1024:.1f} MB total")
    log(f"Dumping to {dump_path} ...")

    index = {
        'pid': reader.pid,
        'module_base': reader.module_base,
        'timestamp': ts,
        'regions': []
    }
    file_offset = 0

    with open(dump_path, 'wb') as f:
        for i, (base, size) in enumerate(regions):
            data = reader.read(base, size)
            if data:
                f.write(data)
                index['regions'].append({
                    'base': base, 'size': len(data), 'file_offset': file_offset
                })
                file_offset += len(data)
            if (i + 1) % 100 == 0:
                log(f"  {i+1}/{len(regions)} regions...")

    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)

    log(f"Done: {file_offset / 1024 / 1024:.1f} MB written")
    log(f"Index: {index_path}")
    log(f"Module base: {hex(reader.module_base or 0)}")
    log(f"\nNext: python memory_calibrator.py find <hand_id> <card1,card2>")


# ── Offline Search (Phase 2) ────────────────────────────────────────

def _load_dump():
    """Load most recent dump + index."""
    if not os.path.isdir(DUMP_DIR):
        log("No dumps found. Run: python memory_calibrator.py dump"); return None, None
    jsons = sorted([f for f in os.listdir(DUMP_DIR) if f.endswith('.json')])
    if not jsons:
        log("No dump index found"); return None, None
    idx_path = os.path.join(DUMP_DIR, jsons[-1])
    bin_path = idx_path.replace('.json', '.bin')
    if not os.path.exists(bin_path):
        log(f"Missing {bin_path}"); return None, None
    with open(idx_path) as f:
        index = json.load(f)
    log(f"Loaded dump: {jsons[-1]} ({len(index['regions'])} regions)")
    return bin_path, index


def _search_in_dump(bin_path, index, pattern):
    """Search for byte pattern in dump. Returns list of real memory addresses."""
    matches = []
    with open(bin_path, 'rb') as f:
        for region in index['regions']:
            f.seek(region['file_offset'])
            data = f.read(region['size'])
            idx = 0
            while True:
                idx = data.find(pattern, idx)
                if idx == -1:
                    break
                real_addr = region['base'] + idx
                matches.append(real_addr)
                idx += 1
    return matches


def _read_dump_at(bin_path, index, addr, size):
    """Read bytes from dump at a real memory address."""
    for region in index['regions']:
        rbase = region['base']
        rend = rbase + region['size']
        if rbase <= addr < rend:
            offset_in_region = addr - rbase
            avail = min(size, region['size'] - offset_in_region)
            with open(bin_path, 'rb') as f:
                f.seek(region['file_offset'] + offset_in_region)
                return f.read(avail)
    return None


def _verify_table_struct(read_fn, base_addr, hand_id_int, r1, s1, r2, s2):
    """Check if base_addr looks like a valid table struct.
    Returns dict of findings or None."""
    # hand_id should be at base + 0x40
    hid_data = read_fn(base_addr + TABLE['hand_id'], 8)
    if not hid_data or len(hid_data) < 8:
        return None
    hid = int.from_bytes(hid_data, 'little')
    if hid != hand_id_int:
        return None

    # num_cards should be 0-5
    nc_data = read_fn(base_addr + TABLE['num_cards'], 4)
    num_cards = int.from_bytes(nc_data, 'little') if nc_data and len(nc_data) >= 4 else -1

    # Check hero cards at each seat position (0-9)
    hero_seat = None
    for seat_idx in range(10):
        seat_base = base_addr + SEAT['base'] + SEAT['interval'] * seat_idx
        # Read name
        name_data = read_fn(seat_base + SEAT['name'], 20)
        if not name_data:
            continue
        # Read card values (2 cards, 0x08 apart)
        cv = read_fn(seat_base + SEAT['card_values'], 16)
        cs = read_fn(seat_base + SEAT['card_suits'], 16)
        if not cv or not cs or len(cv) < 9 or len(cs) < 9:
            continue
        cr1, cr2 = cv[0], cv[8]
        cs1, cs2 = cs[0], cs[8]
        # Check if this seat has our cards
        if cr1 == r1 and cs1 == s1 and cr2 == r2 and cs2 == s2:
            name = name_data.split(b'\x00')[0].decode('ascii', errors='replace')
            hero_seat = seat_idx
            return {
                'table_base': base_addr,
                'hero_seat': seat_idx,
                'hero_name': name,
                'hand_id': hid,
                'num_community': num_cards,
            }
        # Also check reversed card order
        if cr1 == r2 and cs1 == s2 and cr2 == r1 and cs2 == s1:
            name = name_data.split(b'\x00')[0].decode('ascii', errors='replace')
            return {
                'table_base': base_addr,
                'hero_seat': seat_idx,
                'hero_name': name,
                'hand_id': hid,
                'num_community': num_cards,
                'cards_reversed': True,
            }
    return None


def cmd_find(hand_id_str, cards_str):
    """Search dump for hand_id, verify table struct layout."""
    bin_path, index = _load_dump()
    if not bin_path:
        return

    r1, s1 = card_to_rank_suit(cards_str[0])
    r2, s2 = card_to_rank_suit(cards_str[1])
    if r1 is None:
        log(f"Bad cards: {cards_str}"); return

    hand_id_int = int(hand_id_str)
    log(f"Searching for hand_id={hand_id_str} cards={cards_str}")
    log(f"Card values: [{r1},{s1}] [{r2},{s2}]")

    # Search for hand_id as int64 little-endian
    pattern = struct.pack('<Q', hand_id_int)
    matches = _search_in_dump(bin_path, index, pattern)
    log(f"hand_id as int64: {len(matches)} matches")

    # Also try ASCII
    ascii_matches = _search_in_dump(bin_path, index, hand_id_str.encode('ascii'))
    log(f"hand_id as ASCII: {len(ascii_matches)} matches")

    # For each int64 match, check if base_addr = match - 0x40 is a valid table struct
    found = []
    read_fn = lambda addr, size: _read_dump_at(bin_path, index, addr, size)

    for addr in matches:
        table_base = addr - TABLE['hand_id']  # hand_id is at offset 0x40
        result = _verify_table_struct(read_fn, table_base, hand_id_int, r1, s1, r2, s2)
        if result:
            found.append(result)
            log(f"  FOUND table struct at {hex(table_base)}")
            log(f"    hero_seat={result['hero_seat']} name={result['hero_name']}")
            log(f"    community_cards={result['num_community']}")

    if not found:
        log("\nNo valid table struct found via int64 hand_id.")
        log("Trying brute force: scanning all memory for card byte pattern...")
        _brute_force_search(bin_path, index, hand_id_int, r1, s1, r2, s2)
        return

    # Try to find pointer chain back to module base
    module_base = index.get('module_base')
    if module_base and found:
        log(f"\nModule base: {hex(module_base)}")
        log(f"Table base:  {hex(found[0]['table_base'])}")
        log(f"Offset from module: {hex(found[0]['table_base'] - module_base)}")
        log("\nTo find pointer chain, use Cheat Engine pointer scan on the table base address.")
        log("Or run: python memory_calibrator.py chain")

    # Save what we found
    save_calibration({
        'table_base': found[0]['table_base'],
        'hero_seat': found[0]['hero_seat'],
        'module_base': module_base,
        'hand_id': hand_id_str,
    })
    log(f"\nSaved to {CALIBRATION_FILE}")


def _brute_force_search(bin_path, index, hand_id_int, r1, s1, r2, s2):
    """Scan entire dump for the card byte pattern [r1, padding, r2] with suits nearby."""
    log(f"Looking for rank bytes {r1},{r2} with suits {s1},{s2} (0x08 spacing)...")
    candidates = 0
    read_fn = lambda addr, size: _read_dump_at(bin_path, index, addr, size)

    with open(bin_path, 'rb') as f:
        for region in index['regions']:
            f.seek(region['file_offset'])
            data = f.read(region['size'])
            # Look for [r1, ?, ?, ?, ?, ?, ?, ?, r2] pattern (0x08 spacing)
            for i in range(len(data) - 16):
                if data[i] == r1 and i + 8 < len(data) and data[i + 8] == r2:
                    # Check suits at +4 offset (standard) or nearby
                    for suit_off in [4, 2, 1]:
                        if i + 8 + suit_off >= len(data):
                            continue
                        if data[i + suit_off] == s1 and data[i + 8 + suit_off] == s2:
                            real_addr = region['base'] + i
                            # Check if hand_id is nearby (within 0x200 before)
                            for hid_off in [0x9C, 0x5C, 0x40, 0x24]:
                                check_addr = real_addr - hid_off
                                hid_data = _read_dump_at(bin_path, index, check_addr, 8)
                                if hid_data and len(hid_data) >= 8:
                                    hid = int.from_bytes(hid_data, 'little')
                                    if hid == hand_id_int:
                                        log(f"  MATCH at {hex(real_addr)} (hand_id at -{hex(hid_off)})")
                                        candidates += 1
                            if candidates == 0 and r1 < 13 and r2 < 13:
                                # Just log first few without hand_id verification
                                if candidates < 5:
                                    log(f"  Candidate at {hex(real_addr)} (no hand_id nearby)")
                                candidates += 1
                                if candidates >= 20:
                                    break
            if candidates >= 20:
                break

    if candidates == 0:
        log("No candidates found. Card encoding may differ from expected 0-12 rank values.")
        log("Try different encodings: 2-14 for ranks, or single-byte combined 0-51.")


# ── Live Scan (no dump needed) ──────────────────────────────────────

def cmd_scan(hand_id_str, cards_str):
    """Live scan: search PS memory directly for hand_id + verify table struct."""
    reader = ProcessReader()
    if not reader.attach():
        return

    r1, s1 = card_to_rank_suit(cards_str[0])
    r2, s2 = card_to_rank_suit(cards_str[1])
    if r1 is None:
        log(f"Bad cards: {cards_str}"); return

    hand_id_int = int(hand_id_str)
    pattern = struct.pack('<Q', hand_id_int)
    log(f"Live scanning for hand_id={hand_id_str} cards={cards_str}")

    matches = []
    for base, size in reader.iter_regions():
        if size > 100 * 1024 * 1024:
            continue
        data = reader.read(base, size)
        if not data:
            continue
        idx = 0
        while True:
            idx = data.find(pattern, idx)
            if idx == -1:
                break
            matches.append(base + idx)
            idx += 1

    log(f"hand_id matches: {len(matches)}")

    read_fn = lambda addr, size: reader.read(addr, size)
    for addr in matches:
        table_base = addr - TABLE['hand_id']
        result = _verify_table_struct(read_fn, table_base, hand_id_int, r1, s1, r2, s2)
        if result:
            log(f"FOUND table at {hex(table_base)} seat={result['hero_seat']} name={result['hero_name']}")
            save_calibration({
                'table_base': table_base,
                'hero_seat': result['hero_seat'],
                'module_base': reader.module_base,
            })
            log(f"Saved to {CALIBRATION_FILE}")
            return

    log("No valid table struct found. Try dump + offline search for more options.")


# ── Fast Card Read (after calibration) ──────────────────────────────

def cmd_read():
    """Read cards using saved calibration."""
    cal = load_calibration()
    if not cal or not cal.get('table_base'):
        log("Not calibrated. Run find or scan first."); return

    reader = ProcessReader()
    if not reader.attach():
        return

    table_base = cal['table_base']
    seat_idx = cal.get('hero_seat', 0)
    seat_base = table_base + SEAT['base'] + SEAT['interval'] * seat_idx

    # Read hero cards
    cv = reader.read(seat_base + SEAT['card_values'], 16)
    cs = reader.read(seat_base + SEAT['card_suits'], 16)
    if cv and cs and len(cv) >= 9 and len(cs) >= 9:
        r1, r2 = cv[0], cv[8]
        s1, s2 = cs[0], cs[8]
        if r1 <= 12 and r2 <= 12 and s1 <= 3 and s2 <= 3:
            card1 = RANKS[r1] + SUITS[s1]
            card2 = RANKS[r2] + SUITS[s2]
            log(f"Hero cards: {card1} {card2}")
        else:
            log(f"Invalid card values: r={r1},{r2} s={s1},{s2}")
    else:
        log("Could not read card memory")

    # Read community cards
    nc = reader.read_int(table_base + TABLE['num_cards'])
    if nc and 0 < nc <= 5:
        cards = []
        for i in range(nc):
            v = reader.read_int(table_base + TABLE['card_values'] + 0x08 * i)
            s_data = reader.read(table_base + TABLE['card_suits'] + 0x08 * i, 1)
            if v is not None and s_data and 0 <= v <= 12:
                s_idx = s_data[0] if s_data[0] <= 3 else 0
                cards.append(RANKS[v] + SUITS[s_idx])
        log(f"Community: {' '.join(cards)}")

    # Read hand_id
    hid = reader.read_int(table_base + TABLE['hand_id'], 8)
    if hid:
        log(f"Hand ID: {hid}")


def read_cards_fast():
    """API for helper_bar: returns ['Ah', 'Kd'] or None."""
    cal = load_calibration()
    if not cal or not cal.get('table_base'):
        return None
    reader = ProcessReader()
    if not reader.attach():
        return None
    seat_base = cal['table_base'] + SEAT['base'] + SEAT['interval'] * cal.get('hero_seat', 0)
    cv = reader.read(seat_base + SEAT['card_values'], 16)
    cs = reader.read(seat_base + SEAT['card_suits'], 16)
    if not cv or not cs or len(cv) < 9 or len(cs) < 9:
        return None
    r1, r2, s1, s2 = cv[0], cv[8], cs[0], cs[8]
    if r1 > 12 or r2 > 12 or s1 > 3 or s2 > 3:
        return None
    return [RANKS[r1] + SUITS[s1], RANKS[r2] + SUITS[s2]]


def is_calibrated():
    cal = load_calibration()
    return cal is not None and cal.get('table_base') is not None


def calibrate_after_gpt(gpt_result):
    """Called from helper_bar after GPT returns. Tries live scan."""
    hand_id = gpt_result.get('hand_id')
    hero_cards = gpt_result.get('hero_cards')
    if not hand_id or not hero_cards or len(hero_cards) < 2:
        return
    cmd_scan(str(hand_id), hero_cards)


# ── Persistence ─────────────────────────────────────────────────────

def load_calibration():
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE) as f:
                return json.load(f)
        except:
            pass
    return None


def save_calibration(data):
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# ── CLI ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == 'dump':
        cmd_dump()
    elif cmd == 'find' and len(sys.argv) >= 4:
        cmd_find(sys.argv[2], sys.argv[3].split(','))
    elif cmd == 'scan' and len(sys.argv) >= 4:
        cmd_scan(sys.argv[2], sys.argv[3].split(','))
    elif cmd == 'read':
        cmd_read()
    else:
        print(__doc__)
