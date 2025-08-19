from PIL import Image, ImageEnhance
import numpy as np
import io
import os
import math
import zlib
import vars.global_var as gv
from src.blp1_JPEG_encoder import export_blp1_jpeg
from src.dds_dxt_encoder import export_dds_dxt
from src.system import get_data_subdir
from src.psd_decoder import psd_path_to_pil
from src.blp_decoder import blp_path_to_pil, blp_to_pil
from src.custom_frames import get_custom_frame_section

# Global cache for loaded frame images
FRAME_CACHE = {}

_EPS = 1e-8

def srgb_to_linear(u):
    u = np.clip(u, 0.0, 1.0)
    return np.where(u <= 0.04045, u/12.92, ((u+0.055)/1.055)**2.4)

def linear_to_srgb(u):
    u = np.clip(u, 0.0, 1.0)
    return np.where(u <= 0.0031308, 12.92*u, 1.055*(u**(1/2.4)) - 0.055)

def alpha_over_linear(base_rgba: Image.Image, over_rgba: Image.Image) -> Image.Image:
    """Linear-light Porter–Duff 'over' to match GIMP/Photoshop (linear precision)."""
    # to float [0..1]
    b = np.asarray(base_rgba.convert("RGBA"), dtype=np.float32) / 255.0
    o = np.asarray(over_rgba.convert("RGBA"), dtype=np.float32) / 255.0

    # decode sRGB -> linear
    brgb_lin = srgb_to_linear(b[..., :3]); ba = b[..., 3]
    orgb_lin = srgb_to_linear(o[..., :3]); oa = o[..., 3]

    # premultiplied colors in linear
    b_p = brgb_lin * ba[..., None]
    o_p = orgb_lin * oa[..., None]

    # over in linear
    out_a = oa + ba * (1.0 - oa)
    out_p = o_p + b_p * (1.0 - oa[..., None])

    # unpremultiply (still linear)
    out_rgb_lin = np.where(out_a[..., None] > _EPS, out_p / out_a[..., None], 0.0)

    # encode back to sRGB for typical PNG viewing
    out_rgb_srgb = linear_to_srgb(out_rgb_lin)
    out = np.dstack([
        np.clip(out_rgb_srgb * 255.0 + 0.5, 0, 255).astype(np.uint8),
        np.clip(out_a        * 255.0 + 0.5, 0, 255).astype(np.uint8),
    ])
    return Image.fromarray(out, "RGBA")


def load_pil_image(path):
    """Loads an image from the given path using Pillow with enhanced error handling."""
    extension = os.path.splitext(path)[1].lower()
    
    if extension == ".psd":
        try:
            return psd_path_to_pil(path)
        except Exception:
            raise  # Propagate error to parent
    
    # For non-PSD files, try standard open first.
    img = None
    open_error = None  # Store the first error
    
    try:
        img = Image.open(path)
        if extension == ".blp":
            img.load()
    except Exception as e:
        open_error = e  # Store error but don't raise yet
        img = None

    # If opening failed and file is .blp, attempt alternative method.
    if img is None and extension == ".blp":
        try:
            return blp_path_to_pil(path)
        except Exception:
            raise  # Propagate blp_to_pil failure
    
    # If opening failed and it's not a .blp, raise the first error
    if img is None:
        raise open_error
    
    return img

def clear_alpha(input_image: Image.Image) -> Image.Image:
    size=input_image.size
    input_image = input_image.convert("RGBA")
    black_image = Image.new('RGBA',size, color='black')
    input_image = Image.alpha_composite(black_image,input_image)
    input_image = input_image.convert("RGB")
    return input_image

def remove_colors_of_alpha_pixels(input_image: Image.Image) -> Image.Image:
    """Removes (sets to zero) all color information for fully transparent pixels."""
    if input_image.mode != "RGBA":
        return input_image
    # Convert image to NumPy array (shape: H x W x 4)
    img_array = np.array(input_image)
    # Mask: Identify fully transparent pixels (A == 0)
    transparent_mask = img_array[:, :, 3] <= gv.REMOVE_COLORS_THRESHOLD
    # Set RGB values to 0 where pixels are fully transparent
    img_array[transparent_mask, :3] = 0  # Set R, G, B to 0
    # Convert back to PIL Image
    return Image.fromarray(img_array, mode="RGBA")

