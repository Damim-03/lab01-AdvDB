import os
import struct

# -------------------------
# Global
# -------------------------
PAGE_SIZE = 4096  # 4 KB per page

# -------------------------
# Part 1: Given functions for setting up the heap file
# -------------------------

def create_heap_file(file_name):
    """
    Create a new empty heap file.
    (creates an empty file if not exists; truncates if exists)
    """
    with open(file_name, 'wb') as f:
        pass  # empty file


def read_page(file_name, page_number):
    """
    Read a specific page (4 KB) from the heap file given the page number.
    Returns bytes of length PAGE_SIZE.
    """
    file_size = os.path.getsize(file_name)
    last_page_number = file_size // PAGE_SIZE - 1
    if page_number > last_page_number or page_number < 0:
        raise ValueError(f"Page {page_number} does not exist in the file.")
    with open(file_name, 'rb') as f:
        f.seek(page_number * PAGE_SIZE)
        page_data = f.read(PAGE_SIZE)
    if len(page_data) != PAGE_SIZE:
        raise IOError("Failed to read a full page.")
    return page_data


def append_page(file_name, page_data):
    """
    Appends the provided page data to the end of the file.
    page_data must be exactly PAGE_SIZE bytes.
    """
    if len(page_data) != PAGE_SIZE:
        raise ValueError(f"Page data must be exactly {PAGE_SIZE} bytes.")
    with open(file_name, 'ab') as f:
        f.write(page_data)


def write_page(file_name, page_number, page_data):
    """
    Write data to a specific page in the heap file.
    Overwrites the page at page_number.
    """
    file_size = os.path.getsize(file_name)
    last_page_number = file_size // PAGE_SIZE - 1
    if page_number > last_page_number or page_number < 0:
        raise ValueError(f"Page {page_number} does not exist in the file.")
    if len(page_data) != PAGE_SIZE:
        raise ValueError(f"page_data must be exactly {PAGE_SIZE} bytes long.")
    with open(file_name, 'r+b') as f:
        f.seek(page_number * PAGE_SIZE)
        f.write(page_data)


# -------------------------
# Part 2: Bytes manipulation examples & helpers
# -------------------------

def new_empty_page_bytes():
    """
    Return a new empty page (bytes) initialized with zeros and valid footer:
    - free_space_offset = 0 (2 bytes at 4094-4095)
    - slot_count = 0 (2 bytes at 4092-4093)
    """
    buf = bytearray(PAGE_SIZE)  # all zeros
    # footer: at 4092..4093 = slot_count, 4094..4095 = free_space_offset
    struct.pack_into('>H', buf, 4092, 0)  # slot_count = 0
    struct.pack_into('>H', buf, 4094, 0)  # free_space_offset = 0
    return bytes(buf)


# Helper: read footer values from a page bytes
def read_footer(page_data):
    """
    Returns (slot_count, free_space_offset)
    slot_count: number of slot entries (unsigned short)
    free_space_offset: offset (unsigned short)
    """
    slot_count = struct.unpack('>H', page_data[4092:4094])[0]
    free_space_offset = struct.unpack('>H', page_data[4094:4096])[0]
    return slot_count, free_space_offset


# Helper: compute slot entry byte position for slot index i (0-based)
def slot_entry_pos(slot_index):
    """
    Each slot entry is 4 bytes: (2 bytes offset, 2 bytes length)
    Slot entries start immediately before the 4-byte footer and grow backwards.
    slot_index = 0 for first added slot (the earliest slot).
    The nth slot (slot_index) is stored at:
        pos = PAGE_SIZE - 4 - (slot_index + 1) * 4
    """
    return PAGE_SIZE - 4 - (slot_index + 1) * 4


# -------------------------
# Part 3: Lab directives - required functions
# -------------------------

def Calculate_free_space(page_data):
    """
    Calculate free space in a page.
    page_data: bytes length PAGE_SIZE
    Returns free_space (int: number of free bytes available for new record plus its 4-bytes slot).
    (Free space available for placing raw record bytes; caller must account slot entry size)
    """
    if len(page_data) != PAGE_SIZE:
        raise ValueError("page_data length must be PAGE_SIZE.")
    slot_count, free_space_offset = read_footer(page_data)
    # slot table size (bytes) = slot_count * 4
    # footer size = 4
    slot_table_and_footer = slot_count * 4 + 4
    used = free_space_offset + slot_table_and_footer
    free_space = PAGE_SIZE - used
    return free_space


