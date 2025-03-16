#include "module.h"

#include "stdio.h"
#include "filemanager.h"
#include "tools.h"
#include "squish.h"
#include <vector>

Module::MemoryList Module::memoryBlocksList;
std::map< std::string, int > Module::formatList;
bool Module::isInitialized = false;


void Module::InitModule() {
  if( Module::isInitialized ) {
    return;
  }

  formatList.insert( std::make_pair( "dxt1", squish::kDxt1 ) );
  formatList.insert( std::make_pair( "dxt3", squish::kDxt3 ) );
  formatList.insert( std::make_pair( "dxt5", squish::kDxt5 ) );
}//InitModule


PyObject* Module::supportedFormats( PyObject *self, PyObject *args ) {
  Module::InitModule();
  return Py_BuildValue( "[s,s,s,s]", "bmp", "tga", "jpg", "png" );
}//supportedFormats


PyObject* Module::picture2dxt( PyObject *self, PyObject *args ) {
  Module::InitModule();
  size_t width, height;
  bool isTransparent;
  Memory fileData, imageDataRGBA, imageDataDXT;

  char *fileName, *format;
  if( !PyArg_ParseTuple( args, "ss", &fileName, &format ) ) {
    LOGE( "picture2dxt => bad parameters, need: '/path/to/file/name', 'format'" );
    return NULL;
  }

  FileManagerType fileManager;
  if( !fileManager.FileExists( fileName ) ) {
    LOGE( "File '%s' not fount", fileName );
    return NULL;
  }
  fileManager.GetFile( fileName, fileData );

  decodeFuncHandlerType *decodeFuncHandler = NULL;

  auto imageType = Module::GetImageType( fileData );
  switch( imageType ) {
  case MODULE_IMAGE_TYPE_BMP:
    decodeFuncHandler = Module::DecodeBMP;
    break;
  case MODULE_IMAGE_TYPE_TGA:
    decodeFuncHandler = Module::DecodeTGA;
    break;
  case MODULE_IMAGE_TYPE_JPG:
    decodeFuncHandler = Module::DecodeJPG;
    break;
  case MODULE_IMAGE_TYPE_PNG:
    decodeFuncHandler = Module::DecodePNG;
    break;
  default:
    LOGE( "Unknown format" );
    return NULL;
  }

  if( !decodeFuncHandler || !decodeFuncHandler( fileData, imageDataRGBA, isTransparent, width, height ) ) {
    return NULL;
  }

  auto formatRes = formatList.find( format );
  if( formatRes == formatList.end() ) {
    LOGE( "Unknown format '%s'", format );
    return NULL;
  }

  Module::EncodeDXT( imageDataRGBA, width, height, imageDataDXT, formatRes->second );
  return Py_BuildValue( "{s:y#,s:i,s:i,s:i}", "data", imageDataDXT.GetData(), imageDataDXT.GetLength(), "width", width, "height", height, "length", imageDataDXT.GetLength() );
}//picture2dxt


PyObject* Module::picture2etc1( PyObject *self, PyObject *args ) {
  Module::InitModule();
  size_t width, height;
  bool isTransparent;
  Memory fileData, imageDataRGBA, imageDataETC1;

  char *fileName;
  int quality;
  if( !PyArg_ParseTuple( args, "si", &fileName, &quality ) ) {
    LOGE( "picture2etc1 => bad parameters, need: '/path/to/file/name'" );
    return NULL;
  }

  FileManagerType fileManager;
  if( !fileManager.FileExists( fileName ) ) {
    LOGE( "File '%s' not fount", fileName );
    return NULL;
  }
  fileManager.GetFile( fileName, fileData );

  decodeFuncHandlerType *decodeFuncHandler = NULL;

  auto imageType = Module::GetImageType( fileData );
  switch( imageType ) {
  case MODULE_IMAGE_TYPE_BMP:
    decodeFuncHandler = Module::DecodeBMP;
    break;
  case MODULE_IMAGE_TYPE_TGA:
    decodeFuncHandler = Module::DecodeTGA;
    break;
  case MODULE_IMAGE_TYPE_JPG:
    decodeFuncHandler = Module::DecodeJPG;
    break;
  case MODULE_IMAGE_TYPE_PNG:
    decodeFuncHandler = Module::DecodePNG;
    break;
  default:
    LOGE( "Unknown format" );
    return NULL;
  }

  if( !decodeFuncHandler || !decodeFuncHandler( fileData, imageDataRGBA, isTransparent, width, height ) ) {
    return NULL;
  }

  Module::EncodeETC1( imageDataRGBA, width, height, imageDataETC1, quality );
  return Py_BuildValue( "{s:y#,s:i,s:i,s:i}", "data", imageDataETC1.GetData(), imageDataETC1.GetLength(), "width", width, "height", height, "length", imageDataETC1.GetLength() );
}//picture2etc1


