import struct
import io
from PIL import Image

def blp_path_to_pil(path):
    with open(path, "rb") as f:
        data = f.read()
    return blp_to_pil(data)

def blp_to_pil(data):
    """
    Reads a BLP bytes data (assumed to use CONTENT_JPEG) and restores the original JPEG data
    by combining the common JPEG header and the first mipmap's JPEG data block.
    The BLP file structure is assumed to be:
      - 156-byte fixed header:
          * Bytes 0-3: Magic ("BLP1" or "BLP2")
          * Bytes 4-7: Compression (0 for CONTENT_JPEG)
          * Bytes 8-11: Flags
          * Bytes 12-15: Width
          * Bytes 16-19: Height
          * Bytes 20-23: PictureType
          * Bytes 24-27: PictureSubType
          * Bytes 28-91: MipMapOffsets array (16 DWORDs)
          * Bytes 92-155: MipMapSizes array (16 DWORDs)
      - JPEG header block:
          * 4 bytes: JPEG header size (DWORD)
          * N bytes: JPEG header (up to 624 bytes)
      - Then, the JPEG data blocks for each mipmap.
    This function reads the JPEG header block (common header) and then
    extracts the first mipmap's JPEG data (using the first element of the
    MipMapOffsets and MipMapSizes arrays) and writes their concatenation to output_jpeg.
    In case of discrepancies (e.g. file too short), an exception is raised.
    """
    file_len = len(data)
    if file_len < 156:
        raise ValueError(f"File too short ({file_len} bytes); expected at least 156 bytes.")
    # Read magic (bytes 0-3) and ensure we have a BLP file.
    magic = data[0:4]
    if magic not in (b"BLP1", b"BLP2"):
        raise ValueError(f"Invalid magic: {magic}. Not a valid BLP file.")
    
    # Read Compression field (bytes 4-7)
    compression = struct.unpack_from("<I", data, 4)[0]
    if compression != 0:
        raise ValueError(f"BLP compression is {compression}, expected 0 (CONTENT_JPEG).")
    
    # Read first mipmap offset and size:
    first_mipmap_offset = struct.unpack_from("<I", data, 28)[0]  # first DWORD in MipMapOffsets array
    first_mipmap_size   = struct.unpack_from("<I", data, 92)[0]  # first DWORD in MipMapSizes array

    # After the fixed header (156 bytes) comes the JPEG header block.
    offset = 156
    if file_len < offset + 4:
        raise ValueError("File too short to contain JPEG header size field.")
    jpeg_header_size = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if jpeg_header_size > 624:
        raise ValueError(f"JPEG header size {jpeg_header_size} exceeds maximum allowed (624).")
    if file_len < offset + jpeg_header_size:
        raise ValueError("File too short for declared JPEG header data.")
    
    common_header = data[offset:offset + jpeg_header_size]
    offset += jpeg_header_size

    # Now, verify that the first mipmap block exists.
    if first_mipmap_offset == 0 or first_mipmap_size == 0:
        raise ValueError("First mipmap block is missing (offset or size is 0).")
    if file_len < first_mipmap_offset + first_mipmap_size:
        raise ValueError("File too short for first mipmap block as declared by header.")
    
    first_mip_data = data[first_mipmap_offset:first_mipmap_offset + first_mipmap_size]
    
    # Combine the common JPEG header and the first mipmap's JPEG data.
    restored_jpeg = common_header + first_mip_data
    img = Image.open(io.BytesIO(restored_jpeg))

    if img.mode=="CMYK":
        img=YMCK_to_RGBA(img)

    return img

def YMCK_to_RGBA(im: Image.Image):
    """Convert        an RGB(A) image to CMYX, where K is trivial (all zero)."""
    # Ensure we have an RGB image
    im = im.convert("CMYK") 
    c, m, y, k = im.split()
    # Swap red and blue channels (i.e., invert R and B)
    c, y = y, c
    # Manually compute the CMYK channels:
    r = c.point(lambda i: 255 - i)
    g = m.point(lambda i: 255 - i)
    b = y.point(lambda i: 255 - i)
    a = k.point(lambda i: 255 - i)
    # Merge the manually computed CMY channels with the trivial K channel
    return Image.merge("RGBA", (r, g, b, a))