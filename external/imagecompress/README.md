py.texture.compress
===================

C++ python module for compression pictures using algorithm <code>DXT1</code>/<code>DXT3</code>/<code>DXT5</code>/<code>ETC1</code>.

Released: version 1.1

Supported formats: <code>tga</code>, <code>jpg</code>, <code>png</code>, <code>bmp (24/32bpp)</code>, <code>RGBA-bytes</code>


Example:
```python
import imagecompress
#2 steps
imageRGBA = imagecompress.jpg2rgba( 'test.jpg' )
dxt1byteData = imagecompress.rgba2dxt1( imageRGBA )
#or 1 step
dxt5byteData = imagecompress.picture2dxt( 'test.png', 'dxt5' )
etc1byteData = imagecompress.picture2etc1( 'test.png', 0 ) #0 - quality [0-2]
#or if we needed only RGBA-data
rgba = imagecompress.decode2rgba( 'test.tga' )
print( rgba )
#{'length': 5432, 'bytes': b'123456', 'width': 128, 'height': 256}
```
where:
```python
imageRGBA = dict(
    width = pictureWidthInPixels, #int
    height = pictureHeightInPixels, #int
    data = RGBAbyteData, #bytes = 'RGBARGBARGBA...RGBA'
)
```

Functions in module:
```
supportedFormats() = {'jpg', 'tga'...} - list of supported formats
picture2dxt( '/path/to/image/file', 'format' ) - read picture from file, decode and return compressed bytes (format: 'dxt1', 'dxt3', 'dxt5')
picture2etc1( '/path/to/image/file', quality ) - read picture from file, decode and return compressed bytes (format: 'etc1'), quality - 0:low, 1:medium, 2:high
decode2rgba( '/path/to/image/file' ) - read picture from file, decompress and return RGBA-bytes; result = { 'width':int, 'height':int, 'data':bytes, 'length':int }
tga2rgba( '/path/to/image/file' ), png2rgba(...), jpg2rgba(...), bmp2rgba(...) == decode2rgba
rgba2dxt1( rgbaData ), rgba2dxt3(...), rgba2dxt5(...) - compress RGBA-data to DTX1/DXT3/DXT5; rgbaData = result = { 'width':int, 'height':int, 'data':bytes, 'length':int };
rgba2etc1( rgbaData ) - compress RGBA-data to ETC1; rgbaData = result = { 'width':int, 'height':int, 'data':bytes, 'length':int, 'quality':int };
```

*NOTE: c++ code contains jpeglib, pnglib, zlib source-code. Visual Studio 2012 solution.*
