"""
Cache (.cache) Archive Extract and Repack
Handles ZIP archives with custom Dark Sector LZFX compression (method 64).
"""

import struct
import os
import zlib
from pathlib import Path
from modules.lzfx import darksector_decompress, darksector_compress


class ZipEntry:
    """Represents a single file entry in the ZIP/cache archive."""

    def __init__(self):
        self.name = ""
        self.method = 0
        self.crc32 = 0
        self.comp_size = 0
        self.uncomp_size = 0
        self.offset = 0
        self.data_offset = 0
        self.ver_made = 0x000C
        self.ver_need = 0
        self.flag = 0
        self.modtime = 0
        self.moddate = 0
        self.disk = 0
        self.int_attr = 0
        self.ext_attr = 0
        self.extra = b''
        self.local_extra = b''
        self.comment = b''


def parse_cache(filepath: str) -> list:
    """Parse a .cache file and return list of ZipEntry objects."""
    with open(filepath, 'rb') as f:
        data = f.read()

    entries = []

    eocd_offset = data.rfind(b'PK\x05\x06')
    if eocd_offset < 0:
        raise ValueError("Invalid cache file: EOCD not found")

    (eocd_sig, disk_num, disk_start, central_entries_disk,
     central_entries, central_size, central_offset,
     comment_len) = struct.unpack_from('<IHHHHIIH', data, eocd_offset)

    pos = central_offset
    for i in range(central_entries):
        if pos + 46 > len(data):
            break

        sig = struct.unpack_from('<I', data, pos)[0]
        if sig != 0x02014B50:
            break

        entry = ZipEntry()
        (_, entry.ver_made, entry.ver_need, entry.flag, entry.method,
         entry.modtime, entry.moddate, entry.crc32, entry.comp_size,
         entry.uncomp_size, name_len, extra_len, comment_len,
         entry.disk, entry.int_attr, entry.ext_attr,
         entry.offset) = struct.unpack_from('<IHHHHHHIIIHHHHHII', data, pos)

        name_start = pos + 46
        entry.name = data[name_start:name_start + name_len].decode('ascii', errors='replace')
        entry.extra = data[name_start + name_len:name_start + name_len + extra_len]
        entry.comment = data[name_start + name_len + extra_len:
                             name_start + name_len + extra_len + comment_len]

        local_pos = entry.offset
        if local_pos + 30 <= len(data):
            local_name_len = struct.unpack_from('<H', data, local_pos + 26)[0]
            local_extra_len = struct.unpack_from('<H', data, local_pos + 28)[0]
            local_extra_start = local_pos + 30 + local_name_len
            entry.local_extra = data[local_extra_start:local_extra_start + local_extra_len]
            entry.data_offset = local_pos + 30 + local_name_len + local_extra_len

        entries.append(entry)
        pos = name_start + name_len + extra_len + comment_len

    return entries


def extract_cache(cache_path: str, output_dir: str, progress_callback=None):
    """Extract all files from a .cache archive."""
    with open(cache_path, 'rb') as f:
        cache_data = f.read()

    entries = parse_cache(cache_path)
    total = len(entries)
    extracted = 0
    errors = []

    for i, entry in enumerate(entries):
        if progress_callback:
            progress_callback(i + 1, total, entry.name)

        if entry.name.endswith('/') and entry.uncomp_size == 0:
            dir_path = os.path.join(output_dir, entry.name)
            os.makedirs(dir_path, exist_ok=True)
            continue

        comp_data = cache_data[entry.data_offset:entry.data_offset + entry.comp_size]

        try:
            if entry.method == 0:
                file_data = comp_data
            elif entry.method == 64:
                file_data = darksector_decompress(comp_data, entry.uncomp_size)
            elif entry.method == 8:
                file_data = zlib.decompress(comp_data, -15)
            else:
                errors.append(f"Unsupported method {entry.method}: {entry.name}")
                continue

            file_path = os.path.join(output_dir, entry.name.replace('/', os.sep))
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            extracted += 1

        except Exception as e:
            errors.append(f"Error extracting {entry.name}: {str(e)}")

    return extracted, total, errors


