import os, struct
PAGE_SIZE = 4096

def create_heap_file(fname):
    open(fname, 'wb').close()

def read_page(fname, n):
    with open(fname, 'rb') as f:
        f.seek(n * PAGE_SIZE)
        return f.read(PAGE_SIZE)

def append_page(fname, data):
    with open(fname, 'ab') as f: f.write(data)

def write_page(fname, n, data):
    with open(fname, 'r+b') as f:
        f.seek(n * PAGE_SIZE)
        f.write(data)

def new_empty_page():
    b = bytearray(PAGE_SIZE)
    struct.pack_into('>HH', b, 4092, 0, 0)
    return bytes(b)

def read_footer(p):
    s, f = struct.unpack('>HH', p[4092:4096])
    return s, f

def slot_pos(i): return PAGE_SIZE - 4 - (i + 1) * 4

def free_space(p):
    s, f = read_footer(p)
    return PAGE_SIZE - (f + s * 4 + 4)

def insert_record(p, rec):
    s, f = read_footer(p)
    if len(rec) + 4 > free_space(p): raise ValueError("No space")
    b = bytearray(p)
    struct.pack_into(f'{len(rec)}s', b, f, rec)
    struct.pack_into('>HH', b, slot_pos(s), f, len(rec))
    struct.pack_into('>HH', b, 4092, s + 1, f + len(rec))
    return bytes(b)

def insert_to_file(fname, rec):
    if not os.path.exists(fname): create_heap_file(fname)
    size = os.path.getsize(fname); np = size // PAGE_SIZE
    for i in range(np):
        try:
            p = read_page(fname, i)
            newp = insert_record(p, rec)
            write_page(fname, i, newp)
            return i, read_footer(p)[0]
        except ValueError: pass
    newp = insert_record(new_empty_page(), rec)
    append_page(fname, newp)
    return np, 0

def get_record(p, i):
    s, _ = read_footer(p)
    if i >= s: raise IndexError
    off, l = struct.unpack('>HH', p[slot_pos(i):slot_pos(i) + 4])
    return p[off:off + l]

def get_all(fname):
    if not os.path.exists(fname): return []
    size = os.path.getsize(fname); np = size // PAGE_SIZE
    out = []
    for n in range(np):
        p = read_page(fname, n)
        s, _ = read_footer(p)
        for i in range(s): out.append((n, i, get_record(p, i)))
    return out

if __name__ == "__main__":
    f = "heapfile.dat"; create_heap_file(f)
    for r in [b'AAAAA', b'BBBBBB']:
        p, s = insert_to_file(f, r)
        print(f"Inserted {r} -> page {p}, slot {s}")
    for p, s, d in get_all(f):
        print(f"Page {p}, Slot {s}: {d}")
    print("Free space:", free_space(read_page(f, 0)))
