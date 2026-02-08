"""
Memory Calibrator v3 - Auto-dump on F9, offline analysis

On each F9 press, helper_bar calls save_dump() which:
  1. Dumps all readable PS memory to a .bin file
  2. Saves metadata (timestamp) to a .json sidecar

After GPT returns, helper_bar calls tag_dump() which adds:
  - hand_id, hero_cards, community_cards, pot, opponents

Then run offline:
  python memory_calibrator.py analyze   # Search ALL dumps automatically
  python memory_calibrator.py read      # Read cards from calibrated address

Table struct layout (from poker-supernova, PokerStars 7):
  table_base + 0x40 = hand_id (int64)
  table_base + 0x58 = num_community_cards (int32)
  table_base + 0x64 = community card_values (0x08 spacing)
  table_base + 0x68 = community card_suits  (0x08 spacing)
  table_base + 0x0218 + seat*0x0160 + 0x00 = name (string)
  table_base + 0x0218 + seat*0x0160 + 0x9C = card_values (0x08 spacing)
  table_base + 0x0218 + seat*0x0160 + 0xA0 = card_suits  (0x08 spacing)
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

# Known struct offsets (stable across PS versions, pointer chain changes)
TABLE = {'hand_id': 0x40, 'num_cards': 0x58, 'card_values': 0x64, 'card_suits': 0x68}
SEAT = {'base': 0x0218, 'interval': 0x0160, 'name': 0x00, 'card_values': 0x9C, 'card_suits': 0xA0}


def log(msg):
    print(f"[MEM] {msg}")


def card_to_rank_suit(card_str):
    if not card_str or len(card_str) < 2:
        return None, None
    r, s = card_str[0].upper(), card_str[1].lower()
    if r not in RANKS or s not in SUITS:
        return None, None
    return RANKS.index(r), SUITS.index(s)


# ── Process Reader (Windows only) ───────────────────────────────────

class ProcessReader:
    def __init__(self):
        self.handle = None
        self.pid = None
        self.module_base = None

    def attach(self):
        if not IS_WINDOWS:
            return False
        self.pid = self._find_pid()
        if not self.pid:
            return False
        self.handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, self.pid)
        if not self.handle:
            return False
        self.module_base = self._get_module_base()
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
            return None

    def _get_module_base(self):
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
        nread = ctypes.c_size_t()
        ok = ctypes.windll.kernel32.ReadProcessMemory(
            self.handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(nread))
        return buf.raw[:nread.value] if ok and nread.value > 0 else None

    def iter_regions(self):
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


# ── Dump on F9 (called from helper_bar) ─────────────────────────────

_reader = None

def save_dump(timestamp=None):
    """Called on F9 press. Dumps PS memory to disk. Returns dump_id or None."""
    global _reader
    if not IS_WINDOWS:
        return None
    if _reader is None:
        _reader = ProcessReader()
    if not _reader.handle:
        if not _reader.attach():
            return None

    os.makedirs(DUMP_DIR, exist_ok=True)
    ts = timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')
    dump_id = f'dump_{ts}'
    bin_path = os.path.join(DUMP_DIR, f'{dump_id}.bin')
    meta_path = os.path.join(DUMP_DIR, f'{dump_id}.json')

    regions = []
    file_offset = 0
    with open(bin_path, 'wb') as f:
        for base, size in _reader.iter_regions():
            if size > 100 * 1024 * 1024:
                continue
            data = _reader.read(base, size)
            if data:
                f.write(data)
                regions.append({'base': base, 'size': len(data), 'file_offset': file_offset})
                file_offset += len(data)

    meta = {
        'dump_id': dump_id,
        'timestamp': ts,
        'pid': _reader.pid,
        'module_base': _reader.module_base,
        'regions': regions,
        'bytes_total': file_offset,
    }
    with open(meta_path, 'w') as f:
        json.dump(meta, f)

    return dump_id


def tag_dump(dump_id, gpt_result):
    """Called after GPT returns. Tags the dump with vision data."""
    if not dump_id:
        return
    meta_path = os.path.join(DUMP_DIR, f'{dump_id}.json')
    if not os.path.exists(meta_path):
        return
    with open(meta_path) as f:
        meta = json.load(f)

    meta['hand_id'] = gpt_result.get('hand_id')
    meta['hero_cards'] = gpt_result.get('hero_cards', [])
    meta['community_cards'] = gpt_result.get('community_cards', [])
    meta['pot'] = gpt_result.get('pot')
    meta['opponents'] = []
    for opp in gpt_result.get('opponents', []):
        meta['opponents'].append({
            'name': opp.get('name', ''),
            'has_cards': opp.get('has_cards', False),
        })

    with open(meta_path, 'w') as f:
        json.dump(meta, f)


# ── Offline Analysis ────────────────────────────────────────────────

def _load_tagged_dumps():
    """Load all dumps that have been tagged with GPT data."""
    if not os.path.isdir(DUMP_DIR):
        return []
    dumps = []
    for fname in sorted(os.listdir(DUMP_DIR)):
        if not fname.endswith('.json'):
            continue
        meta_path = os.path.join(DUMP_DIR, fname)
        bin_path = meta_path.replace('.json', '.bin')
        if not os.path.exists(bin_path):
            continue
        with open(meta_path) as f:
            meta = json.load(f)
        if not meta.get('hand_id') or not meta.get('hero_cards'):
            continue  # not tagged yet
        meta['_bin_path'] = bin_path
        dumps.append(meta)
    return dumps


def _search_dump(bin_path, regions, pattern):
    """Search for byte pattern in dump file. Returns real memory addresses."""
    matches = []
    with open(bin_path, 'rb') as f:
        for r in regions:
            f.seek(r['file_offset'])
            data = f.read(r['size'])
            idx = 0
            while True:
                idx = data.find(pattern, idx)
                if idx == -1:
                    break
                matches.append(r['base'] + idx)
                idx += 1
    return matches


def _read_dump_at(bin_path, regions, addr, size):
    """Read bytes from dump at a real memory address."""
    for r in regions:
        if r['base'] <= addr < r['base'] + r['size']:
            off = addr - r['base']
            avail = min(size, r['size'] - off)
            with open(bin_path, 'rb') as f:
                f.seek(r['file_offset'] + off)
                return f.read(avail)
    return None


def _verify_table_struct(read_fn, base, hand_id_int, hero_cards, opponent_names=None):
    """Check if base looks like a valid table struct. Returns info dict or None."""
    # Verify hand_id at +0x40
    hid_data = read_fn(base + TABLE['hand_id'], 8)
    if not hid_data or len(hid_data) < 8:
        return None
    if int.from_bytes(hid_data, 'little') != hand_id_int:
        return None

    r1, s1 = card_to_rank_suit(hero_cards[0])
    r2, s2 = card_to_rank_suit(hero_cards[1])
    if r1 is None:
        return None

    # Check each seat for hero cards
    for seat_idx in range(10):
        seat_base = base + SEAT['base'] + SEAT['interval'] * seat_idx
        cv = read_fn(seat_base + SEAT['card_values'], 16)
        cs = read_fn(seat_base + SEAT['card_suits'], 16)
        if not cv or not cs or len(cv) < 9 or len(cs) < 9:
            continue
        cr1, cr2, cs1, cs2 = cv[0], cv[8], cs[0], cs[8]
        # Match either order
        match = (cr1 == r1 and cs1 == s1 and cr2 == r2 and cs2 == s2)
        match_rev = (cr1 == r2 and cs1 == s2 and cr2 == r1 and cs2 == s1)
        if match or match_rev:
            name_data = read_fn(seat_base + SEAT['name'], 20)
            name = name_data.split(b'\x00')[0].decode('ascii', errors='replace') if name_data else ''
            # Bonus: check if opponent names match other seats
            opp_names_found = []
            if opponent_names:
                for si in range(10):
                    if si == seat_idx:
                        continue
                    sb = base + SEAT['base'] + SEAT['interval'] * si
                    nd = read_fn(sb + SEAT['name'], 20)
                    if nd:
                        sn = nd.split(b'\x00')[0].decode('ascii', errors='replace')
                        if sn and sn in opponent_names:
                            opp_names_found.append(sn)
            return {
                'table_base': base,
                'hero_seat': seat_idx,
                'hero_name': name,
                'cards_reversed': match_rev,
                'opp_names_found': opp_names_found,
            }
    return None


def cmd_analyze():
    """Analyze all tagged dumps to find the table struct."""
    dumps = _load_tagged_dumps()
    if not dumps:
        log("No tagged dumps found.")
        log("Play some hands with --calibrate, then run this again.")
        return

    log(f"Found {len(dumps)} tagged dumps")
    results = []

    for meta in dumps:
        hand_id = meta['hand_id']
        hero_cards = meta['hero_cards']
        bin_path = meta['_bin_path']
        regions = meta['regions']
        opp_names = [o['name'] for o in meta.get('opponents', []) if o.get('name')]

        log(f"\n--- {meta['dump_id']}: hand_id={hand_id} cards={hero_cards} ---")

        try:
            hand_id_int = int(hand_id)
        except (ValueError, TypeError):
            log(f"  Invalid hand_id: {hand_id}")
            continue

        # Search for hand_id as int64
        pattern = struct.pack('<Q', hand_id_int)
        matches = _search_dump(bin_path, regions, pattern)
        log(f"  hand_id int64 matches: {len(matches)}")

        read_fn = lambda addr, size, bp=bin_path, rg=regions: _read_dump_at(bp, rg, addr, size)

        found = False
        for addr in matches:
            table_base = addr - TABLE['hand_id']
            result = _verify_table_struct(read_fn, table_base, hand_id_int, hero_cards, opp_names)
            if result:
                log(f"  FOUND: table_base={hex(table_base)} seat={result['hero_seat']} name={result['hero_name']}")
                if result['opp_names_found']:
                    log(f"  Opponents confirmed: {result['opp_names_found']}")
                result['dump_id'] = meta['dump_id']
                result['module_base'] = meta.get('module_base')
                result['hand_id'] = hand_id
                results.append(result)
                found = True
                break

        if not found:
            # Try ASCII hand_id
            ascii_matches = _search_dump(bin_path, regions, str(hand_id).encode('ascii'))
            log(f"  hand_id ASCII matches: {len(ascii_matches)}")
            # Try searching for opponent names as anchors
            if opp_names:
                for name in opp_names[:3]:
                    name_matches = _search_dump(bin_path, regions, name.encode('ascii'))
                    log(f"  name '{name}' matches: {len(name_matches)}")

    if not results:
        log("\nNo table structs found in any dump.")
        log("Possible reasons:")
        log("  - Card encoding differs from 0-12 rank / 0-3 suit")
        log("  - Struct layout changed from poker-supernova offsets")
        log("  - hand_id stored differently (not int64)")
        return

    # Check consistency across dumps
    log(f"\n=== RESULTS: {len(results)} table structs found ===")
    for r in results:
        mb = r.get('module_base') or 0
        tb = r['table_base']
        log(f"  {r['dump_id']}: base={hex(tb)} module+{hex(tb - mb)} seat={r['hero_seat']} name={r['hero_name']}")

    # Save calibration from most recent result
    best = results[-1]
    save_calibration({
        'table_base': best['table_base'],
        'hero_seat': best['hero_seat'],
        'hero_name': best['hero_name'],
        'module_base': best.get('module_base'),
        'module_offset': best['table_base'] - (best.get('module_base') or 0),
    })
    log(f"\nCalibration saved to {CALIBRATION_FILE}")


# ── Fast Card Read ──────────────────────────────────────────────────

def read_cards_fast():
    """API for helper_bar: returns ['Ah', 'Kd'] or None."""
    cal = load_calibration()
    if not cal or not cal.get('table_base'):
        return None
    global _reader
    if _reader is None:
        _reader = ProcessReader()
    if not _reader.handle:
        if not _reader.attach():
            return None
    seat_base = cal['table_base'] + SEAT['base'] + SEAT['interval'] * cal.get('hero_seat', 0)
    cv = _reader.read(seat_base + SEAT['card_values'], 16)
    cs = _reader.read(seat_base + SEAT['card_suits'], 16)
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
    """Legacy API - now a no-op since we use dump+analyze workflow."""
    pass


def load_calibration():
    try:
        with open(CALIBRATION_FILE) as f:
            return json.load(f)
    except:
        return None


def save_calibration(data):
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# ── CLI ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else ''
    if cmd == 'analyze':
        cmd_analyze()
    elif cmd == 'read':
        cal = load_calibration()
        if not cal:
            log("Not calibrated. Run: python memory_calibrator.py analyze")
        else:
            cards = read_cards_fast()
            log(f"Cards: {cards}" if cards else "Could not read cards")
    elif cmd == 'dump':
        did = save_dump()
        log(f"Saved: {did}" if did else "Failed (Windows only)")
    elif cmd == 'list':
        dumps = _load_tagged_dumps()
        log(f"{len(dumps)} tagged dumps:")
        for d in dumps:
            log(f"  {d['dump_id']}: hand={d.get('hand_id')} cards={d.get('hero_cards')} "
                f"opps={[o['name'] for o in d.get('opponents',[])]}")
    else:
        print("Usage:")
        print("  python memory_calibrator.py analyze  # Search all dumps for table struct")
        print("  python memory_calibrator.py read     # Read cards (after calibration)")
        print("  python memory_calibrator.py list     # Show tagged dumps")
        print("  python memory_calibrator.py dump     # Manual dump (normally auto on F9)")
