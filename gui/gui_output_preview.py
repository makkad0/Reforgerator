import wx
import math
import threading
from PIL import Image

import vars.global_var as gv
import vars.sizes as cs

from src.converter import load_pil_image
from src.converter import apply_frame
from src.converter import apply_format
from src.converter import bufferbytedata_to_pilimage
from gui.gui_file_systems import pil_image_to_wx
from src.localisation import get_local_text


class OutputPreviewImage(wx.Panel):
    """
    A panel to display the output preview images.
    1) Initially empty (and cleared when a folder is loaded).
    2) When image(s) are loaded, it shows previews of output images generated by applying a frame to each input image.
       - If the total number of images is less than or equal to gv.INPUT_IMAGES_MAXNUM,
         they are arranged in an N x N grid (where N*N is the smallest number ≥ gv.INPUT_IMAGES_MAXNUM).
       - If more than gv.INPUT_IMAGES_MAXNUM images are loaded, a text preview is shown:
         a) The first line reads "Total N images will be generated:".
         b) If exactly gv.INPUT_IMAGES_MAXNUM+1 images are selected, then each image's options is drawn on a separate line.
         c) If more than gv.INPUT_IMAGES_MAXNUM+1 images are selected, the first gv.INPUT_IMAGES_MAXNUM
            lines show the options and the final line shows "and M more".
    3) The panel is cleared/updated as input changes.
    """
    def __init__(self, parent, size, *args, **kwargs):
        super().__init__(parent, size=size, *args, **kwargs)
        self.top_parent = self.GetTopLevelParent()
        self.logstream= self.top_parent.log_ctrl.log
        self.SetMinSize(size)
        self.SetMaxSize(size)
        self.preview_bitmap = None
        self.default_text = get_local_text("images_output_no_preview_text")
        self.Bind(wx.EVT_PAINT, self.on_paint)

    def on_paint(self, event):
        dc = wx.PaintDC(self)
        dc.Clear()
        width, height = self.GetSize()
        if self.preview_bitmap:
            dc.DrawBitmap(self.preview_bitmap, 0, 0, True)
        else:
            dc.SetFont(wx.Font(cs.OUTPUT_LIST_FONTSIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            dc.SetTextForeground(wx.Colour(128, 128, 128))
            tw, th = dc.GetTextExtent(self.default_text)
            x = (width - tw) // 2
            y = (height - th) // 2
            dc.DrawText(self.default_text, x, y)

    def clear_preview(self):
        """Clears the current preview."""
        self.preview_bitmap = None
        self.Refresh()

    def update_preview(self):
        """
        Master function to update the output preview.
        If no images are selected or a folder is loaded, the preview is cleared.
        Otherwise, if the number of images is less than or equal to gv.INPUT_IMAGES_MAXNUM,
        it displays a grid preview; otherwise, it displays a text preview.
        """

        if not(self.top_parent.state_updating_is_allowed):
            return

        current_selection = self.top_parent.current_selection
        # Clear preview if no images
        if not current_selection.paths:
            self.clear_preview()
            return

        total = len(current_selection.paths) * current_selection.calculate_number_of_variations()

        if total<=0:
            self.clear_preview()
            return

        if total <= gv.OUTPUT_IMAGES_MAXNUM:
            #self.show_output_images_grid_preview()
            thread = threading.Thread(target=self.calculate_output_images_grid_preview)
        else:
            #self.show_output_images_text_preview()
            thread = threading.Thread(target=self.show_output_images_text_preview)
        thread.setDaemon(True)
        thread.start()

    def calculate_output_images_grid_preview(self):
        """
        Performs the heavy grid preview computation.
        Runs on a background thread.
        """
        current_selection = self.top_parent.current_selection
        if not current_selection.paths:
            return

        images_number = len(current_selection.paths)
        images_number = min(images_number, gv.OUTPUT_IMAGES_MAXNUM)
        paths = current_selection.paths[:images_number]
        images_to_process = []
        for path in paths:
            image = load_pil_image(path=path)
            images_to_process.append(image)
            
        images_finish = []
        # Determine the actual number of images and limit by gv.INPUT_IMAGES_MAXNUM.
        max_images = images_number * current_selection.calculate_number_of_variations()
        max_images = min(max_images, gv.OUTPUT_IMAGES_MAXNUM)
        # Compute the minimal grid dimension (N x N) to fully contain max_images.
        grid_size = math.ceil(math.sqrt(max_images))
        preview_w, preview_h = cs.IMAGE_PREVIEW_SIZE
        sub_w = preview_w // grid_size
        sub_h = preview_h // grid_size

        # Fixed placeholder options.
        true_size_options, true_style_options, true_border_options, true_format_options = current_selection.recieve_true_variations()
        format_suboption_dict = current_selection.recieve_suboptions([gv.DDS_SETTINGS, gv.BLP_SETTINGS,gv.TGA_SETTINGS])
        extras_suboption_dict = current_selection.recieve_suboptions([gv.OPTIONS_EXTRAS])
        j=0

        # Iterate over each image (up to max_images).
        for i, image in enumerate(images_to_process):
            path = paths[i]
            # Iterate over all True variants for apply_frame options.
            for size_option in true_size_options:
                for style_option in true_style_options:
                    for border_option in true_border_options:
                        try:
                            # Apply frame transformation.
                            processed_img = apply_frame(image, size_option, style_option, border_option,extras_suboption_dict)
                            # Now, for each available format option, further process the image.
                            for format_option in true_format_options:
                                final_img = apply_format(processed_img, format_option,format_suboption_dict,True)
                                final_img = bufferbytedata_to_pilimage(final_img,gv.OUTPUT_FILE_FORMATS[format_option])
                                final_img = final_img.resize((sub_w, sub_h), Image.LANCZOS)
                                # Compute grid cell coordinates.
                                row = j // grid_size
                                col = j % grid_size
                                j += 1
                                x = col * sub_w
                                y = row * sub_h
                                images_finish.append((final_img, (x, y)))
                        except Exception as e:
                            wx.CallAfter(self.logstream("output_preview_error",path,e))
        # Update the preview on the main thread.
        wx.CallAfter(self.update_images_grid_preview, images_finish)

    def update_images_grid_preview(self, images_finish):
        """Called on the main thread to update the preview after computation."""
        preview_w, preview_h = cs.IMAGE_PREVIEW_SIZE
        bmp = wx.Bitmap(preview_w, preview_h)
        mem_dc = wx.MemoryDC(bmp)
        mem_dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        mem_dc.Clear()

        for img, (x, y) in images_finish:
            bmp_img = wx.Bitmap(pil_image_to_wx(img))
            mem_dc.DrawBitmap(bmp_img, x, y, True)

        mem_dc.SelectObject(wx.NullBitmap)
        self.preview_bitmap = bmp
        self.Refresh()

    def show_output_images_text_preview(self):
        """
        Creates a text preview when the number of images exceeds gv.INPUT_IMAGES_MAXNUM.
        The text preview includes:
        1. A first line showing "Total N images will be generated:".
        2. If exactly gv.INPUT_IMAGES_MAXNUM+1 images are selected, list each image's fixed options on separate lines.
        3. If more than gv.INPUT_IMAGES_MAXNUM+1 images are selected, list the first gv.INPUT_IMAGES_MAXNUM lines 
            and then a final line showing "and M more".
        """
        current_selection = self.top_parent.current_selection
        preview_w, preview_h = cs.IMAGE_PREVIEW_SIZE
        bmp = wx.Bitmap(preview_w, preview_h)
        mem_dc = wx.MemoryDC(bmp)
        mem_dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        mem_dc.Clear()
        font = wx.Font(cs.OUTPUT_LIST_FONTSIZE, wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        mem_dc.SetFont(font)
        mem_dc.SetTextForeground(wx.Colour(0, 0, 0))
        _, line_height = mem_dc.GetTextExtent("Ag")

        total = len(current_selection.paths) * current_selection.calculate_number_of_variations()
        lines = []
        lines.append(get_local_text('images_output_will_generate').format(total))
        total_text_height = line_height * len(lines)
        y = (preview_h - total_text_height) // 2
        for line in lines:
            tw, _ = mem_dc.GetTextExtent(line)
            x = (preview_w - tw) // 2
            mem_dc.DrawText(line, x, y)
            y += line_height
        mem_dc.SelectObject(wx.NullBitmap)
        # Update the preview on the main thread.
        wx.CallAfter(self.update_text_grid_preview,bmp)

    def update_text_grid_preview(self,bmp):
        """Called on the main thread to update the preview after computation."""
        self.preview_bitmap = bmp
        self.Refresh()

    def create_loading_bitmap(self):
        """
        Creates a simple bitmap that displays a "Loading..." message.
        """
        preview_w, preview_h = cs.IMAGE_PREVIEW_SIZE
        bmp = wx.Bitmap(preview_w, preview_h)
        mem_dc = wx.MemoryDC(bmp)
        mem_dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        mem_dc.Clear()
        mem_dc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        mem_dc.SetTextForeground(wx.Colour(0, 0, 0))
        text = "Loading..."
        tw, th = mem_dc.GetTextExtent(text)
        x = (preview_w - tw) // 2
        y = (preview_h - th) // 2
        mem_dc.DrawText(text, x, y)
        mem_dc.SelectObject(wx.NullBitmap)
        return bmp

