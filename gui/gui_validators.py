import wx

class SliderSyncValidator(wx.Validator):
    """ Validator that keeps a slider and a text field in sync. """

    def __init__(self, slider):
        super().__init__()
        self.slider = slider  # Reference to the slider

        self.Bind(wx.EVT_CHAR, self.on_char)         # Restrict input to numbers but allow arrow keys
        self.Bind(wx.EVT_TEXT_ENTER, self.on_enter)  # Handle Enter key
        self.Bind(wx.EVT_KILL_FOCUS, self.on_focus_lost)  # Sync when losing focus

    def Clone(self):
        """ Required for wx.Validator. """
        return SliderSyncValidator(self.slider)

    def Validate(self, parent):
        """ Validates the input and updates the slider. """

        top = self.slider.GetTopLevelParent()

        if not(top.state_updating_is_allowed):
            return False

        text_ctrl = self.GetWindow()
        value = text_ctrl.GetValue().strip()

        if value.isdigit():
            num_value = int(value)
            min_val = self.slider.GetMin()
            max_val = self.slider.GetMax()

            if min_val <= num_value <= max_val:
                self.slider.SetValue(num_value)  # ✅ Sync slider with valid input
                 # Retrieve the top-level parent and call its save method if it exists.
                if hasattr(top, 'save_blp_compression_value'):
                    top.save_blp_compression_value()
                return True

        # ❌ If invalid, reset text field to match the slider
        text_ctrl.ChangeValue(str(self.slider.GetValue()))  # ✅ Use ChangeValue() to avoid unnecessary events
        return False

    def TransferToWindow(self):
        """ Transfers data to the control (not needed here). """
        return True

    def TransferFromWindow(self):
        """ Transfers data from the control (not needed here). """
        return True

    def on_char(self, event):
        """ Restricts input to numbers but allows navigation keys. """
        keycode = event.GetKeyCode()
        
        if keycode in (wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_DELETE, wx.WXK_BACK, wx.WXK_TAB, wx.WXK_RETURN, wx.WXK_CONTROL_C, wx.WXK_CONTROL_V):
            event.Skip()  # ✅ Allow navigation and deletion
            return

        if chr(keycode).isdigit():
            event.Skip()  # ✅ Allow numbers

    def on_focus_lost(self, event):
        """ Updates slider value when focus is lost. """
        self.Validate(None)
        event.Skip()

    def on_enter(self, event):
        """ Syncs the slider when Enter is pressed. """
        self.Validate(None)  # ✅ Calls validation method
        #event.Skip()