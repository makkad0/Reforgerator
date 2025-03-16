from setuptools import setup, Extension
from Cython.Build import cythonize
import os

extensions = [
    Extension(
        "packbits",                      # Change from "pytoshop.packbits" to "packbits"
        ["packbits.pyx","packbits.c"],  # Source remains in pytoshop/packbits.pyx
    )
]

setup(
    name="packbits",
    ext_modules=cythonize(extensions, compiler_directives={"language_level": "3"}),
)