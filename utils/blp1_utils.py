import struct, os,  json, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from typing import IO
from PIL import Image
from typing import List
current_directory = os.getcwd()
scripts_directory = os.path.join(current_directory, 'src')
sys.path.append(scripts_directory)
from blp1_JPEG_encoder import export_blp1_jpeg # type: ignore
from blp1_JPEG_encoder import scan_common_header # type: ignore

def analyze_blp_file(file_path: str, output_json: str) -> None:
    """
    Reads an input .blp file and separates it into blocks per the BLP specification.
    For each block the function records:
      - A name for the block.
      - The start and end byte indices.
      - The length in bytes.
      - A description (and sometimes parsed values).
    
    Blocks recognized include:
      1. The fixed header (Magic, Compression, Flags, Width, Height,
         PictureType, PictureSubType, MipMapOffsets, MipMapSizes).
      2. For CONTENT_JPEG (Compression==0): the JPEG header size and JPEG header block,
         then each mipmap level (using the offsets and sizes).
      3. For uncompressed content (Compression==1): the palette block and then each mipmap block.
      4. Any remaining bytes are recorded as an "Unallocated" block.
    
    The collected block information is written as JSON to output_json.
    """
    # Read the entire file.
    try:
        with open(file_path, "rb") as f:
            data = f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return

    file_len = len(data)
    blocks: List[dict] = []
    
    def add_block(name: str, start: int, end: int, description: str, extra=None):
        block = {
            "name": name,
            "start": start,
            "end": end,
            "length": end - start + 1,
            "description": description
        }
        if extra is not None:
            block["value"] = extra
        blocks.append(block)
    
    # Check file length against minimum header size.
    HEADER_SIZE = 156  # bytes: 4+4+4+4+4+4+4 + (16*4)+(16*4)
    if file_len < HEADER_SIZE:
        add_block("Error", 0, file_len - 1, f"File too short: {file_len} bytes; minimum header size is {HEADER_SIZE}.")
        with open(output_json, "w") as out:
            json.dump(blocks, out, indent=2)
        return
    
    offset = 0
    # Block 1: Magic (bytes 0-3)
    magic = data[0:4]
    try:
        magic_str = magic.decode("ascii")
    except Exception:
        magic_str = str(magic)
    add_block("Magic", 0, 3, "Magic value; should be 'BLP1' or 'BLP2'.", magic_str)
    offset += 4
    
    # Block 2: Compression (DWORD, bytes 4-7)
    compression = struct.unpack_from("<I", data, offset)[0]
    comp_desc = "0 = CONTENT_JPEG, 1 = Uncompressed" if compression in (0, 1) else f"Unexpected value {compression}"
    add_block("Compression", offset, offset + 3, "Compression type.", compression)
    offset += 4

    # Block 3: Flags (DWORD, bytes 8-11)
    flags = struct.unpack_from("<I", data, offset)[0]
    add_block("Flags", offset, offset + 3, "Flags (bitfield).", flags)
    offset += 4

    # Block 4: Width (DWORD, bytes 12-15)
    width = struct.unpack_from("<I", data, offset)[0]
    add_block("Width", offset, offset + 3, "Image width.", width)
    offset += 4

    # Block 5: Height (DWORD, bytes 16-19)
    height = struct.unpack_from("<I", data, offset)[0]
    add_block("Height", offset, offset + 3, "Image height.", height)
    offset += 4

    # Block 6: PictureType (DWORD, bytes 20-23)
    pic_type = struct.unpack_from("<I", data, offset)[0]
    add_block("PictureType", offset, offset + 3, "Picture type.", pic_type)
    offset += 4

    # Block 7: PictureSubType (DWORD, bytes 24-27)
    pic_subtype = struct.unpack_from("<I", data, offset)[0]
    add_block("PictureSubType", offset, offset + 3, "Picture subtype.", pic_subtype)
    offset += 4

    # Block 8: MipMapOffsets array (16 DWORDs, bytes 28-91)
    mip_offsets = []
    for i in range(16):
        off_val = struct.unpack_from("<I", data, offset)[0]
        mip_offsets.append(off_val)
        offset += 4
    add_block("MipMapOffsets", 28, 91, "Array of 16 mipmap offsets (DWORDs).", mip_offsets)

    # Block 9: MipMapSizes array (16 DWORDs, bytes 92-155)
    mip_sizes = []
    for i in range(16):
        sz = struct.unpack_from("<I", data, offset)[0]
        mip_sizes.append(sz)
        offset += 4
    add_block("MipMapSizes", 92, 155, "Array of 16 mipmap sizes (DWORDs).", mip_sizes)
    
    # At this point, offset should be 156.
    # Process remaining blocks based on Compression.
    if compression == 0:
        # JPEG content
        if file_len < offset + 4:
            add_block("Error", offset, file_len - 1, "File too short to contain JPEG header size.")
        else:
            jpeg_header_size = struct.unpack_from("<I", data, offset)[0]
            add_block("JPEGHeaderSize", offset, offset+3, "JPEG header size (DWORD).", jpeg_header_size)
            offset += 4
            if jpeg_header_size > 624:
                add_block("Warning", offset, offset + jpeg_header_size - 1,
                          f"JPEG header size {jpeg_header_size} exceeds maximum of 624 bytes.", jpeg_header_size)
            if file_len < offset + jpeg_header_size:
                add_block("Error", offset, file_len - 1, "File too short for declared JPEG header data.")
                jpeg_header_size = file_len - offset
            add_block("JPEGHeader", offset, offset + jpeg_header_size - 1,
                      "JPEG header data (common to all mipmaps).", f"{jpeg_header_size} bytes")
            offset += jpeg_header_size

            # Now, for each mipmap level where size > 0, record its block.
            for level in range(16):
                sz = mip_sizes[level]
                off_val = mip_offsets[level]
                offset += sz
                if sz == 0:
                    continue
                if off_val + sz > file_len:
                    add_block(f"MipMapLevel{level}", off_val, file_len - 1,
                              f"MipMap level {level} data truncated (expected {sz} bytes).")
                else:
                    add_block(f"MipMapLevel{level}", off_val, off_val + sz - 1,
                              f"MipMap level {level} JPEG data.", f"{sz} bytes")
    elif compression == 1:
        # Uncompressed content: expect a palette block next.
        palette_size = 256 * 4
        if file_len < offset + palette_size:
            add_block("Error", offset, file_len - 1, "File too short to contain palette data.")
        else:
            add_block("Palette", offset, offset + palette_size - 1,
                      "Palette data (256 colors, 4 bytes each).")
        offset += palette_size
        # Then each mipmap level.
        for level in range(16):
            sz = mip_sizes[level]
            off_val = mip_offsets[level]
            if sz == 0:
                continue
            if off_val + sz > file_len:
                add_block(f"MipMapLevel{level}", off_val, file_len - 1,
                          f"MipMap level {level} data truncated (expected {sz} bytes).")
            else:
                add_block(f"MipMapLevel{level}", off_val, off_val + sz - 1,
                          f"MipMap level {level} uncompressed data.", f"{sz} bytes")
    else:
        add_block("Error", offset, file_len - 1, f"Unknown compression value: {compression}")
    
    # Any remaining bytes not assigned to a block.
    if offset < file_len:
        add_block("Unallocated", offset, file_len - 1,
                  "Remaining bytes not recognized by the parser.")
    
    # Write the blocks list as JSON.
    with open(output_json, "w") as out:
        json.dump(blocks, out, indent=2)


