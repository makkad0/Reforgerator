import os
import configparser
import vars.global_var as gv
import vars.var_for_init as iv
from PIL import Image
from src.system import get_data_subdir

OPTION_START_WORD = "section"


def init_CUSTOM_FRAMES_DICT(dict: dict = None):
    # Ensure we're modifying the global variable
    if dict:
        iv.CUSTOM_FRAMES_DICT = dict
    else:
        iv.CUSTOM_FRAMES_DICT = parse_all_ini()
    for frame in iv.CUSTOM_FRAMES_DICT.values():
        frame_id = frame.get("id")
        frame_prefix = frame.get("prefix")
        if frame_id is not None and frame_prefix is not None:
            iv.CUSTOM_FRAME_PREFIXES[frame_id] = frame_prefix

def init_CUSTOM_FRAMES_DICT_from_string(file_string):
    init_CUSTOM_FRAMES_DICT(parse_ini_files_from_string(file_string))

def get_custom_frame_section(id,style,size):
    return iv.CUSTOM_FRAMES_DICT.get(id).get(get_option_key(style,size))

def get_option_key(style_val,size_val):
    return f'{OPTION_START_WORD}_{style_val}_{size_val}'

def parse_ini_file(filepath):
    """
    Parse and validate a single .ini file.
    Returns a dictionary with keys:
      - file, id, name, prefix, main_folder (optional)
      - section_style_size  ... for additional sections
    If the file does not meet the requirements, returns None.
    """
    config = configparser.ConfigParser()
    # Make option names case-insensitive.
    config.optionxform = str.lower  
    try:
        config.read(filepath)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

    sections = config.sections()
    if not sections:
        #print(f"File '{filepath}' does not contain any sections.")
        return None

    # The first section is taken as the main section.
    main_section = config[sections[0]]
    id_value = main_section.get("id", "").strip()
    name_value = main_section.get("name", "").strip()
    prefix_value = main_section.get("prefix", "").strip()
    if not id_value or not name_value or not prefix_value:
        #print(f"File '{filepath}' is missing one of the required keys in the main section (id, name, prefix).")
        return None
    
    # extension is optional.
    extension_value = main_section.get("extension", "").strip() or gv.FRAMES_FILETYPE
    # main_folder is optional.
    main_folder_value = main_section.get("main_folder", "").strip()

    result = {
        "file": os.path.basename(filepath),
        "id": id_value,
        "name": name_value,
        "prefix": prefix_value,
        "extension_value": extension_value,
        "main_folder": main_folder_value,
    }

    # Validate additional sections.
    valid_sizes = gv.OPTIONS_SIZE["options"]
    valid_styles = gv.OPTIONS_STYLE["options"]

    option_index = 1
    seen_combinations = set()  # To ignore duplicate size-style combinations.
    # Iterate through the remaining sections.
    for section in sections[1:]:
        sec = config[section]
        size_val = sec.get("size", "").strip()
        style_val = sec.get("style", "").strip()
        # Optional keys.
        path_val = sec.get("path", "").strip() or None
        if not size_val or not style_val:
            continue  # Skip sections missing required keys.
        if size_val not in valid_sizes or style_val not in valid_styles:
            continue  # Skip sections with invalid size or style.
        combination = (size_val, style_val)
        if combination in seen_combinations:
            continue  # Skip duplicate valid sections.
        seen_combinations.add(combination)

        im_pos_val = sec.get("im_pos", "").strip() or None
        if im_pos_val:
            try:
                im_pos_tuple = tuple(map(int, im_pos_val.split(",")))
            except Exception:
                im_pos_tuple = None
        else:
            im_pos_tuple = None
        im_size_val = sec.get("im_size", "").strip() or None
        if im_size_val:
            try:
                im_size_tuple = tuple(map(int, im_size_val.split(",")))
            except Exception:
                im_size_tuple = None
        else:
            im_size_tuple = None

        im_size_tuple, im_pos_tuple  = get_vaildated_size_pos(im_size_tuple,im_pos_tuple,gv.SIZE_MAPPING[size_val])

        option_dict = {
            "size": size_val,
            "style": style_val,
            "path": path_val,
            "im_pos": im_pos_tuple,
            "im_size": im_size_tuple,   
        }
        result[get_option_key(style_val,size_val)] = option_dict
        option_index += 1

    return result

