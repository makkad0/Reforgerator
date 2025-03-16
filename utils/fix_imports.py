import sys
import os

def fix_module_paths():
    """Ensure the correct path for imported modules, handling PyInstaller packaging."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS  # Use the extracted temp folder for PyInstaller
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))  # Normal script location

    sys.path.append(os.path.join(base_path, "external/jpgwrapper"))  # Add jpgwrapper to sys.path