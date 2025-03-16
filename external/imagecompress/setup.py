import os
import sys
import glob
from setuptools import setup, Extension

# List of basenames to exclude (files that define main() or duplicate implementations)
EXCLUDE_FILES = {
    "cjpeg.c", "djpeg.c", "jpegtran.c", "rdjpgcom.c",
    "wrjpgcom.c", "pngtest.c", "example.c",
    "jmemname.c", "jmemnobs.c",
}

def find_source_files(root_dir, patterns=("*.cpp", "*.c")):
    files = []
    for pattern in patterns:
        for filepath in glob.glob(os.path.join(root_dir, "**", pattern), recursive=True):
            if os.path.basename(filepath).lower() in EXCLUDE_FILES:
                continue
            files.append(filepath)
    return files

# Collect source files recursively from the current directory.
source_files = find_source_files(os.getcwd())

print("Found the following source files:")
for src in source_files:
    print("  ", src)

# Define important include directories (adjust these paths as needed)
include_dirs = [
    os.path.join(os.getcwd(), "vc", "imagecompress", "src", "zlib"),
    os.path.join(os.getcwd(), "vc", "imagecompress", "src", "squish"),
    os.path.join(os.getcwd(), "vc", "imagecompress", "src", "pnglib"),
    os.path.join(os.getcwd(), "vc", "imagecompress", "src", "jpeglib"),
    os.path.join(os.getcwd(), "vc", "imagecompress", "src", "etc1"),
    os.path.join(os.getcwd(), "include"),  # if you have additional headers here
    # Ensure Python headers are found (this is usually handled automatically)
    os.path.join(sys.prefix, "include"),
]

# Define macros based on the VS project settings.
# For a Release build, these macros are typically defined:
define_macros = [
    ("WIN32", "1"),
    ("NDEBUG", "1"),
    ("_CONSOLE", "1"),
    ("HAVE_CONFIG_H", "1"),
    ("PY_SSIZE_T_CLEAN", "1"),
]

# On Windows, add Python library directory (adjust to your Python installation if necessary)
library_dirs = [
    os.path.join(sys.prefix, "libs"),
]

# Optionally, if linking is not automatic, specify the Python library name (e.g. "python312")
libraries = []
if sys.platform == "win32":
    # This may be needed; if so, uncomment the next line:
    # libraries.append("python312")
    pass

# For MSVC, use /O2 for optimization.
extra_compile_args = ["/O2", "/DPY_SSIZE_T_CLEAN"]

extension_mod = Extension(
    "imagecompress",       # Module name to import as "import imagecompress"
    sources=source_files,
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    define_macros=define_macros,
    extra_compile_args=extra_compile_args,
    language="c++",
)

setup(
    name="py.texture.compress",
    version="1.1",
    description="A lightweight C++ module for DDS compression (DXT1/DXT3/DXT5) for Python",
    ext_modules=[extension_mod],
)