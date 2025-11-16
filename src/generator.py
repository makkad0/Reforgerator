import os
import re
from typing import Any, Optional
import vars.global_var as gv
import vars.var_for_init as iv
from src.converter import load_pil_image
from src.converter import apply_frame
from src.converter import apply_format
from src.converter import save_buffer_to_file
from src.localisation import get_local_text
from src.stored_var import CurrentSelection  
from src.log import LogOutputStream
from src.system import get_data_subdir

def is_valid_filename(filename):
    """
    Checks if the given filename is valid across Windows, Mac and Linux.
    Allowed characters are alphanumeric, underscore, hyphen, period and space.
    """
    return re.match(r'^[\w\-. ]+$', filename) is not None

def merge_prefix(basename, prefix):
    """
    Merges the given prefix with basename by removing duplicate parts.
    
    It finds the longest suffix of `prefix` that is a prefix of `basename` 
    and then returns prefix + (basename with that overlapping part removed).
    
    Example 1:
      prefix = "DISBTN", basename = "BTNButton"  --> returns "DISBTNButton"
    Example 2:
      prefix = "BTN", basename = "BTNBTNButton"  --> returns "BTNBTNButton"
    """
    max_overlap = ""
    for i in range(1, len(prefix) + 1):
        suffix = prefix[-i:]
        if basename.startswith(suffix) and len(suffix) > len(max_overlap):
            max_overlap = suffix
    return prefix + basename[len(max_overlap):]

def get_output_path(path, output_folder, size_option, style_option, border_option, format_option):
    """
    Constructs an output file path based on the original image path and options.
    """
    base , ext = os.path.splitext(os.path.basename(path))
    ext = gv.OUTPUT_FILE_FORMATS[format_option]
    new_filename =  f"{base}_{size_option}_{style_option}_{border_option}{ext}"
    output_path =  os.path.join(output_folder,new_filename)

    return output_path


def set_output_folder(output_suboption_dict: dict = {}, create_new_folder: bool = True ) -> str:
    """
    Sets and validates the output folder.
    - If output_suboption_dict.get("output_folder") is a relative path and
      gv.OUTPUT_FOLDER_BASE is defined (non-empty), it is joined with gv.OUTPUT_FOLDER_BASE.
    - If gv.OUTPUT_FOLDER_BASE is None or empty, then the provided folder (relative)
      is used as is.
    - If the provided folder is absolute, it is used as is.
    - Expects a non-empty 'output_folder' value in output_suboption_dict.
    - Raises an error if the 'output_folder' is empty, only spaces, or if the folder creation fails.
    Parameters:
        output_suboption_dict (dict): Dictionary containing the 'output_folder' key.
    Returns:
        str: The validated output folder path.
    """
    base = get_data_subdir("output")
    output_folder = output_suboption_dict.get("output_folder")
    if not(output_folder.strip()):
        output_folder = base

    if not output_folder:
        raise ValueError("No valid output folder provided.")
    
    # If the output folder is relative and a base is defined, join them.
    if not os.path.isabs(output_folder):   
        if base and base.strip():
            output_folder = os.path.join(base, output_folder)

    if create_new_folder:
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                raise RuntimeError(f"Failed to create output folder '{output_folder}': {e}")
    return output_folder