def repack_cache(original_cache_path: str, input_dir: str, output_cache_path: str,
                 progress_callback=None):
    """Repack files into a .cache archive, preserving original structure."""
    with open(original_cache_path, 'rb') as f:
        orig_cache_data = f.read()

    original_entries = parse_cache(original_cache_path)
    total = len(original_entries)

    input_files = {}
    input_dir_path = Path(input_dir)
    for file_path in input_dir_path.rglob('*'):
        if file_path.is_file():
            rel_path = file_path.relative_to(input_dir_path).as_posix()
            input_files[rel_path] = str(file_path)

    local_headers = bytearray()
    central_dir = bytearray()
    file_count = 0
    errors = []

    for i, orig_entry in enumerate(original_entries):
        if progress_callback:
            progress_callback(i + 1, total, orig_entry.name)

        if orig_entry.name.endswith('/') and orig_entry.uncomp_size == 0:
            continue

        disk_file_exists = orig_entry.name in input_files

        try:
            if disk_file_exists:
                with open(input_files[orig_entry.name], 'rb') as f:
                    file_data = f.read()
                disk_size = len(file_data)
            else:
                file_data = None
                disk_size = -1

            method = orig_entry.method
            uncomp_size = orig_entry.uncomp_size

            disk_matches_entry = (disk_size == orig_entry.uncomp_size)

            if disk_matches_entry and method == 64:
                comp_data = orig_cache_data[orig_entry.data_offset:
                                            orig_entry.data_offset + orig_entry.comp_size]
                comp_size = orig_entry.comp_size
            elif disk_matches_entry and method == 0:
                comp_data = file_data
                comp_size = disk_size
                uncomp_size = disk_size
            elif not disk_matches_entry and disk_file_exists:
                is_last_entry = True
                for future_entry in original_entries[i+1:]:
                    if future_entry.name == orig_entry.name:
                        is_last_entry = False
                        break

                if is_last_entry:
                    comp_data = file_data
                    comp_size = disk_size
                    uncomp_size = disk_size
                    method = 0
                else:
                    comp_data = orig_cache_data[orig_entry.data_offset:
                                                orig_entry.data_offset + orig_entry.comp_size]
                    comp_size = orig_entry.comp_size
            else:
                comp_data = orig_cache_data[orig_entry.data_offset:
                                            orig_entry.data_offset + orig_entry.comp_size]
                comp_size = orig_entry.comp_size

            crc = orig_entry.crc32
            name_bytes = orig_entry.name.encode('ascii')
            offset = len(local_headers)

            local_header = struct.pack('<IHHHHHI IHH',
                0x04034B50, orig_entry.ver_need if orig_entry.ver_need else 0x000C,
                orig_entry.flag, method, orig_entry.modtime, orig_entry.moddate,
                crc, comp_size, uncomp_size, len(name_bytes),
                len(orig_entry.local_extra))
            local_headers.extend(local_header)
            local_headers.extend(name_bytes)
            local_headers.extend(orig_entry.local_extra)
            local_headers.extend(comp_data)

            cd_entry = struct.pack('<IHHHHHHIIIHHHHHII',
                0x02014B50, orig_entry.ver_made, orig_entry.ver_need,
                orig_entry.flag, method, orig_entry.modtime, orig_entry.moddate,
                crc, comp_size, uncomp_size, len(name_bytes),
                len(orig_entry.extra), len(orig_entry.comment),
                0, orig_entry.int_attr, orig_entry.ext_attr, offset)
            central_dir.extend(cd_entry)
            central_dir.extend(name_bytes)
            central_dir.extend(orig_entry.extra)
            central_dir.extend(orig_entry.comment)

            file_count += 1

        except Exception as e:
            errors.append(f"Error packing {orig_entry.name}: {str(e)}")

    central_dir_offset = len(local_headers)
    central_dir_size = len(central_dir)

    eocd = struct.pack('<IHHHHIIH',
        0x06054B50, 0, 0, file_count, file_count,
        central_dir_size, central_dir_offset, 0)

    os.makedirs(os.path.dirname(os.path.abspath(output_cache_path)), exist_ok=True)
    with open(output_cache_path, 'wb') as f:
        f.write(local_headers)
        f.write(central_dir)
        f.write(eocd)

    return file_count, total, errors
