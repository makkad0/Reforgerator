#define PY_SSIZE_T_CLEAN  // Fix for 'y#' format in PyArg_ParseTuple
#include <Python.h>
#include "source/jpgwrapper.h"  // your JPEG conversion functions

// Example wrapper for ConvertToJpg (you should adjust parameters as needed)
static PyObject* py_compress_bgra_to_jpeg(PyObject* self, PyObject* args) {
    const char* inputBuffer;
    int inputLength, width, height, quality;
    int bottomUp = 0;  // Default value (False = top-down)
    int progressive = 0;  // Default: sequential JPEG

    // Fix: Change |p (boolean) to |i (integer)
    if (!PyArg_ParseTuple(args, "y#iii|p", &inputBuffer, &inputLength, &width, &height, &quality, &progressive)) {
        return NULL;
    }

    // Prepare Buffers
    Buffer source, target;
    source.buf = const_cast<char*>(inputBuffer);
    source.length = inputLength;

    // Call JPEG compression function
    bool success = ConvertToJpg(source, target, width, height, 4, quality, progressive, bottomUp);
    if (!success) {
        PyErr_SetString(PyExc_RuntimeError, "JPEG compression failed.");
        return NULL;
    }

    // Convert to Python bytes object
    PyObject* result = PyBytes_FromStringAndSize(target.buf, target.length);
    
    // Free allocated memory
    delete[] target.buf;

    return result;
}

// Define the methods exported by this module.
static PyMethodDef jpgwrapperMethods[] = {
    {"compress_bgra_to_jpeg", py_compress_bgra_to_jpeg, METH_VARARGS,
     "Compress a BGRA8 image into JPEG bytes.\n"
     "Arguments: image_buffer (bytes), buffer_length, width, height, quality"},
    {NULL, NULL, 0, NULL}  // Sentinel
};

// Define the module.
static struct PyModuleDef jpgwrappermodule = {
    PyModuleDef_HEAD_INIT,
    "jpgwrapper",                         // Module name
    "Module for converting BGRA8 images to JPEG.", // Module documentation
    -1,                                   // Size of per-interpreter state (-1 if global)
    jpgwrapperMethods
};

// Module initialization function
PyMODINIT_FUNC PyInit_jpgwrapper(void) {
    return PyModule_Create(&jpgwrappermodule);
}