def verify_blp_file(file_path: str) -> List[str]:
    """
    Verifies byte-by-byte the structure of the input .blp file against the specification.
    
    Checks include:
      - File length is at least the fixed header size (156 bytes).
      - The magic field equals "BLP1" or "BLP2".
      - Compression field is 0 (JPEG) or 1 (uncompressed).
      - Width and Height are nonzero and do not exceed 65,535.
      - PictureType is one of an expected set.
      - The header contains 16 DWORD offsets and 16 DWORD sizes.
      - For CONTENT_JPEG (compression==0): a DWORD JPEG header size is present and does not exceed 624,
        and the combined mipmap data (using each offset and size) does not exceed file length.
    
    Returns:
      A list of error messages. If the list is empty, the file passed all checks.
    """
    errors = []
    try:
        with open(file_path, "rb") as f:
            data = f.read()
    except Exception as e:
        errors.append(f"Failed to read file: {e}")
        return errors

    file_len = len(data)
    # Fixed header size: 4 (magic) + 4 (compression) + 4 (flags) + 4 (width) + 4 (height)
    # + 4 (picture type) + 4 (picture subtype) + 16*4 (mip offsets) + 16*4 (mip sizes) = 156 bytes.
    HEADER_SIZE = 156
    if file_len < HEADER_SIZE:
        errors.append(f"File too short: {file_len} bytes; must be at least {HEADER_SIZE} bytes.")
        return errors

    offset = 0
    # Magic: 4 bytes
    magic = data[offset:offset+4]
    offset += 4
    if magic not in (b"BLP1", b"BLP2"):
        errors.append(f"Invalid magic value: {magic!r}. Expected b'BLP1' or b'BLP2'.")
    
    # Compression: 4 bytes (DWORD)
    try:
        (compression,) = struct.unpack_from("<I", data, offset)
    except struct.error as e:
        errors.append(f"Error reading Compression field: {e}")
        return errors
    offset += 4
    if compression not in (0, 1):
        errors.append(f"Invalid Compression value: {compression}; expected 0 (JPEG) or 1 (Uncompressed).")
    
    # Flags: 4 bytes
    try:
        (flags,) = struct.unpack_from("<I", data, offset)
    except struct.error as e:
        errors.append(f"Error reading Flags field: {e}")
        return errors
    offset += 4

    # Width and Height: each 4 bytes
    try:
        (width,) = struct.unpack_from("<I", data, offset)
    except struct.error as e:
        errors.append(f"Error reading Width: {e}")
        return errors
    offset += 4
    try:
        (height,) = struct.unpack_from("<I", data, offset)
    except struct.error as e:
        errors.append(f"Error reading Height: {e}")
        return errors
    offset += 4
    if width == 0 or height == 0:
        errors.append(f"Invalid dimensions: width={width}, height={height} (must be > 0).")
    if width > 65535 or height > 65535:
        errors.append(f"Dimensions exceed maximum allowed: width={width}, height={height} (max 65535).")
    
    # PictureType and PictureSubType: each 4 bytes
    try:
        (picture_type,) = struct.unpack_from("<I", data, offset)
    except struct.error as e:
        errors.append(f"Error reading PictureType: {e}")
        return errors
    offset += 4
    try:
        (picture_subtype,) = struct.unpack_from("<I", data, offset)
    except struct.error as e:
        errors.append(f"Error reading PictureSubType: {e}")
        return errors
    offset += 4
    # (Spec suggests allowed picture types might be 3,4,5; some implementations use 2 for JPEG)
    if picture_type not in (2, 3, 4, 5):
        errors.append(f"Unexpected PictureType: {picture_type} (expected 2,3,4,5).")
    
    # Read 16 mipmap offsets.
    mip_offsets = []
    for i in range(16):
        try:
            (mo,) = struct.unpack_from("<I", data, offset)
        except struct.error as e:
            errors.append(f"Error reading mipmap offset index {i}: {e}")
            break
        mip_offsets.append(mo)
        offset += 4

    # Read 16 mipmap sizes.
    mip_sizes = []
    for i in range(16):
        try:
            (ms,) = struct.unpack_from("<I", data, offset)
        except struct.error as e:
            errors.append(f"Error reading mipmap size index {i}: {e}")
            break
        mip_sizes.append(ms)
        offset += 4

    # At this point, offset should be HEADER_SIZE (156 bytes)
    # If Compression==0 (JPEG content) then a JPEG header block follows.
    if compression == 0:
        # There must be at least 4 bytes for JPEG header size.
        if file_len < offset + 4:
            errors.append("File too short to contain JPEG header size field.")
        else:
            try:
                (jpeg_header_size,) = struct.unpack_from("<I", data, offset)
            except struct.error as e:
                errors.append(f"Error reading JPEG header size: {e}")
                jpeg_header_size = 0
            offset += 4
            if jpeg_header_size > 624:
                errors.append(f"JPEG header size {jpeg_header_size} exceeds maximum 624 bytes.")
            if file_len < offset + jpeg_header_size:
                errors.append("File too short to contain declared JPEG header data.")
            else:
                # Optionally, one might inspect jpeg_header contents.
                jpeg_header = data[offset:offset+jpeg_header_size]
            offset += jpeg_header_size

        # For each mipmap (where size != 0), check that offset+size does not exceed file length.
        for i in range(16):
            ms = mip_sizes[i]
            mo = mip_offsets[i]
            if ms != 0:
                if mo + ms > file_len:
                    errors.append(f"Mipmap level {i}: offset {mo} + size {ms} exceeds file length {file_len}.")
    else:
        # For uncompressed content, additional checks could include verifying the presence of a palette.
        palette_size = 256 * 4  # expecting 256 DWORDs for the palette.
        if file_len < offset + palette_size:
            errors.append("File too short to contain the expected 256-color palette for uncompressed BLP.")
        # (Additional checks for uncompressed mipmap data can be added here.)
    
    return errors

