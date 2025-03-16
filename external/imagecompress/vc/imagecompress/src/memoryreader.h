/*==============================
  Класс MemoryReader
  Класс работы с буффером как с файлом
==============================*/

#pragma once

#include "memory.h"
#include "tools.h"
#include <string>

class MemoryReader
{
private:
  Memory  data;
  size_t  curPos,
          curLength;
  uint8_t *curData;  //либо указатель на data либо на внешний блок
  MemoryReader( MemoryReader& );
  MemoryReader& operator=( MemoryReader& );

public:
  MemoryReader();
  MemoryReader( Memory &source );
  virtual ~MemoryReader();

  void    SetSource     ( void *srcData, size_t length );
  void    CopyFromSource( void *srcData, size_t length );
  int     Read          ( void *dest, size_t len );
  size_t  Read          ( void *dest, size_t len, size_t numBlocks );
  void    Free          ();
  void    SeekFromStart ( size_t pos );
  void    SeekFromCur   ( long dpos );
  inline
    int   GetCurPos     () { return this->curPos; }

  void operator>>( std::string &str );

  template< class T >
  void operator>>( T &data );

  bool CheckSizeToRead( size_t sizeToRead );

  template< class T >
  bool CheckDataSizeToRead( T dataToRead );
};


template< class T >
void MemoryReader::operator>>( T &data ) {
  if( !this->CheckDataSizeToRead( data ) ) {
    LOGE( "MemoryReader::operator>> => out of bounds" );
    return;
  }
  memcpy( &data, this->curData + this->curPos, sizeof( data ) );
  this->curPos += sizeof( data );
}//operator>>

template< class T >
bool MemoryReader::CheckDataSizeToRead( T dataToRead ) {
  return this->CheckSizeToRead( sizeof( dataToRead ) );
}//CheckDataSizeToRead
