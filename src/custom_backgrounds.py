import os
import vars.var_for_init as iv
import vars.global_var as gv
from src.system import get_data_subdir
from PIL import Image

# Global cache for loaded background images
BACKGROUND_CACHE = {}

def scan_custom_backgrounds():
    """
    Scans the custom_backgrounds folder and returns a dictionary of available backgrounds.
    Returns a dict mapping filename (with extension) to full file path.
    """
    backgrounds = {}
    # Use DIRS from global_var for the path
    # get_data_subdir("custom_backgrounds") will use DIRS["custom_backgrounds"] which is "frames\\custom_backgrounds"
    backgrounds_dir = get_data_subdir("custom_backgrounds")
    
    if not os.path.isdir(backgrounds_dir):
        return backgrounds
    
    # Get supported extensions from INPUT_IMAGE_DEFAULT_TYPES
    supported_extensions = set()
    if gv.INPUT_IMAGE_DEFAULT_TYPES:
        for ext in gv.INPUT_IMAGE_DEFAULT_TYPES.split(","):
            ext = ext.strip().lower()
            if ext:
                supported_extensions.add("." + ext)
    
    try:
        for filename in os.listdir(backgrounds_dir):
            filepath = os.path.join(backgrounds_dir, filename)
            if os.path.isfile(filepath):
                name, ext = os.path.splitext(filename)
                if ext.lower() in supported_extensions:
                    # Store with full filename (including extension) as key
                    backgrounds[filename] = filepath
    except Exception:
        pass  # Return empty dict if scanning fails
    
    return backgrounds

def init_CUSTOM_BACKGROUNDS_DICT(dict: dict = None):
    """Initialize the global CUSTOM_BACKGROUNDS_DICT."""
    if dict:
        iv.CUSTOM_BACKGROUNDS_DICT = dict
    else:
        iv.CUSTOM_BACKGROUNDS_DICT = scan_custom_backgrounds()

def get_background_path(background_name: str):
    """Get the full path to a background image by name (with or without extension)."""
    if not background_name or background_name == "None":
        return None
    # Try exact match first (with extension)
    if background_name in iv.CUSTOM_BACKGROUNDS_DICT:
        return iv.CUSTOM_BACKGROUNDS_DICT[background_name]
    # Try without extension (for backward compatibility)
    name_without_ext = os.path.splitext(background_name)[0]
    for filename, filepath in iv.CUSTOM_BACKGROUNDS_DICT.items():
        if os.path.splitext(filename)[0] == name_without_ext:
            return filepath
    return None

def load_background_image(background_name: str, target_size: tuple):
    """
    Load and cache a background image, resizing it to target_size.
    Returns the PIL Image or None if not found.
    """
    if not background_name or background_name == "None":
        return None
    
    # Check cache first (cache key includes name and size)
    cache_key = (background_name, target_size)
    if cache_key in BACKGROUND_CACHE:
        return BACKGROUND_CACHE[cache_key]
    
    # Get the background path
    bg_path = get_background_path(background_name)
    if not bg_path or not os.path.exists(bg_path):
        return None
    
    try:
        bg_image = Image.open(bg_path).convert("RGBA")
        # Resize to target size
        if bg_image.size != target_size:
            bg_image = bg_image.resize(target_size, Image.LANCZOS)
        # Cache it
        BACKGROUND_CACHE[cache_key] = bg_image
        return bg_image
    except Exception:
        return None

def clear_background_cache():
    """Clear the background image cache."""
    BACKGROUND_CACHE.clear()

