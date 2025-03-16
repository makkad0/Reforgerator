import os
import var.global_var as gv
from src.system import get_data_subdir

# Global dictionary for localization text.
LOCAL_TEXT = {}

def update_localisation(language_code):
    """
    Loads the localization file for the specified language code.
    For example, if language_code is "eng", it will load "local_eng.txt".
    :param language_code: The code of the language to load (e.g., "eng" or "rus").
    """
    global LOCAL_TEXT
    # Determine the base directory (adjust as needed)
    localization_file = os.path.join(get_data_subdir("localisations"), f"local_{language_code}.txt")
    
    if os.path.isfile(localization_file):
        # Clear any existing localization data.
        LOCAL_TEXT.clear()
        # Read the localization file line by line.
        with open(localization_file, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    LOCAL_TEXT[key.strip()] = value.strip()

def get_local_text(key,check_existance:bool = False):
    """
    Returns the localized text for a given key. If the key is missing,
    returns the key name enclosed in angle brackets.
    
    :param key: The localization key to retrieve.
    :return: The localized text or a placeholder.
    """
    default=f"<{key}>"
    if check_existance:
        default=""
    return LOCAL_TEXT.get(key,default)

def get_tooltip_text(code:str = None,check_existance:bool = False):
    if code:
        return get_local_text(f'tooltip_{code}',check_existance)
    else:
        return ""