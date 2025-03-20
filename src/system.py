import sys
import os
import __main__
from pathlib import Path
import appdirs
import vars.global_var as gv

def get_exe_dir():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.join(os.path.dirname(__main__.__file__),"data")
    return exe_dir

def get_data_subdir(data_subdir:str=None):
    if data_subdir:
        if data_subdir in gv.DIRS:
            return os.path.join(get_exe_dir(),gv.DIRS[data_subdir])
    return get_exe_dir() 

def get_special_config_dir(app_name=gv.PROGRAM_NAME):
    """
    Returns an OS-appropriate directory for storing user config.
    - Windows: %APPDATA%/MyApp
    - Linux: ~/.config/MyApp
    - macOS: ~/Library/Application Support/MyApp
    """
    try:
        import appdirs
        config_dir = appdirs.user_config_dir(app_name)
    except ImportError:
        # Fallback: place it in user's home or a subfolder
        home_dir = str(Path.home())
        config_dir = os.path.join(home_dir, f".{app_name}")
    
    os.makedirs(config_dir, exist_ok=True)  # Make sure it exists
    return config_dir