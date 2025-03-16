import io
import tempfile
import wx
import os
from PIL import Image as PILImage
from src.localisation import get_local_text
from src.converter import load_pil_image

def load_pil_image_wxmessagebox(path):
    try:
        pil_image=load_pil_image(path)
        return pil_image
    except Exception as e:
        wx.MessageBox( get_local_text("message_window_load_error").format(path,str(e)), get_local_text("message_window_load_error_title"), wx.OK | wx.ICON_ERROR)
        return None
    
def pil_image_to_wx(pil_image):
    pil_image = pil_image.convert("RGBA")  # Ensure transparency support
    # Save to an in-memory PNG buffer
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    buffer.seek(0)
    # Save to a temporary file (since wx.Image cannot load from BytesIO)
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp_file.write(buffer.getvalue())
    tmp_file.close()
    # Load wx.Image from the temporary file
    wx_image = wx.Image(tmp_file.name, wx.BITMAP_TYPE_PNG)
    os.unlink(tmp_file.name)  # Delete temp file after use
    return wx_image