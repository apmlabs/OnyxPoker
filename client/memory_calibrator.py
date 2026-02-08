"""
Memory Calibrator v4 - Message buffer approach (signature-based search)

Reads hero cards + actions from PokerStars message buffer in memory.

The message buffer is an array of 0x40-byte entries on the heap:
  +0x00: hand_id (8B LE)
  +0x08: sequence (4B)
  +0x14: msg_type (1B) — 0x0A=new_hand, 0x01=action, 0x02=seated, 0x07=action_start
  +0x16: seat_index (1B, 0-based)
  +0x17: action_code (1B) — 0x43=CALL, 0x45=RAISE, 0x46=FOLD, 0x50=POST_BB, 0x70=POST_SB
  +0x18: amount (2B uint16, cents)
  +0x1C: name_ptr (4B) -> player name
  +0x20: name_len (4B)
  +0x24: name_capacity (4B)
  +0x28: extra_ptr (4B) -> hero's type 0x02: 4-byte ASCII cards (e.g. "8h5d")
  +0x2C: extra_len (4B)

Buffer discovery: 10-byte signature `00 88 00 00 00 00 00 00 00 00` immediately
precedes the first entry. Scan memory for signature, validate first entry
(hand_id in range + seq=1), pick highest hand_id = current hand.

On Windows (live):
  helper_bar.py calls save_dump() on F9, tag_dump() after GPT returns.

Offline analysis:
  python memory_calibrator.py list      # Show tagged dumps
  python memory_calibrator.py analyze   # Verify message buffer in all dumps
  python memory_calibrator.py read      # Read cards (Windows only)
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

HERO_NAME = 'idealistslp'
ENTRY_SIZE = 0x40
# 10-byte signature immediately before first buffer entry
BUFFER_SIGNATURE = bytes([0x00, 0x88, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
ACTION_NAMES = {0x42: 'BET', 0x43: 'CALL', 0x45: 'RAISE', 0x46: 'FOLD', 0x50: 'POST_BB', 0x63: 'CHECK', 0x70: 'POST_SB'}
MSG_TYPES = {0x0A: 'NEW_HAND', 0x01: 'ACTION', 0x02: 'SEATED', 0x05: 'DEAL', 0x06: 'WIN', 0x07: 'ACTION_START'}


def log(msg):
    print(f"[MEM] {msg}")


# ── Entry Decoder ────────────────────────────────────────────────────

def decode_entry(data_40bytes, read_str_fn=None):
    """Decode a single 0x40-byte message buffer entry."""
    e = data_40bytes
    hand_id = struct.unpack('<Q', e[0:8])[0]
    seq = struct.unpack('<I', e[8:12])[0]
    msg_type = e[0x14]
    seat = e[0x16]
    action_code = e[0x17]
    amount = struct.unpack('<H', e[0x18:0x1A])[0]
    name_ptr = struct.unpack('<I', e[0x1C:0x20])[0]
    name_len = struct.unpack('<I', e[0x20:0x24])[0]
    extra_ptr = struct.unpack('<I', e[0x28:0x2C])[0]
    extra_len = struct.unpack('<I', e[0x2C:0x30])[0]

    name = None
    extra = None
    if read_str_fn and 0x01000000 < name_ptr < 0x7FFFFFFF:
        name = read_str_fn(name_ptr, 64)
    if read_str_fn and 0x01000000 < extra_ptr < 0x7FFFFFFF:
        extra = read_str_fn(extra_ptr, 16)

    return {
        'hand_id': hand_id, 'seq': seq, 'msg_type': msg_type,
        'seat': seat, 'action_code': action_code, 'amount': amount,
        'name_ptr': name_ptr, 'name': name,
        'extra_ptr': extra_ptr, 'extra': extra,
    }


def decode_buffer(buf_addr, read_bytes_fn, read_str_fn, max_entries=30):
    """Decode all entries from a message buffer. Returns list of entry dicts."""
    entries = []
    first_hid = None
    for i in range(max_entries):
        data = read_bytes_fn(buf_addr + i * ENTRY_SIZE, ENTRY_SIZE)
        if not data or len(data) < ENTRY_SIZE:
            break
        e = decode_entry(data, read_str_fn)
        if i == 0:
            first_hid = e['hand_id']
        elif e['hand_id'] != first_hid:
            break
        entries.append(e)
    return entries


def format_entry(e):
    """Human-readable string for one entry."""
    if e['msg_type'] == 0x0A:
        return f"[{e['seq']:2d}] NEW_HAND"
    elif e['msg_type'] == 0x02:
        cards = f" [{e['extra']}]" if e['extra'] else ""
        seat = f"seat={e['seat']}" if e['seat'] != 255 else "BOARD"
        return f"[{e['seq']:2d}] SEATED {seat} {e['name'] or ''}{cards}"
    elif e['msg_type'] == 0x05:
        return f"[{e['seq']:2d}] DEAL"
    elif e['msg_type'] == 0x06:
        return f"[{e['seq']:2d}] WIN {e['name'] or ''}"
    elif e['msg_type'] == 0x01:
        act = ACTION_NAMES.get(e['action_code'], f"0x{e['action_code']:02X}")
        return f"[{e['seq']:2d}] {act} {e['name'] or '?'} {e['amount']}c"
    elif e['msg_type'] == 0x07:
        return f"[{e['seq']:2d}] ACTION_START {e['name'] or ''}"
    mt = MSG_TYPES.get(e['msg_type'], f"0x{e['msg_type']:02X}")
    return f"[{e['seq']:2d}] type={mt} seat={e['seat']} {e['name'] or ''}"


def extract_hand_data(entries):
    """Extract poker-relevant data from decoded entries."""
    if not entries:
        return None
    hand_id = entries[0]['hand_id']
    hero_cards = None
    community_cards = []
    players = {}
    actions = []

    for e in entries:
        if e['msg_type'] == 0x05:
            # DEAL marker — street boundary for action tracking
            actions.append((None, 'DEAL', 0))
        elif e['msg_type'] == 0x02:
            if e['seat'] == 255 and e['extra']:
                # Community cards: seat=255, extra = card string
                cc = e['extra']
                for i in range(0, len(cc) - 1, 2):
                    community_cards.append(cc[i:i+2])
            else:
                players[e['seat']] = e['name']
                if e['extra'] and e['name'] == HERO_NAME:
                    hero_cards = e['extra']
        elif e['msg_type'] == 0x01:
            act = ACTION_NAMES.get(e['action_code'], f"0x{e['action_code']:02X}")
            actions.append((e['name'], act, e['amount']))

    return {'hand_id': hand_id, 'hero_cards': hero_cards, 'players': players,
            'actions': actions, 'community_cards': community_cards}


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
            log("PokerStars.exe not found"); return False
        self.handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, self.pid)
        if not self.handle:
            log("OpenProcess failed"); return False
        self.module_base = self._get_module_base()
        log(f"Attached: PID={self.pid} module=0x{self.module_base or 0:X}")
        return True

    def _find_pid(self):
        import subprocess
        try:
            out = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq PokerStars.exe" /FO CSV',
                shell=True, stderr=subprocess.DEVNULL)
            for line in out.decode().strip().split('\n')[1:]:
                parts = line.split(',')
                if len(parts) >= 2:
                    return int(parts[1].strip('"'))
        except Exception:
            pass
        return None

    def _get_module_base(self):
        try:
            hMods = (ctypes.c_void_p * 1024)()
            needed = ctypes.c_ulong()
            ctypes.windll.psapi.EnumProcessModulesEx(
                self.handle, hMods, ctypes.sizeof(hMods),
                ctypes.byref(needed), 0x03)
            return hMods[0] if needed.value > 0 else None
        except Exception:
            return None

    def read(self, addr, size):
        if not self.handle:
            return None
        buf = ctypes.create_string_buffer(size)
        nread = ctypes.c_size_t()
        ok = ctypes.windll.kernel32.ReadProcessMemory(
            self.handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(nread))
        return buf.raw[:nread.value] if ok and nread.value > 0 else None

    def read_str(self, addr, maxlen=64):
        data = self.read(addr, maxlen)
        if not data:
            return None
        end = data.find(b'\x00')
        if end <= 0:
            return None
        try:
            return data[:end].decode('ascii')
        except Exception:
            return None

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
    """Called on F9. Dumps PS memory to disk. Returns dump_id or None."""
    global _reader
    if not IS_WINDOWS:
        return None
    if _reader is None:
        _reader = ProcessReader()
    if not _reader.handle and not _reader.attach():
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
        'dump_id': dump_id, 'timestamp': ts,
        'pid': _reader.pid, 'module_base': _reader.module_base,
        'regions': regions, 'bytes_total': file_offset,
    }
    with open(meta_path, 'w') as f:
        json.dump(meta, f)
    log(f"Dump: {len(regions)} regions, {file_offset/1024/1024:.0f} MB")
    return dump_id


def tag_dump(dump_id, gpt_result):
    """Called after GPT returns. Tags dump with vision data."""
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
    meta['opponents'] = [
        {'name': o.get('name', ''), 'has_cards': o.get('has_cards', False)}
        for o in gpt_result.get('opponents', [])
    ]
    with open(meta_path, 'w') as f:
        json.dump(meta, f)


# ── Dump File Helpers ────────────────────────────────────────────────

def _load_tagged_dumps():
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
        if not meta.get('hero_cards') or len(meta['hero_cards']) < 2:
            continue
        meta['_bin_path'] = bin_path
        dumps.append(meta)
    return dumps


def _make_read_fns(bin_path, regions):
    """Return (read_bytes, read_str) functions for a dump file."""
    def read_bytes(addr, size):
        for r in regions:
            if r['base'] <= addr < r['base'] + r['size']:
                off = addr - r['base']
                with open(bin_path, 'rb') as f:
                    f.seek(r['file_offset'] + off)
                    return f.read(min(size, r['size'] - off))
        return None

    def read_str(addr, maxlen=64):
        data = read_bytes(addr, maxlen)
        if not data:
            return None
        end = data.find(b'\x00')
        if end <= 0:
            return None
        try:
            return data[:end].decode('ascii')
        except Exception:
            return None

    return read_bytes, read_str


# ── Signature-Based Buffer Finder ────────────────────────────────────

def find_buffer_in_dump(bin_path, regions, expected_cards_ascii=None):
    """Find the message buffer using the 0x88 signature.

    Scans for `00 88 00 00 00 00 00 00 00 00`, validates the first entry
    (hand_id in 200B-300B, seq=1), picks highest hand_id. Tiebreak by
    checking which candidate has readable hero name_ptr.

    Returns (buf_addr, entries) or (None, None).
    """
    read_bytes, read_str = _make_read_fns(bin_path, regions)
    candidates = []  # (buf_addr, hand_id)

    with open(bin_path, 'rb') as f:
        for r in regions:
            f.seek(r['file_offset'])
            data = f.read(r['size'])
            idx = 0
            while True:
                idx = data.find(BUFFER_SIGNATURE, idx)
                if idx < 0:
                    break
                entry_off = idx + 10  # signature is 10 bytes before first entry
                if entry_off + 16 <= len(data):
                    hid = struct.unpack('<Q', data[entry_off:entry_off+8])[0]
                    seq = struct.unpack('<I', data[entry_off+8:entry_off+12])[0]
                    if 200_000_000_000 < hid < 300_000_000_000 and seq == 1:
                        candidates.append((r['base'] + entry_off, hid))
                idx += 1

    if not candidates:
        return None, None

    # Pick highest hand_id
    max_hid = max(c[1] for c in candidates)
    best = [c for c in candidates if c[1] == max_hid]

    if len(best) == 1:
        buf_addr = best[0][0]
    else:
        # Tiebreak: find the one with readable hero name in SEATED entries
        buf_addr = best[0][0]
        for ba, hid in best:
            entries = decode_buffer(ba, read_bytes, read_str)
            for e in entries:
                if e['msg_type'] == 0x02 and e['name'] == HERO_NAME:
                    buf_addr = ba
                    break

    entries = decode_buffer(buf_addr, read_bytes, read_str)
    return (buf_addr, entries) if len(entries) >= 3 else (None, None)


def _fuzzy_match(a, b):
    """Check if two names match allowing 1-char difference (GPT vision errors like O/0)."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(c1 != c2 for c1, c2 in zip(a, b)) <= 1
    # Length differs by 1: check if one is substring-ish
    short, long = (a, b) if len(a) < len(b) else (b, a)
    diffs = 0
    si = li = 0
    while si < len(short) and li < len(long):
        if short[si] != long[li]:
            diffs += 1
            li += 1
        else:
            si += 1
            li += 1
    return diffs <= 1


