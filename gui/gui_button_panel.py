import wx
import threading

import var.sizes as cs

from gui.gui_tooltip import HoverOverlay
from gui.gui_browse_output import gui_browse_output

from src.generator import generate_images
from src.localisation import get_local_text
from src.localisation import get_tooltip_text

class ButtonClass:

    def after_generation(self):
        self.parent.generation_start=False
        self.parent.update_generation_state()
        self.parent.current_selection.stop_requested=False
        self.button_list['btn_stop'].Enable(False)

    def run_generation(self,input_data):
        # Run your long-running process in the background
        generate_images(input_data,self.parent)
        # Optionally, use wx.CallAfter to update GUI when done:
        wx.CallAfter(self.after_generation)

    def on_save_image(self, event):
        if not self.parent.current_selection.paths:
            wx.MessageBox(get_local_text("message_window_generate_warning_no_image"), get_local_text("message_window_generate_warning_no_image_title"), wx.OK | wx.ICON_WARNING)
            self.parent.log_ctrl.log("output_no_image_warning")
            return
        self.parent.generation_start=True
        self.button_list['btn_stop'].Enable(True)
        self.parent.update_generation_state()
        threading.Thread(target=self.run_generation, args=(self.parent.current_selection,), daemon=True).start()

    def on_abort_generation(self, event):
        self.parent.current_selection.stop_requested=True
        return

    def on_browse(self, event):
        gui_browse_output(self.parent)

    def on_quit(self, event):
        self.parent.Close()

    def init_button(self,code,size,action):
        panel=self.panel
        parent=self.parent

        label=get_local_text(code)
        btn=wx.Button(panel, label=label)

        # Get the text width and height
        text_width, text_height = btn.GetTextExtent(label)

        # Ensure button width expands if text exceeds the given size
        min_width = max(size, text_width + 7)  # Adding padding for better UI
        btn.SetMinSize((min_width, -1))

        tooltip = get_tooltip_text(code,True)
        if tooltip:
            btn.tooltip_overlay = HoverOverlay(
                parent=self.panel,
                item = btn,
                type = "active",
                tooltip_text=tooltip,
            )
            if hasattr(parent,'overlay_items'):
                parent.overlay_items.append(btn.tooltip_overlay)
        btn.Bind(wx.EVT_BUTTON,action)
        return btn

    def __init__(self, parent, panel):

        self.panel = panel
        self.parent = parent
        self.button_list = {}

        btn_dict = {
            'btn_open_image': {
                'size': cs.BUTTON_BIG_MIN_X_SIZE,
                'action': parent.input_panel.open_image_dialog,
            },
            'btn_open_folder': {
                'size': cs.BUTTON_BIG_MIN_X_SIZE,
                'action': parent.input_panel.open_folder_dialog,
            },
            'btn_convert': {
                'size': cs.BUTTON_SMALL_MIN_X_SIZE,
                'action': self.on_save_image,
            },
            'btn_stop': {
                'size': cs.BUTTON_SMALL_MIN_X_SIZE,
                'action': self.on_abort_generation,
            },
            'btn_browse': {
                'size': cs.BUTTON_BIG_MIN_X_SIZE,
                'action': self.on_browse,
            },
            'btn_quit': {
                'size': cs.BUTTON_BIG_MIN_X_SIZE,
                'action': self.on_quit,
            },
        }

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()

        for code, params in btn_dict.items():
            btn = self.init_button(code,params["size"],params["action"])
            btn_sizer.Add(btn, flag=wx.ALL | wx.EXPAND, border=cs.PADSIZE_BUTTONS)
            self.button_list[code]=btn
        btn_sizer.AddStretchSpacer()

        self.button_list['btn_stop'].Enable(False)
        self.btn_sizer = btn_sizer