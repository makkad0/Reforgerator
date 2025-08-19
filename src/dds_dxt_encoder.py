import struct
import math
import external.imagecompress as imagecompress
from typing import IO
from PIL import Image

def _ceil_to_mult4(n: int) -> int:
    return ((n + 3) // 4) * 4

def _pad_to_block_rgba(im: Image.Image) -> Image.Image:
    """
    Pad an RGBA image so width/height are multiples of 4 (min 4).
    Uses edge-pixel replication; never shrinks content.
    """
    if im.mode != "RGBA":
        im = im.convert("RGBA")

    w, h = im.size
    new_w = max(4, _ceil_to_mult4(w))
    new_h = max(4, _ceil_to_mult4(h))

    if new_w == w and new_h == h:
        return im

    canvas = Image.new("RGBA", (new_w, new_h))
    # Paste original
    canvas.paste(im, (0, 0))

    # Pad right edge if needed
    if new_w > w:
        right_col = im.crop((w - 1, 0, w, h)).resize((new_w - w, h), Image.NEAREST)
        canvas.paste(right_col, (w, 0))

    # Pad bottom (over full width including the new right area)
    if new_h > h:
        bottom_row = canvas.crop((0, h - 1, new_w, h)).resize((new_w, new_h - h), Image.NEAREST)
        canvas.paste(bottom_row, (0, h))

    return canvas

def export_dds_dxt(image: Image.Image, fp: IO[bytes], compression: str = "DXT1", num_mips: int = None) -> None:
    """
    Export a Pillow image (in any mode) as a DDS file using DXT1/DXT3/DXT5 compression,
    with a full mipmap chain.
    
    num_mips: Set to None to generate full mipmap chain
    """
    num_mips_max = 16
    # Full chain length for NPOT: floor(log2(max(w,h)))+1
    w0, h0 = image.size
    full_chain = int(math.floor(math.log2(max(w0, h0)))) + 1
    target_mips = full_chain if num_mips is None else min(num_mips, full_chain)
    target_mips = min(target_mips, num_mips_max)

    dxt_fourcc = compression.encode("utf-8")

    mip_levels = []
    current_image = image.convert("RGBA")
    w, h = current_image.size

    for _ in range(target_mips):
        # Compress current level (will pad to multiples of 4 internally)
        mip_levels.append(compress_image_to_dxt(current_image, dxt_fourcc))
        if w == 1 and h == 1:
            break
        w2 = max(1, w // 2)
        h2 = max(1, h // 2)
        current_image = current_image.resize((w2, h2), Image.LANCZOS)
        w, h = w2, h2

    write_dds(fp, mip_levels, dxt_fourcc)

def compress_image_to_dxt(im: Image.Image, dxt_fourcc: bytes):
    """
    Convert a PIL image to compressed DXT data.
    - Convert to RGBA.
    - Pad to multiples of 4 in each dimension (min 4) by replicating edge pixels.
    - Compress with the chosen BC format.

    Returns: (logical_width, logical_height, compressed_bytes)
             logical_* are the true NPOT dimensions for this mip level.
    """
    im = im.convert("RGBA")
    logical_w, logical_h = im.width, im.height

    # Pad this level to block-aligned size
    padded = _pad_to_block_rgba(im)
    comp_w, comp_h = padded.size  # multiples of 4

    rgba_data = {
        'width': comp_w,
        'height': comp_h,
        'data': padded.tobytes(),
        'length': comp_w * comp_h * 4
    }

    if dxt_fourcc == b"DXT1":
        comp_result = imagecompress.rgba2dxt1(rgba_data)
    elif dxt_fourcc == b"DXT3":
        comp_result = imagecompress.rgba2dxt3(rgba_data)
    elif dxt_fourcc == b"DXT5":
        comp_result = imagecompress.rgba2dxt5(rgba_data)
    else:
        raise ValueError("Unsupported compression format")

    return (logical_w, logical_h, comp_result['data'])


def pad_to_4x4(pixels, width, height):
    # 'pixels' is a flat list of RGBA pixels of size width x height.
    # Create a 4x4 list by replicating the existing pixels.
    padded = []
    for y in range(4):
        for x in range(4):
            # Clamp x and y to the available dimensions
            src_x = min(x, width - 1)
            src_y = min(y, height - 1)
            padded.append(pixels[src_y * width + src_x])
    return padded

def write_dds(f, mip_levels, dxt_fourcc):
    """
    Write a DDS file given a list of mip levels.
    
    Each element in mip_levels is a tuple: (width, height, compressed_data).
    The DDS header is created using the dimensions of the first (largest) mip level,
    and the file contains all mip levels one after the other.
    """
    # Use the first mip level dimensions for the header.
    width0, height0, _ = mip_levels[0]
    mipmap_count = len(mip_levels)
    header = create_dds_header(width0, height0, mipmap_count, dxt_fourcc)
    
    total_expected_data = 0

    f.write(header)
    for (w, h, data) in mip_levels:
        # Calculate expected data size for this mip level.
        if dxt_fourcc == b"DXT1":
            block_size = 8
        else:
            block_size = 16
        num_blocks_w = max(1, (w + 3) // 4)
        num_blocks_h = max(1, (h + 3) // 4)
        expected_size = num_blocks_w * num_blocks_h * block_size
        total_expected_data += expected_size
        #if len(data) != expected_size:
        #    print(f"Warning: Mip level {w}x{h} compressed data length is {len(data)} bytes, expected {expected_size} bytes.")
        f.write(data)
    
def create_dds_header(width, height, mipmap_count, dxt_fourcc):
    dwSize = 124  # must be 124
    # Flags: required fields for a DDS file
    DDSD_CAPS        = 0x1
    DDSD_HEIGHT      = 0x2
    DDSD_WIDTH       = 0x4
    DDSD_PIXELFORMAT = 0x1000
    DDSD_LINEARSIZE  = 0x80000
    DDSD_MIPMAPCOUNT = 0x20000
    flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE
    if mipmap_count > 1:
        flags |= DDSD_MIPMAPCOUNT

    # Calculate pitch/linear size for compressed formats.
    block_size = 8 if dxt_fourcc == b"DXT1" else 16
    num_blocks_w = max(1, (width + 3) // 4)
    num_blocks_h = max(1, (height + 3) // 4)
    pitchOrLinearSize = num_blocks_w * num_blocks_h * block_size

    depth = 0  # non-volume texture
    reserved1 = (0,) * 11

    header_part1 = struct.pack("<I I I I I I I 11I",
        dwSize, flags, height, width, pitchOrLinearSize, depth, mipmap_count, *reserved1)

    # DDS_PIXELFORMAT structure (32 bytes)
    pfSize = 32
    DDPF_FOURCC = 0x4
    pfFlags = DDPF_FOURCC
    pfFourCC = dxt_fourcc   # e.g. b"DXT1", b"DXT3", or b"DXT5"
    pfRGBBitCount = 0
    pfRBitMask = 0
    pfGBitMask = 0
    pfBBitMask = 0
    pfABitMask = 0
    dds_pixelformat = struct.pack("<I I 4s I I I I I",
        pfSize, pfFlags, pfFourCC, pfRGBBitCount,
        pfRBitMask, pfGBitMask, pfBBitMask, pfABitMask)

    # DDS_CAPS: For mipmapped textures, DDSCAPS_COMPLEX and DDSCAPS_MIPMAP must be set
    DDSCAPS_TEXTURE = 0x1000
    DDSCAPS_COMPLEX = 0x8
    DDSCAPS_MIPMAP  = 0x400000
    caps1 = DDSCAPS_TEXTURE
    if mipmap_count > 1:
        caps1 |= DDSCAPS_COMPLEX | DDSCAPS_MIPMAP

    caps2 = 0
    caps3 = 0
    caps4 = 0
    dwReserved2 = 0
    header_part3 = struct.pack("<I I I I I", caps1, caps2, caps3, caps4, dwReserved2)

    magic = b"DDS "
    final_header = magic + header_part1 + dds_pixelformat + header_part3

    if len(final_header) != 128:
        raise ValueError(f"Final DDS header length is {len(final_header)} bytes; expected 128 bytes.")
    return final_header