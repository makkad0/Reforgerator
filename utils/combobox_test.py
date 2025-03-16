import wx

class MultiSelectComboPopup(wx.ComboPopup):
    def __init__(self):
        super().__init__()
        self.lb = None
        self.value = []

    def AddItem(self, txt):
        self.lb.Append(txt)

    def OnCheck(self, event):
        index = event.GetInt()
        if self.lb.IsChecked(index):
            if index not in self.value:
                self.value.append(index)
        else:
            if index in self.value:
                self.value.remove(index)
        self.UpdateParentTextCtrl()

    def UpdateParentTextCtrl(self):
        selections = [self.lb.GetString(i) for i in self.value]
        self.GetComboCtrl().SetValue(", ".join(selections))

    # Required methods for ComboPopup interface
    def Init(self):
        self.value = []

    def Create(self, parent):
        self.lb = wx.CheckListBox(parent, style=wx.LB_MULTIPLE)
        self.lb.Bind(wx.EVT_CHECKLISTBOX, self.OnCheck)
        return True

    def GetControl(self):
        return self.lb

    def SetStringValue(self, value):
        items = value.split(", ")
        for i in range(self.lb.GetCount()):
            if self.lb.GetString(i) in items:
                self.lb.Check(i, True)
                if i not in self.value:
                    self.value.append(i)
            else:
                self.lb.Check(i, False)
                if i in self.value:
                    self.value.remove(i)

    def GetStringValue(self):
        selections = [self.lb.GetString(i) for i in self.value]
        return ", ".join(selections)

class MultiSelectCombo(wx.ComboCtrl):
    def __init__(self, parent, choices=[]):
        super().__init__(parent, style=wx.CB_READONLY)
        self.popup = MultiSelectComboPopup()
        self.SetPopupControl(self.popup)
        for choice in choices:
            self.popup.AddItem(choice)

    def GetValue(self):
        return self.popup.GetStringValue()

# Main application frame
class MyFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Multi-Select Combo Example", size=(300, 200))
        panel = wx.Panel(self)

        # Create the multi-select combo control
        choices = ["Option 1", "Option 2", "Option 3", "Option 4"]
        multi_select_combo = MultiSelectCombo(panel, choices=choices)

        # Layout using a sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(multi_select_combo, 0, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(sizer)
        self.Centre()

if __name__ == "__main__":
    app = wx.App(False)
    frame = MyFrame()
    frame.Show()
    app.MainLoop()