void Module::EncodeETC1( Memory &inBuffer, size_t width, size_t height, Memory &outBuffer, int quality ) {
  size_t
    resultBufferSize = ( width * height ) >> 1,
    blocksPerRow = width >> 2,
    blocksPerColumn = height >> 2;
  Memory memBlock( 4 * 4 * 4 );
  outBuffer.Alloc( resultBufferSize );
  uint8_t
    *srcData = memBlock.GetData(),
    *destData = outBuffer.GetData();
  rg_etc1::etc1_pack_params packParams;

  packParams.m_dithering = false;
  switch( quality ) {
  case 0: packParams.m_quality = rg_etc1::cLowQuality; break;
  case 1: packParams.m_quality = rg_etc1::cMediumQuality; break;
  case 2: packParams.m_quality = rg_etc1::cHighQuality; break;
  default: packParams.m_quality = rg_etc1::cLowQuality; break; LOGE( "Module::EncodeETC1 => quality[%d] is unavailable", quality ); break;
  }

  rg_etc1::pack_etc1_block_init();
  for( size_t blockRow = 0; blockRow < blocksPerColumn; ++blockRow ) {
    for( size_t blockColumn = 0; blockColumn < blocksPerRow; ++blockColumn ) {
      for( size_t row = 0; row < 4; ++row ) {
        memcpy( srcData + row * 4 * 4, inBuffer.GetData() + 4 * ( blockColumn * 4 + blockRow * width ), 4 * 4 );
      }
      rg_etc1::pack_etc1_block( destData, ( unsigned int* ) srcData, packParams );
      destData += 8;
    }
  }
}//EncodeETC1


void Module::EncodeDXT( Memory &inBuffer, size_t width, size_t height, Memory &outBuffer, int dxtFormat ) {
  const size_t resultSize = squish::GetStorageRequirements( width, height, dxtFormat );
  outBuffer.Alloc( resultSize );
  squish::CompressImage( inBuffer.GetData(), width, height, outBuffer.GetData(), dxtFormat );
}//EncodeDXT


MODULE_IMAGE_TYPES_LIST Module::GetImageType( Memory &memory ) {
  uint8_t *data = memory.GetData();

  if( memory.GetLength() >= 2 ) {
    unsigned short *sign = ( unsigned short* ) data;
    if( *sign == 0x4D42 ) { //BM
      return MODULE_IMAGE_TYPE_BMP;
    }
  }
  if( memory.GetLength() >= 3 ) {
    unsigned short *sign = ( unsigned short* ) data;
    if( *sign == 0 && (data[2] == 0x02 || data[2] == 0x0A) ) {
      return MODULE_IMAGE_TYPE_TGA;
    }
  }
  if( memory.GetLength() >= 4 ) {
    uint32_t *sign = ( uint32_t* ) data;
    if( *sign == 0x474E5089 ) { //0x89 PNG
      return MODULE_IMAGE_TYPE_PNG;
    }
  }
  if( memory.GetLength() >= 10 ) {
    uint32_t *sign = ( uint32_t* ) ( data + 6 );
    if( *sign == 0x4649464A ) { //JFIF
      return MODULE_IMAGE_TYPE_JPG;
    }
  }

  return MODULE_IMAGE_TYPE_UNKNOWN;
}//GetImageType


PyObject* Module::decode2rgba( PyObject *self, PyObject *args ) {
  Module::InitModule();
  const char *fileName;
  if( !PyArg_ParseTuple( args, "s", &fileName ) ) {
    LOGE( "fileName is NULL" );
    return NULL;
  }
  size_t
    width = 0,
    height = 0;

  FileManagerType fileManager;
  if( !fileManager.FileExists( fileName ) ) {
    LOGE( "File '%s' not fount", fileName );
    return NULL;
  }

  Memory memory, imageDataRGBA;
  bool isTransparent;
  fileManager.GetFile( fileName, memory );

  if( !memory.GetLength() ) {
    LOGE( "[Error] file is too short" );
    return NULL;
  }

  decodeFuncHandlerType *decodeFuncHandler = NULL;

  auto imageType = Module::GetImageType( memory );
  switch( imageType ) {
  case MODULE_IMAGE_TYPE_BMP:
    decodeFuncHandler = Module::DecodeBMP;
    break;
  case MODULE_IMAGE_TYPE_TGA:
    decodeFuncHandler = Module::DecodeTGA;
    break;
  case MODULE_IMAGE_TYPE_JPG:
    decodeFuncHandler = Module::DecodeJPG;
    break;
  case MODULE_IMAGE_TYPE_PNG:
    decodeFuncHandler = Module::DecodePNG;
    break;
  default:
    LOGE( "Unknown format" );
    return NULL;
  }

  if( decodeFuncHandler ) {
    if( decodeFuncHandler( memory, imageDataRGBA, isTransparent, width, height ) ) {
      return Py_BuildValue( "{s:y#,s:i,s:i,s:i}", "data", imageDataRGBA.GetData(), imageDataRGBA.GetLength(), "width", width, "height", height, "length", imageDataRGBA.GetLength() );
    }
  } else {
    return NULL;
  }

  return NULL;
}//decode2rgba


