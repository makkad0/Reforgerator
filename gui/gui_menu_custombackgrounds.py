import vars.var_for_init as iv
import vars.global_var as gv
import wx
from src.localisation import get_local_text
from src.custom_backgrounds import init_CUSTOM_BACKGROUNDS_DICT, scan_custom_backgrounds

class CustomBackgroundsMenu(wx.Menu):
    def __init__(self, parent):
        """
        Initialize the Custom Backgrounds menu.
          - parent: the parent window (used for posting events)
        """
        super(CustomBackgroundsMenu, self).__init__()
        self.parent = parent
        self.top_parent = self.parent.parent
        self.top_parent.custom_background = self
        self.menu_items = {}  # Maps background name to wx.MenuItem.
        self.external_state = "None"  # Will hold the selected background name or "None"
        self.BuildMenu()
        self.InitMenu()

    def InitMenu(self):
        self.section = "CUSTOM_SECTION"
        self.option = "custom_background"
        self.output_preview_change = True
        self.update_convert_btn_state = False
        self.top_parent.all_interactive_items.append(self)
        state = self.top_parent.config.get(self.section, self.option, fallback="None")
        
        # Validate that the selected background still exists
        # If the background file was deleted, reset to "None"
        if state and state != "None":
            from src.custom_backgrounds import get_background_path
            import os
            bg_path = get_background_path(state)
            if not bg_path or not os.path.exists(bg_path):
                # Background file doesn't exist, reset to default
                state = "None"
                # Update config and current_selection
                if not self.top_parent.config.has_section(self.section):
                    self.top_parent.config.add_section(self.section)
                self.top_parent.config.set(self.section, self.option, "None")
                self.top_parent.current_selection.set_value(self.section, self.option, "None")
                from src import config_manager
                config_manager.save_configuration_OS(self.top_parent.config)
        
        self.SetValue(state)

    def BuildMenu(self):
        """
        Build the menu items from the custom backgrounds dictionary.
        Always includes "None" as the default option.
        """
        # Clear existing items
        items_to_remove = []
        for item in self.GetMenuItems():
            items_to_remove.append(item)
        for item in items_to_remove:
            self.Remove(item)
        self.menu_items.clear()
        
        # Always add "None" option first
        none_item = self.AppendRadioItem(-1, get_local_text("mune_none_item"))
        self.menu_items["None"] = none_item
        self.Bind(wx.EVT_MENU, self.OnMenuSelect, none_item)
        
        # Get the dictionary of custom backgrounds
        backgrounds_dict = iv.CUSTOM_BACKGROUNDS_DICT
        if not backgrounds_dict:
            return
        
        # Build a list of filenames (with extensions) sorted alphabetically
        items = sorted(backgrounds_dict.keys())
        
        # Create radio menu items for each background (show filename with extension)
        for filename in items:
            item = self.AppendRadioItem(-1, filename)
            self.menu_items[filename] = item
            self.Bind(wx.EVT_MENU, self.OnMenuSelect, item)
        
        # Add separator and refresh option
        self.AppendSeparator()
        refresh_item = self.Append(-1, get_local_text("menu_custom_backgrounds_refresh"))
        self.Bind(wx.EVT_MENU, self.OnRefresh, refresh_item)

    def OnMenuSelect(self, event):
        """
        Event handler for when any radio menu item is selected.
        Updates the external_state variable and posts a custom event.
        """
        selected_id = event.GetId()
        selected_name = None
        
        # Find which background name corresponds to the selected menu item ID
        for name, menu_item in self.menu_items.items():
            if menu_item.GetId() == selected_id:
                selected_name = name
                break
        
        if selected_name:
            self.external_state = selected_name
            # Ensure CUSTOM_SECTION exists in config
            if not self.top_parent.config.has_section(self.section):
                self.top_parent.config.add_section(self.section)
            # Update the current selection (store as string)
            self.top_parent.current_selection.set_value(self.section, self.option, str(selected_name))
            # Save to config (ensure it's saved as string, not None)
            if selected_name == "None":
                # Save as string "None" explicitly
                self.top_parent.config.set(self.section, self.option, "None")
            else:
                self.top_parent.config.set(self.section, self.option, str(selected_name))
            from src import config_manager
            config_manager.save_configuration_OS(self.top_parent.config)
            # Trigger preview update if available (only if preview is already generated)
            if hasattr(self.top_parent, 'output_panel') and self.output_preview_change:
                # Check if preview is available (paths exist)
                if hasattr(self.top_parent, 'current_selection') and self.top_parent.current_selection.paths:
                    self.top_parent.output_panel.update_preview()

    def OnRefresh(self, event):
        """Refresh the backgrounds list by rescanning the folder."""
        # Rescan backgrounds
        init_CUSTOM_BACKGROUNDS_DICT()
        
        # Get current selection
        current_selection = self.external_state
        
        # Rebuild menu
        self.BuildMenu()
        
        # Check if previously selected background still exists
        if current_selection != "None" and current_selection not in self.menu_items:
            # Background was deleted, reset to None
            current_selection = "None"
            self.external_state = "None"
            self.top_parent.current_selection.set_value(self.section, self.option, "None")
            self.top_parent.config.set(self.section, self.option, "None")
            from src import config_manager
            config_manager.save_configuration_OS(self.top_parent.config)
            # Update preview if available
            if hasattr(self.top_parent, 'output_panel'):
                self.top_parent.output_panel.update_preview()
        
        # Restore selection
        self.SetValue(current_selection)

    def SetValue(self, state_str):
        """
        Programmatically select an item based on the state_str (background name or "None").
        """
        if not state_str or state_str.strip() == "":
            state_str = "None"
        else:
            state_str = state_str.strip()
        
        # Check if the background exists in menu items
        if state_str in self.menu_items:
            self.menu_items[state_str].Check(True)
            self.external_state = state_str
        else:
            # Background not found, default to None
            if "None" in self.menu_items:
                self.menu_items["None"].Check(True)
                self.external_state = "None"

    def GetValue(self):
        """
        Returns the selected background name or "None".
        """
        return self.external_state
    
    def IsEnabled(self):
        return True

