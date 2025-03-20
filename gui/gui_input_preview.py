import wx
import os
import math
from PIL import Image

import vars.global_var as gv
import vars.sizes as cs

from src.localisation import get_local_text
from gui.gui_file_systems import load_pil_image_wxmessagebox
from gui.gui_file_systems import pil_image_to_wx

def get_folder_text_lines(dc, folder_path, max_width):
    """
    Returns up to 2 lines of text representing folder_path.
    The first line is the directory portion (ensuring it ends with os.sep)
    and the second is the folder name.
    If a line is too wide, characters from the beginning are trimmed and
    an ellipsis is prefixed.
    """
    ellipsis = "..."
    # Use only the basename for the folder name.
    dir_path, folder_name = os.path.split(folder_path)
    if dir_path and not dir_path.endswith(os.sep):
        dir_path += os.sep
    line1 = dir_path
    w1, _ = dc.GetTextExtent(line1)
    if w1 > max_width:
        # Remove from beginning until it fits, preserving the trailing separator.
        preserved = line1[-1]  # os.sep
        trim_part = line1[:-1]
        while trim_part and dc.GetTextExtent(ellipsis + trim_part + preserved)[0] > max_width:
            trim_part = trim_part[1:]
        line1 = ellipsis + trim_part + preserved
    line2 = folder_name
    w2, _ = dc.GetTextExtent(line2)
    if w2 > max_width:
        while line2 and dc.GetTextExtent(ellipsis + line2)[0] > max_width:
            line2 = line2[1:]
        line2 = ellipsis + line2
    return [line1, line2]

