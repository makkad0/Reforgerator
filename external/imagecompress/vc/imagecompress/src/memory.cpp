#include "memory.h"
#include "string.h"

Memory::Memory()
:length( 0 ), data( 0 ) {
}

Memory::~Memory() {
  this->Free();
}

Memory::Memory( size_t setLength )
:length( 0 ) {
  this->Alloc( setLength );
}

Memory::Memory( Memory& copyFrom ) {
  if( copyFrom.length ) {
    this->Alloc( copyFrom.length );
    memcpy( this->data, copyFrom.data, copyFrom.length );
  }
}

void Memory::Alloc( size_t setLength, bool nullMemory ) {
  if( this->length ) {
    this->Free();
  }

  if( !setLength ) {
    return;
  }

  this->data = new unsigned char[ setLength ];
  this->length = setLength;

  if( nullMemory ) {
    memset( this->data, 0, this->length );
  }
}//Alloc

void Memory::Free() {
  if( this->length ) {
    delete [] this->data;
    this->data = 0;
    this->length = 0;
  }
}//Free

void Memory::Resize( size_t setLength, bool nullNewMemory ) {
  if( setLength == this->length ) {
    return;
  }
  if( !setLength ) {
    this->Free();
    return;
  }
  size_t copyLength = ( setLength > this->length ? this->length : setLength );
  size_t oldLength = this->length;
  Memory tmp( copyLength );
  memcpy( tmp.data, this->data, copyLength );
  this->Alloc( setLength );
  memcpy( this->data, tmp.data, copyLength );

  if( nullNewMemory && this->length > oldLength ) {
    memset( this->data + oldLength, 0, this->length - oldLength );
  }
}//Resize

Memory& Memory::operator=( Memory& copyFrom ) {
  if( this->length != copyFrom.length ) {
    this->Alloc( copyFrom.length );
  }

  if( this->length ) {
    memcpy( this->data, copyFrom.data, this->length );
  }

  return *this;
}//operator= Memory