bool Module::DecodeBMP( Memory &inBuffer, Memory &outBuffer, bool &isTransparent, size_t &outWidth, size_t &outHeight ) {
  ImageType_BMP_FileHeader *fileHeader;
  ImageType_BMP_InfoHeader *infoHeader;
  size_t x, y;
  size_t srcPos, destPos;
  isTransparent = false;

  if( inBuffer.GetLength() < sizeof( ImageType_BMP_FileHeader ) + sizeof( ImageType_BMP_InfoHeader ) ) {
    LOGE( "ImageLoader::LoadBMP => data too short" );
      return NULL;
  }

  uint8_t *data = inBuffer.GetData();
  fileHeader = (ImageType_BMP_FileHeader*) data;
  infoHeader = (ImageType_BMP_InfoHeader*) ( data + sizeof( ImageType_BMP_FileHeader ) );

  outWidth = infoHeader->biWidth;
  outHeight = infoHeader->biHeight;
  outBuffer.Alloc( outWidth * outHeight * 4 );

  uint32_t *dataDest = ( uint32_t* ) outBuffer.GetData();
  switch( infoHeader->biBitCount )
  {
    case 24: {
      for( y = 0; y < outHeight; ++y ) {
        for( x = 0; x < outWidth; ++x ) {
          destPos = ( outHeight - y - 1 ) * outWidth + x;
          srcPos  = fileHeader->bfOffBits + (y * outWidth + x) * 3;
          dataDest[ destPos ] = COLOR_ARGB(
              0xFF,
              data[ srcPos + 0 ],
              data[ srcPos + 1 ],
              data[ srcPos + 2 ]
          );
        }//x
      }
    }
    break;
    case 32: {
      for( y = 0; y < outHeight; ++y ) {
        for( x = 0; x < outWidth; ++x ) {
          destPos = ( outHeight - y - 1 ) * outWidth + x;
          srcPos  = fileHeader->bfOffBits + (y * outWidth + x) * 4;
          dataDest[ destPos ] = COLOR_ARGB(
              data[ srcPos + 4 ], //255
              data[ srcPos + 0 ],
              data[ srcPos + 1 ],
              data[ srcPos + 2 ]
          );
        }
      }
    }
    break;
    default:
      LOGE( "BMP Failed: bpp %d", infoHeader->biBitCount );
      return false;
    break;
  }//switch

  return true;
}//DecodeBMP