def restore_jpeg_from_blp(input_blp: str, output_jpeg: str, mip_level: int = 0) -> None:
    """
    Reads a BLP file (assumed to use CONTENT_JPEG) and restores the original JPEG data
    by combining the common JPEG header and one mipmap's JPEG data block.

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
          * N bytes: JPEG header data (up to 624 bytes)
      - Followed by JPEG data blocks for each mipmap.

    The optional parameter mip_level specifies the desired mipmap:
      - mip_level = 0 (default) restores the main JPEG image,
      - mip_level = 1 restores mipmap level 1,
      - mip_level = 2 restores mipmap level 2, etc.
    If the requested level is not available (i.e. its offset or size is 0),
    the function will choose the highest available mipmap level.
    """
    with open(input_blp, "rb") as f:
        data = f.read()

    file_len = len(data)
    if file_len < 156:
        raise ValueError(f"File too short ({file_len} bytes); expected at least 156 bytes.")

    # Verify magic (bytes 0-3)
    magic = data[0:4]
    if magic not in (b"BLP1", b"BLP2"):
        raise ValueError(f"Invalid magic: {magic}. Not a valid BLP file.")

    # Verify compression (bytes 4-7)
    compression = struct.unpack_from("<I", data, 4)[0]
    if compression != 0:
        raise ValueError(f"BLP compression is {compression}, expected 0 (CONTENT_JPEG).")

    # Read the 16-element arrays of mipmap offsets and sizes.
    mipmap_offsets = list(struct.unpack_from("<16I", data, 28))
    mipmap_sizes   = list(struct.unpack_from("<16I", data, 92))

    def choose_mipmap_level(requested_level: int) -> int:
        # If the requested level exists and is available, return it.
        if 0 <= requested_level < len(mipmap_offsets):
            if mipmap_offsets[requested_level] != 0 and mipmap_sizes[requested_level] != 0:
                return requested_level
        # Otherwise, scan from the highest level down to 0 and pick the first available.
        for lvl in reversed(range(len(mipmap_offsets))):
            if mipmap_offsets[lvl] != 0 and mipmap_sizes[lvl] != 0:
                return lvl
        raise ValueError("No mipmap level available in this BLP file.")

    chosen_level = choose_mipmap_level(mip_level)
    
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

    # Retrieve the chosen mipmap block.
    chosen_offset = mipmap_offsets[chosen_level]
    chosen_size   = mipmap_sizes[chosen_level]
    if chosen_offset == 0 or chosen_size == 0:
        raise ValueError(f"Mipmap level {chosen_level} block is missing (offset or size is 0).")
    if file_len < chosen_offset + chosen_size:
        raise ValueError("File too short for chosen mipmap block as declared by header.")
    
    mip_data = data[chosen_offset:chosen_offset + chosen_size]

    # Combine common JPEG header and the chosen mipmap JPEG data.
    restored_jpeg = common_header + mip_data

    with open(output_jpeg, "wb") as out_f:
        out_f.write(restored_jpeg)

    print(f"Restored JPEG from mipmap level {chosen_level} saved as {output_jpeg}")

