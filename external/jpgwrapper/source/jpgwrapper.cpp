#include "jpgwrapper.h"

typedef struct {
	struct jpeg_destination_mgr pub; /* base class */
	JOCTET* buffer; /* buffer start address */
	int bufsize; /* size of buffer */
	size_t datasize; /* final size of compressed data */
	int* outsize; /* user pointer to datasize */
	int errcount; /* counts up write errors due to buffer overruns */
} memory_destination_mgr;

typedef memory_destination_mgr* mem_dest_ptr;

METHODDEF(void) init_destination(j_compress_ptr cinfo) {
	mem_dest_ptr dest = (mem_dest_ptr)cinfo->dest;
	dest->pub.next_output_byte = dest->buffer; /* set destination buffer */
	dest->pub.free_in_buffer = dest->bufsize; /* input buffer size */
	dest->datasize = 0; /* reset output size */
	dest->errcount = 0; /* reset error count */
}

METHODDEF(boolean) empty_output_buffer(j_compress_ptr cinfo) {
	mem_dest_ptr dest = (mem_dest_ptr)cinfo->dest;
	dest->pub.next_output_byte = dest->buffer;
	dest->pub.free_in_buffer = dest->bufsize;
	++dest->errcount; /* need to increase error count */
	return TRUE;
}

METHODDEF(void) term_destination(j_compress_ptr cinfo) {
	mem_dest_ptr dest = (mem_dest_ptr)cinfo->dest;
	dest->datasize = dest->bufsize - dest->pub.free_in_buffer;
	if (dest->outsize) *dest->outsize += (int)dest->datasize;
}

GLOBAL(void) jpeg_memory_dest(j_compress_ptr cinfo, JOCTET* buffer, int bufsize, int* outsize) {
	mem_dest_ptr dest;
	if (cinfo->dest == 0) {
		cinfo->dest = (struct jpeg_destination_mgr*)(*cinfo->mem->alloc_small)((j_common_ptr)cinfo, JPOOL_PERMANENT, sizeof(memory_destination_mgr));
	}
	dest = (mem_dest_ptr)cinfo->dest;
	dest->bufsize = bufsize;
	dest->buffer = buffer;
	dest->outsize = outsize;
	dest->pub.init_destination = init_destination;
	dest->pub.empty_output_buffer = empty_output_buffer;
	dest->pub.term_destination = term_destination;
}

METHODDEF(void) init_source(j_decompress_ptr dinfo)
{
}

METHODDEF(boolean) fill_input_buffer(j_decompress_ptr dinfo)
{
	return FALSE;
}

METHODDEF(void) skip_input_data(j_decompress_ptr dinfo, long num_bytes)
{
	if ((size_t)num_bytes > dinfo->src->bytes_in_buffer) {
		dinfo->src->next_input_byte = 0; // no buffer byte
		dinfo->src->bytes_in_buffer = 0; // no input left
	} else {
		dinfo->src->next_input_byte += num_bytes;
		dinfo->src->bytes_in_buffer -= num_bytes;
	}
}

METHODDEF(void) term_source (j_decompress_ptr dinfo)
{
}

GLOBAL(void) jpeg_memory_src(j_decompress_ptr dinfo, unsigned char* buffer, size_t size)
{
	struct jpeg_source_mgr* src;
	if (dinfo->src == 0) {
		dinfo->src = (struct jpeg_source_mgr *)(*dinfo->mem->alloc_small)((j_common_ptr)dinfo, JPOOL_PERMANENT, sizeof(struct jpeg_source_mgr));
	}
	src = dinfo->src;
	src->next_input_byte = buffer;
	src->bytes_in_buffer = size;
	src->init_source = init_source;
	src->fill_input_buffer = fill_input_buffer;
	src->skip_input_data = skip_input_data;
	src->term_source = term_source;
	src->resync_to_restart = jpeg_resync_to_restart;
}

typedef struct {
  struct jpeg_error_mgr pub; /* base class */
  jmp_buf setjmp_buffer; /* for return to caller */
} returnctrl_error_mgr;

typedef returnctrl_error_mgr* return_error_ptr;

METHODDEF(void) return_error_exit(j_common_ptr cinfo)
{
  return_error_ptr myerr = (return_error_ptr)cinfo->err;
  (*cinfo->err->output_message)(cinfo); /* display error msg */
  longjmp(myerr->setjmp_buffer, 1); /* return control to the setjmp point */
}