def build_output_path(original_path, output_folder, 
                      size_option, style_option, border_option, format_option, 
                      output_suboption_dict,
                      true_style_options, true_format_options, true_border_options, used_output_paths,
                      relative_subfolder=""):
    """
    Constructs the output file path with the following behavior:
    
    1. If "outputset_basename" is provided in output_suboption_dict (and is valid),
       it replaces the input file's basename; otherwise, the basename is extracted
       from the original file.
    
    2. If gv.FRAMES_LISTFILE contains a prefix for border_option, that prefix is
       merged into the basename (to avoid duplicate parts).
    
    3. The extension is determined from gv.OUTPUT_FILE_FORMATS.
    
    4. If output_suboption_dict["outputset_subfolders"] is True, then a subfolder
       structure is created under output_folder using the options:
         - A folder for size_option,
         - Under it, a folder for style_option,
         - Under that, a folder for format_option.
       Folder names are taken from gv.FRAMES_LISTFILE (if available). Moreover, if
       output_suboption_dict["outputset_merged"] is True, then parent and child folder
       names are merged (using an underscore) when there is only one child option.
    
    5. Before returning the final file path, if a file with that name already exists 
       (was already created during this run), a suffix _N is added
       (with N starting at 1) to the basename until a unique file name is found.
    
    Returns the unique output file path.
    """
    def merge_dicts_ignore_conflicts(dict1, dict2):
        return {**dict1, **{k: v for k, v in dict2.items() if k not in dict1}}

    EXTENDED_LISTFILE = merge_dicts_ignore_conflicts (gv.FRAMES_LISTFILE,iv.CUSTOM_FRAME_PREFIXES)

    # 1. Determine the base filename.
    custom_basename = output_suboption_dict.get("output_basename")
    if custom_basename and custom_basename.strip() and is_valid_filename(custom_basename.strip()):
        basename = custom_basename.strip()
    else:
        basename = os.path.splitext(os.path.basename(original_path))[0]
    
    # 2. Merge border prefix if available.
    use_prefix = output_suboption_dict.get("outputset_prefix", True)
    if use_prefix:
        prefix = None
        if border_option in EXTENDED_LISTFILE:
            prefix = EXTENDED_LISTFILE.get(border_option)
        if prefix:
            basename = merge_prefix(basename, prefix)

    
    # 3. Determine file extension.
    extension = gv.OUTPUT_FILE_FORMATS.get(format_option, "")
    
    # 4. Build subfolder structure if enabled.
    if output_suboption_dict.get("outputset_subfolders", True):
        merge_enabled = output_suboption_dict.get("outputset_merged",True)
        # Create a list of folder items in the order they should appear.
        folder_items = [
            {"option": size_option, "count": 1},  # Always add size folder.
            {"option": style_option, "count": len(true_style_options)},
            {"option": format_option, "count": len(true_format_options)}
        ]
        if not use_prefix:
            folder_items.append({"option": border_option, "count": len(true_border_options)})
        
        folders = []
        for item in folder_items:
            # Get the folder name from EXTENDED_LISTFILE if available.
            folder_name = EXTENDED_LISTFILE.get(item["option"], item["option"])
            if merge_enabled and item["count"] == 1 and folders:
                # Merge with the previous folder.
                folders[-1] = folders[-1] + "_" + folder_name
            else:
                folders.append(folder_name)
        final_folder = os.path.join(output_folder, *folders)
        if not os.path.exists(final_folder):
            os.makedirs(final_folder)
    else:
        final_folder = output_folder
    
    # Append the relative subfolder (replicating input folder structure) if provided.
    if relative_subfolder:
        final_folder = os.path.join(final_folder, relative_subfolder)
        if not os.path.exists(final_folder):
            os.makedirs(final_folder)
    else:
        if not os.path.exists(final_folder):
            os.makedirs(final_folder)
    
    # 5. Construct the file path and ensure uniqueness.
    file_path = os.path.join(final_folder, basename + extension)
    unique_path = file_path
    n = 1
    while unique_path in used_output_paths:
        unique_path = os.path.join(final_folder, f"{basename}_{n}{extension}")
        n += 1
    used_output_paths.add(unique_path)
    return unique_path