def optimal_crop_margin(dim: int, crop_percent: float) -> int:
    """
    Compute the optimal integer margin to crop from a given dimension so that
    the cropped size is as close as possible to (1 - crop_percent) of the original.
    
    The target margin is exactly (crop_percent/2) of the dimension, but since
    the value must be an integer, we compare the floor and ceiling values and select
    the one that minimizes the error.
    Args:
        dim (int): The original dimension (width or height).
        crop_percent (float): The overall fraction of the dimension to crop (e.g., 0.10 for 10%).
    Returns:
        int: The optimal integer margin.
    """
    target = dim * (crop_percent / 2)
    m_floor = int(math.floor(target))
    m_ceil = int(math.ceil(target))
    
    # Ensure at least 1 pixel is cropped if possible.
    if m_floor < 1:
        m_floor = 1
    if m_ceil < 1:
        m_ceil = 1

    # Safety check: cropping should not make the dimension non-positive.
    if dim - 2 * m_floor <= 0:
        m_floor = 1
    if dim - 2 * m_ceil <= 0:
        m_ceil = 1

    # The target remaining ratio should be (1 - crop_percent)
    error_floor = abs((dim - 2 * m_floor) / dim - (1 - crop_percent))
    error_ceil = abs((dim - 2 * m_ceil) / dim - (1 - crop_percent))
    
    return m_floor if error_floor <= error_ceil else m_ceil

def crop_image(input_image: Image.Image, crop_percent:float = 0.1) -> Image.Image:
    """
    Crop the input Pillow image symmetrically by relative value.
    This removes value/2 from each side.
    """
    width, height = input_image.size

    if crop_percent>=0.95 or crop_percent<=0:
        return input_image

    crop_margin_w = optimal_crop_margin(width, crop_percent)
    crop_margin_h = optimal_crop_margin(height, crop_percent)

    # Calculate new dimensions after cropping
    new_width = width - 2 * crop_margin_w
    new_height = height - 2 * crop_margin_h    

    # Validate that the new dimensions are positive.
    if new_width <= 0 or new_height <= 0:
        return input_image
    
    # Define the crop box as (left, upper, right, lower)
    left = crop_margin_w
    top = crop_margin_h
    right = width - crop_margin_w
    bottom = height - crop_margin_h
    
    # Crop and return the image
    return input_image.crop((left, top, right, bottom))

