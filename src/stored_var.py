import configparser
import vars.global_var as gv
import os

def process_folder(input_folder,input_suboption_dict,multifolder_regime=False):
    # Each item is a tuple: (full_file_path, relative_subfolder)
    file_items = []
    if input_folder and os.path.isdir(input_folder):
        # Prepare allowed extensions.
        allowed_extensions = []
        allowed_ext_string = input_suboption_dict.get("input_process_filetypes", "")
        if allowed_ext_string:
            allowed_extensions = [ext.strip().lower() for ext in allowed_ext_string.split(",") if ext.strip()]

        if input_suboption_dict.get("input_process_subfolders", False):
            # Recursively process all files in all subdirectories.
            for root, dirs, files in os.walk(input_folder):
                for file in files:
                    ext = os.path.splitext(file)[1].lstrip(".").lower()
                    if ext in allowed_extensions:
                        full_path = os.path.join(root, file)
                        relative_subfolder = os.path.relpath(root, input_folder)
                        if multifolder_regime:
                            relative_subfolder = os.path.join( os.path.basename(input_folder),relative_subfolder)
                        file_items.append((full_path, relative_subfolder))
        else:
            # Only process files in the top-level folder.
            for file in os.listdir(input_folder):
                full_path = os.path.join(input_folder, file)
                if os.path.isfile(full_path):
                    ext = os.path.splitext(file)[1].lstrip(".").lower()
                    if ext in allowed_extensions:
                        if multifolder_regime:
                            relative_subfolder = os.path.basename(input_folder)
                        else:
                            relative_subfolder = ""
                        file_items.append((full_path, relative_subfolder))
    return file_items

