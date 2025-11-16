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

class CustomSizeValidator(wx.Validator):
    """ Validator for custom size text fields (default-9999, max 4 chars). """
    
    def __init__(self, min_val=None, max_val=None):
        super().__init__()
        import vars.global_var as gv
        # Use CUSTOM_SIZE_MIN (1) for validation, but default value is CUSTOM_SIZE_DEFAULT_X (256)
        self.min_val = min_val if min_val is not None else gv.CUSTOM_SIZE_MIN
        self.max_val = max_val if max_val is not None else gv.CUSTOM_SIZE_MAX
        self.Bind(wx.EVT_CHAR, self.on_char)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
        self.Bind(wx.EVT_KILL_FOCUS, self.on_focus_lost)

    def Clone(self):
        """ Required for wx.Validator. """
        return CustomSizeValidator(self.min_val, self.max_val)

    def Validate(self, parent):
        """ Validates the input (default-9999). """
        text_ctrl = self.GetWindow()
        value = text_ctrl.GetValue().strip()
        
        if not value:
            # Empty is allowed during typing, will be validated on focus loss
            return True
            
        if value.isdigit():
            num_value = int(value)
            if self.min_val <= num_value <= self.max_val:
                return True
        
        # Invalid: reset to default or last valid value
        if hasattr(text_ctrl, 'last_valid_value'):
            text_ctrl.ChangeValue(str(text_ctrl.last_valid_value))
        else:
            text_ctrl.ChangeValue(str(self.min_val))
        return False

    def TransferToWindow(self):
        """ Transfers data to the control (not needed here). """
        return True

    def TransferFromWindow(self):
        """ Transfers data from the control (not needed here). """
        return True

    def on_char(self, event):
        """ Restricts input to numbers and limits to 4 characters. """
        keycode = event.GetKeyCode()
        text_ctrl = self.GetWindow()
        
        # Allow navigation, deletion, and clipboard keys
        if keycode in (wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_UP, wx.WXK_DOWN, 
                      wx.WXK_DELETE, wx.WXK_BACK, wx.WXK_TAB, wx.WXK_RETURN, 
                      wx.WXK_CONTROL_C, wx.WXK_CONTROL_V, wx.WXK_CONTROL_A):
            event.Skip()
            return
        
        # Check if adding this character would exceed 4 characters
        current_text = text_ctrl.GetValue()
        if len(current_text) >= 4 and keycode not in (wx.WXK_DELETE, wx.WXK_BACK):
            return  # Block input if already at max length
        
        # Allow digits only
        if chr(keycode).isdigit():
            event.Skip()

    def on_focus_lost(self, event):
        """ Validates and saves value when focus is lost. """
        import vars.global_var as gv
        text_ctrl = self.GetWindow()
        value = text_ctrl.GetValue().strip()
        
        # Determine default value based on which field this is
        if hasattr(text_ctrl, 'option'):
            if text_ctrl.option == 'size_custom_x':
                default_val = gv.CUSTOM_SIZE_DEFAULT_X
            elif text_ctrl.option == 'size_custom_y':
                default_val = gv.CUSTOM_SIZE_DEFAULT_Y
            else:
                default_val = self.min_val
        else:
            default_val = self.min_val
        
        if not value:
            # If empty, set to default
            text_ctrl.ChangeValue(str(default_val))
            value = str(default_val)
        
        if value.isdigit():
            num_value = int(value)
            if self.min_val <= num_value <= self.max_val:
                text_ctrl.last_valid_value = num_value
                # Save to config if handler exists
                if hasattr(text_ctrl, 'section') and hasattr(text_ctrl, 'option'):
                    top = text_ctrl.GetTopLevelParent()
                    if hasattr(top, 'on_custom_size_change'):
                        top.on_custom_size_change(text_ctrl)
            else:
                # Out of range, clamp to valid range
                clamped = max(self.min_val, min(self.max_val, num_value))
                text_ctrl.ChangeValue(str(clamped))
                text_ctrl.last_valid_value = clamped
                if hasattr(text_ctrl, 'section') and hasattr(text_ctrl, 'option'):
                    top = text_ctrl.GetTopLevelParent()
                    if hasattr(top, 'on_custom_size_change'):
                        top.on_custom_size_change(text_ctrl)
        else:
            # Not a number, reset to last valid or default
            if hasattr(text_ctrl, 'last_valid_value'):
                text_ctrl.ChangeValue(str(text_ctrl.last_valid_value))
            else:
                text_ctrl.ChangeValue(str(default_val))
                text_ctrl.last_valid_value = default_val
        
        event.Skip()

    def on_enter(self, event):
        """ Validates when Enter is pressed. """
        self.on_focus_lost(event)