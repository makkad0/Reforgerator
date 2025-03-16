from setuptools import setup, Extension
import numpy as np
import glob
import os
import sys

# List of basenames to exclude (files that define main() or duplicate implementations)
EXCLUDE_FILES = {}

def find_source_files(root_dir, patterns=("*.cpp",)):
    files = []
    for pattern in patterns:
        for filepath in glob.glob(os.path.join(root_dir, "**", pattern), recursive=True):
            # Only add if it's a file with a .cpp extension.
            if not os.path.isfile(filepath):
                continue
            if os.path.splitext(filepath)[1].lower() != '.cpp':
                continue
            if os.path.basename(filepath).lower() in EXCLUDE_FILES:
                continue
            files.append(filepath)
    return files

# Collect source files recursively from the current directory.
source_files = find_source_files(os.getcwd())

print("Found the following source files:")
for src in source_files:
    print("  ", src)

# Define include directories.
include_dirs = [
    #os.path.join(os.getcwd(),"source", "libjpeg"),
    np.get_include(),
]

# Link directly with libjpeg.lib via extra_objects.
#extra_objects = [os.path.join(os.getcwd(),"source","libjpeg","jpeg-static.lib")]
extra_objects = [os.path.join(os.getcwd(),"source","libjpeg","turbojpeg-static.lib")]

# Set extra compile arguments conditionally (MSVC ignores '-std=c++11').
extra_compile_args = []
extra_link_args = []
if sys.platform == "win32":
    # Define XMD_H to prevent redefinition of INT32 and other types.
    #extra_compile_args.append("/DXMD_H")
    extra_compile_args.append("/MT")
    extra_link_args.append("/NODEFAULTLIB:LIBCMTD")  # Remove conflicting runtime library
else:
    extra_compile_args = ["-std=c++11"]


module = Extension(
    "jpgwrapper",              # Name of the Python module to create.
    sources=source_files,       # Source files (only .cpp files).
    include_dirs=include_dirs,  # Include directories for libjpeg and NumPy.
    language="c++",             # Specify C++ language for compilation.
    extra_compile_args=extra_compile_args,  # Adjust C++ standard as needed.
    extra_objects=extra_objects,  # Link directly with libjpeg.lib.
    extra_link_args=extra_link_args,  # Add linker args
)

setup(
    name="jpgwrapper",
    version="1.0",
    ext_modules=[module],
)