bool Module::DecodeTGA( Memory &inBuffer, Memory &outBuffer, bool &isTransparent, size_t &outWidth, size_t &outHeight ) {
  if( !inBuffer.GetLength() ) {
    LOGE( "No data or file too short" );
    return false;
  }

  unsigned char *data = inBuffer.GetData();
  unsigned char idLength = data[ 0 ];
  if( data[ 1 ] ) {
    LOGE( "ImageLoader::LoadTGA => idLength" );
    return false;
  }

  unsigned char compressed = data[ 2 ]; //RLE-compression
  if( !( compressed == 2 || compressed == 0x0A ) ) {
    LOGE( "ImageLoader::LoadTGA => unknown compression" );
    return false;
  }

  unsigned short
    *w = ( unsigned short* ) ( data + 12 ),
    *h = ( unsigned short* ) ( data + 14 );
  outWidth = *w;
  outHeight = *h;

  unsigned char bpp = data[ 16 ];
  if( !( bpp == 24 || bpp == 32 ) ) {
    LOGE( "ImageLoader::LoadTGA => unknown bpp[%d]", bpp );
    return false;
  }

  size_t src_pos = 18 + idLength;

  isTransparent = false;
  outBuffer.Alloc( outWidth * outHeight * 4 );
  unsigned char *dest = outBuffer.GetData();

  if( compressed == 2 ) { //not compressed
    size_t x, y;
    unsigned char mult = bpp >> 3;
    for( y = 0; y < outHeight; y++) {
      for( x = 0; x < outWidth; x++) {
        size_t dest_pos = ( x + y * outWidth ) << 2;
        src_pos  = ( x + y * outWidth ) * mult + 18;
        dest[ dest_pos     ] = data[ src_pos + 2 ];
        dest[ dest_pos + 1 ] = data[ src_pos + 1 ];
        dest[ dest_pos + 2 ] = data[ src_pos + 0 ];
        dest[ dest_pos + 3 ] = ( bpp == 32 ? data[ src_pos + 3 ] : 255);
        if( bpp == 32 && data[ src_pos + 3 ] != 0xFF ) {
          isTransparent = true;
        }
      }//x
    }//y
  } else { //RLE-compression 0x0A
    size_t src_pos = 18 + idLength, dest_pos = 0;
    unsigned char q;
    unsigned char r, g, b, a = 255;
    size_t x = 0, y = 0;
    while( y < outHeight ) {
      unsigned char block = data[ src_pos++ ];
      unsigned char num = block & 127;

      if( block & 128 ) { //compressed block
        b = data[ src_pos ];
        g = data[ src_pos + 1 ];
        r = data[ src_pos + 2 ];
        if( bpp == 32 ) {
          a = data[ src_pos + 3 ];
          src_pos += 4;
        } else {
          src_pos += 3;
        }
        for( q = 0; q < num + 1; ++q ) {
          dest_pos = ( x + y * outWidth ) << 2;
          dest[ dest_pos ] = r;
          dest[ dest_pos + 1 ] = g;
          dest[ dest_pos + 2 ] = b;
          dest[ dest_pos + 3 ] = a;
          if( a != 0xFF ) {
            isTransparent = true;
          }

          x = ( x + 1 ) % outWidth;
          if( !x ) {
            ++y;
          }
        }
      } else { //not compressed block
        for( q = 0; q < num + 1; ++q ) {
          dest_pos = ( x + y * outWidth ) << 2;
          b = data[ src_pos ];
          g = data[ src_pos + 1 ];
          r = data[ src_pos + 2 ];
          if( bpp == 32 ) {
            a = data[ src_pos + 3 ];
            src_pos += 4;
          } else {
            src_pos += 3;
          }

          dest[ dest_pos ] = r;
          dest[ dest_pos + 1 ] = g;
          dest[ dest_pos + 2 ] = b;
          dest[ dest_pos + 3 ] = a;
          if( a != 0xFF ) {
            isTransparent = true;
          }

          x = ( x + 1 ) % outWidth;
          if( !x ) {
            ++y;
          }
        }//for q < num
      }//not compressed block
    }//while y < outHeight
  }//RLE-compression

  return true;
}//DecodeTGA


bool Module::DecodeJPG( Memory &inBuffer, Memory &outBuffer, bool &isTransparent, size_t &outWidth, size_t &outHeight ) {
  isTransparent = false;
  jpeg_decompress_struct	    cinfo;
  ImgJpg::_gImporterJPEGError	jerr;

  MemoryReader file;
  file.SetSource( inBuffer.GetData(), inBuffer.GetLength() );

  cinfo.err = jpeg_std_error( &jerr.pub );
  jerr.pub.error_exit = ImgJpg::JPEGErrorExit;

  if( setjmp(jerr.setjmp_buffer) )
  {
	  jpeg_destroy_decompress( &cinfo );
	  file.Free();
    return false;
  }
  jpeg_create_decompress( &cinfo );
  ImgJpg::JPEGStdioSrcgMemoryReader( &cinfo, &file );
  jpeg_read_header( &cinfo, TRUE );
  jpeg_start_decompress( &cinfo );
  int row_stride = cinfo.output_width * cinfo.output_components;
  Memory temp_mem( cinfo.output_height * row_stride );
  JSAMPARRAY bufferNew = ( *cinfo.mem->alloc_sarray )( ( j_common_ptr ) &cinfo, JPOOL_IMAGE, row_stride, 1 );
  memset( *bufferNew, 0, sizeof(JSAMPLE) * row_stride );

  int y = 0;
  while( cinfo.output_scanline < cinfo.output_height )
  {
	  jpeg_read_scanlines( &cinfo, bufferNew, 1 );
    uint8_t* temp = ( uint8_t* ) temp_mem.GetData() + ( ( cinfo.output_height - y - 1 ) * row_stride );
	  memcpy( temp, bufferNew[0], row_stride );
	  ++y;
  }

  outWidth = cinfo.image_width;
  outHeight = cinfo.image_height;

  {
    uint32_t x, y;
    int pos3b, pos4b;
    outBuffer.Alloc( outHeight * outWidth * 4 );
    uint8_t *src_mem = (uint8_t*) temp_mem.GetData(), *dest_mem = (uint8_t*) outBuffer.GetData();
    for( y = 0; y < outHeight; ++y )
    for( x = 0; x < outWidth; ++x )
    {
      pos3b = ( x + y * outWidth ) * 3;
      pos4b = ( x + y * outWidth ) * 4;
      dest_mem[ pos4b    ] = src_mem[ pos3b + 0 ];
      dest_mem[ pos4b + 1] = src_mem[ pos3b + 1 ];
      dest_mem[ pos4b + 2] = src_mem[ pos3b + 2 ];
      dest_mem[ pos4b + 3] = 255;
    }
  }
  temp_mem.Free();

  jpeg_finish_decompress( &cinfo );
  jpeg_destroy_decompress( &cinfo );
  file.Free();

  return true;
}//DecodeJPG


