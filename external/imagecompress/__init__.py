import sys
import os

# Auto-fix the module path when imported
if getattr(sys, 'frozen', False):  # Running as an .exe
    base_path = sys._MEIPASS
else:  # Running as a script
    base_path = os.path.abspath(os.path.dirname(__file__))

sys.path.append(base_path)  # Ensure the correct path for .pyd files

# Import the compiled extension
from .imagecompress import *