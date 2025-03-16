#include "memoryreader.h"
#include "tools.h"


MemoryReader::MemoryReader()
  :curPos( 0 ), curLength( 0 ), curData( NULL )
{
}//constructor


MemoryReader::MemoryReader( Memory &source )
:curPos( 0 )
{
  this->curData = source.GetData();
  this->curLength = source.GetLength();
  this->curPos = 0;
}//constructor


MemoryReader::~MemoryReader()
{
}//destructor


/*
----------
  Read
  Чтение блока
----------
*/
int MemoryReader::Read( void *dest, size_t length )
{
  size_t realLen = ( length < this->curLength - this->curPos ? length : this->curLength - this->curPos );

  memcpy( dest, this->curData + this->curPos, realLen );
  this->curPos += realLen;

  return realLen;
}//Read


/*
----------
  Read
  Чтение нескольких блоков
----------
*/
size_t MemoryReader::Read( void *dest, size_t length, size_t numBlocks )
{
  size_t realLen = Min2( length * numBlocks, this->curLength - this->curPos );
  size_t ret;
  if( realLen < length * numBlocks )
    ret = size_t( realLen / length );
  else
    ret = numBlocks;

  memcpy( dest, this->curData + this->curPos, realLen );
  this->curPos += realLen;

  return ret;
}//Read


/*
----------
  SetSource
  Установка источника данных
----------
*/
void MemoryReader::SetSource( void *srcData, size_t length )
{
  this->curData = ( uint8_t* ) srcData;
  this->curLength = length;
  this->curPos = 0;
}//SetSource


/*
----------
  CopyFromSource
----------
*/
void MemoryReader::CopyFromSource( void *srcData, size_t length )
{
  if( !srcData )
    return;

  this->data.Alloc( length );
  this->curData = this->data.GetData();
  memcpy( this->curData, srcData, length );
  this->curLength = length;
}//CopyFromSource


/*
----------
  Free
----------
*/
void MemoryReader::Free()
{
  this->data.Free();
  this->curLength = this->curPos = 0;
  this->curData = 0;
}//Free


/*
----------
  SeekFromStart
----------
*/
void MemoryReader::SeekFromStart( size_t pos )
{
  if( pos > this->curLength )
    return;

  this->curPos = pos;
}//SeekFromStart


/*
----------
  SeekFromCur
----------
*/
void MemoryReader::SeekFromCur( long dpos )
{
  if( this->curPos + dpos > this->curLength ) {
    return;
  }

  this->curPos += dpos;
}//SeekFromCur




/*
=============
  CheckSizeToRead
=============
*/
bool MemoryReader::CheckSizeToRead( size_t sizeToWrite )
{
  return ( this->curPos + sizeToWrite <= this->curLength );
}//CheckSizeToRead



/*
=============
  operator>>
=============
*/
void MemoryReader::operator>>( std::string &str )
{
  size_t strLen;
  this->operator >>( strLen );
  if( !this->CheckSizeToRead( strLen ) ) {
    LOGE( "MemoryReader::operator>> => out of bounds" );
    str = "";
    return;
  }

  Memory tmp( strLen + 1 );
  memcpy( tmp.GetData(), this->curData + this->curPos, strLen );
  tmp[ tmp.GetLength() - 1 ] = 0;
  str = ( char* ) tmp.GetData();

  this->curPos += strLen;
}//operator>>
