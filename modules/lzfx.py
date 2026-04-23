"""
LZFX Compression / Decompression
Pure Python port of lzfx.c used in Dark Sector's custom ZIP method 64.
"""

import struct

LZFX_MAX_LIT = 1 << 5   # 32
LZFX_MAX_OFF = 1 << 13  # 8192
LZFX_MAX_REF = (1 << 8) + (1 << 3)  # 264
CHUNK_SIZE = 0x4000  # 16384 bytes per chunk


def lzfx_decompress(data: bytes, expected_size: int) -> bytes:
    """Decompress LZFX compressed data."""
    ip = 0
    out = bytearray(expected_size)
    op = 0
    in_end = len(data)

    while ip < in_end:
        ctrl = data[ip]
        ip += 1

        if ctrl < 0x20:
            ctrl += 1
            if ip + ctrl > in_end:
                break
            if op + ctrl > expected_size:
                break
            out[op:op + ctrl] = data[ip:ip + ctrl]
            op += ctrl
            ip += ctrl
        else:
            length = ctrl >> 5
            if length == 7:
                if ip >= in_end:
                    break
                length += data[ip]
                ip += 1
            length += 2

            if ip >= in_end:
                break

            ref = op - ((ctrl & 0x1F) << 8) - 1 - data[ip]
            ip += 1

            if ref < 0:
                break
            if op + length > expected_size:
                break

            for _ in range(length):
                out[op] = out[ref]
                op += 1
                ref += 1

    return bytes(out[:op])


def lzfx_compress(data: bytes) -> bytes:
    """Compress data using LZFX algorithm."""
    if len(data) == 0:
        return b''

    if len(data) < 4:
        out = bytearray()
        out.append(len(data) - 1)
        out.extend(data)
        return bytes(out)

    HTAB_BITS = 16
    HTAB_SIZE = 1 << HTAB_BITS
    htab = [0] * HTAB_SIZE

    ip = 0
    in_end = len(data)
    out = bytearray(len(data) * 2 + 16)
    op = 0
    lit = 0
    op += 1

    def frst(p):
        return (data[p] << 8) | data[p + 1]

    def nxt(v, p):
        return ((v << 8) | data[p + 2]) & 0xFFFFFFFF

    def idx(h):
        return (((h >> (3 * 8 - HTAB_BITS)) - h) & (HTAB_SIZE - 1))

    hval = frst(ip)

    while ip + 2 < in_end:
        hval = nxt(hval, ip)
        hslot = idx(hval)
        ref = htab[hslot]
        htab[hslot] = ip

        off = ip - ref - 1

        if (ref < ip and
            off < LZFX_MAX_OFF and
            ip + 4 < in_end and
            ref > 0 and
            data[ref] == data[ip] and
            data[ref + 1] == data[ip + 1] and
            data[ref + 2] == data[ip + 2]):

            length = 3
            maxlen = min(in_end - ip - 2, LZFX_MAX_REF)
            while length < maxlen and data[ref + length] == data[ip + length]:
                length += 1

            out[op - lit - 1] = lit - 1 if lit > 0 else 0
            if lit == 0:
                op -= 1

            length -= 2

            if length < 7:
                out[op] = (off >> 8) + (length << 5)
                op += 1
                out[op] = off & 0xFF
                op += 1
            else:
                out[op] = (off >> 8) + (7 << 5)
                op += 1
                out[op] = length - 7
                op += 1
                out[op] = off & 0xFF
                op += 1

            lit = 0
            op += 1

            ip += length + 1

            if ip + 3 >= in_end:
                ip += 1
                break

            hval = frst(ip)
            hval = nxt(hval, ip)
            htab[idx(hval)] = ip
            ip += 1
        else:
            lit += 1
            out[op] = data[ip]
            op += 1
            ip += 1

            if lit == LZFX_MAX_LIT:
                out[op - lit - 1] = lit - 1
                lit = 0
                op += 1

    while ip < in_end:
        lit += 1
        out[op] = data[ip]
        op += 1
        ip += 1

        if lit == LZFX_MAX_LIT:
            out[op - lit - 1] = lit - 1
            lit = 0
            op += 1

    out[op - lit - 1] = lit - 1 if lit > 0 else 0
    if lit == 0:
        op -= 1

    return bytes(out[:op])


def darksector_decompress(data: bytes, expected_size: int) -> bytes:
    """Decompress Dark Sector chunked LZFX data (ZIP method 64)."""
    result = bytearray()
    pos = 0

    while pos < len(data) and len(result) < expected_size:
        if pos + 8 > len(data):
            break
        chunk_comp_size = struct.unpack('>I', data[pos:pos + 4])[0]
        chunk_uncomp_size = struct.unpack('>I', data[pos + 4:pos + 8])[0]
        pos += 8

        if chunk_comp_size == 0:
            break

        chunk_data = data[pos:pos + chunk_comp_size]
        pos += chunk_comp_size
        decompressed = lzfx_decompress(chunk_data, chunk_uncomp_size)
        result.extend(decompressed)

    return bytes(result[:expected_size])


def darksector_compress(data: bytes) -> bytes:
    """Compress data using Dark Sector chunked LZFX format (ZIP method 64)."""
    result = bytearray()
    offset = 0

    while offset < len(data):
        chunk = data[offset:offset + CHUNK_SIZE]
        chunk_uncomp_size = len(chunk)
        offset += chunk_uncomp_size

        compressed = lzfx_compress(chunk)

        result.extend(struct.pack('>I', len(compressed)))
        result.extend(struct.pack('>I', chunk_uncomp_size))
        result.extend(compressed)

    return bytes(result)
