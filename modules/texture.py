"""
Texture Extract and Repack
Handles .tga.1 font texture files (raw DXT3 data without headers).
All Dark Sector PS3 font textures use DXT3 (BC2) format.
"""

import struct
import os
from PIL import Image
from modules.dxt_codec import make_dds_header, encode_dxt3, encode_dxt5


# ============================================================================
#  Format Detection — All font textures are DXT3
# ============================================================================

TEXTURE_SIZE_MAP = {
    4194304: ('DXT3', 2048, 2048),
    2097152: ('DXT3', 2048, 1024),
    1048576: ('DXT3', 1024, 1024),
    524288:  ('DXT3', 1024, 512),
    262144:  ('DXT3', 512, 512),
}


def detect_texture_format(filepath):
    """Auto-detect DXT format and resolution from file size."""
    file_size = os.path.getsize(filepath)
    if file_size in TEXTURE_SIZE_MAP:
        return TEXTURE_SIZE_MAP[file_size]
    total_blocks = file_size // 16
    if total_blocks <= 0:
        return None
    for w, h in [(2048, 2048), (2048, 1024), (1024, 2048), (1024, 1024),
                 (1024, 512), (512, 1024), (512, 512), (512, 256), (256, 256)]:
        if (w // 4) * (h // 4) == total_blocks:
            return ('DXT3', w, h)
    return None



# ============================================================================
#  Extract (.tga.1 -> PNG on black background)
# ============================================================================

def extract_texture(input_path, output_dir, fmt=None, width=None, height=None):
    """Extract a .tga.1 texture file to PNG with black background."""
    with open(input_path, 'rb') as f:
        raw_data = f.read()

    if fmt and width and height:
        detected = (fmt, width, height)
    else:
        detected = detect_texture_format(input_path)
        if not detected:
            raise ValueError(
                f"Cannot auto-detect format for {os.path.basename(input_path)} "
                f"(size: {len(raw_data)} bytes)."
            )

    dxt_fmt, w, h = detected
    expected_size = (w // 4) * (h // 4) * 16
    if len(raw_data) != expected_size:
        raise ValueError(
            f"Data size mismatch: expected {expected_size} for "
            f"{dxt_fmt} {w}x{h}, got {len(raw_data)}."
        )

    dds_header = make_dds_header(w, h, dxt_fmt)
    basename = os.path.basename(input_path)
    if basename.lower().endswith('.tga.1'):
        basename = basename[:-6]

    os.makedirs(output_dir, exist_ok=True)
    temp_dds = os.path.join(output_dir, basename + '.dds')
    with open(temp_dds, 'wb') as f:
        f.write(dds_header + raw_data)

    img = Image.open(temp_dds)

    # Font textures store glyph data in the alpha channel.
    # Output: white glyphs on black background (from alpha channel).
    if img.mode == 'RGBA':
        alpha = img.split()[3]  # Alpha channel has the font data
        img = alpha.convert('RGB')  # Grayscale alpha -> RGB (white on black)

    png_path = os.path.join(output_dir, basename + '.png')
    img.save(png_path)

    try:
        os.remove(temp_dds)
    except OSError:
        pass

    return png_path, f"{dxt_fmt} {w}x{h}"


def extract_texture_batch(input_dir, output_dir, progress_callback=None, recursive=False):
    """Extract all .tga.1 files in a directory to PNG."""
    tga_files = []
    if recursive:
        for root, dirs, files in os.walk(input_dir):
            for f in files:
                if f.lower().endswith('.tga.1'):
                    tga_files.append((os.path.join(root, f), f))
    else:
        for f in os.listdir(input_dir):
            if f.lower().endswith('.tga.1'):
                tga_files.append((os.path.join(input_dir, f), f))
    tga_files.sort(key=lambda x: x[1])
    total = len(tga_files)
    extracted = 0
    errors = []
    for i, (filepath, filename) in enumerate(tga_files):
        if progress_callback:
            progress_callback(i + 1, total, filename)
        try:
            extract_texture(filepath, output_dir)
            extracted += 1
        except Exception as e:
            errors.append(f"{filename}: {str(e)}")
    return extracted, total, errors


# ============================================================================
#  Repack (PNG -> .tga.1)
# ============================================================================

def repack_texture(png_path, output_path, fmt, width, height):
    """Repack a PNG image back to raw .tga.1 texture data.
    
    Input PNG should be white-on-black (alpha channel visualization).
    For Glyph textures: RGB=(0,0,0), Alpha=white font
    For Shadow textures: RGB=(255,255,255), Alpha=white font
    """
    img = Image.open(png_path)

    if img.size != (width, height):
        img = img.resize((width, height), Image.LANCZOS)

    # Determine if shadow or glyph from filename
    basename = os.path.basename(png_path).lower()
    is_shadow = 'shadow' in basename

    # Convert the white-on-black PNG back to RGBA for DXT encoding
    if img.mode in ('L', 'LA'):
        # Grayscale: use pixel values as alpha
        alpha = img.convert('L')
    elif img.mode in ('RGB', 'RGBA'):
        # Use luminance as alpha (white = opaque, black = transparent)
        alpha = img.convert('L')
    else:
        alpha = img.convert('L')

    if is_shadow:
        # Shadow: white color, varying alpha
        color_layer = Image.new('RGB', (width, height), (255, 255, 255))
    else:
        # Glyph: black color, varying alpha
        color_layer = Image.new('RGB', (width, height), (0, 0, 0))

    rgba_img = Image.merge('RGBA', (*color_layer.split(), alpha))
    pixel_data = rgba_img.tobytes()

    if fmt.upper() == 'DXT3':
        raw_blocks = encode_dxt3(pixel_data, width, height)
    elif fmt.upper() == 'DXT5':
        raw_blocks = encode_dxt5(pixel_data, width, height)
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(raw_blocks)
    return f"{fmt} {width}x{height}, {len(raw_blocks):,} bytes"


def repack_texture_batch(png_dir, original_dir, output_dir, progress_callback=None, recursive=False):
    """Repack all PNG files back to .tga.1 using originals for format detection."""
    png_files_list = []
    if recursive:
        for root, dirs, files in os.walk(png_dir):
            for f in files:
                if f.lower().endswith('.png') and not f.lower().endswith('_alpha.png'):
                    png_files_list.append((os.path.join(root, f), f))
    else:
        for f in os.listdir(png_dir):
            if f.lower().endswith('.png') and not f.lower().endswith('_alpha.png'):
                png_files_list.append((os.path.join(png_dir, f), f))
    png_files_list.sort(key=lambda x: x[1])
    total = len(png_files_list)
    repacked = 0
    errors = []
    for i, (png_path_full, png_name) in enumerate(png_files_list):
        if progress_callback:
            progress_callback(i + 1, total, png_name)
        try:
            basename = os.path.splitext(png_name)[0]
            original_name = basename + '.tga.1'
            original_path = None
            if recursive:
                for root, dirs, files in os.walk(original_dir):
                    if original_name in files:
                        original_path = os.path.join(root, original_name)
                        break
            else:
                candidate = os.path.join(original_dir, original_name)
                if os.path.exists(candidate):
                    original_path = candidate
            if not original_path:
                errors.append(f"{png_name}: Original .tga.1 not found")
                continue
            detected = detect_texture_format(original_path)
            if not detected:
                errors.append(f"{png_name}: Cannot detect format from original")
                continue
            fmt, w, h = detected
            output_path = os.path.join(output_dir, original_name)
            repack_texture(png_path_full, output_path, fmt, w, h)
            repacked += 1
        except Exception as e:
            errors.append(f"{png_name}: {str(e)}")
    return repacked, total, errors