def apply_frame(input_image: Image.Image, size_option: str = "size_256x256", style_option: str = "style_hd", border_option:str ="border_button", extras:dict = None, misc:dict = None) -> Image.Image:
    """
    Applies a frame border to the input_image based on the provided options.
    
    Parameters:
        input_image (PIL.Image): A preloaded PIL image object.
        size_option (str): One of OPTIONS_SIZE ("size_64x64", "size_128x128", "size_256x256").
        style_option (str): One of OPTIONS_STYLE ("style_sd", "style_hd").
        border_option (str): One of OPTIONS_BORDER ("border_button", "border_disabled",
                            "border_passive", "border_autocast", "border_none").
                            
    Returns:
        PIL.Image: The updated image after resizing and (if applicable) combining with the frame border.
    """
    
    def _pick_closest_frame_size_option_by_max_dim(w: int, h: int) -> str:
        """Choose the size_* option (excluding size_original) whose square side is closest to max(w, h)."""
        max_dim = max(w, h)
        candidates = [k for k in gv.SIZE_MAPPING.keys() if k.startswith("size_") and k != "size_original"]
        if not candidates:
            raise ValueError("No frame size candidates available.")
        # SIZE_MAPPING[k] is e.g. (64, 64), (128, 128), (256, 256)
        return min(candidates, key=lambda k: abs(max(gv.SIZE_MAPPING[k]) - max_dim))

    if extras:
        black_frame = extras.get('extras_blackframe')
        hero_frame = extras.get('extras_heroframe')
        alpha = extras.get('extras_alpha')
        crop = extras.get('extras_crop')
    else:
        black_frame = False
        hero_frame = False
        alpha = True
        crop = False

    # Determine canvas / frame sizing mode
    orig_w, orig_h = input_image.size
    is_size_original = (size_option == gv.OPTION_SIZE_ORIGINAL)

    if is_size_original:
        # Keep output at original size; choose closest square frame for artwork source
        effective_size_option = _pick_closest_frame_size_option_by_max_dim(orig_w, orig_h)
        canvas_size = (orig_w, orig_h)                          # final output size
        frame_size = gv.SIZE_MAPPING[effective_size_option]      # native frame asset size
        target_size = canvas_size                                # default resize for image layer
    else:
        effective_size_option = size_option
        canvas_size = gv.SIZE_MAPPING.get(size_option)
        frame_size = canvas_size
        if canvas_size is None:
            raise ValueError(f"Invalid size option: {size_option}")
        target_size = canvas_size

    # Custom Frame Information
    custom_frame = False
    custom_size = None
    custom_position = None

    if border_option not in gv.OPTIONS_BORDER['options']:
        custom_frame = True
        custom_frame_options = get_custom_frame_section(border_option, style_option, effective_size_option)

        # Raw values are absolute in the native frame coordinate system (frame_size)
        raw_custom_size = custom_frame_options.get("im_size", frame_size)   # (w, h)
        raw_custom_pos  = custom_frame_options.get("im_pos", (0, 0))        # (x, y)

        # If custom size equals full frame, treat it as "no custom size"
        raw_size_is_full = (tuple(raw_custom_size) == tuple(frame_size))

        if is_size_original:
            # Scale custom values from native frame space -> canvas space
            sx = canvas_size[0] / frame_size[0]
            sy = canvas_size[1] / frame_size[1]

            if not raw_size_is_full:
                # Scaled size where the input image will be resized into
                custom_size = (
                    max(1, int(round(raw_custom_size[0] * sx))),
                    max(1, int(round(raw_custom_size[1] * sy)))
                )
                target_size = custom_size  # image layer target size becomes scaled custom size

            if raw_custom_pos != (0, 0):
                # Scaled top-left paste position on the canvas
                custom_position = (
                    int(round(raw_custom_pos[0] * sx)),
                    int(round(raw_custom_pos[1] * sy))
                )
        else:
            # Non-original mode: use raw absolute values in the native frame space
            if not raw_size_is_full:
                custom_size = tuple(raw_custom_size)
                target_size = custom_size
            if raw_custom_pos != (0, 0):
                custom_position = tuple(raw_custom_pos)

    if target_size is None:
        raise ValueError(f"Invalid size option: {size_option}")
    
    # Crop and Resize
    if crop:
        resized_image = crop_image(input_image).resize(target_size, Image.LANCZOS)
    else:
        resized_image = input_image.resize(target_size, Image.LANCZOS)
    
    hd_dis_desaturation = False
    frame_image = None

    # If the border option is not a 'border_none'.
    if border_option != "border_none":

        if style_option == "style_hd":
            hd_dis_desaturation = border_option in gv.BORDER_HD_DESATURATION
            
        if not(custom_frame):
            # Construct the folder and file names using global variables.
            size_folder = gv.FRAMES_LISTFILE.get(effective_size_option)
            style_folder = gv.FRAMES_LISTFILE.get(style_option)
            border_name = gv.FRAMES_LISTFILE.get(border_option)
            if not all([size_folder, style_folder, border_name]):
                raise ValueError("Invalid option provided in one of size, style, or border.")
            # Build the frame file path:
            # Folder structure: frames/ <size_folder> / <style_folder> / (<border_name> + FRAMES_FILETYPE)
            frame_file = border_name + gv.FRAMES_FILETYPE
            frame_path = os.path.join(get_data_subdir("frames"), size_folder, style_folder, frame_file)
        else:
            frame_path = custom_frame_options.get("path")
            if not(os.path.isabs(frame_path)):
                frame_path = os.path.join(get_data_subdir("custom_frames"),frame_path)
            
        # Use a cache key based on the current options.
        cache_key = (effective_size_option, style_option, border_option)
        
        # Attempt to retrieve the frame image from the global cache.
        if cache_key in FRAME_CACHE:
            frame_image = FRAME_CACHE[cache_key]
        else:
            try:
                frame_image = Image.open(frame_path).convert("RGBA")
                if frame_image.size!=frame_size:
                    frame_image = frame_image.resize(frame_size, Image.LANCZOS)
                FRAME_CACHE[cache_key] = frame_image  # Store in cache for future use.
            except Exception as e:
                frame_image = Image.new("RGBA",frame_size, (0, 0, 0, 0))
   
    # Ensure the resized image is in RGBA mode for proper alpha compositing.
    if resized_image.mode != "RGBA":
        resized_image = resized_image.convert("RGBA")
    
    # Black Frame
    if black_frame:
        black_frame_image_source = None
        black_frame_section='OPTIONS_EXTRAS'
        black_frame_option='extras_blackframe'
        # Construct the folder and file names using global variables.
        black_frame_size_folder = gv.FRAMES_LISTFILE.get(effective_size_option)
        black_frame_section_folder = gv.FRAMES_LISTFILE.get(black_frame_section)
        black_frame_name = gv.FRAMES_LISTFILE.get(black_frame_option)
        black_frame_file = black_frame_name + gv.FRAMES_FILETYPE
        black_frame_path = os.path.join(get_data_subdir("frames"),black_frame_size_folder,black_frame_section_folder,black_frame_file)
        cache_key = (effective_size_option,black_frame_section,black_frame_option)
        if cache_key in FRAME_CACHE:
            black_frame_image_source = FRAME_CACHE[cache_key]
        else:
            try:
                black_frame_image_source = Image.open(black_frame_path).convert("RGBA")
                FRAME_CACHE[cache_key] = black_frame_image_source  # Store in cache for future use.
            except Exception as e:
                black_frame_image_source = Image.new("RGBA",frame_size, (0, 0, 0, 0))

        if black_frame_image_source:
            black_frame_image=black_frame_image_source
            if custom_size:
                black_frame_image = black_frame_image.resize(target_size, Image.LANCZOS)
            #resized_image = alpha_over_linear(resized_image,black_frame_image)
            resized_image = Image.alpha_composite(resized_image,black_frame_image)

    # Hero Frame
    hero_frame_image = None
    if hero_frame:
        hero_frame_image_source = None
        hero_frame_section='OPTIONS_EXTRAS'
        hero_frame_option='extras_heroframe'
        # Construct the folder and file names using global variables.
        hero_frame_size_folder = gv.FRAMES_LISTFILE.get(effective_size_option)
        hero_frame_section_folder = gv.FRAMES_LISTFILE.get(hero_frame_section)
        hero_frame_name = gv.FRAMES_LISTFILE.get(hero_frame_option)
        hero_frame_file = hero_frame_name + gv.FRAMES_FILETYPE
        hero_frame_path = os.path.join(get_data_subdir("frames"),hero_frame_size_folder,hero_frame_section_folder,hero_frame_file)
        cache_key = (effective_size_option,hero_frame_section,hero_frame_option)
        if cache_key in FRAME_CACHE:
            hero_frame_image_source = FRAME_CACHE[cache_key]
        else:
            try:
                hero_frame_image_source = Image.open(hero_frame_path).convert("RGBA")
                FRAME_CACHE[cache_key] = hero_frame_image_source  # Store in cache for future use.
            except Exception as e:
                hero_frame_image_source = Image.new("RGBA",frame_size, (0, 0, 0, 0))

        if hero_frame_image_source:
            hero_frame_image=hero_frame_image_source
            resized_image = Image.alpha_composite(resized_image,hero_frame_image)

    # Combine the images:
    # The resized image is used as the base layer (first layer) and the frame image is composited on top.
    if frame_image:

        # Render-size for the frame equals the output canvas
        frame_render = frame_image if frame_image.size == canvas_size else frame_image.resize(canvas_size, Image.LANCZOS)

        if custom_position or custom_size:
            if custom_position:
                new_position = custom_position
            else:
                new_position = (0,0)
            buffer_image = Image.new("RGBA",canvas_size, (0, 0, 0, 0))
            buffer_image.paste(resized_image ,new_position,resized_image )
            buffer_image.paste(frame_render ,(0,0),frame_render )
            resized_image = buffer_image
        else:
            resized_image = Image.alpha_composite(resized_image,frame_render)

    if hd_dis_desaturation:

        hd_dis_defaults = {
            "reforged_hd_disabled_saturation": 0.5,
            "reforged_hd_disabled_contrast":   0.82,
        }

        def get01(name: str) -> float:
            """Fetch from misc (if present), ensure 0<=v<=1, else fall back to default."""
            default = hd_dis_defaults[name]
            v = (misc.get(name, default) if misc else default)
            try:
                v = float(v)
                return v if 0.0 <= v <= 2.0 else default
            except Exception:
                return default

        hd_dis_saturation = get01("reforged_hd_disabled_saturation")
        hd_dis_contrast = get01("reforged_hd_disabled_contrast")

        # Create a Color enhancer object
        enhancer = ImageEnhance.Color(resized_image)
        # Decrease saturation by 50%
        resized_image = enhancer.enhance(hd_dis_saturation)
        # Create a contrast enhancer
        enhancer = ImageEnhance.Contrast(resized_image)
        # Decrease contrast by 18% (set factor to 0.82)
        resized_image = enhancer.enhance(hd_dis_contrast)
        # Create a contrast enhancer
        #enhancer = ImageEnhance.Brightness(resized_image)
        # Decrease brightness by 20% (set factor to 0.8)
        #resized_image = enhancer.enhance(0.8)

    if alpha:
        resized_image = remove_colors_of_alpha_pixels(resized_image)
    else:
        resized_image = clear_alpha(resized_image)

    return resized_image


