#include "module.h"

#define GETSTATE( m ) ( ( struct moduleState* ) PyModule_GetState ( m ) )

struct moduleState {
  PyObject *error;
};

static PyMethodDef ModuleMethods[] = {
  { "tga2rgba",  Module::tga2rgba, METH_VARARGS, "Decode TGA file to RGBA" },
  { "jpg2rgba",  Module::jpg2rgba, METH_VARARGS, "Decode JPG file to RGBA (alpha = 255)" },
  { "png2rgba",  Module::png2rgba, METH_VARARGS, "Decode PNG file to RGBA" },
  { "bmp2rgba",  Module::bmp2rgba, METH_VARARGS, "Decode BMP (24/32 bpp) file to RGBA (alpha = 255)" },
  { "decode2rgba",  Module::decode2rgba, METH_VARARGS, "Decode picture file to RGBA (bmp, tga, jpg, png)" },
  { "rgba2dxt1",  Module::rgba2dxt1, METH_VARARGS, "Compress RGBA data as DXT1" },
  { "rgba2dxt3",  Module::rgba2dxt3, METH_VARARGS, "Compress RGBA data as DXT3" },
  { "rgba2dxt5",  Module::rgba2dxt5, METH_VARARGS, "Compress RGBA data as DXT5" },
  { "rgba2etc1",  Module::rgba2etc1, METH_VARARGS, "Compress RGBA data as ETC1" },
  { "supportedFormats",  Module::supportedFormats, METH_VARARGS, "List of allowed pictures formats" },
  { "picture2dxt",  Module::picture2dxt, METH_VARARGS, "Compress picture file to DXT1/DXT3/DXT5 format" },
  { "picture2etc1",  Module::picture2etc1, METH_VARARGS, "Compress picture file to ETC1 format" },
  { "free",  Module::free, METH_VARARGS, "Free reserved module memory" },
  { NULL, NULL, 0, NULL }
};

static int imageCompressTraverse( PyObject *m, visitproc visit, void *arg ) {
  Py_VISIT( GETSTATE( m )->error );
  return 0;
}//imageCompressTraverse

static int imageCompressClear( PyObject *m ) {
  Py_CLEAR( GETSTATE( m )->error );
  return 0;
}//imageCompressClear

static struct PyModuleDef moduleDef = {
  PyModuleDef_HEAD_INIT,
  "imagecompress",
  NULL,
  sizeof( struct moduleState ),
  ModuleMethods,
  NULL,
  imageCompressTraverse,
  imageCompressClear,
  NULL
};

PyMODINIT_FUNC PyInit_imagecompress() {
  PyObject *module = PyModule_Create( &moduleDef );
  if( module == NULL ) {
    return NULL;
  }
  struct moduleState *st = GETSTATE( module );
  st->error = PyErr_NewException( "imagecompress.Error", NULL, NULL );
  if( st->error == NULL ) {
    Py_DECREF( module );
    return NULL;
  }

  return module;
}//PyInit_imagecompress
