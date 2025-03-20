import io, struct
from typing import IO
from PIL import Image
import external.jpgwrapper as jpgw
import numpy as np


def has_transparency(im: Image.Image):
        # If the image mode is not RGBA, it has no transparency
    if im.mode != "RGBA":
        return False
    alpha_channel = np.array(im)[:, :, 3]  # Extract alpha channel
    if np.any(alpha_channel < 255):  # Check if any pixel is non-opaque
        return True
    return False

def RGBA_to_BGRA(im: Image.Image):
    # Ensure we have an RGBA image
    im = im.convert("RGBA") 
    r, g, b, a = im.split()  # Ignore alpha channel
    return Image.merge("RGBA", (b, g, r, a))

def RGB_to_YMCX(im: Image.Image):
    """Convert an RGB(A) image to CMYX, where K is trivial (all zero)."""
    # Ensure we have an RGB image
    im = im.convert("RGB") 
    r, g, b = im.split()  # Ignore alpha channel
    # Swap red and blue channels (i.e., invert R and B)
    r, b = b, r
    # Manually compute the CMY channels:
    c = r.point(lambda i: 255 - i)
    m = g.point(lambda i: 255 - i)
    y = b.point(lambda i: 255 - i)
    # Make K a trivial channel (all black component is removed)
    k = Image.new("L", im.size, 0)  # K is all zeros (trivial black)
    # Merge the manually computed CMY channels with the trivial K channel
    return Image.merge("CMYK", (c, m, y, k))

