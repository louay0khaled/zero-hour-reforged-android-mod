#!/usr/bin/env python3
"""BIGF archive writer/parser/verifier (EA BIG format as used by Generals/ZH).

Layout:
  char[4]  "BIGF"
  uint32 LE total archive size
  uint32 BE number of files
  uint32 BE index size (bytes of the whole index incl. header? -> in practice:
             offset of first file data = 16 + sum(entries); index size field is
             the size of the index block starting at byte 16, i.e. firstData-16+?)
  Per entry:
    uint32 BE offset
    uint32 BE size
    char[] name, NUL-terminated
Data blobs follow.
"""
import struct, sys, os

def write_big(entries, out_path):
    """entries: list of (arcname:str, data:bytes). Names use backslashes."""
    header_size = 16
    index_size = 0
    for name, data in entries:
        index_size += 8 + len(name.encode('ascii')) + 1
    total_index_field = index_size + 16  # EA convention: index size includes header
    first_data = header_size + index_size
    total_size = first_data + sum(len(d) for _, d in entries)
    out = bytearray()
    out += b'BIGF'
    out += struct.pack('<I', total_size)
    out += struct.pack('>I', len(entries))
    out += struct.pack('>I', total_index_field)
    off = first_data
    for name, data in entries:
        out += struct.pack('>I', off)
        out += struct.pack('>I', len(data))
        out += name.encode('ascii') + b'\x00'
        off += len(data)
    for name, data in entries:
        out += data
    with open(out_path, 'wb') as f:
        f.write(out)
    return total_size

def read_big(path):
    with open(path, 'rb') as f:
        raw = f.read()
    assert raw[:4] in (b'BIGF', b'BIG4'), f"bad magic {raw[:4]!r} in {path}"
    total = struct.unpack('<I', raw[4:8])[0]
    count = struct.unpack('>I', raw[8:12])[0]
    idxsize = struct.unpack('>I', raw[12:16])[0]
    pos = 16
    entries = []
    for _ in range(count):
        off, size = struct.unpack('>II', raw[pos:pos+8]); pos += 8
        end = raw.index(b'\x00', pos)
        name = raw[pos:end].decode('ascii', 'replace'); pos = end + 1
        entries.append((name, off, size))
    return raw, total, count, idxsize, entries

def verify(path):
    raw, total, count, idxsize, entries = read_big(path)
    ok = total == len(raw)
    print(f"{path}: magic ok, files={count}, header_total={total}, actual={len(raw)}, total_match={ok}, index_size_field={idxsize}")
    for name, off, size in entries:
        assert off + size <= len(raw), f"entry {name} out of range"
    return entries

if __name__ == '__main__':
    if sys.argv[1] == 'list':
        raw, total, count, idxsize, entries = read_big(sys.argv[2])
        for name, off, size in entries:
            print(f"{off:>10} {size:>10}  {name}")
        print(f"# {count} files, total {total} (actual {len(raw)})")
    elif sys.argv[1] == 'extract':
        raw, total, count, idxsize, entries = read_big(sys.argv[2])
        want = sys.argv[3].lower()
        for name, off, size in entries:
            if name.lower() == want:
                sys.stdout.buffer.write(raw[off:off+size])
                break
        else:
            sys.exit("not found")
