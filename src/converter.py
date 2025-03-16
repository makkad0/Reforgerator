from PIL import Image, ImageEnhance
import numpy as np
import io
import os
import math
import tempfile
import var.global_var as gv
from src.blp1_JPEG_encoder import export_blp1_jpeg
from src.dds_dxt_encoder import export_dds_dxt
from src.system import get_data_subdir
from src.psd_decoder import psd_path_to_pil
from src.blp_decoder import blp_path_to_pil, blp_to_pil
from src.custom_frames import get_custom_frame_section

# Global cache for loaded frame images
FRAME_CACHE = {}

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

def apply_frame(input_image: Image.Image, size_option: str = "size_256x256", style_option: str = "style_hd", border_option:str ="border_button", extras:dict = None) -> Image.Image:
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
    
    if extras:
        black_frame = extras.get('extras_blackframe')
        alpha = extras.get('extras_alpha')
        crop = extras.get('extras_crop')
    else:
        black_frame = False
        alpha = True
        crop = False

    if black_frame and style_option != "style_hd":
        black_frame = False

    # Get the target dimensions.
    target_size = gv.SIZE_MAPPING.get(size_option)
    frame_size = gv.SIZE_MAPPING.get(size_option)

    # Custom Frame Information
    custom_frame = False
    custom_size = None
    custom_position = None
    if border_option not in gv.OPTIONS_BORDER['options']:
        custom_frame = True
        custom_frame_options = get_custom_frame_section(border_option,style_option,size_option)
        custom_size = custom_frame_options.get("im_size",frame_size)
        custom_position = custom_frame_options.get("im_pos",(0,0))
        if custom_size == frame_size:
           custom_size = None
        else:
           target_size = custom_size
        if custom_position == (0,0):
            custom_position = None

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
            size_folder = gv.FRAMES_LISTFILE.get(size_option)
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
        cache_key = (size_option, style_option, border_option)
        
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
        black_frame_size_folder = gv.FRAMES_LISTFILE.get(size_option)
        black_frame_section_folder = gv.FRAMES_LISTFILE.get(black_frame_section)
        black_frame_name = gv.FRAMES_LISTFILE.get(black_frame_option)
        black_frame_file = black_frame_name + gv.FRAMES_FILETYPE
        black_frame_path = os.path.join(get_data_subdir("frames"),black_frame_size_folder,black_frame_section_folder,black_frame_file)
        cache_key = (size_option,black_frame_section,black_frame_option)
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
            resized_image = Image.alpha_composite(resized_image,black_frame_image)

    # Combine the images:
    # The resized image is used as the base layer (first layer) and the frame image is composited on top.
    if frame_image:

        if custom_position or custom_size:
            if custom_position:
                new_position = custom_position
            else:
                new_position = (0,0)
            buffer_image = Image.new("RGBA",frame_size, (0, 0, 0, 0))
            buffer_image.paste(resized_image ,new_position,resized_image )
            buffer_image.paste(frame_image ,(0,0),frame_image )
            resized_image = buffer_image
        else:
            resized_image = Image.alpha_composite(resized_image,frame_image)

    if hd_dis_desaturation:
        # Create a Color enhancer object
        enhancer = ImageEnhance.Color(resized_image)
        # Decrease saturation by 50%
        resized_image = enhancer.enhance(0.5)
        # Create a contrast enhancer
        enhancer = ImageEnhance.Contrast(resized_image)
        # Decrease contrast by 10% (set factor to 0.9)
        resized_image = enhancer.enhance(0.9)

    if alpha:
        resized_image = remove_colors_of_alpha_pixels(resized_image)
    else:
        resized_image = clear_alpha(resized_image)

    return resized_image


def apply_format(input_image: Image.Image, format_option: str = "format_dds", format_suboption_dict: dict = {}):

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
            progressive=format_suboption_dict["blp_progressive"]
        else:
            progressive=False

        try:
            export_blp1_jpeg(input_image,buffer,quality = quality, num_mips = num_mips, progressive = progressive)
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