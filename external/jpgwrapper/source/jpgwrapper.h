#ifndef JpgWrapper
	#define JpgWrapper

	#include <cstdio>
	#include <cstring>
	#include <csetjmp>

	#include "libjpeg/jpeglib.h"
	#include "./buffer.h"

	GLOBAL(bool)ConvertToJpg(Buffer &source, Buffer &target, int width, int height, int bytespp, int quality, bool progressive, bool bottomUp);
	GLOBAL(bool)DecompressJpg(Buffer &source, Buffer &target, int &width, int &height, int &bytespp);
#endif