def get_marker_description(marker):
    """
    Returns a detailed description for the given JPEG marker.
    'marker' is an integer in the form 0xFFXX.
    """
    if marker == 0xFFD8:
        return "SOI (Start Of Image): Indicates the beginning of a JPEG file. No length field."
    elif marker == 0xFFD9:
        return "EOI (End Of Image): Marks the end of the JPEG file. No length field."
    elif 0xFFD0 <= marker <= 0xFFD7:
        return (f"RST{marker - 0xFFD0} (Restart Marker): "
                "Inserted every r macroblocks (where r is set by the DRI marker) for error recovery. "
                "No length field.")
    elif 0xFFE0 <= marker <= 0xFFEF:
        appn = marker - 0xFFE0
        desc = f"APP{appn} (Application Segment): Variable size. "
        if appn == 0:
            desc += "Typically contains JFIF metadata."
        elif appn == 1:
            desc += "Typically contains Exif metadata."
        else:
            desc += "Application-specific data."
        return desc
    elif marker == 0xFFFE:
        return "COM (Comment): Contains a text comment. Variable size."
    elif marker == 0xFFDD:
        return "DRI (Define Restart Interval): Specifies the restart interval for restart markers."
    elif marker == 0xFFC0:
        return "SOF0 (Start Of Frame - Baseline DCT): Contains image dimensions, color component info, etc."
    elif marker == 0xFFC2:
        return "SOF2 (Start Of Frame - Progressive DCT): Contains image dimensions, color component info, etc."
    elif marker == 0xFFDB:
        return "DQT (Define Quantization Table): Contains quantization tables used for compression."
    elif marker == 0xFFC4:
        return "DHT (Define Huffman Table): Contains Huffman coding tables used for entropy coding."
    elif marker == 0xFFDA:
        return "SOS (Start Of Scan): Marks the beginning of the compressed image data."
    else:
        return "Unknown or unsupported marker."