bool Module::DecodePNG( Memory &inBuffer, Memory &outBuffer, bool &isTransparent, size_t &outWidth, size_t &outHeight ) {
  png_structp   png_ptr;
  png_infop     info_ptr;
  png_uint_32   img_width = 0, img_height = 0;
  int           bit_depth = 0, color_type = 0, interlace_type = 0;

  MemoryReader memReader;
  memReader.SetSource( inBuffer.GetData(), inBuffer.GetLength() );
  Memory data_mem( 256 );
  char *pdata = ( char* ) data_mem.GetData();

  memReader.Read( pdata, 4 );
  if( !png_check_sig( ( uint8_t* ) pdata ,4 ) )
  {
    memReader.Free();
    return false;
  }
  png_ptr = png_create_read_struct( PNG_LIBPNG_VER_STRING, 0, 0, 0 );
  if( png_ptr == NULL )
  {
    memReader.Free();
    return false;
  }
  info_ptr = png_create_info_struct( png_ptr );
  if( info_ptr == NULL )
  {
    memReader.Free();
    return false;
  }
  memReader.SeekFromStart( 4 );
  png_set_read_fn( png_ptr, ( void* ) &memReader, ImgPng::PNGReadFunctiongMemoryReader );

  png_set_sig_bytes( png_ptr, 4 );

  png_read_info( png_ptr, info_ptr );
  png_get_IHDR( png_ptr, info_ptr, &img_width, &img_height, &bit_depth,
    &color_type, &interlace_type, 0, 0 );
  if( bit_depth == 16 )
    png_set_strip_16( png_ptr );
  if( color_type == PNG_COLOR_TYPE_PALETTE && bit_depth <= 8 )
    png_set_palette_to_rgb( png_ptr );
  if( color_type == PNG_COLOR_TYPE_GRAY && bit_depth < 8 )
    png_set_gray_1_2_4_to_8( png_ptr );
  if( png_get_valid( png_ptr, info_ptr, PNG_INFO_tRNS ) )
    png_set_tRNS_to_alpha( png_ptr );
  if( color_type == PNG_COLOR_TYPE_GRAY || color_type == PNG_COLOR_TYPE_GRAY_ALPHA )
    png_set_gray_to_rgb( png_ptr );
  double gamma = 0.0;
  if( png_get_gAMA( png_ptr, info_ptr, &gamma ) )
    png_set_gamma( png_ptr, 2.2, gamma );
  else
    png_set_gamma( png_ptr, 2.2, 0.45455 );
  png_read_update_info( png_ptr, info_ptr );
  png_get_IHDR( png_ptr, info_ptr, &img_width, &img_height, &bit_depth, &color_type, 0, 0, 0 );
  png_uint_32 row_bytes = png_get_rowbytes( png_ptr, info_ptr );
  data_mem.Alloc( img_height * row_bytes );
  pdata = ( char* ) data_mem.GetData();
  png_byte **row_pointers = new png_byte * [ img_height ];
  for( unsigned int i = 0; i < img_height; ++i )
    row_pointers[ i ] = ( uint8_t* ) pdata + i * row_bytes;
  png_read_image( png_ptr, row_pointers );
  png_destroy_read_struct( &png_ptr, 0, 0 );
  if( row_pointers ) {
    delete row_pointers;
    row_pointers = 0;
  }
  memReader.Free();

  outWidth = img_width;
  outHeight = img_height;
  outBuffer.Alloc( outWidth * outHeight * 4 );

  if( color_type == PNG_COLOR_TYPE_RGB ) {
    uint32_t x, y, pos1, pos2;
    Byte *dataDest = ( Byte* ) outBuffer.GetData();
    for( y = 0; y < outHeight; ++y )
    for( x = 0; x < outWidth; ++x )
    {
      pos1 = x * 3 + row_bytes * y;
      pos2 = ( x + y * outWidth ) << 2;
      dataDest[ pos2     ] = pdata[ pos1 + 0 ];
      dataDest[ pos2 + 1 ] = pdata[ pos1 + 1 ];
      dataDest[ pos2 + 2 ] = pdata[ pos1 + 2 ];
      dataDest[ pos2 + 3 ] = 0xFF;
    }
    isTransparent = false;
  }
  else
  if( color_type == PNG_COLOR_TYPE_RGB_ALPHA ) {
    uint32_t x, y, pos;
    Byte *dataDest = ( Byte* ) outBuffer.GetData();
    for( y = 0; y < outHeight; ++y)
    for( x = 0; x < outWidth; ++x)
    {
      pos = ( x + y * outWidth ) << 2;
      dataDest[ pos     ] = pdata[ pos + 0 ];
      dataDest[ pos + 1 ] = pdata[ pos + 1 ];
      dataDest[ pos + 2 ] = pdata[ pos + 2 ];
      dataDest[ pos + 3 ] = pdata[ pos + 3 ];
      if( pdata[ pos + 3 ] != 0xFF ) {
        isTransparent = true;
      }
    }
  }

  return true;
}//DecodePNG


