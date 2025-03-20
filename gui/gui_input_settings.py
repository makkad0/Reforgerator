import wx
import vars.global_var as gv
import vars.sizes as cs
from src.localisation import get_local_text

# Custom popup using wx.ComboPopup with a CheckListBox inside a dedicated subpanel.

class MultiSelectComboPopup(wx.ComboPopup):
    def __init__(self, parent_panel):
        super().__init__()
        self.subpanel = None   # Our dedicated subpanel.
        self.lb = None         # The CheckListBox inside the subpanel.
        self.value = []        # List of selected item indices.
        self._down_item = None # Stores the item index from the mouse down event.
        self.parent_panel = parent_panel  # Reference to MultiSelectComboPanel.

    def AddItem(self, txt):
        self.lb.Append(txt)

    def OnLeftDown(self, event):
        pos = event.GetPosition()
        result = self.lb.HitTest(pos)
        try:
            item, flags = result
        except TypeError:
            item = result
            flags = 0
        # Record the item where the mouse down occurred.
        self._down_item = item
        event.Skip(False)  # Suppress default behavior.

    def OnLeftUp(self, event):
        pos = event.GetPosition()
        result = self.lb.HitTest(pos)
        try:
            item, flags = result
        except TypeError:
            item = result
            flags = 0
        # Only process if mouse down and up happened on the same item.
        if item != wx.NOT_FOUND and (item == self._down_item):
            current_state = self.lb.IsChecked(item)
            new_state = not current_state
            self.lb.Check(item, new_state)
            if new_state:
                if item not in self.value:
                    self.value.append(item)
                self.lb.Select(item)
            else:
                if item in self.value:
                    self.value.remove(item)
                self.lb.Deselect(item)
            self.UpdateParentTextCtrl()
        self._down_item = None  # Clear the stored item.
        event.Skip(False)

    def OnLeftDClick(self, event):
        # For a double click, simulate a down and up on the same item.
        self.OnLeftDown(event)
        self.OnLeftUp(event)
        event.Skip(False)

    def UpdateParentTextCtrl(self):
        # Build a string from the currently checked items.
        selections = [self.lb.GetString(i) for i in self.value]
        # If more than 3 items are selected, show a summary.
        if len(selections) > cs.VF_MAX_CHOICE_INT:
            display_text =  get_local_text("input_process_filetypes_formats").format(len(selections))
        else:
            display_text = ",".join(selections)
        self.GetComboCtrl().SetValue(display_text)
        self.TriggerOptionChange()  # Call external update function

    # --- Required methods for the ComboPopup interface ---
    def Init(self):
        self.value = []

    def Create(self, parent):
        # Create a dedicated subpanel as a child of the popup container.
        self.subpanel = wx.Panel(parent, style=wx.BORDER_SIMPLE)
        # Create the CheckListBox inside the subpanel.
        self.lb = wx.CheckListBox(self.subpanel, style=wx.LB_MULTIPLE)
        # Bind our custom mouse event handlers.
        self.lb.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.lb.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.lb.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        # Lay out the CheckListBox within the subpanel.
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.lb, 1, wx.EXPAND | wx.ALL, 0)
        self.subpanel.SetSizer(sizer)
        self.subpanel.Fit()
        return True

    def GetControl(self):
        # Return the subpanel as the widget for the popup.
        return self.subpanel

    def SetStringValue(self, value):
        # Get the list of valid choices from the checklist.
        valid_choices = [self.lb.GetString(i) for i in range(self.lb.GetCount())]
        # Split the input value by commas.
        parts = [s.strip() for s in value.split(",") if s.strip()]
        # If every part is a valid choice, update internal state.
        if all(part in valid_choices for part in parts):
            for i in range(self.lb.GetCount()):
                if self.lb.GetString(i) in parts:
                    self.lb.Check(i, True)
                    if i not in self.value:
                        self.value.append(i)
                    self.lb.Select(i)
                else:
                    self.lb.Check(i, False)
                    if i in self.value:
                        self.value.remove(i)
                    self.lb.Deselect(i)
        else:
            # Otherwise, assume it's a summary (e.g., "5 formats") and ignore.
            return

    def GetStringValue(self):
        selections = [self.lb.GetString(i) for i in self.value]
        return ",".join(selections)

    def GetAdjustedSize(self, minWidth, prefHeight, maxHeight):
        # Set the popup's height based on the number of choices.
        item_height = self.lb.GetCharHeight() + cs.VF_PAD_PER_ITEM  # approximate height per item.
        count = self.lb.GetCount()
        desired_height = count * item_height + cs.VF_PAD_EXTRA   # overall padding.
        if desired_height > maxHeight:
            desired_height = maxHeight
        return wx.Size(minWidth, desired_height)

    def TriggerOptionChange(self):
        """Call the parent panel's on_universal_option_change method."""
        if self.parent_panel.update_global:
            event = wx.CommandEvent(wx.EVT_COMBOBOX.typeId)
            event.SetEventObject(self.parent_panel)  # Set reference to the combo control.
            wx.PostEvent(self.parent_panel, event)  # Post event to the panel.

# Custom MultiSelectCombo control based on wx.ComboCtrl.
class MultiSelectCombo(wx.ComboCtrl):
    def __init__(self, parent, choices=[]):
        # Use wx.CB_READONLY to prevent text editing.
        super().__init__(parent, style=wx.CB_READONLY, size=(cs.VF_WINDOW_SIZE, -1))
        # Create our custom popup and associate it.
        self.popup = MultiSelectComboPopup(parent)
        self.SetPopupControl(self.popup)
        # Populate the popup with the provided choices.
        for choice in choices:
            self.popup.AddItem(choice)

    def GetValue(self):
        return self.popup.GetStringValue()

# A new panel that encapsulates the MultiSelectCombo control.
class MultiSelectComboPanel(wx.Panel):
    def __init__(self, parent, choices=None):
        if choices is None:
            # If choices are not provided, use default formats from gv.INPUT_IMAGE_DEFAULT_TYPES.
            choices = MultiSelectComboPanel.get_format_choices(gv.INPUT_IMAGE_DEFAULT_TYPES)
        super().__init__(parent)
        self.update_global=True
        sizer = wx.BoxSizer(wx.VERTICAL)
        # Create an instance of our MultiSelectCombo.
        self.multi_combo = MultiSelectCombo(self,choices=choices)
        sizer.Add(self.multi_combo, 0, wx.EXPAND | wx.ALL, 0)
        self.SetSizer(sizer)
        self.Layout()
        # Bind a custom event for universal option changes.
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_box_change)

    def GetValue(self):
        return self.multi_combo.GetValue()

    def SetValue(self, value, event_call:bool = True):
        """
        Updates the selection in multi_combo.

        :param value: A string of selected values, comma-separated (e.g., "png,jpg,bmp").
        """
        if self.multi_combo:
            self.update_global=event_call
            self.multi_combo.popup.SetStringValue(value)
            self.multi_combo.popup.UpdateParentTextCtrl()
            self.update_global=True

    def on_combo_box_change(self,event):
        self.GetTopLevelParent().on_universal_option_change(event)

    def enable_MultiSelectComboPanel(self,enable):
        self.Enable(enable)
        self.multi_combo.Enable(enable)

    @staticmethod
    def get_format_choices(format_string):
        """
        Given a comma-separated string of formats (e.g., "png,jpg,jpeg,..."),
        return a list of trimmed format strings.
        """
        return [s.strip() for s in format_string.split(',') if s.strip()]
