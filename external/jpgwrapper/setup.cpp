#define PY_SSIZE_T_CLEAN  // Fix for 'y#' format in PyArg_ParseTuple
#include <Python.h>
#include "source/jpgwrapper.h"  // your JPEG conversion functions

// Example wrapper for ConvertToJpg (you should adjust parameters as needed)
static PyObject* py_compress_bgra_to_jpeg(PyObject* self, PyObject* args) {
    const char* inputBuffer;
    int inputLength, width, height, quality;
    int bottomUp = 0;  // Default value (False = top-down)
    int progressive = 0;  // Default: sequential JPEG
    int optimize_coding = 0;  // Default: use default Huffman tables
    // Declare optional objects for the custom DC and AC tables.
    PyObject* customDcObj = Py_None;
    PyObject* customAcObj = Py_None;

    // Fix: Change |p (boolean) to |i (integer)
    if (!PyArg_ParseTuple(args, "y#iii|ppOO", &inputBuffer, &inputLength, &width, &height, &quality, &progressive, &optimize_coding, &customDcObj, &customAcObj)) {
        return NULL;
    }

    const JHUFF_TBL* customDcTable = NULL;
    int numDcTables = 0;
    const JHUFF_TBL* customAcTable = NULL;
    int numAcTables = 0;
    
    // Process custom DC table object.
    if (customDcObj != Py_None) {
        if (PyBytes_Check(customDcObj)) {
            Py_ssize_t dcLen = PyBytes_Size(customDcObj);
            if (dcLen != sizeof(JHUFF_TBL)) {
                PyErr_SetString(PyExc_ValueError,
                    "customDcTable bytes size does not match sizeof(JHUFF_TBL)");
                return NULL;
            }
            customDcTable = reinterpret_cast<const JHUFF_TBL*>(PyBytes_AsString(customDcObj));
            numDcTables = 1;
        }
        else if (PyList_Check(customDcObj)) {
            Py_ssize_t list_len = PyList_Size(customDcObj);
            bool found = false;
            for (Py_ssize_t j = 0; j < list_len; j++) {
                PyObject* item = PyList_GetItem(customDcObj, j);
                if (!PyBytes_Check(item)) {
                    PyErr_SetString(PyExc_TypeError,
                        "Each element of customDcTable list must be a bytes object");
                    return NULL;
                }
                if (PyBytes_Size(item) == sizeof(JHUFF_TBL)) {
                    customDcTable = reinterpret_cast<const JHUFF_TBL*>(PyBytes_AsString(item));
                    numDcTables = 1;
                    found = true;
                    break;
                }
            }
            if (!found) {
                PyErr_SetString(PyExc_ValueError,
                    "No element in customDcTable list has size matching sizeof(JHUFF_TBL)");
                return NULL;
            }
        }
        else {
            PyErr_SetString(PyExc_TypeError,
                "customDcTable must be a bytes object, a list of bytes objects, or None");
            return NULL;
        }
    }
    
    // Process custom AC table object.
    if (customAcObj != Py_None) {
        if (PyBytes_Check(customAcObj)) {
            Py_ssize_t acLen = PyBytes_Size(customAcObj);
            if (acLen != sizeof(JHUFF_TBL)) {
                PyErr_SetString(PyExc_ValueError,
                    "customAcTable bytes size does not match sizeof(JHUFF_TBL)");
                return NULL;
            }
            customAcTable = reinterpret_cast<const JHUFF_TBL*>(PyBytes_AsString(customAcObj));
            numAcTables = 1;
        }
        else if (PyList_Check(customAcObj)) {
            Py_ssize_t list_len = PyList_Size(customAcObj);
            bool found = false;
            for (Py_ssize_t j = 0; j < list_len; j++) {
                PyObject* item = PyList_GetItem(customAcObj, j);
                if (!PyBytes_Check(item)) {
                    PyErr_SetString(PyExc_TypeError,
                        "Each element of customAcTable list must be a bytes object");
                    return NULL;
                }
                if (PyBytes_Size(item) == sizeof(JHUFF_TBL)) {
                    customAcTable = reinterpret_cast<const JHUFF_TBL*>(PyBytes_AsString(item));
                    numAcTables = 1;
                    found = true;
                    break;
                }
            }
            if (!found) {
                PyErr_SetString(PyExc_ValueError,
                    "No element in customAcTable list has size matching sizeof(JHUFF_TBL)");
                return NULL;
            }
        }
        else {
            PyErr_SetString(PyExc_TypeError,
                "customAcTable must be a bytes object, a list of bytes objects, or None");
            return NULL;
        }
    }

    // Prepare Buffers
    Buffer source, target;
    source.buf = const_cast<char*>(inputBuffer);
    source.length = inputLength;

    // Call JPEG compression function
    bool success = ConvertToJpg(source, target, width, height, 4, quality, progressive, optimize_coding, customDcTable, numDcTables,
        customAcTable, numAcTables);
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
     "Arguments: image_buffer (bytes), buffer_length, width, height, quality, progressive, optimize_coding, customDCObj (bytes), customACObj (bytes)"},
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