def parse_jpeg_markers(file_path):
    """
    Parses the JPEG file at 'file_path' and returns a tuple (markers, total_bytes)
    where 'markers' is a list of dictionaries containing marker information.
    """
    with open(file_path, 'rb') as f:
        data = f.read()

    markers = []
    index = 0
    data_len = len(data)

    while index < data_len:
        # Markers always begin with one or more 0xFF bytes.
        if data[index] != 0xFF:
            index += 1
            continue

        marker_start = index  # record marker start offset

        # Skip any fill bytes (multiple 0xFF bytes)
        while index < data_len and data[index] == 0xFF:
            index += 1

        if index >= data_len:
            break

        marker_byte = data[index]
        marker = (0xFF << 8) | marker_byte  # Combine 0xFF with the marker byte
        index += 1

        marker_info = {
            "offset": marker_start,
            "marker": hex(marker),
            "description": get_marker_description(marker)
        }

        # Markers that do NOT include a length field: SOI, EOI, and restart markers.
        if marker in (0xFFD8, 0xFFD9) or (0xFFD0 <= marker <= 0xFFD7):
            markers.append(marker_info)
            continue

        # For markers with a length field, the next two bytes specify the segment length.
        if index + 2 > data_len:
            marker_info["error"] = "Insufficient data for length field."
            markers.append(marker_info)
            break

        segment_length = int.from_bytes(data[index:index+2], byteorder='big')
        marker_info["segment_length"] = segment_length
        index += 2

        if segment_length < 2:
            marker_info["error"] = "Invalid segment length."
            markers.append(marker_info)
            continue

        # Extract segment data (length field includes its 2 bytes, so subtract 2)
        seg_data_length = segment_length - 2
        segment_data = data[index:index + seg_data_length]
        # Convert the first 50 bytes (or less) of the segment data to a hex string for preview.
        preview = segment_data[:50].hex()
        marker_info["data_preview"] = preview

        index += seg_data_length

        # Special handling for SOS marker: after SOS, the scan data follows until the EOI marker.
        if marker == 0xFFDA:
            # Look for the next EOI marker (0xFFD9) in the remaining data.
            eoi_index = data.find(b'\xff\xd9', index)
            if eoi_index == -1:
                marker_info["error"] = "EOI marker not found after SOS."
                markers.append(marker_info)
                break
            else:
                sos_scan_data_length = eoi_index - index
                marker_info["sos_scan_data_length"] = sos_scan_data_length
                sos_preview = data[index:index+50].hex()
                marker_info["sos_data_preview"] = sos_preview
                index = eoi_index  # EOI marker will be processed next.

        markers.append(marker_info)
    return markers, data_len

def save_jpeg_rgb(im: Image.Image, output_path: str, quality: int = 75):
    """
    Save a Pillow image as a JPEG file using raw RGB encoding.
    This is intended to simulate older JPEG compression methods (used in BLP files)
    that operate directly on RGB (or BGRA) data without converting to Y'CbCr.
    
    Parameters:
      im         : Input Pillow image.
      output_path: Path for the output JPEG file.
      quality    : JPEG quality (1-95).
      
    Note: JPEG normally requires conversion to Y'CbCr. Passing rawmode="RGB"
    attempts to bypass this. If your Pillow version does not support it,
    the function will fall back to standard JPEG encoding.
    """
    # Ensure the image is in RGB mode.
    im_rgb = im.convert("RGB")
    try:
        # Attempt to force raw RGB encoding.
        im_rgb.save(output_path, "JPEG", quality=quality, progressive=True, subsampling=0, keep_rgb=True)
        print(f"Saved JPEG (raw RGB) to {output_path}")
    except TypeError as e:
        print("rawmode parameter not supported by this Pillow version. Using standard JPEG encoding.")
        im_rgb.save(output_path, "JPEG", quality=quality, subsampling=0)
        print(f"Saved JPEG (standard) to {output_path}")

