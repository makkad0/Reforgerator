#include "filemanager.h"
#include "tools.h"
#include <direct.h>

FileManagerWin32::FileManagerWin32() {
}

FileManagerWin32::~FileManagerWin32() {
}

bool FileManagerWin32::FileExists( const std::string &fileName ) const {
  FILE *file;
  std::string name = fileName;
  fopen_s( &file, name.c_str(), "rb" );
  if( !file ) {
    LOGE( "File '%s' not found", name.c_str() );
    return false;
  }
  fclose( file );

  return true;
}//FileExists

bool FileManagerWin32::GetFile( const std::string& fileName, Memory& fileContent, bool endZeroByte ) const {
  std::string name = fileName;
  FILE *file;
  fileContent.Free();
  fopen_s( &file, name.c_str(), "rb" );
  if( !file ) {
    LOGE( "File '%s' not found", name.c_str() );
    return false;
  }
  fseek( file, 0, SEEK_END );
  size_t fileSize = ftell( file );
  if( fileSize ) {
    fseek( file, 0, SEEK_SET );
    fileContent.Alloc( fileSize + ( endZeroByte ? 1 : 0 ) );
    fread( fileContent.GetData(), fileSize, 1, file );
    fileContent[ fileContent.GetLength() - 1 ] = 0;
  }
  fclose( file );

  return true;
}//GetFile