PyObject* Module::jpg2rgba( PyObject *self, PyObject *args ) {
  Module::InitModule();
  const char *fileName;
  if( !PyArg_ParseTuple( args, "s", &fileName ) ) {
    LOGE( "fileName is NULL" );
    return NULL;
  }
  size_t
    width = 0,
    height = 0;
  bool isTransparent = false;

  FileManagerType fileManager;
  if( !fileManager.FileExists( fileName ) ) {
    LOGE( "File '%s' not fount", fileName );
    return NULL;
  }

  Memory memory, imageDataRGBA;
  fileManager.GetFile( fileName, memory );

  Module::DecodeJPG( memory, imageDataRGBA, isTransparent, width, height );

  return Py_BuildValue( "{s:y#,s:i,s:i,s:i}", "data", imageDataRGBA.GetData(), imageDataRGBA.GetLength(), "width", width, "height", height, "length", imageDataRGBA.GetLength() );
}//jpg2rgba


PyObject* Module::png2rgba( PyObject *self, PyObject *args ) {
  Module::InitModule();
  const char *fileName;
  if( !PyArg_ParseTuple( args, "s", &fileName ) ) {
    LOGE( "fileName is NULL" );
    return NULL;
  }
  size_t
    width = 0,
    height = 0;
  bool isTransparent = false;

  FileManagerType fileManager;
  if( !fileManager.FileExists( fileName ) ) {
    LOGE( "File '%s' not fount", fileName );
    return NULL;
  }

  Memory memory, imageDataRGBA;
  fileManager.GetFile( fileName, memory );

  Module::DecodePNG( memory, imageDataRGBA, isTransparent, width, height );

  return Py_BuildValue( "{s:y#,s:i,s:i,s:i}", "data", imageDataRGBA.GetData(), imageDataRGBA.GetLength(), "width", width, "height", height, "length", imageDataRGBA.GetLength() );
}//png2rgba


PyObject* Module::bmp2rgba( PyObject *self, PyObject *args ) {
  Module::InitModule();
  const char *fileName;
  if( !PyArg_ParseTuple( args, "s", &fileName ) ) {
    LOGE( "fileName is NULL" );
    return NULL;
  }
  size_t
    width = 0,
    height = 0;
  bool isTransparent = false;

  FileManagerType fileManager;
  if( !fileManager.FileExists( fileName ) ) {
    LOGE( "File '%s' not fount", fileName );
    return NULL;
  }

  Memory memory, imageDataRGBA;
  fileManager.GetFile( fileName, memory );

  Module::DecodeBMP( memory, imageDataRGBA, isTransparent, width, height );

  return Py_BuildValue( "{s:y#,s:i,s:i,s:i}", "data", imageDataRGBA.GetData(), imageDataRGBA.GetLength(), "width", width, "height", height, "length", imageDataRGBA.GetLength() );
}//bmp2rgba


PyObject* Module::tga2rgba( PyObject *self, PyObject *args ) {
  Module::InitModule();
  const char *fileName;
  if( !PyArg_ParseTuple( args, "s", &fileName ) ) {
    LOGE( "fileName is NULL" );
    return NULL;
  }
  size_t
    width = 0,
    height = 0;
  bool isTransparent = false;

  FileManagerType fileManager;
  if( !fileManager.FileExists( fileName ) ) {
    LOGE( "File '%s' not fount", fileName );
    return NULL;
  }

  Memory memory, imageDataRGBA;
  fileManager.GetFile( fileName, memory );

  Module::DecodeTGA( memory, imageDataRGBA, isTransparent, width, height );

  return Py_BuildValue( "{s:y#,s:i,s:i,s:i}", "data", imageDataRGBA.GetData(), imageDataRGBA.GetLength(), "width", width, "height", height, "length", imageDataRGBA.GetLength() );
}//tga2rgba


PyObject* Module::free( PyObject *self, PyObject *args ) {
  Module::InitModule();
  for( auto& memory: Module::memoryBlocksList ) {
    delete memory;
  }
  Module::memoryBlocksList.clear();
  return Py_BuildValue( "i", 1 );
}//free