def insert_record_data_to_page_data(page_data, record_data):
    """
    Insert record_data (bytes) into page_data (bytes). Returns new page_data (bytes) if success.
    Raises ValueError if not enough space.
    Steps:
      - read footer (slot_count, free_space_offset)
      - compute free_space
      - check if record fits (record_length + 4 (slot entry)) <= free_space
      - write record bytes starting at free_space_offset
      - write slot entry at proper position: (offset, length)
      - update footer: new free_space_offset and slot_count+1
    NOTE: record_data must be bytes-like.
    """
    if not isinstance(record_data, (bytes, bytearray)):
        raise TypeError("record_data must be bytes or bytearray.")

    if len(page_data) != PAGE_SIZE:
        raise ValueError("page_data length must be PAGE_SIZE.")

    slot_count, free_space_offset = read_footer(page_data)
    record_len = len(record_data)

    # compute free space available
    slot_table_and_footer = slot_count * 4 + 4
    free_space = PAGE_SIZE - (free_space_offset + slot_table_and_footer)

    # each new record will need record_len bytes + 4 bytes in slot table
    if record_len + 4 > free_space:
        raise ValueError("Not enough space in this page to insert the record.")

    # convert to mutable buffer
    buf = bytearray(page_data)

    # 1) insert record bytes at free_space_offset
    # use struct.pack_into to copy bytes: format f'{record_len}B' and unpack record_data
    if record_len > 0:
        fmt = f'{record_len}B'
        struct.pack_into(fmt, buf, free_space_offset, *record_data)

    # 2) write new slot entry (offset, length) at the next slot entry position
    new_slot_index = slot_count  # 0-based
    pos = slot_entry_pos(new_slot_index)
    # pack offset and length as unsigned short big-endian
    struct.pack_into('>H', buf, pos, free_space_offset)
    struct.pack_into('>H', buf, pos + 2, record_len)

    # 3) update footer:
    # new free_space_offset = old + record_len
    new_free_space_offset = free_space_offset + record_len
    new_slot_count = slot_count + 1
    struct.pack_into('>H', buf, 4094, new_free_space_offset)
    struct.pack_into('>H', buf, 4092, new_slot_count)

    return bytes(buf)


def insert_record_to_file(file_name, record_data):
    """
    Find a page in file_name with enough free space and insert record_data.
    If file is empty or no page has space, create a new page and append it.
    record_data must be bytes.
    Returns (page_number, slot_id) on success where slot_id is 0-based index in that page.
    """
    if not isinstance(record_data, (bytes, bytearray)):
        raise TypeError("record_data must be bytes or bytearray.")

    # If file doesn't exist, create it
    if not os.path.exists(file_name):
        create_heap_file(file_name)

    file_size = os.path.getsize(file_name)
    num_pages = file_size // PAGE_SIZE

    # Try to insert in existing pages
    for page_no in range(num_pages):
        page = read_page(file_name, page_no)
        try:
            updated_page = insert_record_data_to_page_data(page, record_data)
            # read footer of original page to know slot_count before insertion
            old_slot_count, _ = read_footer(page)
            # write updated page
            write_page(file_name, page_no, updated_page)
            return page_no, old_slot_count  # inserted at slot index = old_slot_count
        except ValueError:
            continue  # not enough space, try next page

    # Not found -> create new page and insert
    new_page = new_empty_page_bytes()
    updated_page = insert_record_data_to_page_data(new_page, record_data)
    append_page(file_name, updated_page)
    # new page number is num_pages (0-based)
    return num_pages, 0  # first slot in new page


def get_record_from_page(page_data, record_id):
    """
    Retrieve a record from the specified page_data given record_id (0-based).
    Returns bytes of the record.
    Raises IndexError if record_id invalid.
    """
    slot_count, _ = read_footer(page_data)
    if record_id < 0 or record_id >= slot_count:
        raise IndexError("record_id out of range for this page.")
    pos = slot_entry_pos(record_id)
    offset, length = struct.unpack('>HH', page_data[pos:pos + 4])
    if length == 0:
        return b''  # empty record
    return page_data[offset:offset + length]


def get_record_from_file(file_name, page_number, record_id):
    """
    Retrieve a record from the specified page_number of the heap file given record_id.
    Returns bytes.
    """
    page = read_page(file_name, page_number)
    return get_record_from_page(page, record_id)


def get_all_record_from_page(page_data):
    """
    Retrieve all records from the specified page_data.
    Returns list of bytes (each record).
    """
    slot_count, _ = read_footer(page_data)
    records = []
    for i in range(slot_count):
        rec = get_record_from_page(page_data, i)
        records.append(rec)
    return records


def get_all_record_from_file(file_name):
    """
    Retrieve all records from the heap file.
    Returns list of tuples: (page_number, slot_id, record_bytes)
    """
    if not os.path.exists(file_name):
        return []
    file_size = os.path.getsize(file_name)
    num_pages = file_size // PAGE_SIZE
    all_records = []
    for p in range(num_pages):
        page = read_page(file_name, p)
        slot_count, _ = read_footer(page)
        for i in range(slot_count):
            rec = get_record_from_page(page, i)
            all_records.append((p, i, rec))
    return all_records


# -------------------------
# Example usage & Arabic explanations
# -------------------------
if __name__ == "__main__":
    fname = "heapfile.dat"

    # 1) Create (or reset) heapfile
    create_heap_file(fname)
    print("Created empty heap file:", fname)

    # 2) Insert few records (bytes)
    r1 = b'HELLO'            # 5 bytes
    r2 = b'WORLD!!'          # 7 bytes
    r3 = b'BBBBBBBBBBBB'     # 12 bytes

    p1, s1 = insert_record_to_file(fname, r1)
    print(f"Inserted r1 at page {p1}, slot {s1}")

    p2, s2 = insert_record_to_file(fname, r2)
    print(f"Inserted r2 at page {p2}, slot {s2}")

    p3, s3 = insert_record_to_file(fname, r3)
    print(f"Inserted r3 at page {p3}, slot {s3}")

    # 3) Read back one record
    rec = get_record_from_file(fname, p1, s1)
    print("Read record:", rec)

    # 4) List all records
    all_recs = get_all_record_from_file(fname)
    print("All records (page,slot,bytes):")
    for page_no, slot_id, data in all_recs:
        print(f" page {page_no} slot {slot_id} -> {data}")

    # 5) Show free space in first page
    first_page = read_page(fname, 0)
    free = Calculate_free_space(first_page)
    print("Free space in page 0 (bytes):", free)