def get_vaildated_size_pos(im_size, im_pos, size_val):
    """
    Validate im_size and im_pos against the provided size_val.
    
    Parameters:
    im_size: Either None or a tuple (x, y) representing the image size.
    im_pos:  Either None or a tuple (x, y) representing the image position.
    size_val: A tuple (width, height) representing the maximum allowed size.
    
    Validation steps:
    1) If im_size (or im_pos) is not None:
        - It must be a tuple of length 2.
        - Both elements must be integers and >= 0.
        - The first element must be <= size_val[0] and the second <= size_val[1].
    2) Additionally, for im_size, each element must be > 0.
    3) If both im_size and im_pos are provided, check that:
            im_size[0] + im_pos[0] < size_val[0] and
            im_size[1] + im_pos[1] < size_val[1].
        If this fails, set im_pos to None.
    
    Returns:
    A tuple (validated_im_size, validated_im_pos), where each is either a valid tuple or None.
    """
    # Validate im_size.
    if im_size is not None:
        if not (isinstance(im_size, tuple) and len(im_size) == 2):
            im_size = None
        else:
            x, y = im_size
            if not (isinstance(x, int) and isinstance(y, int)):
                im_size = None
            elif x <= 0 or y <= 0:
                im_size = None
            elif x > size_val[0] or y > size_val[1]:
                im_size = None

    # Validate im_pos.
    if im_pos is not None:
        if not (isinstance(im_pos, tuple) and len(im_pos) == 2):
            im_pos = None
        else:
            x, y = im_pos
            if not (isinstance(x, int) and isinstance(y, int)):
                im_pos = None
            elif x < 0 or y < 0:
                im_pos = None
            elif x >= size_val[0] or y >= size_val[1]:
                im_pos = None

    # If both are provided, ensure that the combined dimensions do not exceed size_val.
    if im_size is not None and im_pos is not None:
        if (im_size[0] + im_pos[0] > size_val[0]) or (im_size[1] + im_pos[1] > size_val[1]):
            im_pos = None

    return im_size, im_pos


def is_valid_dict_key(key):
    """Check if a string can be used as a dictionary key."""
    try:
        _ = {key: "value"}  # Attempt to use it as a key
        return True
    except Exception:
        return False

def get_unique_id(current_id, used_ids):
    """
    Check if the current_id is either already used or is in gv.OPTIONS_BORDER.
    If so, append _n (n=1,2,...) until a unique id is found.
    """
    if not is_valid_dict_key(current_id):
        current_id = "custom_border"

    unique_id = current_id
    n = 1
    while unique_id in used_ids or unique_id in gv.OPTIONS_BORDER:
        unique_id = f"{current_id}_{n}"
        n += 1
    return unique_id