def insert_jpeg_data_into_blp(jpeg_datas: list[bytes], width, height, fp: IO[bytes]) -> None:

    num_mips = len(jpeg_datas)

    # Compute common JPEG header (up to 624 bytes)
    max_common_header=624 
    common_header = scan_common_header(jpeg_datas, max_common_header)
    
    # Remove the common header from each JPEG block
    jpeg_blocks = [data[len(common_header):] for data in jpeg_datas]
    
    # BLP1 header fields
    magic = b"BLP1"
    compression = 0  # CONTENT_JPEG
    flags = 0        # Set flags as needed (e.g. 8 for alpha; here we ignore alpha)
    extra_field = 5     # For JPEG content
    has_mipmaps = 1  # The hasMipmaps field is a boolean for if mipmaps are present for the image. If 0 then no mipmaps exist and the image will be present at full resolution at mipmap level 0.
    
    # Fixed header size: 4+4+4+4+4+4+4 + (16*4)+(16*4) = 156 bytes.
    header_size = 156
    # JPEG header block: 4 bytes for header size + len(common_header)
    jpeg_header_block_size = 4 + len(common_header)
    data_start_offset = header_size + jpeg_header_block_size
    
    # Compute offsets and sizes for each of the 16 mipmap levels.
    num_levels = 16
    offsets = []
    sizes = []
    current_offset = data_start_offset
    for i in range(num_levels):
        if i < len(jpeg_blocks):
            block = jpeg_blocks[i]
            offsets.append(current_offset)
            sizes.append(len(block))
            current_offset += len(block)
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