GLOBAL(bool)ConvertToJpg(Buffer &source, Buffer &target, int width, int height, int bytespp, int quality, bool progressive, bool bottomUp)
{
	int numBytes = 0; //size of jpeg after compression
	int dummySize = ((width * height * 4) * 2) + 10000; // max possible size
	char *storage = new char[dummySize]; //storage buffer
	struct jpeg_compress_struct cinfo;
	returnctrl_error_mgr jerr;
	JSAMPROW row_pointer[1];
	cinfo.err = jpeg_std_error(&jerr.pub);
	jerr.pub.error_exit = return_error_exit;
	if (setjmp(jerr.setjmp_buffer)) { // return_error_exit returns here
		jpeg_destroy_compress(&cinfo); // cleanup
		delete[] storage;
		return false;
	}

	jpeg_create_compress(&cinfo);
	JOCTET *jpgbuff = (JOCTET*)storage;
	jpeg_memory_dest(&cinfo, jpgbuff, dummySize, &numBytes);
	cinfo.image_width = width;
	cinfo.image_height = height;
	cinfo.input_components = bytespp;
	cinfo.in_color_space = JCS_UNKNOWN;
	jpeg_set_defaults(&cinfo);
	jpeg_set_quality(&cinfo, quality, TRUE);
	if (progressive) {
		jpeg_simple_progression(&cinfo);  // Enable progressive JPEG mode
	}
	jpeg_start_compress(&cinfo, TRUE);
	int stride = width * bytespp;

	if (bottomUp) {
		while (cinfo.next_scanline < cinfo.image_height) {
			row_pointer[0] = (JSAMPLE*)&source.buf[(cinfo.image_height - cinfo.next_scanline - 1) * stride];
			(void)jpeg_write_scanlines(&cinfo, row_pointer, 1);
		}
	} else {
		while (cinfo.next_scanline < cinfo.image_height) {
			row_pointer[0] = (JSAMPLE*)&source.buf[cinfo.next_scanline * stride];
			(void)jpeg_write_scanlines(&cinfo, row_pointer, 1);
		}
	}
	jpeg_finish_compress(&cinfo);
	jpeg_destroy_compress(&cinfo); // cleanup

	if (numBytes <= 0) {
		fprintf(stderr, "Conversion to jpg failed ...");
		delete[] storage;
		return false;
	}

	target.buf = new char[numBytes];
	target.length = numBytes;
	memcpy(target.buf, storage, numBytes);
	delete[] storage;
	return true;
}

GLOBAL(bool)DecompressJpg(Buffer &source, Buffer &target, int &width, int &height, int &bytespp)
{
	struct jpeg_decompress_struct cinfo;
	returnctrl_error_mgr jerr;
	JSAMPARRAY buffer;
	int stride;
	cinfo.err = jpeg_std_error(&jerr.pub);
	jerr.pub.error_exit = return_error_exit;
	if (setjmp(jerr.setjmp_buffer)) { // return_error_exit returns here
		jpeg_destroy_decompress(&cinfo); // cleanup
		if (target.buf)
			delete[] target.buf;
		return false;
	}

	jpeg_create_decompress(&cinfo);
	jpeg_memory_src(&cinfo, (unsigned char*)source.buf, source.length);
	(void)jpeg_read_header(&cinfo, TRUE);
	(void)jpeg_start_decompress(&cinfo);
	stride = cinfo.output_width * cinfo.output_components;
	char* tempbuf = new char[stride * cinfo.output_height];
	buffer = (*cinfo.mem->alloc_sarray)((j_common_ptr)&cinfo, JPOOL_IMAGE, stride, 1);
	width = cinfo.output_width;
	height = cinfo.output_height;
	bytespp = cinfo.output_components;
	while (cinfo.output_scanline < height) {
		(void)jpeg_read_scanlines(&cinfo, buffer, 1);
		memcpy(&tempbuf[(height - cinfo.output_scanline) * stride], buffer[0], stride);
	}
	if (bytespp >= 3) {
		target.buf = tempbuf;
		target.length = stride * cinfo.output_height;
		for (int i = 0; i < width * height; i++) { // swap R and B
			char temp = target.buf[i * bytespp + 2];
			target.buf[i * bytespp + 2] = target.buf[i * bytespp];
			target.buf[i * bytespp] = temp;
		}
	}
	(void)jpeg_finish_decompress(&cinfo);
	jpeg_destroy_decompress(&cinfo);
	return true;
}
