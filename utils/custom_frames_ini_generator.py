import sys,os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.custom_frames import get_ini_files_string, parse_ini_files_from_string, OPTION_START_WORD
import configparser
import vars.global_var as gv

def generate_ini_from_frame(frame, output_filepath):
    """
    Generate a .ini file from a given frame dictionary.
    The frame is expected to have a "main" block (keys: id, name, prefix, extension_value, main_folder)
    and additional sections with keys formatted as f"{style}_{size}".
    """
    config = configparser.ConfigParser()

    # Build main section.
    config.add_section("main")
    config.set("main", "id", frame.get("id", ""))
    config.set("main", "name", frame.get("name", ""))
    config.set("main", "prefix", frame.get("prefix", ""))
    config.set("main", "extension", frame.get("extension_value", ""))
    if frame.get("main_folder"):
        config.set("main", "main_folder", frame.get("main_folder"))

    # Process additional sections.
    for key, value in frame.items():
        if key.startswith(OPTION_START_WORD):
            # key is expected to be formatted as "option_{style}_{size}".
            config.add_section(key)
            for subkey, subvalue in value.items():
                if subvalue is None:
                    continue  # Skip None values.
                if isinstance(subvalue, tuple):
                    subvalue = ",".join(map(str, subvalue))
                else:
                    subvalue = str(subvalue)
                config.set(key, subkey, subvalue)

    with open(output_filepath, "w") as configfile:
        config.write(configfile)
    print(f"Generated ini file: {output_filepath}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = "tempoutput"
    output_dir_path=os.path.join(script_dir,output_dir)
    ini_list = get_ini_files_string()
    frames = parse_ini_files_from_string(ini_list)
    print("Parsed frames:")
    for key, value in frames.items():
        ini_file_name=f"{key}.ini"
        ini_file_path=os.path.join(output_dir_path,ini_file_name)
        generate_ini_from_frame(value,ini_file_path)