if __name__ == "__main__":

    scenarios= [
        "save_as_blp_file", #scenario_num=0
        "analyze_blp_file", #1
        "analyze_jpeg_file", #2
        "save_jpeg_rgb", #3
        "insert_jpeg_data_into_blp", #4
    ]
    scenario_num=1
    scenario=scenarios[min(scenario_num,len(scenarios)-1)]
    print(scenario)

    input_name_file_custom=""
    #input_name_file_custom="input.blp"
    mipmap_level_jpeg_restoration = 0

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = "tempoutput"
    output_folder=os.path.join(script_dir,output_dir)
    input_dir = "tempinput"
    input_folder=os.path.join(script_dir,input_dir)

    if scenario=="save_as_blp_file":
        
        if not(input_name_file_custom):
            input_name="input.jpg"
        else:
            input_name=input_name_file_custom

        input_file_path=os.path.join( input_folder, input_name)
        base_name=os.path.splitext(os.path.basename(input_file_path))[0]
        output_file_path=os.path.join(output_folder,base_name)
        output_file_path_blp=os.path.splitext(output_file_path)[0] + ".blp"
        # Open any image (RGB, RGBA, etc.)
        im = Image.open(input_file_path)
        # Open an output file for writing binary data.
        with open(output_file_path_blp, "wb") as fp:
            export_quality = 75
            export_blp1_jpeg(im, fp, quality=export_quality,num_mips=5, progressive=False)

        #Analyzing blp container
        input_file_path=output_file_path_blp
        output_file_path_json=os.path.splitext(output_file_path)[0] + ".blp.json"
        analyze_blp_file(input_file_path,output_file_path_json)

        #Extract jpeg from blp
        output_file_path_jpeg=os.path.splitext(output_file_path)[0] + ".jpg"
        restore_jpeg_from_blp(input_file_path,output_file_path_jpeg)

        #Analyze_jpeg_file
        input_file_path=output_file_path_jpeg
        markers, total_bytes = parse_jpeg_markers(input_file_path)
        output_data = {
            "file": input_name,
            "total_bytes": total_bytes,
            "markers": markers
        }
        output_file_path_json=os.path.join(output_folder,base_name+".jpg.json")
        with open(output_file_path_json, 'w') as f:
            json.dump(output_data, f, indent=4)
            print(f"JSON output written to {output_file_path_json}")

    elif scenario=="analyze_blp_file":

        if not(input_name_file_custom):
            input_name="input.blp"
        else:
            input_name=input_name_file_custom

        input_file_path=os.path.join( input_folder, input_name)
        base_name=os.path.splitext(os.path.basename(input_file_path))[0]
        output_file_path=os.path.join(output_folder,base_name)
        output_file_path_json=os.path.splitext(output_file_path)[0] + ".blp.json"
        analyze_blp_file(input_file_path,output_file_path_json)

        #Extract jpeg from blp
        output_file_path_jpeg=os.path.splitext(output_file_path)[0] + f"_mip{mipmap_level_jpeg_restoration}.jpg"
        restore_jpeg_from_blp(input_file_path,output_file_path_jpeg,mipmap_level_jpeg_restoration)

        #Analyze_jpeg_file
        input_file_path=output_file_path_jpeg
        markers, total_bytes = parse_jpeg_markers(input_file_path)
        output_data = {
            "file": input_name,
            "total_bytes": total_bytes,
            "markers": markers
        }
        output_file_path_json=os.path.join(output_folder,base_name+f"_mip{mipmap_level_jpeg_restoration}.jpg.json")

        with open(output_file_path_json, 'w') as f:
            json.dump(output_data, f, indent=4)
            print(f"JSON output written to {output_file_path_json}")

    elif scenario=="analyze_jpeg_file":

        if not(input_name_file_custom):
            input_name="input.jpg"
        else:
            input_name=input_name_file_custom

        input_file_path=os.path.join( input_folder, input_name)
        base_name=os.path.splitext(os.path.basename(input_file_path))[0]
        output_file_path=os.path.join(output_folder,base_name)
        output_file_path_json=os.path.splitext(output_file_path)[0] + ".jpg.json"
        markers, total_bytes = parse_jpeg_markers(input_file_path)
        output_data = {
            "file": input_name,
            "total_bytes": total_bytes,
            "markers": markers
        }
        with open(output_file_path_json, 'w') as f:
            json.dump(output_data, f, indent=4)
        print(f"JSON output written to {output_file_path_json}")

    elif scenario=="save_jpeg_rgb":

        if not(input_name_file_custom):
            input_name="input.png"
        else:
            input_name=input_name_file_custom

        input_file_path=os.path.join( input_folder, input_name)
        base_name=os.path.splitext(os.path.basename(input_file_path))[0]
        output_file_path=os.path.join(output_folder,base_name)
        output_file_path_jpg=os.path.splitext(output_file_path)[0] + ".jpg"
        quality = 15  # Adjust quality as desired
        im = Image.open(input_file_path)
        save_jpeg_rgb(im,output_file_path_jpg, quality)

        input_file_path=output_file_path_jpg
        markers, total_bytes = parse_jpeg_markers(input_file_path)
        output_data = {
            "file": input_name,
            "total_bytes": total_bytes,
            "markers": markers
        }
        output_file_path_json=os.path.join(output_folder,base_name+".json")
        with open(output_file_path_json, 'w') as f:
            json.dump(output_data, f, indent=4)
            print(f"JSON output written to {output_file_path_json}")

    elif scenario=="insert_jpeg_data_into_blp":

        if not(input_name_file_custom):
            input_name="input.jpg"
        else:
            input_name=input_name_file_custom
            
        input_file_path=os.path.join( input_folder, input_name)
        base_name=os.path.splitext(os.path.basename(input_file_path))[0]

        jpeg_file_1=input_file_path

        input_name_list= []
        input_name_list.append(jpeg_file_1)

        jpeg_datas = [] 

        # Open the JPEG file
        im = Image.open(input_file_path)
        width, height=im.size

        for file_path in input_name_list:
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    data = f.read()
                    #print(len(data))
                    jpeg_datas.append(data)
            else:
                print(f"Warning: {file_path} not found; stopping mipmap reading.")
                break
        
        output_file_path=os.path.join(output_folder,base_name)
        output_file_path_blp=os.path.splitext(output_file_path)[0] + ".blp"
        with open(output_file_path_blp, "wb") as out_fp:
            insert_jpeg_data_into_blp(jpeg_datas,width, height, out_fp)
            print(f"BLP file written to {output_file_path_blp}")