import argparse
import sys
import os
import vars.global_var as gv
import vars.var_for_init as iv
import src.config_manager as config_manager
import src.localisation as localisation
from src.generator import generate_images
from src.stored_var import CurrentSelection
from src.cli_logger import TerminalLogger
from src.custom_frames import init_CUSTOM_FRAMES_DICT_from_string
def parse_arguments():
    """
    Parses command-line arguments for CLI mode.
    """
    parser = argparse.ArgumentParser(description=f"{gv.PROGRAM_FULLNAME} - GUI & CLI Mode")
    
    parser.add_argument(
        "--cli", "--no-gui", 
        action="store_true", 
        help="Run the program in command-line mode instead of GUI."
    )

    parser.add_argument(
        "-i", "--image", 
        type=str, 
        help="Specify input image files (comma-separated). Example: -i image1.png,image2.jpg,image3.bmp"
    )

    parser.add_argument(
        "-d", "--directory", 
        type=str, 
        help="Specify one or more input directories containing images (comma-separated). Example: -d path/to/images"
    )

    parser.add_argument(
        "-c", "--config", 
        type=str, 
        help=("Specify a custom configuration file (e.g., 'user_config.cfg'). "
              "Only options present in this file will override the default settings. "
              "Any options not provided will be taken from the default configuration.")
    )

    # If sys.argv only contains the script name, return empty parsed arguments
    if len(sys.argv) == 1:
        return parser.parse_args([])

    return parser.parse_args()

def cli_mode(args):
    """
    Runs the program in command-line mode, processing images based on arguments.
    """
    if not args.image and not args.directory:
        print("Error: You must specify either an input image (-i) or an input directory (-d).")
        sys.exit(1)

    def_config_file_path = config_manager.DEFAULT_CFG
    user_config_file_path = args.config if args.config else def_config_file_path

    main_config=config_manager.init_configuration(def_config_file_path)
    user_config=config_manager.init_configuration(user_config_file_path)

    if not main_config and not user_config:
        print("Error: Unable to load the config file.")
        sys.exit(1)

    config_manager.apply_subconfig_on_configuration(user_config,main_config)

    print(f"Running in CLI mode. *Press CTRL+C to stop processing.")
    print(f"Using config: {user_config_file_path}")

    input_data=CurrentSelection(None)
    input_data.read_config_file(main_config)

    # load custom frames
    custom_frame_list = input_data.get_value("CUSTOM_SECTION","custom_frames")
    if custom_frame_list and custom_frame_list!=gv.DEFAULT_OPTION_PLACEHOLDER:
        init_CUSTOM_FRAMES_DICT_from_string(custom_frame_list)
        for key in iv.CUSTOM_FRAMES_DICT.keys():
            input_data.add_option(gv.OPTIONS_BORDER['section'],key,True)
    
    # load custom backgrounds
    from src.custom_backgrounds import init_CUSTOM_BACKGROUNDS_DICT
    init_CUSTOM_BACKGROUNDS_DICT()

    # Supported extensions
    extensions_raw = input_data.get_value("OPTIONS_INPUT","input_process_filetypes")
    extensions = set(extensions_raw.split(","))

    # load localisation
    language_code = input_data.get_value("LANG","program_lang")
    isatty = False
    if hasattr(sys,"stdout"): 
        if hasattr(sys.stdout,"isatty"):
            isatty = sys.stdout.isatty()
    if not(isatty):
        language_code="eng"
    localisation.update_localisation(language_code)

    valid_files=None
    valid_dirs=None
    # Process input files
    if args.image:
        input_paths = [file.strip() for file in args.image.split(",")]
        valid_files = [file for file in input_paths if os.path.splitext(file)[1][1:].lower() in extensions]
        excluded_files = [file for file in input_paths if file not in valid_files]
        
        if excluded_files:
            print(f"Warning: The following files have unsupported extensions and will be excluded: {', '.join(excluded_files)}")
        
    # Process input directory
    if args.directory:
        directories = [dir.strip() for dir in args.directory.split(",")]
        valid_dirs = [dir for dir in directories if os.path.isdir(dir)]

        excluded_dirs = [dir for dir in directories if dir not in valid_dirs]
        if excluded_dirs:
            print(f"Warning: The following directories are invalid and will be excluded: {', '.join(excluded_dirs)}")

    # Ensure at least one valid input source is provided
    if not valid_dirs  and not valid_files:
        print("Error: No valid input files or directories provided. Please specify at least one input source.")
        sys.exit(1)

    input_data.init_input_items(folders=valid_dirs,images=valid_files)

    generate_images(input_data,TerminalLogger())