def generate_folder_icon(folder_path, width, height, border=cs.IP_FOLDERICON_BORDER):
    """
    Generates a composite folder icon.
      - Retrieves the OS's standard folder bitmap via wx.ArtProvider.
      - Draws the folder text (using get_folder_text_lines) in the bottom area.
      - Uses the specified font for drawing text.
      - Draws an inner border (padding) of 'border' pixels.
    The effective drawing area is width-2*border by height-2*border.
    Returns a wx.Bitmap.
    """
    # Calculate available area inside the border.
    avail_w = width - 2 * border
    avail_h = height - 2 * border
    # Reserve bottom area for text (say 20 pixels) from available height.
    text_area = cs.IP_FOLDERICON_TEXTAREA  
    folder_img_height = avail_h - text_area

    # Get the standard folder bitmap.
    folder_bmp = None
    try:
        folder_bmp = wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, (avail_w, folder_img_height))
    except Exception as e:
        pass
    if not folder_bmp or not folder_bmp.IsOk():
        # Fallback: create a bitmap and draw the folder emoji.
        folder_bmp = wx.Bitmap(avail_w, folder_img_height)
        dc_temp = wx.MemoryDC(folder_bmp)
        dc_temp.SetBackground(wx.Brush(wx.Colour(255,255,255)))
        dc_temp.Clear()
        # Determine font: if not provided, choose one that fills most of folder_img_height.
        font_size = max(cs.IP_FOLDERICON_EMOJI_FONT_MIN, min(cs.IP_FOLDERICON_EMOJI_FONT_MAX,folder_img_height - 10))
        font = wx.Font( font_size , wx.FONTFAMILY_DEFAULT,
                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        dc_temp.SetFont(font)
        emoji = "📁"
        tw, th = dc_temp.GetTextExtent(emoji)
        x = (avail_w - tw) // 2
        y = (folder_img_height - th) // 2
        dc_temp.DrawText(emoji, x, y)
        dc_temp.SelectObject(wx.NullBitmap)

    # Create composite bitmap.
    bmp = wx.Bitmap(width, height)
    mem_dc = wx.MemoryDC(bmp)
    mem_dc.SetBackground(wx.Brush(wx.Colour(255,255,255)))
    mem_dc.Clear()

    # Draw the folder image at the top of the available area (centered horizontally).
    folder_w = folder_bmp.GetWidth()
    folder_h = folder_bmp.GetHeight()
    x_img = border + (avail_w - folder_w) // 2
    y_img = border
    mem_dc.DrawBitmap(folder_bmp, x_img, y_img, True)

    # If a font is provided, set it for the DC (this affects text measurement and drawing).
    font = wx.Font(cs.IP_FOLDERICON_TEXT_FONT, wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
    mem_dc.SetFont(font)

    # Draw folder text in the bottom text area.
    text_max_width = avail_w
    # Use the folder's base name.
    lines = get_folder_text_lines(mem_dc, folder_path, text_max_width)
    # Measure text height using current font.
    _, line_height = mem_dc.GetTextExtent("Ay")
    total_text_height = line_height * len(lines)
    # Center the text vertically within the text area.
    text_y = border + avail_h - total_text_height
    for line in lines:
        tw, _ = mem_dc.GetTextExtent(line)
        text_x = border + (avail_w - tw) // 2
        mem_dc.DrawText(line, text_x, text_y)
        text_y += line_height

    mem_dc.SelectObject(wx.NullBitmap)
    return bmp

class TransparentPanel(wx.Panel):
    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize):
        # Create the panel with transparent window style and no border.
        style = wx.TRANSPARENT_WINDOW | wx.NO_BORDER
        super().__init__(parent, id, pos, size, style)
        # Set a background colour with 0 alpha.
        self.SetBackgroundColour(wx.Colour(0, 0, 0, 0))
        # Prevent the default background erasing.
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

    def OnEraseBackground(self, event):
        # Do nothing to keep it transparent.
        pass

class PreviewDropTarget(wx.FileDropTarget):
    """Allows dragging and dropping an image file or a folder into the preview area."""
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.current_selection=self.window.GetTopLevelParent().current_selection

    def OnDropFiles(self, x, y, itemnames):
        if not itemnames:
            return True
        # Process dropped folders and files.
        valid_images = []
        valid_folders =[]
        # Prepare allowed extensions for files in itemnames
        allowed_ext_string = gv.INPUT_IMAGE_DEFAULT_TYPES
        allowed_extensions = [ext.strip().lower() for ext in allowed_ext_string.split(",") if ext.strip()]
        # Process each dropped item.
        for f in itemnames:
            if os.path.isdir(f):
                valid_folders.append(f)
            elif os.path.isfile(f):
                # Check file extension.
                ext = os.path.splitext(f)[1].lstrip(".").lower()
                if ext in allowed_extensions:
                    valid_images.append(f)
        if valid_images or valid_folders:
            self.window.user_input_init(folders=valid_folders,images=valid_images)
        return True

class InputImagePanel(wx.Panel):
    """Custom panel that acts as an image preview area with drag-and-drop support."""
    def __init__(self, parent, size, *args, **kwargs):
        super().__init__(parent, size=size, *args, **kwargs)
        self.SetMinSize(size)
        self.SetMaxSize(size)
        self.SetWindowStyleFlag(wx.BORDER_NONE)

        self.top_parent = self.GetTopLevelParent()

        self.current_selection = self.top_parent.current_selection

        self.logstream= self.top_parent.log_ctrl.log
        # Image preview variables
        self.preview_bitmap = None
        self.default_text = get_local_text("images_input_click_to_open")
        
        # Bind painting and click events to the main panel
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self.open_image_dialog)

        # Create an invisible overlay panel for drag-and-drop
        self.overlay_panel = TransparentPanel(self, size=self.GetSize())

        #self.overlay_panel.SetDropTarget(PreviewDropTarget(self))
        self.top_parent.panel.SetDropTarget(PreviewDropTarget(self))


        self.overlay_panel.SetTransparent(0)
        self.overlay_panel.Bind(wx.EVT_LEFT_DOWN, self.open_image_dialog)
        self.overlay_panel.SetWindowStyleFlag(self.overlay_panel.GetWindowStyleFlag() & ~wx.TAB_TRAVERSAL)
        self.Bind(wx.EVT_SIZE, self.on_resize)

    def user_input_init(self,images=[],folders=[]):
        # Rebind overlay click.
        if folders and not(images):
            self.overlay_panel.Bind(wx.EVT_LEFT_DOWN, self.open_folder_dialog)
        else:
            self.overlay_panel.Bind(wx.EVT_LEFT_DOWN, self.open_image_dialog)
        # Number of items
        num_folders = len(folders)
        num_images = len(images)
        num_items=num_folders+num_images
        # Update stored paths
        self.current_selection.init_input_items(folders=folders,images=images)
        self.current_selection.gather_paths()
        try:
            # Update input preview
            self.update_input_preview()
            # Update basename indicator
            self.top_parent.set_input_image_basename()
            # Update anything else
            self.top_parent.update_global_state()
            # Update logs
            if num_images==1 and not(folders):
                basename = os.path.basename(images[0])
                self.logstream("input_image_loaded",basename)
            elif num_images>1 and not(folders):
                self.logstream("input_images_loaded",num_images)
            elif not(images) and num_folders==1:
                basename=os.path.basename(folders[0])
                self.logstream("input_folder_loaded",basename)
            elif not(images) and num_folders>1:
                self.logstream("input_folders_loaded",num_folders)
            else:
                self.logstream("input_items_loaded",num_items)
        except ValueError as failed_image_pil:
            self.close_image_folder()
            self.logstream("input_image_error",failed_image_pil)

    def update_input_preview(self):
        folders = self.current_selection.paths_folders
        images =  self.current_selection.paths_images
        num_folders = len(folders)
        num_images = len(images)
        num_items = num_folders+num_images
        # Try load pictures from 'images' list
        if images:
            success = True
            num_show_images = max(gv.INPUT_IMAGES_MAXNUM - num_folders, 0)
            loaded_images_pil = []
            for path in images[:num_show_images]:
                pil_image = load_pil_image_wxmessagebox(path=path)
                success = bool(pil_image)
                if success:
                    loaded_images_pil.append(pil_image)
                else:
                    failed_image_pil=path
                    break
            if not(success):
                raise ValueError(failed_image_pil)
            self.current_selection.loaded_images_pillow = loaded_images_pil

        if num_items <= gv.INPUT_IMAGES_MAXNUM:
            self.show_images_grid_preview()
        else:
            self.show_images_text_preview()

    def on_resize(self, event):
        """Ensure the overlay panel always covers the entire main panel."""
        self.overlay_panel.SetSize(self.GetSize())
        event.Skip()

    def on_paint(self, event):
        """Handles drawing the preview panel, including borders, image preview, and text."""
        dc = wx.PaintDC(self)
        dc.Clear()
        width, height = self.GetSize()
        # Draw a debug rectangle to confirm that drawing commands work.
        #dc.SetPen(wx.Pen("red", 2))
        #dc.DrawRectangle(0, 0, width, height)

        if self.preview_bitmap:
            # Draw the preview image (covering the full area without gaps)
            dc.DrawBitmap(self.preview_bitmap, 0, 0, True)
        else:
            # Draw centered greyed text
            text = self.default_text
            dc.SetFont(wx.Font(cs.INPUT_LIST_FONTSIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            dc.SetTextForeground(wx.Colour(128, 128, 128))
            tw, th = dc.GetTextExtent(text)
            x = (width - tw) // 2
            y = (height - th) // 2
            dc.DrawText(text, x, y)

    def get_wild_card(self,supported_types, default_types):
        """
        Constructs a wildcard string for wx.FileDialog from a comma-separated list
        of file extensions. If supported_types is empty or invalid, default_types is used.

        Example:
        gv.INPUT_IMAGE_DEFAULT_TYPES = "png,jpg,jpeg,bmp,tga,dds,webp,blp,ico"
        returns: "Image files (*.png;*.jpg;*.jpeg;*.bmp;*.tga;*.dds;*.webp;*.blp;*.ico)|*.png;*.jpg;*.jpeg;*.bmp;*.tga;*.dds;*.webp;*.blp;*.ico"
        """
        # Use default_types if supported_types is empty or only whitespace.
        if not supported_types or not supported_types.strip():
            supported_types = default_types

        # Split the extensions on comma and remove any extra whitespace.
        extensions = [ext.strip().lower() for ext in supported_types.split(',') if ext.strip()]
        if not extensions:
            # Fallback to default_types if the list is empty.
            extensions = [ext.strip().lower() for ext in default_types.split(',') if ext.strip()]

        # Create a list of file masks.
        masks = ["*." + ext for ext in extensions]
        mask_string = ";".join(masks)
        description = f"{get_local_text("dialog_image_files")} ({mask_string})"
        wildcard = f"{description}|{mask_string}"
        return wildcard


    def open_image_dialog(self, event):
        """Opens a file dialog for selecting one or more images.
        """
        supported_types=self.GetTopLevelParent().current_selection.get_value("OPTIONS_INPUT","input_process_filetypes")
        wildcard = self.get_wild_card(supported_types,gv.INPUT_IMAGE_DEFAULT_TYPES)
        with wx.FileDialog(self, get_local_text("dialog_open"), wildcard=wildcard,
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_CANCEL:
                return
            paths = file_dialog.GetPaths()
            self.user_input_init(images=paths)

    def close_image_folder(self):
        current_selection = self.top_parent.current_selection
        current_selection.clearinputs()
        self.preview_bitmap = None
        self.Refresh()
        self.top_parent.update_global_state()
        self.logstream("input_clear")
        
    def open_folder_dialog(self,event):
        dlg = wx.DirDialog(self, "Select a folder", style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            folder_path = dlg.GetPath()
            folders = []
            folders.append(folder_path)
            self.user_input_init(folders=folders)
        dlg.Destroy()

    # Updated show_images_grid_preview.
    def show_images_grid_preview(self):
        """
        Creates a composite preview for images arranged in an N x N grid,
        where N is the smallest integer such that N*N >= min(total_items, gv.INPUT_IMAGES_MAXNUM).
        First images from images_pillow are placed, then folder icons (generated with generate_folder_icon)
        are added. Total number of items does not exceed gv.INPUT_IMAGES_MAXNUM.
        """
        current_selection = self.top_parent.current_selection
        images_pillow = current_selection.loaded_images_pillow
        folders = current_selection.paths_folders
        images = current_selection.paths_images
        items = current_selection.paths_items

        if not items:
            return

        num_items = len(items)
        max_items = min(num_items, gv.INPUT_IMAGES_MAXNUM)
        grid_size = math.ceil(math.sqrt(max_items))
        preview_w, preview_h = cs.IMAGE_PREVIEW_SIZE
        bmp = wx.Bitmap(preview_w, preview_h)
        mem_dc = wx.MemoryDC(bmp)
        mem_dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        mem_dc.Clear()

        sub_w = preview_w // grid_size
        sub_h = preview_h // grid_size

        j=0
        for i in range(max_items):
            path=items[i]
            if os.path.isdir(path) and path in folders:
                bmp_img = generate_folder_icon(path, sub_w, sub_h)
            elif os.path.isfile(path) and path in images:
                image = images_pillow[j]
                img_scaled = image.resize((sub_w, sub_h), Image.LANCZOS)
                wx_image = pil_image_to_wx(img_scaled)
                bmp_img = wx.Bitmap(wx_image)
                j += 1
            else:
                self.logstream("input_preview_error",path, "")
                break
            row = i // grid_size
            col = i % grid_size
            x = col * sub_w
            y = row * sub_h
            mem_dc.DrawBitmap(bmp_img, x, y, True)
        mem_dc.SelectObject(wx.NullBitmap)
        self.preview_bitmap = bmp
        self.Refresh()


    def show_images_text_preview(self):
        """If more than 4 files are selected, this method displays a text preview:
           1) The first line shows "Total N images are selected:".
           2) If exactly 5 files are selected, each file's base name is drawn on a separate line.
           3) If more than 5 files are selected, the next 4 lines show the first 4 base names (truncated
              from the beginning with an ellipsis if needed), and the final line shows "and M more".
        """
        current_selection = self.top_parent.current_selection
        preview_w, preview_h = cs.IMAGE_PREVIEW_SIZE
        bmp = wx.Bitmap(preview_w, preview_h)
        mem_dc = wx.MemoryDC(bmp)
        mem_dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        mem_dc.Clear()
        font = wx.Font(cs.INPUT_LIST_FONTSIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        mem_dc.SetFont(font)
        mem_dc.SetTextForeground(wx.Colour(0, 0, 0))
        
        # Determine the height of a line of text.
        _, line_height = mem_dc.GetTextExtent("Ag")
        
        def truncate_text(text, max_width):
            """Truncates text from the beginning with an ellipsis if it exceeds max_width."""
            ellipsis = "..."
            if mem_dc.GetTextExtent(text)[0] <= max_width:
                return text
            while mem_dc.GetTextExtent(ellipsis + text)[0] > max_width and len(text) > 0:
                text = text[1:]
            return ellipsis + text

        total = len(current_selection.paths_items)
        lines = []
        # First line: total count
        lines.append(get_local_text("items_input_preview_text_total").format(total))

        regular=0
        extra=0
        if total == gv.INPUT_IMAGES_MAXNUM+1:
            regular=gv.INPUT_IMAGES_MAXNUM+1
        elif total > gv.INPUT_IMAGES_MAXNUM+1:
            regular=gv.INPUT_IMAGES_MAXNUM
            extra = total - regular

        for path in current_selection.paths_items[:regular]:
            if os.path.isdir(path):
                base = "...\\"+os.path.basename(path)
            else:
                base = os.path.basename(path)
            lines.append(truncate_text(base, preview_w))

        if extra:
            lines.append(truncate_text(get_local_text("items_input_preview_text_and_more").format(extra), preview_w))

        total_text_height = line_height * len(lines)
        y = (preview_h - total_text_height) // 2
        for line in lines:
            tw, _ = mem_dc.GetTextExtent(line)
            x = (preview_w - tw) // 2
            mem_dc.DrawText(line, x, y)
            y += line_height

        mem_dc.SelectObject(wx.NullBitmap)
        self.preview_bitmap = bmp
        self.Refresh()
