import vars.var_for_init as iv
import vars.global_var as gv
import wx
from src.localisation import get_local_text
from src.custom_frames import store_custom_frame_as_option

class CustomFramesMenu(wx.Menu):
    def __init__(self, parent):
        """
        Initialize the Custom Frames menu.
          - parent: the parent window (used for posting events)
        """
        super(CustomFramesMenu, self).__init__()
        self.parent = parent
        self.top_parent = self.parent.parent
        self.top_parent.custom_border = self
        self.menu_items = {}  # Maps filename (from get("file")) to wx.MenuItem.
        self.external_state = gv.DEFAULT_OPTION_PLACEHOLDER  # Will hold a comma-separated string of filenames.
        self.BuildMenu()
        self.InitMenu()

    def InitMenu(self):
        self.section = "CUSTOM_SECTION"
        self.option = "custom_frames"
        self.output_preview_change=True
        self.update_convert_btn_state=True
        self.top_parent.all_interactive_items.append(self)
        state = self.top_parent.config.get(self.section,self.option,fallback=gv.DEFAULT_OPTION_PLACEHOLDER)
        self.SetValue(state)

    def BuildMenu(self):
        """
        Build the menu items from the custom frames dictionary.
        If no valid frames are found, add one disabled "None" option.
        """
        # To obtain the dictionary of custom frames.
        frames_dict = iv.CUSTOM_FRAMES_DICT
        if not frames_dict:
            none_item = self.Append(-1, get_local_text("mune_none_item"))
            none_item.Enable(False)
            return

        # Count occurrences of names using a standard dictionary.
        name_counts = {}
        for frame in frames_dict.values():
            name = frame.get("name", "")
            name_counts[name] = name_counts.get(name, 0) + 1
        
        # Build a list of tuples: (label, filename, frame_id)
        items = []
        for key, frame in frames_dict.items():
            # Use the frame's name as the base label.
            label = f"{frame["name"]} [{frame['file']}]"
            items.append((label, frame["file"],frame["id"]))
        # Sort items alphabetically by label.
        items.sort(key=lambda x: x[0].lower())

        # Create a checkable menu item for each frame.
        for label, filename, frame_id in items:
            item = self.AppendCheckItem(-1, label)
            self.menu_items[filename] = {"menu_item": item, "id": frame_id}
            self.Bind(wx.EVT_MENU, self.OnMenuCheck, item)

    def OnMenuCheck(self, event):
        """
        Event handler for when any checkable menu item is toggled.
        Updates the external_state variable and posts a custom event.
        """
        add_ids = []
        remove_ids = []
        checked_files = []
        for filename, item_data in self.menu_items.items():
            menu_item = item_data['menu_item']
            frame_id = item_data['id']
            if menu_item.IsChecked():
                checked_files.append(filename)
                add_ids.append(frame_id)
            else:
                remove_ids.append(frame_id)
        if checked_files:
            self.external_state = ",".join(checked_files)
        else:
            self.external_state = gv.DEFAULT_OPTION_PLACEHOLDER
        
        # Update the current selection:
        store_custom_frame_as_option(self.top_parent.current_selection, add_ids, remove=False)
        store_custom_frame_as_option(self.top_parent.current_selection, remove_ids, remove=True)
        self.top_parent.on_universal_option_change(event)

    def SetValue(self, state_str):
        """
        Programmatically check items based on the state_str, which is a comma-separated
        string of filenames. Uncheck items not present in state_str.
        """
        state_files = set(s.strip() for s in state_str.split(",") if s.strip() and s.strip() != gv.DEFAULT_OPTION_PLACEHOLDER)
        add_ids = []
        remove_ids = []
        for filename, item_data in self.menu_items.items():
            menu_item = item_data['menu_item']
            frame_id = item_data['id']
            if filename in state_files:
                menu_item.Check(True)
                add_ids.append(frame_id)
            else:
                menu_item.Check(False)
                remove_ids.append(frame_id)
        if state_files:
            self.external_state = ",".join(state_files)
        else:
            self.external_state = gv.DEFAULT_OPTION_PLACEHOLDER

        store_custom_frame_as_option(self.top_parent.current_selection, add_ids, remove=False)
        store_custom_frame_as_option(self.top_parent.current_selection, remove_ids, remove=True)

    def GetValue(self):
        """
        Returns a comma-separated string of filenames corresponding to checked menu items.
        """
        return self.external_state
    
    def IsEnabled(self):
        return True