def repair_ini_file(parsed):
    """
    Given a parsed ini file dictionary, repair it by:
      1) Ensuring that all combinations (style, size) exist in the additional sections.
      2) For each additional section with path=None, set path = os.path.join(main_folder, gv.FRAMES_LISTFILE[size],
         gv.FRAMES_LISTFILE[style], prefix+extension_value).
      3) For additional sections with im_pos or im_size missing, search for a reference value from other sections
         and scale it according to gv.SIZE_PROPORTIONS. If no candidate is found, default to (0,0).
    Returns the repaired dictionary.
    """
    main_folder = parsed.get("main_folder")
    prefix = parsed.get("prefix")
    extension_value = parsed.get("extension_value")
    
    # Build a temporary dict for additional sections keyed by (style, size)
    options_dict = {}
    for key, value in list(parsed.items()):
        if key.startswith(OPTION_START_WORD):
            style = value.get("style")
            size = value.get("size")
            if style and size:
                options_dict[(style, size)] = value

    # Ensure every combination of style and size exists.
    for style in gv.OPTIONS_STYLE["options"]:
        for size in gv.OPTIONS_SIZE["options"]:
            if (style, size) not in options_dict:
                options_dict[(style, size)] = {
                    "size": size,
                    "style": style,
                    "path": None,
                    "im_pos": None,
                    "im_size": None
                }
    
    # Rule 2: Repair missing path if main_folder is provided.
    for (style, size), option in options_dict.items():
        path = option.get("path")
        if path is None:
            path = os.path.join(gv.FRAMES_LISTFILE[size],
                    gv.FRAMES_LISTFILE[style],
                    prefix + extension_value)
            if main_folder:
                path = os.path.join(main_folder,path)
            option["path"] = path
        elif (not os.path.isabs(path)) and main_folder:
            path = os.path.join(main_folder,path)
            option["path"] = path

    # Helper function to repair im_pos or im_size fields.
    def repair_field(field, style, size, default):
        current_prop = gv.SIZE_PROPORTIONS[size]
        # First, search for candidate in the same style (different size), ordered from bigger to smallest.
        candidates = []
        for other_size in gv.OPTIONS_SIZE["options"]:
            if other_size == size:
                continue
            candidate = options_dict[(style, other_size)].get(field)
            if candidate is not None:
                candidates.append((other_size, candidate))
        if candidates:
            candidates.sort(key=lambda x: gv.SIZE_PROPORTIONS[x[0]], reverse=True)
            ref_size, ref_val = candidates[0]
            ref_prop = gv.SIZE_PROPORTIONS[ref_size]
            scale = current_prop / ref_prop
            return (round(ref_val[0] * scale), round(ref_val[1] * scale))
        # Next, search for candidate with the same size but different style.
        for other_style in gv.OPTIONS_STYLE["options"]:
            if other_style == style:
                continue
            candidate = options_dict[(other_style, size)].get(field)
            if candidate is not None:
                return candidate  # Same size, so no scaling needed.
        # Finally, search any candidate from any combination.
        candidates = []
        for (s, sz), sec in options_dict.items():
            if sec.get(field) is not None:
                candidates.append((sz, sec.get(field)))
        if candidates:
            candidates.sort(key=lambda x: gv.SIZE_PROPORTIONS[x[0]], reverse=True)
            ref_size, ref_val = candidates[0]
            ref_prop = gv.SIZE_PROPORTIONS[ref_size]
            return (round(ref_val[0] * (current_prop / ref_prop)), round(ref_val[1] * (current_prop / ref_prop)))
        # If no candidate is found, default to (0,0).
        return default #(0, 0)
    
    # Sort keys so that sections with bigger sizes are repaired first.
    sorted_keys = sorted(options_dict.keys(), key=lambda key: gv.SIZE_PROPORTIONS[key[1]], reverse=True)
    for key in sorted_keys:
        style, size = key
        option = options_dict[key]
        if option.get("im_pos") is None:
            option["im_pos"] = repair_field("im_pos", style, size, (0,0))
        if option.get("im_size") is None:
            option["im_size"] = repair_field("im_size", style, size, gv.SIZE_MAPPING.get(size))
    
    # Remove old option keys from parsed and add repaired ones in a consistent order.
    keys_to_remove = [key for key in parsed if key.startswith(OPTION_START_WORD)]
    for key in keys_to_remove:
        del parsed[key]
    
    # Order the options as per the order in gv.OPTIONS_STYLE then gv.OPTIONS_SIZE.
    for style in gv.OPTIONS_STYLE["options"]:
        for size in gv.OPTIONS_SIZE["options"]:
            parsed[get_option_key(style,size)] = options_dict[(style, size)]

    return parsed

