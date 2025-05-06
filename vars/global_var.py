PROGRAM_NAME="Reforgerator"
PROGRAM_VERSION="1.1.5"
PROGRAM_AUTHOR="Makkad"
PROGRAM_FULLNAME=PROGRAM_NAME+" "+PROGRAM_VERSION+" by "+PROGRAM_AUTHOR
DIRS = {
    "localisations":"localisations",
    "profiles" :"profiles",
    "config" :"config",
    "credits":"credits",
    "frames": "frames",
    "custom_frames":"frames\\custom_frames",
    "output":"output",
    "external": "external",
}
FILE_DEF_CONFIG = "default.cfg"
FILE_USER_CONFIG = "user_config.cfg"
FRAMES_LISTFILE = {
    "size_64x64": "64x64",
    "size_128x128": "128x128",
    "size_256x256": "256x256",
    "style_sd": "Classic",
    "style_hd": "Reforged",
    "OPTIONS_EXTRAS": "Blackframe",
    "extras_blackframe": "Blackframe_big",
    "border_button": "BTN",
    "border_disabled": "DISBTN",
    "border_passive": "PAS",
    "border_passive_disabled": "DISPAS",
    "border_autocast": "ATC",
    "border_autocast_disabled": "DISATC",
    "border_none": "NONE",
    "format_dds" : "DDS",
    "format_blp" : "BLP",
    "format_tga" : "TGA",
    "format_png" : "PNG",
}
FRAMES_PREFIX = {
    "border_button": "BTN",
    "border_disabled": "DISBTN",
    "border_passive": "PAS",
    "border_passive_disabled": "DISPAS",
    "border_autocast": "ATC",
    "border_autocast_disabled": "DISATC",
    "border_none": "NONE",
}
DEFAULT_OPTION_PLACEHOLDER = "None"
FRAMES_FILETYPE =".png"
OPTIONS_BORDER = {
    "section": "OPTIONS_BORDER",  # Section name in the config file.
    "title": "border_title", # Section name in localisation.
    "options": [
        "border_button",
        "border_disabled",
        "border_passive",
        "border_passive_disabled",
        "border_autocast",
        "border_autocast_disabled",
        "border_none"
    ],
    "update_preview": True,
    "update_generate": True,
}
BORDER_HD_DESATURATION = [
        "border_disabled",
        "border_passive_disabled",
        "border_autocast_disabled",
]
OPTIONS_STYLE = {
    "section": "OPTIONS_STYLE",  # Section name in the config file.
    "title": "style_title", # Section name in localisation.
    "options": [
        "style_sd",
        "style_hd",
    ],
    "update_preview": True,
    "update_generate": True,
}
OPTIONS_EXTRAS = {
    "section": "OPTIONS_EXTRAS",  # Section name in the config file.
    "title": "extras_title", # Section name in localisation.
    "options": [
        "extras_alpha",
        "extras_blackframe",
        "extras_crop",
    ],
    "update_preview": True,
    "update_generate": False,
}
OPTIONS_FORMAT = {
    "section": "OPTIONS_FORMAT",  # Section name in the config file.
    "title": "format_title", # Section name in localisation.
    "options": [
        "format_dds",
        "format_blp",
        "format_tga",
        "format_png",
    ],
    "update_preview": True,
    "update_generate": True,
}
OPTIONS_SIZE = {
    "section": "OPTIONS_SIZE",  # Section name in the config file.
    "title": "size_title", # Section name in localisation.
    "options": [
        "size_64x64",
        "size_128x128",
        "size_256x256",
    ],
    "update_preview": True,
    "update_generate": True,
}
SIZE_MAPPING = {
    "size_64x64": (64, 64),
    "size_128x128": (128, 128),
    "size_256x256": (256, 256),
}
SIZE_PROPORTIONS = {
    "size_64x64": 1,
    "size_128x128": 2,
    "size_256x256": 4,
}
OPTIONS_INPUT = {
    "section": "OPTIONS_INPUT",  # Section name in the config file.
    "title": "input_title", # Section name in localisation.
    "options": [
        "input_process_subfolders",
        "input_process_filetypes",
    ],
    "update_preview": False,
    "update_generate": False,
}
OPTIONS_OUTPUT = {
    "section": "OPTIONS_OUTPUT",  # Section name in the config file.
    "title": "outputset_title", # Section name in localisation.
    "options": [
        "outputset_subfolders",
        "outputset_merged",
        "outputset_prefix",
    ],
    "update_preview": False,
    "update_generate": False,
}
DDS_SETTINGS = {
    "section": "DDS",  # Section name in the config file.
    "title": "", # Section name in localisation.
    "options" : [
        "dds_mipmap",
        "dds_type",
    ],
    "update_preview" : { 
        "dds_mipmap" : False,
        "dds_type" : True,
    },
    "update_generate": False,
}
BLP_SETTINGS = {
    "section": "BLP",  # Section name in the config file.
    "title": "", # Section name in localisation.   
    "options" : [
        "blp_mipmap",
        "blp_progressive",
        "blp_compression",
    ],
    "update_preview" : { 
        "blp_mipmap" : False,
        "blp_progressive" : False,
        "blp_compression" : True,
    },
    "update_generate": False,
}
TGA_SETTINGS = {
    "section": "TGA",  # Section name in the config file.
    "title": "", # Section name in localisation.
    "options" : [],
    "update_preview": True,
    "update_generate": False,
}
PNG_SETTINGS = {
    "section": "PNG",  # Section name in the config file.
    "title": "", # Section name in localisation.
    "options" : [],
    "update_preview": True,
    "update_generate": False,
}
OPTIONS_OUTPUT_PATH = {
    "section": "OPTIONS_OUTPUT_PATH",  # Section name in the config file.
    "options": [
        "output_basename",
        "output_folder",
    ],
}
HIDDEN_OPTIONS = []
NON_CHECKBOX_OPTIONS = ["blp_mipmap","blp_compression","dds_type","input_process_filetypes"]
CONFIG_SECTIONS = {
     "format_dds" : "DDS",
     "format_blp" : "BLP",
     "format_tga" : "TGA",
     "format_png" : "PNG",
}
DDS_COMPRESSION_TYPES=["DXT1","DXT3"]
DDS_MIPMAP_VALUES=["Auto","0","1","2","3","4","5","6","7","8"]
BLP_MINCOMPRESSION=0
BLP_MAXCOMPRESSION=100
BLP_SLIDERDELAY_MS=200
BLP_MIPMAP_VALUES=["Auto","0","1","2","3","4","5","6","7","8"]
INPUT_IMAGE_DEFAULT_TYPES = "png,jpg,jpeg,bmp,tga,dds,webp,blp,ico,psd"
INPUT_IMAGES_MAXNUM=4
OUTPUT_IMAGES_MAXNUM=4
OUTPUT_FILE_FORMATS={
     "format_dds" : ".dds",
     "format_blp" : ".blp",
     "format_tga" : ".tga",
     "format_png" : ".png",
}
OUTPUT_FOLDER_DEFAULT="outputs"
REMOVE_COLORS_THRESHOLD = 1