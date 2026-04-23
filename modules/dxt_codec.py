"""
DXT3/DXT5 Texture Codec
Pure Python encoder/decoder for BC2 (DXT3) and BC3 (DXT5) block compression.
Used for Dark Sector PS3 font textures (.tga.1 files).
"""

import struct


def make_dds_header(width, height, fourcc):
    """Create a 128-byte DDS file header."""
    DDSD_CAPS = 0x1
    DDSD_HEIGHT = 0x2
    DDSD_WIDTH = 0x4
    DDSD_PIXELFORMAT = 0x1000
    DDSD_LINEARSIZE = 0x80000
    DDPF_FOURCC = 0x4
    DDSCAPS_TEXTURE = 0x1000

    bw = max(1, width // 4)
    bh = max(1, height // 4)
    block_size = 16  # Both DXT3 and DXT5 are 16 bytes/block
    linear_size = bw * bh * block_size

    flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE

    header = bytearray(128)
    header[0:4] = b'DDS '
    struct.pack_into('<I', header, 4, 124)
    struct.pack_into('<I', header, 8, flags)
    struct.pack_into('<I', header, 12, height)
    struct.pack_into('<I', header, 16, width)
    struct.pack_into('<I', header, 20, linear_size)
    struct.pack_into('<I', header, 76, 32)
    struct.pack_into('<I', header, 80, DDPF_FOURCC)
    header[84:88] = fourcc.encode('ascii')
    struct.pack_into('<I', header, 108, DDSCAPS_TEXTURE)

    return bytes(header)


# ============================================================================
#  BC1 Color Block Encoder (shared by DXT3 and DXT5)
# ============================================================================

def _to_rgb565(r, g, b):
    """Convert 8-bit RGB to packed RGB565."""
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def _from_rgb565(c):
    """Convert RGB565 to 8-bit RGB tuple."""
    r = ((c >> 11) & 0x1F) * 255 // 31
    g = ((c >> 5) & 0x3F) * 255 // 63
    b = (c & 0x1F) * 255 // 31
    return (r, g, b)


def _color_distance_sq(c1, c2):
    """Squared distance between two RGB tuples."""
    return (c1[0]-c2[0])**2 + (c1[1]-c2[1])**2 + (c1[2]-c2[2])**2


def encode_bc1_block(pixels):
    """Encode 16 RGBA pixels into 8-byte BC1 color block.

    Args:
        pixels: list of 16 (R, G, B, A) tuples in row-major order.

    Returns:
        8 bytes: color0(2) + color1(2) + indices(4)
    """
    # Extract RGB
    colors = [(p[0], p[1], p[2]) for p in pixels]

    # Find bounding box endpoints
    r_vals = [c[0] for c in colors]
    g_vals = [c[1] for c in colors]
    b_vals = [c[2] for c in colors]

    color_max = (max(r_vals), max(g_vals), max(b_vals))
    color_min = (min(r_vals), min(g_vals), min(b_vals))

    c0 = _to_rgb565(*color_max)
    c1 = _to_rgb565(*color_min)

    # Ensure c0 > c1 for 4-color mode (no transparency)
    if c0 < c1:
        c0, c1 = c1, c0
    elif c0 == c1:
        # Uniform color block
        indices = 0
        return struct.pack('<HHI', c0, c1, indices)

    # Build 4-color palette
    col0 = _from_rgb565(c0)
    col1 = _from_rgb565(c1)
    col2 = tuple((2 * a + b) // 3 for a, b in zip(col0, col1))
    col3 = tuple((a + 2 * b) // 3 for a, b in zip(col0, col1))
    palette = [col0, col1, col2, col3]

    # Find closest palette entry for each pixel
    indices = 0
    for i, c in enumerate(colors):
        best_idx = 0
        best_dist = _color_distance_sq(c, palette[0])
        for j in range(1, 4):
            dist = _color_distance_sq(c, palette[j])
            if dist < best_dist:
                best_dist = dist
                best_idx = j
        indices |= best_idx << (2 * i)

    return struct.pack('<HHI', c0, c1, indices)


# ============================================================================
#  DXT3 (BC2) Alpha Encoder
# ============================================================================

def encode_dxt3_alpha_block(alphas):
    """Encode 16 alpha values into 8-byte DXT3 explicit alpha block.

    Each alpha is quantized to 4 bits. Two pixels packed per byte.

    Args:
        alphas: list of 16 alpha values (0-255) in row-major order.

    Returns:
        8 bytes of alpha data.
    """
    result = bytearray(8)
    for i in range(0, 16, 2):
        lo = alphas[i] >> 4
        hi = alphas[i + 1] >> 4
        result[i // 2] = lo | (hi << 4)
    return bytes(result)


# ============================================================================
#  DXT5 (BC3) Alpha Encoder
# ============================================================================

def encode_dxt5_alpha_block(alphas):
    """Encode 16 alpha values into 8-byte DXT5 interpolated alpha block.

    Uses two reference alpha endpoints with 3-bit index interpolation.

    Args:
        alphas: list of 16 alpha values (0-255) in row-major order.

    Returns:
        8 bytes: alpha0(1) + alpha1(1) + indices(6)
    """
    a_min = min(alphas)
    a_max = max(alphas)

    if a_min == a_max:
        # Uniform alpha - all indices point to alpha0
        result = bytearray(8)
        result[0] = a_max
        result[1] = a_max
        return bytes(result)

    # Check if we need 0 and 255 in the palette
    has_zero = a_min == 0
    has_full = a_max == 255

    if has_zero or has_full:
        # Use 6-entry mode (alpha0 <= alpha1)
        # Palette: a0, a1, 4 interpolated, 0, 255
        alpha0 = a_min
        alpha1 = a_max
        if alpha0 == alpha1:
            alpha1 = alpha0 + 1 if alpha0 < 255 else alpha0 - 1

        table = [alpha0, alpha1]
        for i in range(1, 5):
            table.append(((5 - i) * alpha0 + i * alpha1) // 5)
        table.append(0)
        table.append(255)
    else:
        # Use 8-entry mode (alpha0 > alpha1)
        alpha0 = a_max
        alpha1 = a_min

        table = [alpha0, alpha1]
        for i in range(1, 7):
            table.append(((7 - i) * alpha0 + i * alpha1) // 7)

    # Find closest index for each pixel
    indices = []
    for a in alphas:
        best_idx = 0
        best_dist = abs(a - table[0])
        for j in range(1, len(table)):
            dist = abs(a - table[j])
            if dist < best_dist:
                best_dist = dist
                best_idx = j
        indices.append(best_idx)

    # Pack result
    result = bytearray(8)
    result[0] = alpha0
    result[1] = alpha1

    # Pack 16 3-bit indices into 48 bits (6 bytes)
    bits = 0
    for i in range(16):
        bits |= indices[i] << (3 * i)

    result[2] = bits & 0xFF
    result[3] = (bits >> 8) & 0xFF
    result[4] = (bits >> 16) & 0xFF
    result[5] = (bits >> 24) & 0xFF
    result[6] = (bits >> 32) & 0xFF
    result[7] = (bits >> 40) & 0xFF

    return bytes(result)


# ============================================================================
#  Full Image Encoders
# ============================================================================

def encode_dxt3(img_data, width, height):
    """Encode RGBA pixel data to raw DXT3 block data.

    Args:
        img_data: bytes/bytearray of RGBA pixels (4 bytes per pixel), row-major.
        width: image width (must be multiple of 4).
        height: image height (must be multiple of 4).

    Returns:
        bytes of raw DXT3 block data (no DDS header).
    """
    result = bytearray()

    for by in range(0, height, 4):
        for bx in range(0, width, 4):
            # Extract 4x4 block
            block_pixels = []
            block_alphas = []
            for py in range(4):
                for px in range(4):
                    x = bx + px
                    y = by + py
                    if x < width and y < height:
                        idx = (y * width + x) * 4
                        r = img_data[idx]
                        g = img_data[idx + 1]
                        b = img_data[idx + 2]
                        a = img_data[idx + 3]
                    else:
                        r, g, b, a = 0, 0, 0, 0
                    block_pixels.append((r, g, b, a))
                    block_alphas.append(a)

            # DXT3: alpha block (8 bytes) + color block (8 bytes)
            result.extend(encode_dxt3_alpha_block(block_alphas))
            result.extend(encode_bc1_block(block_pixels))

    return bytes(result)


def encode_dxt5(img_data, width, height):
    """Encode RGBA pixel data to raw DXT5 block data.

    Args:
        img_data: bytes/bytearray of RGBA pixels (4 bytes per pixel), row-major.
        width: image width (must be multiple of 4).
        height: image height (must be multiple of 4).

    Returns:
        bytes of raw DXT5 block data (no DDS header).
    """
    result = bytearray()

    for by in range(0, height, 4):
        for bx in range(0, width, 4):
            block_pixels = []
            block_alphas = []
            for py in range(4):
                for px in range(4):
                    x = bx + px
                    y = by + py
                    if x < width and y < height:
                        idx = (y * width + x) * 4
                        r = img_data[idx]
                        g = img_data[idx + 1]
                        b = img_data[idx + 2]
                        a = img_data[idx + 3]
                    else:
                        r, g, b, a = 0, 0, 0, 0
                    block_pixels.append((r, g, b, a))
                    block_alphas.append(a)

            # DXT5: alpha block (8 bytes) + color block (8 bytes)
            result.extend(encode_dxt5_alpha_block(block_alphas))
            result.extend(encode_bc1_block(block_pixels))

    return bytes(result)