bool Module::GetImageFromArguments( PyObject *args, size_t M_OUT &width, size_t M_OUT &height, Memory M_OUT &rgbaData, std::string M_OUT *format, int M_OUT *quality ) {
  Module::InitModule();
  PyObject *parameters;
  if( !PyArg_ParseTuple( args, "O!", &PyDict_Type, &parameters ) ) {
    LOGE( "rgba2dxt1 => need dict as first parameter" );
    return NULL;
  }
  PyObject *items = PyDict_Items( parameters );
  PyObject *keys = PyDict_Keys( parameters );
  rgbaData.Free();
  width = 0;
  height = 0;

  auto size = PyList_Size( items );
  for( int q = 0; q < size; ++q ) {
    PyObject *key = PyList_GetItem( keys, q );
    PyObject *item = PyList_GetItem( items, q );
    std::string name = PyBytes_AsString( PyUnicode_AsASCIIString( key ) );
    if( name == "width" ) {
      auto widthItem = PyTuple_GetItem( item, 1 );
      width = PyLong_AsLong( widthItem );
    } else if( name == "height" ) {
      auto heightItem = PyTuple_GetItem( item, 1 );
      height = PyLong_AsLong( heightItem );
    } else if( name == "data" ) {
      PyObject *bytes = PyTuple_GetItem( item, 1 );
      size_t length = PyBytes_Size( bytes );
      rgbaData.Alloc( length );
      memcpy( rgbaData.GetData(), PyBytes_AsString( bytes ), rgbaData.GetLength() );
    } else if( format && name == "format" ) {
      auto formatItem = PyTuple_GetItem( item, 1 );
      *format = PyBytes_AsString( formatItem );
    } else if( quality && name == "quality" ) {
      auto qualityItem = PyTuple_GetItem( item, 1 );
      *quality = PyLong_AsLong( qualityItem );
    }
  }

  return width && height && rgbaData.GetLength();
}//GetImageFromArguments


PyObject* Module::rgba2dxt1( PyObject *self, PyObject *args ) {
  Module::InitModule();
  return Module::DoDXTCompressFromArgs( args, squish::kDxt1 );
}//rgba2dxt1


PyObject* Module::rgba2dxt3( PyObject *self, PyObject *args ) {
  Module::InitModule();
  return Module::DoDXTCompressFromArgs( args, squish::kDxt3 );
}//rgba2dxt3


PyObject* Module::rgba2dxt5( PyObject *self, PyObject *args ) {
  Module::InitModule();
  return Module::DoDXTCompressFromArgs( args, squish::kDxt5 );
}//rgba2dxt5


PyObject* Module::DoDXTCompressFromArgs( PyObject* M_IN args, int format ) {
  Memory compressedData;
  size_t
    width = 0,
    height = 0;
  if( Module::CompressSquish( args, compressedData, width, height, format ) ) {
    return Py_BuildValue( "{s:y#,s:i,s:i,s:i}", "data", compressedData.GetData(), compressedData.GetLength(), "width", width, "height", height, "length", compressedData.GetLength() );
  }

  return Py_BuildValue( "i", 0 );
}//DoDXTCompressFromArgs


bool Module::CompressSquish( PyObject* M_IN args, Memory M_OUT &compressedData, size_t M_OUT &width, size_t M_OUT &height, int format ) {
  Memory rgbaData;
  GetImageFromArguments( args, width, height, rgbaData );

  if( width % 4 || height % 4 ) {
    LOGE( "Bad image size[%dx%d]: must be multiplies by 4", width, height );
    return false;
  }

  const size_t resultSize = squish::GetStorageRequirements( width, height, format );
  compressedData.Alloc( resultSize );
  squish::CompressImage( rgbaData.GetData(), width, height, compressedData.GetData(), format );

  return true;
}//CompressSquish



PyObject* Module::rgba2etc1( PyObject *self, PyObject *args ) {
  Module::InitModule();
  return Module::DoETC1CompressFromArgs( args );
}//rgba2etc1


PyObject* Module::DoETC1CompressFromArgs( PyObject* M_IN args ) {
  Memory compressedData;
  size_t
    width = 0,
    height = 0;
  int quality = 0;
  if( Module::CompressETC1( args, compressedData, width, height, quality ) ) {
    return Py_BuildValue( "{s:y#,s:i,s:i,s:i}", "data", compressedData.GetData(), compressedData.GetLength(), "width", width, "height", height, "length", compressedData.GetLength() );
  }

  return Py_BuildValue( "i", 0 );
}//DoETC1CompressFromArgs


bool Module::CompressETC1( PyObject* M_IN args, Memory M_OUT &compressedData, size_t M_OUT &width, size_t M_OUT &height, int M_OUT &quality ) {
  Memory rgbaData;
  GetImageFromArguments( args, width, height, rgbaData, NULL, &quality );

  if( width % 4 || height % 4 ) {
    LOGE( "Bad image size[%dx%d]: must be multiplies by 4", width, height );
    return false;
  }

  Module::EncodeETC1( rgbaData, width, height, compressedData, quality );

  return true;
}//CompressETC1