def apply_format(input_image: Image.Image, format_option: str = "format_dds", format_suboption_dict: dict = {}, only_preview: bool = False):

    buffer = io.BytesIO()

    if format_option == "format_dds":

        # mipmaps indicates whether to generate mipmaps.
        if "dds_mipmap" in format_suboption_dict:
            if format_suboption_dict["dds_mipmap"]=="Auto":
                num_mips=None
            else:
                num_mips=int(format_suboption_dict["dds_mipmap"])+1
        else:
            num_mips=None 

        # mipmaps indicates whether to generate mipmaps.
        if "dds_type" in format_suboption_dict:
            compression=format_suboption_dict["dds_type"]
        else:
            compression = "DXT1"

        try:
            export_dds_dxt(input_image,buffer,compression = compression, num_mips = num_mips)
        except Exception as e:
            raise IOError(f"DDS saving failed: {e}")

    elif format_option == "format_blp":
        # Example options for BLP.
        # blp_type can be "1.0
        # quality is an integer for quality settings (for BLP 1.0)

        if "blp_compression" in format_suboption_dict:
            quality=int(format_suboption_dict["blp_compression"])
        else:
            quality=95
        if "blp_mipmap" in format_suboption_dict:
            if format_suboption_dict["blp_mipmap"]=="Auto":
                num_mips=None
            else:
                num_mips=int(format_suboption_dict["blp_mipmap"])+1
        else:
            num_mips=None 
        if "blp_progressive" in format_suboption_dict:
            best_compression=format_suboption_dict["blp_progressive"]
        else:
            best_compression=False

        try:
            if only_preview or (not best_compression):
                export_blp1_jpeg(input_image,buffer,quality = quality, num_mips = num_mips, progressive = False, optimize_coding = False, force_bgra = True)
            else:
                # Try all 8 variants (combinations of progressive, optimize_coding, force_bgra)
                best_variant_bytes = None
                best_variant_options = None
                best_compressed_size = None
                for prog in [True, False]:
                    for opt in [True, False]:
                        for bgra in [True, False]:
                            temp_buffer = io.BytesIO()
                            export_blp1_jpeg(
                                input_image,
                                temp_buffer,
                                quality=quality,
                                num_mips=num_mips,
                                progressive=prog,
                                optimize_coding=opt,
                                force_bgra=bgra
                            )
                            variant_bytes = temp_buffer.getvalue()
                            # Compress the variant output with zlib to gauge its “weight.”
                            comp_bytes = zlib.compress(variant_bytes,5)
                            comp_size = len(comp_bytes)
                            # Choose the variant with the smallest compressed size.
                            if best_compressed_size is None or comp_size < best_compressed_size:
                                best_compressed_size = comp_size
                                best_variant_bytes = variant_bytes
                                best_variant_options = (prog, opt, bgra)
                # Write the best variant bytes to the final buffer.
                buffer.write(best_variant_bytes)
        except Exception as e:
            raise IOError(f"BLP saving failed: {e}")
    elif format_option == "format_tga":
        # For TGA we use Pillow's native support.
        compression = "rle"
        try:
            input_image.save(buffer, format="TGA", compression=compression)
        except Exception as e:
            raise IOError(f"TGA saving failed: {e}")
        
    elif format_option == "format_png":
        try:
            input_image.save(buffer, format="PNG")
        except Exception as e:
            raise IOError(f"PNG saving failed: {e}")

    else:

        raise ValueError(f"Unsupported format: {format_option}")

    return buffer

def bufferbytedata_to_pilimage(buffer, extension: str = None) -> Image.Image:
    """
    Converts a BytesIO buffer to a PIL Image. If standard loading fails, it saves
    the buffer as a temporary file and attempts to use load_pil_image(path).
    """
    buffer.seek(0)
    try:
        output_image = Image.open(buffer)
        output_image.load()  # Ensure the image is fully loaded.
        return output_image
    except Exception as e:
         if extension == ".blp":
             return blp_to_pil(buffer.getvalue())

def save_buffer_to_file(buffer, output_path):
    """
    Saves a BytesIO buffer to a file at the specified output path.
    """
    buffer.seek(0)
    with open(output_path, 'wb') as f:
        f.write(buffer.getvalue())