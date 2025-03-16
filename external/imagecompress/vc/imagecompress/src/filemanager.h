#pragma once

#include "memory.h"
#include <string>

class FileManagerWin32;
typedef FileManagerWin32 FileManagerType;

class FileManagerWin32 {
public:
  FileManagerWin32();
  virtual ~FileManagerWin32();
  virtual bool FileExists( const std::string &fileName ) const;
  virtual bool GetFile( const std::string& fileName, Memory& fileContent, bool endZeroByte = false ) const;

private:
  FileManagerWin32( FileManagerWin32& );
  FileManagerWin32& operator=( FileManagerWin32& );
};
