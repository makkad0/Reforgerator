import struct
import external.imagecompress as imagecompress
from typing import IO
from PIL import Image

def export_dds_dxt(image: Image.Image, fp: IO[bytes], compression: str = "DXT1", num_mips: int = None) -> None:
    """
    Export a Pillow image (in any mode) as a DDS file using DXT1/DXT3/DXT5 compression,
    with a full mipmap chain.
    
    num_mips: Set to None to generate full mipmap chain
    """
    num_mips_max = 16
    if num_mips is None:
        num_mips=num_mips_max
    num_mips_count = 0
    dxt_fourcc = compression.encode("utf-8")  # Options: b"DXT1", b"DXT3", b"DXT5"
    # Generate mipmaps.
    mip_levels = []
    # Level 0: original image.
    mip_levels.append(compress_image_to_dxt(image, dxt_fourcc))
    if len(mip_levels)<num_mips:
        w, h = image.size
        current_image = image
        # Generate smaller levels until the dimensions reach 1.
        while w > 1 and h > 1 and len(mip_levels)<num_mips:
            w = max(1, w // 2)
            h = max(1, h // 2)
            current_image = current_image.resize((w, h), Image.LANCZOS)
            mip_levels.append(compress_image_to_dxt(current_image, dxt_fourcc))
    
    #print(f"Generated {len(mip_levels)} mip levels.")
    
    write_dds(fp, mip_levels, dxt_fourcc)

def compress_image_to_dxt(im, dxt_fourcc):
    """
    Convert a PIL image to compressed DXT data.
    
    The image is first converted to RGBA. If the image's dimensions are less than 4x4,
    it is padded to 4x4 by replicating the existing pixels. Then the appropriate
    compression function is used from imagecompress. For DXT1, the resulting data is
    vertically flipped. Returns a tuple: (original_width, original_height, compressed_data).
    """
    # Ensure the image is in RGBA format
    im = im.convert("RGBA")
    original_width, original_height = im.width, im.height

    # If the image is smaller than 4x4, pad it to 4x4 for compression.
    if original_width < 4 or original_height < 4:
        pixels = list(im.getdata())
        padded_pixels = pad_to_4x4(pixels, original_width, original_height)
        # Create a new 4x4 image with the padded data.
        padded_im = Image.new("RGBA", (4, 4))
        padded_im.putdata(padded_pixels)
        im_for_compression = padded_im
    else:
        im_for_compression = im

    # Get the data from the image used for compression.
    data = im_for_compression.tobytes()
    width_for_comp = im_for_compression.width  # This will be 4 if padded, else original width.
    height_for_comp = im_for_compression.height
    rgba_data = {
        'width': width_for_comp,
        'height': height_for_comp,
        'data': data,
        'length': len(data)
    }

    # Compress using the appropriate function.
    if dxt_fourcc == b"DXT1":
        comp_result = imagecompress.rgba2dxt1(rgba_data)
        comp_data = comp_result['data']
    elif dxt_fourcc == b"DXT3":
        comp_result = imagecompress.rgba2dxt3(rgba_data)
        comp_data = comp_result['data']
    elif dxt_fourcc == b"DXT5":
        comp_result = imagecompress.rgba2dxt5(rgba_data)
        comp_data = comp_result['data']
    else:
        raise ValueError("Unsupported compression format")
    
    # Return the original dimensions along with the compressed data.
    return (original_width, original_height, comp_data)

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