# ── Offline Analysis ─────────────────────────────────────────────────

def cmd_analyze():
    """Verify message buffer structure across all tagged dumps."""
    dumps = _load_tagged_dumps()
    if not dumps:
        log("No tagged dumps. Run: python helper_bar.py --calibrate")
        return

    log(f"=== Memory Calibrator v4 (Signature-Based) ===")
    log(f"Dumps: {len(dumps)}\n")

    errors = 0
    for meta in dumps:
        dump_id = meta['dump_id']
        hero_cards = meta['hero_cards']
        bin_path = meta['_bin_path']
        regions = meta['regions']
        opps = [o['name'] for o in meta.get('opponents', []) if o.get('name')]
        expected = ''.join(hero_cards) if hero_cards else None

        log(f"{'='*60}")
        log(f"{dump_id}: cards={hero_cards} opps={opps}")

        t0 = time.time()
        buf_addr, entries = find_buffer_in_dump(bin_path, regions, expected)
        elapsed = time.time() - t0

        if not buf_addr:
            log(f"  FAIL: buffer not found ({elapsed:.1f}s)")
            errors += 1
            continue

        hand_data = extract_hand_data(entries)
        found_cards = hand_data['hero_cards']
        found_community = hand_data['community_cards']

        # Verify cards (allow reversed order)
        cards_ok = False
        if found_cards and expected:
            cards_ok = found_cards == expected
            if not cards_ok and len(found_cards) == 4:
                cards_ok = found_cards[2:4] + found_cards[0:2] == expected

        # Verify community cards against GPT
        comm_expected = meta.get('community_cards', [])
        comm_ok = set(found_community) == set(comm_expected) if comm_expected and found_community else True

        # Verify opponent names (fuzzy: allow 1-char difference for GPT vision errors)
        real_players = {s: n for s, n in hand_data['players'].items() if s != 255 and n}
        found_names = set(real_players.values())
        opps_ok = True
        for opp in opps:
            if opp not in found_names:
                # Fuzzy: check if any name is close (1-char diff or O/0 swap)
                fuzzy = any(_fuzzy_match(opp, fn) for fn in found_names)
                if not fuzzy:
                    opps_ok = False

        if not cards_ok:
            errors += 1

        log(f"  Buffer: 0x{buf_addr:08X} ({len(entries)} entries, {elapsed:.1f}s)")
        log(f"  Hand ID: {hand_data['hand_id']}")
        log(f"  Cards: '{found_cards}' {'OK' if cards_ok else 'FAIL (expected '+str(expected)+')'}")
        log(f"  Players: {dict(real_players)} {'OK' if opps_ok else 'MISMATCH (GPT: '+str(opps)+')'}")
        if found_community:
            log(f"  Community: {found_community} {'OK' if comm_ok else 'MISMATCH (GPT: '+str(comm_expected)+')'}")
        log(f"  Actions: {len(hand_data['actions'])}")
        for e in entries:
            log(f"    {format_entry(e)}")

    log(f"\n{'='*60}")
    log(f"TOTAL ERRORS: {errors}")
    if errors == 0:
        log(f"ALL {len(dumps)} DUMPS VERIFIED")


