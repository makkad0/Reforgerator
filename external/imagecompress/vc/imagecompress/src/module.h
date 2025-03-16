#pragma once

#include "stdio.h"

#define XMD_H
extern "C" {
#include "jpeglib/jpeglib.h"
}
#include "setjmp.h"
#include "pnglib/png.h"

#include "etc1/rg_etc1.h"

#define PY_SSIZE_T_CLEAN
#include "Python.h"
#include <deque>
#include <stdint.h>
#include "tools.h"
#include "memoryreader.h"
#include <map>

class Memory;

enum MODULE_IMAGE_TYPES_LIST {
  MODULE_IMAGE_TYPE_UNKNOWN = 0,
  MODULE_IMAGE_TYPE_BMP     = 1,
  MODULE_IMAGE_TYPE_TGA     = 2,
  MODULE_IMAGE_TYPE_JPG     = 3,
  MODULE_IMAGE_TYPE_PNG     = 4,
};

class Module {
public:
  static PyObject* Func123( PyObject *self, PyObject *args );
  static PyObject* free( PyObject *self, PyObject *args );

  static PyObject* tga2rgba( PyObject *self, PyObject *args );
  static PyObject* jpg2rgba( PyObject *self, PyObject *args );
  static PyObject* png2rgba( PyObject *self, PyObject *args );
  static PyObject* bmp2rgba( PyObject *self, PyObject *args );
  
  static PyObject* decode2rgba( PyObject *self, PyObject *args );
  static PyObject* picture2dxt( PyObject *self, PyObject *args );
  static PyObject* picture2etc1( PyObject *self, PyObject *args );

  static PyObject* rgba2dxt1( PyObject *self, PyObject *args );
  static PyObject* rgba2dxt3( PyObject *self, PyObject *args );
  static PyObject* rgba2dxt5( PyObject *self, PyObject *args );
  static PyObject* rgba2etc1( PyObject *self, PyObject *args );

  static PyObject* supportedFormats( PyObject *self, PyObject *args );

private:
  typedef std::deque< Memory* > MemoryList;
  typedef bool decodeFuncHandlerType( Memory &inBuffer, Memory &outBuffer, bool &isTransparent, size_t &outWidth, size_t &outHeight );

  static MemoryList memoryBlocksList;
  static std::map< std::string, int > formatList;
  static bool isInitialized;

  static bool CompressSquish( PyObject* M_IN args, Memory M_OUT &compressedData, size_t M_OUT &width, size_t M_OUT &height, int format );
  static bool CompressETC1( PyObject* M_IN args, Memory M_OUT &compressedData, size_t M_OUT &width, size_t M_OUT &height, int M_OUT &quality );
  static PyObject* DoDXTCompressFromArgs( PyObject* M_IN args, int format );
  static PyObject* DoETC1CompressFromArgs( PyObject* M_IN args );
  static bool GetImageFromArguments( PyObject* M_IN args, size_t M_OUT &width, size_t M_OUT &height, Memory M_OUT &rgbaData, std::string M_OUT *format = NULL, int M_OUT *quality = 0 );
  static MODULE_IMAGE_TYPES_LIST GetImageType( Memory &memory );
  static void InitModule();
  static bool DecodeBMP( Memory &inBuffer, Memory &outBuffer, bool &isTransparent, size_t &outWidth, size_t &outHeight );
  static bool DecodeTGA( Memory &inBuffer, Memory &outBuffer, bool &isTransparent, size_t &outWidth, size_t &outHeight );
  static bool DecodeJPG( Memory &inBuffer, Memory &outBuffer, bool &isTransparent, size_t &outWidth, size_t &outHeight );
  static bool DecodePNG( Memory &inBuffer, Memory &outBuffer, bool &isTransparent, size_t &outWidth, size_t &outHeight );
  static void EncodeDXT( Memory &inBuffer, size_t width, size_t height, Memory &outBuffer, int dxtFormat );
  static void EncodeETC1( Memory &inBuffer, size_t width, size_t height, Memory &outBuffer, int quality );
};


class ImgJpg
{
public:

  struct  _gImporterJPEGError {
          jpeg_error_mgr  pub;
          jmp_buf setjmp_buffer;
  };

  static const int c_JPEGInputBufferSize;

  static void JPEGErrorExit             ( j_common_ptr cinfo );
  static void JPEGStdioSrcgMemoryReader ( j_decompress_ptr cinfo, MemoryReader* file );
};

class ImgPng
{
public:
  static void PNGReadFunctiongFile        ( png_structp png_ptr, png_bytep data, png_size_t length );
  static void PNGReadFunctiongMemoryReader( png_structp png_ptr, png_bytep data, png_size_t length );

};

#pragma pack(2)

struct ImageType_BMP_FileHeader {
  uint16_t        bfType;
  uint32_t        bfSize;
  uint16_t        bfReserved1;
  uint16_t        bfReserved2;
  uint32_t        bfOffBits;
};

struct ImageType_BMP_InfoHeader {
  uint32_t        biSize;
  int32_t         biWidth;
  int32_t         biHeight;
  uint16_t        biPlanes;
  uint16_t        biBitCount;
  uint32_t        biCompression;
  uint32_t        biSizeImage;
  int32_t         biXPelsPerMeter;
  int32_t         biYPelsPerMeter;
  uint32_t        biClrUsed;
  uint32_t        biClrImportant;
};

#pragma pack()