class CurrentSelection:
    """Stores the current selection of images or folder and manages options."""
    def __init__(self,guiframe: None):
        self.paths = []   # List of all images paths (including in folders) for processing
        self.paths_rel = []
        self.paths_folders = [] # List of input folders paths
        self.paths_images = [] # List of separately selected input images
        self.paths_items = [] #self.paths_folders + self.paths_images
        self.loaded_images_pillow = []
        # all_options is a dict: section -> {option: value, ...}
        self.all_options = {}
        # Additional controlers
        self.stop_requested = False
        
    def init_input_items(self, folders=None,images=None):
        self.clearinputs()
        # Initialize new lists to avoid shared references
        self.paths_folders = list(folders) if folders else []
        self.paths_images = list(images) if images else []
        # Create a separate list for paths_items
        self.paths_items = self.paths_folders + self.paths_images

    def gather_paths(self):
        paths_folders=self.paths_folders
        paths_images=self.paths_images
        self.paths.clear()
        self.paths_rel.clear()
        paths = []
        input_suboption_dict = self.recieve_suboptions([gv.OPTIONS_INPUT])
        multifolder_regime=len(paths_folders)>1 or len(paths_images)>0
        for path in paths_images:
            paths.append(path)
            self.paths_rel.append((path,""))
        for path in paths_folders:
            file_items = process_folder(path, input_suboption_dict,multifolder_regime)
            # Add just the full file paths.
            paths.extend([full_path for full_path, _ in file_items])
            self.paths_rel.extend(file_items)
        self.paths = paths

    def clearinputs(self):
        self.paths.clear()
        self.paths_rel.clear()
        self.paths_folders.clear()
        self.paths_images.clear()
        self.paths_items.clear()
        self.loaded_images_pillow.clear()

    def clear_preloaded_images(self):
        self.loaded_images_pillow.clear()

    # --- Methods for managing all_options ---

    def get_sections(self):
        """Return a list of all section names."""
        return list(self.all_options.keys())

    def get_options(self, section):
        """Return a list of options in a given section."""
        if section in self.all_options:
            return list(self.all_options[section].keys())
        return []

    def get_sections_for_option(self, option):
        """Return a list of sections that contain the given option."""
        sections = []
        for section, options in self.all_options.items():
            if option in options:
                sections.append(section)
        return sections

    def add_option(self, section, option, value):
        """
        Adds a new option (with its value) to a section.
        If the section doesn't exist, it is created.
        If the option already exists with the same value, nothing is done.
        Returns True if the option was added or updated; False if the identical pair exists.
        """
        if section not in self.all_options:
            self.all_options[section] = {}
        if option in self.all_options[section]:
            if self.all_options[section][option] == value:
                return False  # Identical pair exists, so do nothing.
        self.all_options[section][option] = value
        return True

    def remove_option(self, section, option):
        """Removes the specified option from the given section. Returns True if removed."""
        if section in self.all_options and option in self.all_options[section]:
            del self.all_options[section][option]
            # Optionally remove the section if it becomes empty.
            if not self.all_options[section]:
                del self.all_options[section]
            return True
        return False

    def remove_section(self, section):
        """Removes an entire section. Returns True if the section existed and was removed."""
        if section in self.all_options:
            del self.all_options[section]
            return True
        return False

    def set_value(self, section, option, value):
        """
        Sets the value for the given section–option pair.
        If the section or option doesn't exist, they are created.
        """
        if section not in self.all_options:
            self.all_options[section] = {}
        self.all_options[section][option] = value

    def get_value(self, section, option):
        """
        Returns the value for the given section–option pair.
        Returns None if the section or option does not exist.
        """
        if section in self.all_options and option in self.all_options[section]:
            return self.all_options[section][option]
        return None

    def read_config_file(self,config):
        """
        Reads an INI-style config and populates self.all_options.
        For example, given a config file like:
          [OPTIONS_SIZE]
          size_64x64 = False
          size_128x128 = False
          size_256x256 = True
          [OPTIONS_STYLE]
          style_sd = False
          style_hd = True
          ...
        the method fills self.all_options accordingly.
        """
        self.all_options.clear()
        for section in config.sections():
            self.all_options[section] = {}
            for option, value in config.items(section):
                # Convert "True"/"False" to booleans.
                if value.lower() == "true":
                    self.all_options[section][option] = True
                elif value.lower() == "false":
                    self.all_options[section][option] = False
                else:
                    self.all_options[section][option] = value
        return self.all_options

    def generate_cfg_file(self, filename):
        """
        Generates a configuration file in INI format using the current self.all_options.
        The file will have sections and key-value pairs, e.g.:
        
          [OPTIONS_SIZE]
          size_64x64 = False
          size_128x64 = False
          size_256x256 = True
          
          ...
        """
        config = configparser.ConfigParser()
        for section, options in self.all_options.items():
            config[section] = {}
            for option, value in options.items():
                config[section][option] = str(value)
        with open(filename, 'w') as configfile:
            config.write(configfile)

    def recieve_suboptions(self,sections_list):
        result = {}
        for sec in sections_list:
            section_name = sec.get("section")
            options_list = sec.get("options", [])
            for option in options_list:
                value = self.get_value(section_name, option)
                if value is not None:
                    result[option] = value
        return result

    def recieve_true_variations(self):
        """
        Returns the true-valued options for each section in the provided sections_list.
        
        Each element in sections_list should be a dictionary with keys "section" and "options".
        For each such dictionary, the method builds a list of options that have True values
        in self.all_options.
        
        If sections_list is not provided, a default list is used.
        
        If the resulting list has only one element, that list is returned.
        Otherwise, a tuple of lists (in the order of sections_list) is returned.
        
        Example:
        If sections_list = [gv.OPTIONS_SIZE] and in self.all_options the options for
        "OPTIONS_SIZE" are { "size_64x64": True, "size_128x128": False, "size_256x256": True },
        then the method returns ["size_64x64", "size_256x256"].
        """
        sections_list = [gv.OPTIONS_SIZE, gv.OPTIONS_STYLE, gv.OPTIONS_BORDER, gv.OPTIONS_FORMAT]
        result = []
        for sec in sections_list:
            section_name = sec.get("section")
            options_list = self.get_options(section_name)
            true_options = [opt for opt in options_list 
                            if self.all_options.get(section_name, {}).get(opt, False)]
            result.append(true_options)
        return result[0] if len(result) == 1 else tuple(result)

    def calculate_number_of_variations(self):
        """
        Given a list of dictionaries (each with keys "section" and "options"),
        this method checks self.all_options for each section and counts the number of
        options that are set to True. It then returns the product of these counts.

        For example, if for section "OPTIONS_SIZE" there are 2 True options,
        for "OPTIONS_STYLE" there is 1 True option, and for "OPTIONS_BORDER" there are 4 True options,
        the method returns 2 * 1 * 4 = 8.
        
        Parameters:
            sections_list (list): A list of dictionaries, e.g.:
                [
                    {"section": "OPTIONS_SIZE", "options": ["size_64x64", "size_128x128", "size_256x256"]},
                    {"section": "OPTIONS_STYLE", "options": ["style_sd", "style_hd"]},
                    {"section": "OPTIONS_BORDER", "options": ["border_button", "border_disabled", "border_passive", "border_autocast", "border_none"]},
                    # ... other sections if needed.
                ]
                
        Returns:
            int: The product of counts of True options for each section.
                If a section is missing or has no True values, its count is considered 0.
        """
        sections_list=[gv.OPTIONS_SIZE,gv.OPTIONS_STYLE,gv.OPTIONS_BORDER,gv.OPTIONS_FORMAT]
        product = 1
        for section_dict in sections_list:
            section_name = section_dict.get("section")
            options_list = self.get_options(section_name)
            count_true = 0
            if section_name in self.all_options:
                for option in options_list:
                    # Only count if the value is True.
                    if self.all_options[section_name].get(option, False) is True:
                        count_true += 1
            # Multiply the current product by the count for this section.
            product *= count_true
        return product
    
