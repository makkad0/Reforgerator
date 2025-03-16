#ifndef BUFFER_H
	#define BUFFER_H

	typedef struct Buffer {
		char *buf;
		unsigned long length;
		Buffer() {
			buf = 0;
			length = 0;
		}
		Buffer(unsigned long l) {
			length = l;
			buf = new char[l];
		}
		Buffer(char* b, unsigned long l) {
			buf = b;
			length = l;
		}
	} Buffer;

	typedef struct BufferList {
		char **buf;
		unsigned long length;
		BufferList() {
			buf = 0;
			length = 0;
		}
		BufferList(unsigned long l) {
			buf = new char*[l];
			length = l;
		}
		BufferList(char** b, unsigned long l) {
			buf = b;
			length = l;
		}
	} BufferList;
#endif