# --- Main generator function ---
def generate_images(input_data:CurrentSelection = {}, info_stream: Optional[Any] = None):
    """
    Generates images by applying frame and format transformations on each image
    from input_data.paths. The processing iterates over all true option variations.

    This function works in two regimes:
      - Command line: prints status messages to the console.
      - GUI: updates the progress bar, status labels, and logs messages via the
             functions provided in gui_generate_output.py.
    """
    log=LogOutputStream(info_stream)

    #Gather actual data
    input_data.gather_paths()
    file_items=input_data.paths_rel
    if not(file_items):
        log.msg("output_no_image_warning")
        return

    # Retrieve the true-valued options and format suboptions.
    true_size_options, true_style_options, true_border_options, true_format_options = input_data.recieve_true_variations()
    format_suboption_dict = input_data.recieve_suboptions([gv.DDS_SETTINGS, gv.BLP_SETTINGS,gv.TGA_SETTINGS])
    output_suboption_dict = input_data.recieve_suboptions([gv.OPTIONS_OUTPUT,gv.OPTIONS_OUTPUT_PATH,gv.OPTIONS_BASENAME])
    extras_suboption_dict = input_data.recieve_suboptions([gv.OPTIONS_EXTRAS])
    misc_suboption_dict   = input_data.recieve_suboptions([gv.OPTIONS_MISC, gv.OPTIONS_CUSTOM_SIZE])
    # Get custom background option
    custom_background_name = input_data.get_value("CUSTOM_SECTION", "custom_background")
    if custom_background_name is None:
        custom_background_name = "None"
    # Check if output should be in the same directory as input files
    output_samedir = output_suboption_dict.get("outputset_samedir", False)
    
    # Try to set and validate the output folder. Process any errors accordingly.
    # Only set output_folder if outputset_samedir is disabled (will be set per-file if enabled)
    if not output_samedir:
        try:
            output_folder = set_output_folder(output_suboption_dict)
        except Exception as e:
            log.msg("output_folder_error",e)
            return
    else:
        output_folder = None  # Will be set per-file when outputset_samedir is enabled

    num_input_images = len(file_items)
    num_total_images = num_input_images * input_data.calculate_number_of_variations()
    if num_input_images>1:
        output_suboption_dict['output_basename']=None

    #if gui_mode:
    #    gui_log.GaugeInit(num_total_images)
    current_count = 0
    used_output_paths = set()  # Track generated file paths to avoid duplicates.
    
    # Check if background was requested but not found (warning only once per generation)
    if custom_background_name and custom_background_name != "None":
        from src.custom_backgrounds import get_background_path
        bg_path = get_background_path(custom_background_name)
        if not bg_path or not os.path.exists(bg_path):
            log.msg("custom_background_not_found", custom_background_name)

    # Iterate over each image path.
    for (path, rel_path) in file_items:
        input_basename = os.path.basename(path)
        
        # If outputset_samedir is enabled, use the input file's directory as output folder
        # This works correctly for both:
        # - Files selected directly (paths_images): output goes to the file's directory
        # - Files from folders (paths_folders): output goes to each file's directory (which may be a subfolder)
        # - Mixed inputs: each file outputs to its own directory, regardless of source
        if output_samedir:
            file_output_folder = os.path.dirname(path)
            # Don't use relative_subfolder when output is in same directory as input
            file_relative_subfolder = ""
        else:
            file_output_folder = output_folder
            file_relative_subfolder = rel_path
        
        # Iterate over all combinations of true options for frame transformation.
        for size_option in true_size_options:
            for style_option in true_style_options:
                for border_option in true_border_options:
                    try:
                        # Load the image.
                        image = load_pil_image(path)
                        # Apply the frame transformation with custom background
                        image = apply_frame(image, size_option, style_option, border_option, extras_suboption_dict, misc_suboption_dict, custom_background_name)
                        # For each available format option, apply further processing.
                        for format_option in true_format_options:
                            try:
                                output_path = build_output_path(
                                    original_path=path,
                                    output_folder=file_output_folder,
                                    size_option=size_option,
                                    style_option=style_option,
                                    border_option=border_option,
                                    format_option=format_option,
                                    output_suboption_dict=output_suboption_dict,
                                    true_style_options=true_style_options,
                                    true_format_options=true_format_options,
                                    true_border_options=true_border_options,
                                    used_output_paths=used_output_paths,
                                    relative_subfolder=file_relative_subfolder
                                )
                                final_buffer = apply_format(image, format_option, format_suboption_dict)
                                # Save the final image to the computed output path.
                                save_buffer_to_file(final_buffer,output_path)
                                current_count += 1
                                log.update_live_log(log_key="output_generate_images_update",
                                                    message=input_basename,
                                                    current=current_count,
                                                    total=num_total_images,                
                                )
                            except Exception as fe:
                                log.clear_pos()
                                log.msg("output_processing_format_error",input_basename,format_option,fe)
                                return
                            except KeyboardInterrupt:
                                input_data.stop_requested = True
                    except Exception as e:
                        log.clear_pos()
                        log.msg("output_processing_option_error",input_basename,size_option,style_option,border_option,e)
                        return
                    except KeyboardInterrupt:
                        input_data.stop_requested = True

                    # Check if the GUI has signaled a stop (e.g., via the stop button).
                    if input_data.stop_requested:
                        log.update_live_log(log_key="output_generate_images_abort_by_user",
                                            message="",
                                            current=current_count,
                                            total=num_total_images,                
                        )
                        log.clear_pos()
                        return

    # Finalize the GUI (re-enable buttons, etc.) if applicable.
    if num_input_images==1:
        message=get_local_text("log_file_str").format(os.path.basename(file_items[0][0]))
    else:
        message= get_local_text("log_files_str").format(str(num_input_images))
    log.update_live_log(log_key="output_generate_images_success",
                        message=message,
                        current=current_count,
                        total=num_total_images,                
    )
    log.clear_pos()

    # Finalize the CLI
    if hasattr(info_stream,"is_cli"):
        if output_samedir:
            print("Processing completed. Output files saved in the same directories as input files.")
        else:
            print(f"Processing completed. Output folder: {output_folder}")