# ── Fast Card Read (Windows runtime) ────────────────────────────────

def scan_live():
    """Scan live PS memory for current hand data using 0x88 signature.

    Returns dict with hand_id, hero_cards, players, actions, scan_time,
    buf_addr, or None on failure.
    """
    global _reader
    if _reader is None:
        _reader = ProcessReader()
    if not _reader.handle and not _reader.attach():
        return None

    t0 = time.time()
    candidates = []

    for base, size in _reader.iter_regions():
        if size > 100 * 1024 * 1024:
            continue
        data = _reader.read(base, size)
        if not data:
            continue
        idx = 0
        while True:
            idx = data.find(BUFFER_SIGNATURE, idx)
            if idx < 0:
                break
            entry_off = idx + 10
            if entry_off + 16 <= len(data):
                hid = struct.unpack('<Q', data[entry_off:entry_off+8])[0]
                seq = struct.unpack('<I', data[entry_off+8:entry_off+12])[0]
                if 200_000_000_000 < hid < 300_000_000_000 and seq == 1:
                    candidates.append((base + entry_off, hid))
            idx += 1

    if not candidates:
        return None

    candidates.sort(key=lambda c: c[1], reverse=True)

    for buf_addr, hid in candidates:
        entries = decode_buffer(buf_addr, _reader.read, _reader.read_str)
        hand_data = extract_hand_data(entries)
        if hand_data and hand_data['hero_cards']:
            hand_data['scan_time'] = round(time.time() - t0, 2)
            hand_data['buf_addr'] = buf_addr
            hand_data['entry_count'] = len(entries)
            return hand_data

    return None