///////////////////////////////////////////////
///////////////////////////////////////////////
const int ImgJpg::c_JPEGInputBufferSize = 4096;

void ImgJpg::JPEGErrorExit( j_common_ptr cinfo ) {
  ImgJpg::_gImporterJPEGError* myerr = ( ImgJpg::_gImporterJPEGError* ) cinfo->err;
  ( *cinfo->err->output_message )( cinfo );
  longjmp( myerr->setjmp_buffer, 1 );
}//JPEGErrorExit

struct _gImporterJPEGSourcegMemoryReader {
    jpeg_source_mgr pub;
    MemoryReader *file;
    JOCTET *buffer;
    bool sof;
};

boolean JPEGFillInputBuffergMemoryReader( j_decompress_ptr cinfo ) {
  _gImporterJPEGSourcegMemoryReader* src = ( _gImporterJPEGSourcegMemoryReader* ) cinfo->src;
  size_t nbytes = src->file->Read( src->buffer, sizeof( JOCTET ), ImgJpg::c_JPEGInputBufferSize );
  if( nbytes <= 0 ) {
    if( src->sof ) {
      return FALSE;
    }
    src->buffer[ 0 ] = ( JOCTET ) 0xFF;
    src->buffer[ 1 ] = ( JOCTET ) JPEG_EOI;
    nbytes = 2;
  }

  src->pub.next_input_byte = src->buffer;
  src->pub.bytes_in_buffer = nbytes;
  src->sof = false;
  return TRUE;
}//JPEGFillInputBuffergMemoryReader

void JPEGInitSourcegMemoryReader( j_decompress_ptr cinfo ) {
	_gImporterJPEGSourcegMemoryReader* src = ( _gImporterJPEGSourcegMemoryReader* ) cinfo->src;
	src->sof = true;
}//JPEGInitSourcegMemoryReader

void JPEGSkipInputDatagMemoryReader( j_decompress_ptr cinfo, long num_bytes ) {
	_gImporterJPEGSourcegMemoryReader* src = ( _gImporterJPEGSourcegMemoryReader* ) cinfo->src;
	if( num_bytes <= 0 ) {
    return;
  }
	while( num_bytes > ( long ) src->pub.bytes_in_buffer ) {
		num_bytes -= ( long ) src->pub.bytes_in_buffer;
		JPEGFillInputBuffergMemoryReader( cinfo );
	}
	src->pub.next_input_byte += ( size_t ) num_bytes;
	src->pub.bytes_in_buffer -= ( size_t ) num_bytes;
}//JPEGSkipInputDatagMemoryReader

void JPEGTermSource( j_decompress_ptr cinfo ) { }

void ImgJpg::JPEGStdioSrcgMemoryReader( j_decompress_ptr cinfo, MemoryReader* file ) {
  _gImporterJPEGSourcegMemoryReader *src = 0;
  if( cinfo->src == 0 ) {
    cinfo->src = ( struct jpeg_source_mgr * ) ( *cinfo->mem->alloc_small ) 
      ( ( j_common_ptr ) cinfo, JPOOL_PERMANENT, sizeof( _gImporterJPEGSourcegMemoryReader ) );
    src = ( _gImporterJPEGSourcegMemoryReader* ) cinfo->src;
    src->buffer = ( JOCTET* ) ( *cinfo->mem->alloc_small ) 
      ( ( j_common_ptr ) cinfo, JPOOL_PERMANENT, ImgJpg::c_JPEGInputBufferSize * sizeof( JOCTET ) );
    memset( src->buffer, 0, ImgJpg::c_JPEGInputBufferSize * sizeof( JOCTET ) );
  }
  src = ( _gImporterJPEGSourcegMemoryReader* ) cinfo->src;
  src->pub.init_source = JPEGInitSourcegMemoryReader;
  src->pub.fill_input_buffer = JPEGFillInputBuffergMemoryReader;
  src->pub.skip_input_data = JPEGSkipInputDatagMemoryReader;
  src->pub.resync_to_restart = jpeg_resync_to_restart;
  src->pub.term_source = JPEGTermSource;
  src->file = file;
  src->pub.bytes_in_buffer = 0;
  src->pub.next_input_byte = 0;
}//JPEGStdioSrcgMemoryReader

void ImgPng::PNGReadFunctiongMemoryReader( png_structp png_ptr, png_bytep data, png_size_t length ) {
  MemoryReader *file = ( MemoryReader* ) png_get_io_ptr( png_ptr );
  file->Read( data, long( length ) );
}//PNGReadFunctiongMemoryReader
