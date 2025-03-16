import configparser
import os
from pathlib import Path
import var.global_var as gv
from src.system import get_data_subdir,get_special_config_dir


################################
# GLOBAL VARIABLES
################################
USER_CFG_BASE_EXIST = False
USER_CFG_SPECIAL_EXIST = False

USER_CFG_BASE_ACCESS = False
USER_CFG_SPECIAL_ACCESS = False

################################
# PATH CONSTANTS
################################
BASE_CONFIG_DIR   = get_data_subdir("config")
DEFAULT_CFG  = os.path.join(BASE_CONFIG_DIR, gv.FILE_DEF_CONFIG)
USER_CFG_BASE     = os.path.join(BASE_CONFIG_DIR, gv.FILE_USER_CONFIG)

SPECIAL_DIR       = get_special_config_dir()
USER_CFG_SPECIAL  = os.path.join(SPECIAL_DIR, gv.FILE_USER_CONFIG)

PROFILE_DIR   = get_data_subdir("profiles")

################################
# CONFIG FUNCTIONS
################################

def check_user_cfg_base_access(USER_CFG_FILE):
    """
    Checks if we can access (read/write) user_config.cfg at base_dir/config/.
    Steps:
      1) Ensure config directory can be created.
      2) If user_config.cfg exists, test opening it for read+write.
      3) If user_config.cfg doesn't exist, attempt to create a small test file, then remove it.
    Returns:
      True if the base location is writable/readable, False otherwise.
    """
    config_dir = os.path.dirname(USER_CFG_FILE)
    try:
        # Step 1: Make sure directory can be created
        Path(config_dir).mkdir(parents=True, exist_ok=True)

        if os.path.exists(USER_CFG_FILE):
            # Step 2: If file exists, try opening it for append or write
            with open(USER_CFG_FILE, 'a', encoding='utf-8'):
                pass
        else:
            # Step 3: If not exists, try creating a small test file
            test_file = os.path.join(config_dir, "test_write_permission.tmp")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("test")
            os.remove(test_file)
        return True

    except (OSError, PermissionError):
        return False


def init_configuration_from_OS():
    """
    1) Try loading user_config.cfg from base_dir. If it exists, read it.
       If it doesn't exist, try to create from fallback or default.
    2) If base_dir fails (permissions, etc.), fallback to special path.
    3) If that also fails, load default in-memory only (read-only).
    """
    global USER_CFG_BASE_EXIST, USER_CFG_SPECIAL_EXIST, USER_CFG_BASE_ACCESS, USER_CFG_SPECIAL_ACCESS

    USER_CFG_BASE_EXIST = os.path.exists(USER_CFG_BASE)
    USER_CFG_SPECIAL_EXIST = os.path.exists(USER_CFG_SPECIAL)

    USER_CFG_BASE_ACCESS = check_user_cfg_base_access(USER_CFG_BASE)
    USER_CFG_SPECIAL_ACCESS = check_user_cfg_base_access(USER_CFG_SPECIAL)

    try:
        os.makedirs(SPECIAL_DIR, exist_ok=True)
    except:
        pass

    source_config = DEFAULT_CFG

    # 1) If user config exists in base_dir, load it and sync special with loaded
    if USER_CFG_BASE_EXIST:
        source_config = USER_CFG_BASE

    elif USER_CFG_BASE_ACCESS:
        if USER_CFG_SPECIAL_EXIST:
            source_config = USER_CFG_SPECIAL
        else:
            source_config = DEFAULT_CFG

    elif USER_CFG_SPECIAL_EXIST:
        source_config = USER_CFG_SPECIAL

    config = configparser.ConfigParser()
    config.read(source_config, encoding='utf-8')
    if source_config!=DEFAULT_CFG:
        repair_configuration(config)
    save_configuration_OS(config) 
    return config

def save_configuration_OS(config):
    if USER_CFG_BASE_ACCESS:
        with open(USER_CFG_BASE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    if USER_CFG_SPECIAL_ACCESS:        
        with open(USER_CFG_SPECIAL, 'w', encoding='utf-8') as configfile:
            config.write(configfile)

def reset_configuration_OS(config):
    """
    Reverts to default.cfg in memory. Then tries to save in base or fallback.
    """
    config.read(DEFAULT_CFG, encoding='utf-8')
    save_configuration_OS(config)

def repair_configuration(config):

    # Read the default configuration
    default_config = configparser.ConfigParser()
    default_config.read(DEFAULT_CFG)

    # Create a new configuration using the default structure
    new_config = configparser.ConfigParser()
    
    for section in default_config.sections():
        new_config.add_section(section)
        # For each option in the default section, use the user's value if available,
        # otherwise use the default value.
        for key, default_value in default_config.items(section):
            if config.has_option(section, key):
                # Even if the user file had the option in a wrong section,
                # only the correct section is considered here.
                new_config.set(section, key, config.get(section, key))
            else:
                new_config.set(section, key, default_value)

    config.read_dict(new_config)

    del new_config
    del default_config


def load_and_apply_profile(profile, config):
    """
    Loads a profile configuration from the given file path and applies its settings to the provided config.
    Only updates values for section–option pairs that already exist in the current config.
    New section–option pairs in the profile are ignored.
    
    :param profile_path: File path to the profile configuration file.
    :param config: The current configuration (an instance of ConfigParser).
    :return: A new profile_config instance.
    """
    try:
        profile_path=os.path.join(PROFILE_DIR, f'{profile}.cfg')
        # Load profile configuration from file (using UTF-8 encoding).
        profile_config = configparser.ConfigParser()
        profile_config.read(profile_path, encoding='utf-8')
    except Exception as e:
        return config
    apply_subconfig_on_configuration(profile_config, config)
    return profile_config

def apply_subconfig_on_configuration(subconfig, config):
    # Create a new configuration using the structure from the current config.
    new_config = configparser.ConfigParser()
    for section in config.sections():
        new_config.add_section(section)
        for key, value in config.items(section):
            # Update the value from the profile only if the pair exists in the profile config.
            if subconfig.has_option(section, key):
                new_config.set(section, key, subconfig.get(section, key))
            else:
                new_config.set(section, key, value)
    config.read_dict(new_config)
    del new_config

def init_configuration(dir):
    config = configparser.ConfigParser()
    config.read(dir, encoding='utf-8')
    return config