def validate_additional_section_paths(repaired_dict):
    """
    For each additional section in the repaired dict, check if the option["path"]
    is loadable by Pillow. Valid paths are collected. For non-valid paths, repair them 
    using the following order:
      1) Use the path of the biggest valid size for the same style.
      2) If none available for the same style, use a valid path from another style but same size.
      3) If still none, use the biggest valid path available overall.
    If no valid paths are found at all, return the dict as is.
    
    The function also returns a list of valid paths.
    """
    valid_global = []  # list of tuples (style, size, path, proportion)
    valid_by_style = {}  # style -> list of tuples (size, path, proportion)
    valid_by_size = {}   # size -> list of tuples (style, path, proportion)
    
    # Use a list to store (path, is_valid) for each processed path.
    processed_paths = []  # list of tuples (path, is_valid)

    # Iterate through every additional section (using our known keys)
    count = 0
    for style in gv.OPTIONS_STYLE["options"]:
        for size in gv.OPTIONS_SIZE["options"]:
            count += 1
            key = get_option_key(style, size)
            option = repaired_dict.get(key)
            if option is None:
                continue
            path = option.get("path")
            # Check if path is loadable using Pillow
            is_valid = False
            if path:
                found = False
                for (proc_path, validity) in processed_paths:
                    if proc_path == path:
                        is_valid = validity
                        found = True
                        break
                if not found:      
                    try:
                        if not(os.path.isabs(path)):
                            frame_path = os.path.join(get_data_subdir("custom_frames"),path)
                        with Image.open(frame_path) as im:
                            im.verify()
                        is_valid = True
                    except Exception:
                        is_valid = False
                    processed_paths.append((path, is_valid))
            # Mark validity in the option for later reference.
            option["_path_valid"] = is_valid
            if is_valid:
                prop = gv.SIZE_PROPORTIONS.get(size, 1)
                valid_global.append((style, size, path, prop))
                valid_by_style.setdefault(style, []).append((size, path, prop))
                valid_by_size.setdefault(size, []).append((style, path, prop))
    
    # If no valid paths at all, simply return the dict.
    if (not valid_global) or len(valid_global)==count:
        return repaired_dict
    
    # For each additional section that has an invalid path, try to repair it.
    for style in gv.OPTIONS_STYLE["options"]:
        for size in gv.OPTIONS_SIZE["options"]:
            key = get_option_key(style, size)
            option = repaired_dict.get(key)
            if option is None:
                continue
            if option.get("_path_valid"):
                continue  # already valid
            new_path = None
            # 1) Try to get a valid path from the same style.
            if style in valid_by_style and valid_by_style[style]:
                # Choose candidate with the highest proportion (biggest size)
                candidate = max(valid_by_style[style], key=lambda tup: tup[2])
                new_path = candidate[1]
            # 2) If not found, try valid path from same size.
            if new_path is None and size in valid_by_size and valid_by_size[size]:
                candidate = max(valid_by_size[size], key=lambda tup: tup[2])
                new_path = candidate[1]
            # 3) Else, choose the biggest valid available overall.
            if new_path is None:
                candidate = max(valid_global, key=lambda tup: tup[3])
                new_path = candidate[2]
            # If a replacement is found, update the path and mark as valid.
            if new_path:
                option["path"] = new_path
                option["_path_valid"] = True
    
    return repaired_dict




# ----- New Methods for File Listing and Parsing from a String -----
def parse_all_ini():
    return parse_ini_files_from_string(get_ini_files_string())

def get_ini_files_string():
    """
    Returns a comma-separated string of all .ini files in gv.DIRS["custom_frames"].
    For example: "test1.ini,test2.ini"
    """
    directory =  get_data_subdir("custom_frames")  
    files = [f for f in os.listdir(directory) if f.lower().endswith(".ini")]
    return ",".join(files)

def parse_ini_files_from_string(files_string):
    """
    Given a comma-separated string of filenames (e.g., "test1.ini,test2.ini"),
    parse each file found in gv.DIRS["custom_frames"] and return the results dictionary.
    """
    directory = get_data_subdir("custom_frames")
    results = {}
    used_ids = set()
    # Split the input string into individual file names.
    file_list = [fname.strip() for fname in files_string.split(",") if fname.strip()]
    for filename in file_list:
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            parsed = parse_ini_file(filepath)
            if parsed:
                parsed = repair_ini_file(parsed)
                parsed = validate_additional_section_paths(parsed)
                current_id = parsed["id"]
                unique_id = get_unique_id(current_id, used_ids)
                parsed["id"] = unique_id
                used_ids.add(unique_id)
                results[unique_id] = parsed
    return results

def store_custom_frame_as_option(input_data,custom_frame_id_list,remove:bool = False):
    section = gv.OPTIONS_BORDER['section']
    for frame_id in custom_frame_id_list:
        if remove:
            input_data.remove_option(section,frame_id)
        else:
            input_data.add_option(section,frame_id,True)