def rescan_buffer(buf_addr, expected_hand_id=None):
    """Re-read a known buffer address. <1ms. Returns hand_data or None."""
    global _reader
    if _reader is None or not _reader.handle:
        return None
    # Quick validate: read first 16 bytes to check hand_id still matches
    header = _reader.read(buf_addr, 16)
    if not header or len(header) < 16:
        return None
    hid = struct.unpack('<Q', header[0:8])[0]
    if expected_hand_id and hid != expected_hand_id:
        return None  # New hand started or buffer moved
    entries = decode_buffer(buf_addr, _reader.read, _reader.read_str)
    hand_data = extract_hand_data(entries)
    if hand_data:
        hand_data['buf_addr'] = buf_addr
        hand_data['entry_count'] = len(entries)
    return hand_data


def read_cards_fast():
    """API for helper_bar: returns ['Ah', 'Kd'] or None."""
    result = scan_live()
    if not result or not result.get('hero_cards'):
        return None
    cards = result['hero_cards']
    if len(cards) != 4:
        return None
    return [cards[0:2], cards[2:4]]


def is_calibrated():
    """Signature-based approach doesn't need pre-calibration."""
    return IS_WINDOWS


def calibrate_after_gpt(gpt_result):
    """Legacy API - no-op."""
    pass


def load_calibration():
    try:
        with open(CALIBRATION_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def save_calibration(data):
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# ── CLI ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else ''
    if cmd == 'analyze':
        cmd_analyze()
    elif cmd == 'read':
        if not IS_WINDOWS:
            log("Windows only")
        else:
            r = scan_live()
            if r:
                log(f"Cards: {r['hero_cards']}  hand_id: {r['hand_id']}  "
                    f"players: {r['players']}  ({r['scan_time']}s)")
            else:
                log("Could not find buffer")
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
        print("  python memory_calibrator.py analyze  # Verify message buffer in all dumps")
        print("  python memory_calibrator.py read     # Read cards live (Windows only)")
        print("  python memory_calibrator.py list     # Show tagged dumps")
        print("  python memory_calibrator.py dump     # Manual dump (Windows only)")