def create_mipmaps(im: Image.Image, num_mips: int = 16) -> list[Image.Image]:
    """
    Create a full mipmap chain from the input image (in RGB mode).
    The first element is the original image; each subsequent level is half the size (at least 1x1).
    """
    mips = [im]
    width=im.width
    height=im.height
    sizes = [(width,height)]
    while width >= 2 and height >= 2 and num_mips >=2:
        num_mips=num_mips-1
        width = max(1, width // 2)
        height = max(1, height // 2)
        im = im.resize((width, height), Image.LANCZOS)
        mips.append(im)
        sizes.append((width,height))
    return mips, sizes

def scan_common_header(jpeg_datas: list[bytes], max_header: int = 624) -> bytes:
    """
    Find the common prefix among all JPEG-encoded byte strings.
    If there's only one entity, no common header is declared (returns b"").
    The result is truncated to max_header bytes.
    """
    if not jpeg_datas:
        return b""
    common = jpeg_datas[0]
    for data in jpeg_datas[1:]:
        new_common = bytearray()
        for a, b in zip(common, data):
            if a == b:
                new_common.append(a)
            else:
                break
        common = bytes(new_common)
        if not common:
            break
    return common[:max_header]

def move_sof_before_sos(jpeg_bytes: bytes) -> bytes:
    """
    Moves any SOF marker (SOF0: 0xffc0 or SOF2: 0xffc2) to just before the SOS marker (0xffda)
    in the JPEG data.
    
    Args:
        jpeg_bytes (bytes): Original JPEG data.
    
    Returns:
        bytes: Modified JPEG data with SOF0/SOF2 relocated.
    """
    # Ensure the JPEG starts with the SOI marker.
    if not jpeg_bytes.startswith(b'\xff\xd8'):
        raise ValueError("Not a valid JPEG file.")
    
    result = bytearray()
    # Copy the SOI marker.
    result.extend(jpeg_bytes[0:2])
    pos = 2
    sof_segments = []  # List to store SOF segments (SOF0 and/or SOF2)
    
    # Process markers sequentially.
    while pos < len(jpeg_bytes):
        # Each marker should start with 0xFF.
        if jpeg_bytes[pos] != 0xFF:
            pos += 1
            continue

        marker_start = pos
        marker = jpeg_bytes[pos:pos+2]
        pos += 2

        # End-of-Image (EOI) marker: append and break.
        if marker == b'\xff\xd9':
            result.extend(marker)
            break

        # Some markers (like 0xFF01 or restart markers 0xFFD0-0xFFD7) don't have a length field.
        if marker[1] == 0x01 or (0xD0 <= marker[1] <= 0xD7):
            result.extend(marker)
            continue

        # Read the segment length (2 bytes, big-endian).
        if pos + 2 > len(jpeg_bytes):
            break  # avoid reading past the file
        seg_length = int.from_bytes(jpeg_bytes[pos:pos+2], 'big')
        segment_end = pos + seg_length
        segment_data = jpeg_bytes[marker_start:segment_end]
        
        # If this is the SOS marker, insert the saved SOF segments (if any) before SOS.
        if marker == b'\xff\xda':
            for sof in sof_segments:
                result.extend(sof)
            sof_segments.clear()
            result.extend(segment_data)
            # Append the rest (scan data until EOI) as is.
            pos = segment_end
            result.extend(jpeg_bytes[pos:])
            break
        
        # If this is a SOF marker (SOF0 or SOF2), store it (do not add it now).
        if marker in [b'\xff\xc0', b'\xff\xc2']:
            sof_segments.append(segment_data)
        else:
            result.extend(segment_data)
        pos = segment_end

    return bytes(result)

def remove_app14(jpeg_bytes):

    """
    Remove the APP14 marker (0xffee) from a JPEG image represented in memory.
    
    Args:
        jpeg_bytes (bytes): The JPEG image data.
    
    Returns:
        bytes: Modified JPEG data without the APP14 segment.
    """
    # Ensure the JPEG starts with SOI marker (0xFFD8)
    if not jpeg_bytes.startswith(b'\xff\xd8'):
        raise ValueError("Not a valid JPEG file.")
    
    result = bytearray()
    result.extend(jpeg_bytes[0:2])  # Copy SOI marker
    pos = 2
    
    while pos < len(jpeg_bytes):
        # Ensure we're at a marker (should start with 0xFF)
        if jpeg_bytes[pos] != 0xFF:
            pos += 1
            continue

        marker_start = pos
        marker = jpeg_bytes[pos:pos+2]
        pos += 2

        # EOI marker: append and finish
        if marker == b'\xff\xd9':
            result.extend(marker)
            break

        # Some markers (like 0xFF01 or restart markers 0xFFD0-0xFFD7) don't have length fields
        if marker[1] == 0x01 or (0xD0 <= marker[1] <= 0xD7):
            result.extend(marker)
            continue

        # Get the segment length (big-endian, includes the two length bytes)
        if pos + 2 > len(jpeg_bytes):
            break  # Avoid reading beyond the data
        seg_length = int.from_bytes(jpeg_bytes[pos:pos+2], 'big')
        segment_end = pos + seg_length

        # For the SOS marker, append the segment and the rest of the data
        if marker == b'\xff\xda':
            segment_data = jpeg_bytes[marker_start:segment_end]
            result.extend(segment_data)
            pos = segment_end
            result.extend(jpeg_bytes[pos:])
            break

        # Skip the APP14 marker segment (0xffee)
        if marker == b'\xff\xee':
            pos = segment_end
        else:
            segment_data = jpeg_bytes[marker_start:segment_end]
            result.extend(segment_data)
            pos = segment_end

    return bytes(result)

def replace_marker(jpeg_bytes: bytes, marker_to_replace: bytes, new_marker_data: bytes) -> bytes:
    """
    Replaces the segment for the specified marker in JPEG data with new data.
    
    JPEG segments (except for markers without a length field) are structured as:
      [Marker (2 bytes)] [Length (2 bytes, big-endian)] [Segment Data]
    where the length field counts itself (2 bytes) plus the segment data.
    
    For the SOS segment (marker b'\xff\xda'), after replacing the header,
    the remaining scan data (up to the EOI marker) is appended unchanged.
    
    Args:
        jpeg_bytes (bytes): Original JPEG data.
        marker_to_replace (bytes): The marker to replace (e.g., b'\xff\xc0' or b'\xff\xda').
        new_marker_data (bytes): New data for the segment (excluding marker and length field).
    
    Returns:
        bytes: Modified JPEG data with the updated segment.
    
    Raises:
        ValueError: If the JPEG data is invalid or if the specified marker is not found.
    """
    if not jpeg_bytes.startswith(b'\xff\xd8'):
        raise ValueError("Not a valid JPEG file.")
    
    result = bytearray()
    result.extend(jpeg_bytes[:2])  # Copy the SOI marker.
    pos = 2
    replaced = False

    while pos < len(jpeg_bytes):
        # Each segment begins with 0xFF.
        if jpeg_bytes[pos] != 0xFF:
            pos += 1
            continue

        marker_start = pos
        marker = jpeg_bytes[pos:pos+2]
        pos += 2

        # If we encounter the End-of-Image marker, append and exit.
        if marker == b'\xff\xd9':
            result.extend(marker)
            break

        # Some markers (like 0xFF01 or restart markers 0xFFD0-0xFFD7) lack a length field.
        if marker[1] == 0x01 or (0xD0 <= marker[1] <= 0xD7):
            result.extend(marker)
            continue

        # Read the segment length (includes its own 2 bytes).
        if pos + 2 > len(jpeg_bytes):
            break
        seg_length = int.from_bytes(jpeg_bytes[pos:pos+2], 'big')
        segment_end = pos + seg_length

        if marker == marker_to_replace:
            # Build the new segment with updated length.
            new_length = len(new_marker_data) + 2
            new_segment = marker + new_length.to_bytes(2, 'big') + new_marker_data
            result.extend(new_segment)
            replaced = True

            # For the SOS marker, after writing the header, append the remaining scan data.
            if marker == b'\xff\xda':
                pos = segment_end
                result.extend(jpeg_bytes[pos:])
                break
        else:
            # Copy the segment unchanged.
            result.extend(jpeg_bytes[marker_start:segment_end])
        
        pos = segment_end

    if not replaced:
        raise ValueError(f"Marker {marker_to_replace} not found in JPEG data.")

    return bytes(result)


def extract_huff_table(jpeg_bytes: bytes, table_class: int, table_id: int) -> bytes:
    """
    Extract the first DHT marker from jpeg_bytes with the given table_class (0 for DC, 1 for AC)
    and table_id, and reassemble it into a full JHUFF_TBL structure as a bytes object.
    
    The JHUFF_TBL structure is assumed to consist of:
      - bits: 17 unsigned bytes (bits[0] unused, bits[1..16] from the marker)
      - huffval: 256 unsigned bytes (symbols, padded with zeros)
      - sent_table: 1 unsigned byte (set to 0)
    Total size: 17 + 256 + 1 = 274 bytes (if boolean is 1 byte).
    """
    i = 0
    # Table header: high nibble = table_class, low nibble = table_id
    target_header = (table_class << 4) | (table_id & 0x0F)
    while i < len(jpeg_bytes) - 1:
        if jpeg_bytes[i] == 0xFF and jpeg_bytes[i+1] == 0xC4:
            i += 2  # Skip marker bytes
            if i + 2 > len(jpeg_bytes):
                break
            # The next two bytes indicate the segment length (includes these two bytes)
            seg_length = int.from_bytes(jpeg_bytes[i:i+2], byteorder='big')
            dht_data_start = i + 2
            dht_data_end = dht_data_start + seg_length - 2
            if dht_data_end > len(jpeg_bytes):
                break
            segment = jpeg_bytes[dht_data_start:dht_data_end]
            # The first byte is the table info.
            if segment[0] == target_header:
                # There should be at least 1 (table info) + 16 (bits counts) bytes.
                if len(segment) < 17:
                    raise ValueError("DHT segment too short for bits array")
                # Extract counts from bytes 1 to 16.
                bits_counts = list(segment[1:17])
                total_symbols = sum(bits_counts)
                if len(segment) < 1 + 16 + total_symbols:
                    raise ValueError("DHT segment does not contain enough symbol bytes")
                symbols = list(segment[17:17+total_symbols])
                # Build full bits array: bits[0] is unused (set to 0)
                jhuff_bits = [0] + bits_counts
                # Build full huffval array: pad symbols with zeros to 256 bytes.
                jhuff_huffval = symbols + [0]*(256 - len(symbols))
                sent_table = 0  # FALSE
                fmt = "17B256B1B"
                return struct.pack(fmt, *(jhuff_bits + jhuff_huffval + [sent_table]))
            i = dht_data_end
        else:
            i += 1
    raise ValueError(f"No DHT marker found for table_class {table_class} table_id {table_id}")

def extract_huff_tables(jpeg_bytes: bytes, table_id: int = 0) -> tuple[bytes, bytes]:
    """
    Extract the first DC and AC Huffman tables (for the given table_id) from the JPEG byte stream.
    
    Returns:
        tuple: (dc_table, ac_table) as bytes objects each representing a full JHUFF_TBL.
    """
    dc_table = extract_huff_table(jpeg_bytes, table_class=0, table_id=table_id)
    ac_table = extract_huff_table(jpeg_bytes, table_class=1, table_id=table_id)
    return dc_table, ac_table

def export_blp1_jpeg(im: Image.Image, fp: IO[bytes], quality: int = 95, num_mips: int = None, progressive: bool = False, optimize_coding: bool = False, force_bgra: bool = True) -> None:
    """
    Export a Pillow image (in any mode) as a BLP1 file using CONTENT_JPEG,
    with a full mipmap chain.
    
    Process:
      1. Convert the input image to RGB.
      2. Generate a mipmap chain (the first element is the full image,
         each subsequent level is half the size, down to 1x1).
      3. Encode each mipmap level to JPEG in memory (using the given quality).
      4. Compute the common JPEG header (shared by all levels, up to 624 bytes).
      5. For each mipmap, remove the common header from its JPEG data.
      6. Compute offsets and sizes for each mipmap block.
      7. Write out the BLP1 header, the JPEG header block, and then all mipmap data.
    
    BLP1 Header format (all little-endian):
      - 4 bytes: Magic ("BLP1")
      - 4 bytes: Compression (0 for CONTENT_JPEG)
      - 4 bytes: Flags (here 0; if desired, one might set a flag if alpha were preserved)
      - 4 bytes: Width
      - 4 bytes: Height
      - 4 bytes: ExtraField (world edit use this for war3mapMap.blp)
      - 4 bytes: HasMipmaps (commonly 1)
      - 16 DWORDs: MipMapOffset array
      - 16 DWORDs: MipMapSize array
      
    Then, the JPEG header block is written:
      - 4 bytes: Header size (DWORD)
      - N bytes: The common JPEG header (up to 624 bytes)
      
    Then each mipmap's JPEG data (with common header removed) is written.
    """
    num_mips_max=16
    num_mips_false=8
    transp_flag=0
    # Convert input image to BGRA (using CMYK-style treatment for 4-canal JPEG)
    transparency = has_transparency(im)
    if transparency:
        transp_flag=8
        force_bgra = True
    if force_bgra:
        # Ensure we have an RGBA image
        im_bgra = RGBA_to_BGRA(im)
    else:
        im_bgra=RGB_to_YMCX(im)
        
    if num_mips is None:
        num_mips=num_mips_max
    
    num_mips=min(num_mips_max,num_mips)
    num_mips=max(1,num_mips)

    # Generate the full mipmap chain
    mips , mips_sizes = create_mipmaps(im_bgra,num_mips)
    num_mips = len(mips)
    
    # Encode each mipmap level to JPEG (in memory)
    jpeg_datas = []
    count_mip_level = 0
    dct = None
    act = None
    for mip in mips:
        if force_bgra:
            width, height = mip.size
            #Convert image to NumPy array (shape: height x width x 4)
            bgra_bytes = np.array(mip).tobytes()
            data = jpgw.compress_bgra_to_jpeg(bgra_bytes, width, height, quality, progressive, optimize_coding, dct, act)
            if False:
                dct, act = extract_huff_tables(data, table_id=0)
            data = move_sof_before_sos(data)
        else:
            buf = io.BytesIO()
            mip.save(buf, format="JPEG", quality=quality,progressive=progressive, keep_rgb=True, optimize=optimize_coding)
            data = buf.getvalue()
            data = remove_app14(data)
            if not(progressive):
                data = move_sof_before_sos(data)
        jpeg_datas.append(data)
        count_mip_level +=1
    # Compute common JPEG header (up to 624 bytes)
    max_common_header=624 
    common_header = scan_common_header(jpeg_datas, max_common_header)
    
    # Remove the common header from each JPEG block
    jpeg_blocks = [data[len(common_header):] for data in jpeg_datas]
    
    # BLP1 header fields
    magic = b"BLP1"
    compression = 0  # CONTENT_JPEG
    flags = transp_flag      # Set flags as needed (e.g. 8 for alpha)
    width, height = im_bgra.size
    extra_field = 5     # For JPEG content
    has_mipmaps = 1  # The hasMipmaps field is a boolean for if mipmaps are present for the image. If 0 then no mipmaps exist and the image will be present at full resolution at mipmap level 0.
    
    # Fixed header size: 4+4+4+4+4+4+4 + (16*4)+(16*4) = 156 bytes.
    header_size = 156
    # JPEG header block: 4 bytes for header size + len(common_header)
    jpeg_header_block_size = 4 + len(common_header)
    data_start_offset = header_size + jpeg_header_block_size
    
    # Compute offsets and sizes for each of the 16 mipmap levels.
    num_levels = num_mips_max
    offsets = []
    sizes = []
    current_offset = data_start_offset
    old_offset = current_offset
    for i in range(num_levels):
        if i < len(jpeg_blocks):
            block = jpeg_blocks[i]
            mip_width=mips_sizes[i][0]
            mip_height=mips_sizes[i][1]
            offsets.append(current_offset)
            size=len(block)
            sizes.append(size)
            old_offset = current_offset
            current_offset += size
        elif i >= len(jpeg_blocks) and i<num_mips_false and (mip_width>1) and (mip_height>1):
            mip_width=mip_width / 2
            mip_height=mip_height /2
            offsets.append(old_offset)
            sizes.append(size)
        else:
            offsets.append(0)
            sizes.append(0)
    
    # Begin writing the BLP file.
    fp.write(magic)
    fp.write(struct.pack("<I", compression))
    fp.write(struct.pack("<I", flags))
    fp.write(struct.pack("<I", width))
    fp.write(struct.pack("<I", height))
    fp.write(struct.pack("<I", extra_field))
    fp.write(struct.pack("<I", has_mipmaps))
    # Write 16 mipmap offsets.
    for off in offsets:
        fp.write(struct.pack("<I", off))
    # Write 16 mipmap sizes.
    for sz in sizes:
        fp.write(struct.pack("<I", sz))
    
    # Write JPEG header block: first the DWORD with header length, then the header itself.
    fp.write(struct.pack("<I", len(common_header)))
    fp.write(common_header)
    
    # Write each mipmap JPEG data block.
    for block in jpeg_blocks:
        fp.write(block)
