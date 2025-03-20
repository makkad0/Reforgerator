import wx
import os
import src.config_manager as config_manager
from gui.gui_about import AboutDialog
from gui.gui_menu_customframes import CustomFramesMenu
from src.localisation import update_localisation,get_local_text
from src.system import get_data_subdir
import vars.global_var as gv

class TopMenu:
    def update_menu_state(self):

        # It is possible to close input in case of there is at least 1 entry in paths
        enabled=bool(self.parent.current_selection.paths)
        self.update_menu_file_item(wx.ID_CLOSE,enabled)

        # Run Processing menu option synched with Generate Button
        enabled=bool(self.parent.button_list['btn_convert'].IsEnabled())
        self.update_menu_file_item(wx.ID_SAVE,enabled)

        # Abort Processing menu option synched with Abort Button
        enabled=bool(self.parent.button_list['btn_stop'].IsEnabled())
        self.update_menu_file_item(wx.ID_ABORT,enabled)

    def update_menu_file_item(self,id,enabled):
        item = self.file_menu.FindItemById(id)
        item.Enable(enabled)
        
    def on_file_open_images_item(self,event):
        self.parent.input_panel.open_image_dialog(event)

    def on_file_select_folder_item(self,event):
        self.parent.input_panel.open_folder_dialog(event)

    def on_file_close_item(self,event):
        self.parent.input_panel.close_image_folder()

    def on_file_run_processing_item(self,event):
        self.parent.btn_pannel.on_save_image(event)

    def on_file_abort_processing_item(self,event):
        self.parent.btn_pannel.on_abort_generation(event)

    def on_file_exit_item(self,event):
        self.parent.btn_pannel.on_quit(event)

    def on_settings_to_default_item(self,event):
        profile="profile_default"
        self.settings_to_profile(profile)

    def on_profile_item(self,event,profile):
        self.settings_to_profile(profile)

    def on_change_language(self, event, lang_code):
        """
        Set the new program language and update the check marks in the language menu.
        """
        message = get_local_text('dialog_change_language').replace('\\n', '\n')
        message = message.format(lang_code)
        # Create the dialog with OK (Confirm) and Cancel buttons
        dlg = wx.MessageDialog(
            self.parent,
            message,
            get_local_text('dialog_change_language_title'),
            wx.OK | wx.CANCEL | wx.ICON_QUESTION
        )

        if dlg.ShowModal() == wx.ID_OK:
            # Uncheck all language items
            for code, menu_item in self.language_menu_items.items():
                menu_item.Check(False)
            
            # Mark the selected language item as checked
            if lang_code in self.language_menu_items:
                self.language_menu_items[lang_code].Check(True)
            
            # Update the program language using the new language code
            self.set_program_lang(lang_code)
            update_localisation(lang_code)
            wx.GetApp().restart()
        else:
            dlg.Destroy()

        for code, item in self.language_menu_items.items():
            item.Check(code == self.get_program_lang())  # Check if it's the selected language

    def on_about(self, event):
        # Create and show the About dialog.
        dlg = AboutDialog(self.parent, title=get_local_text("credit_dialog_title"))
        dlg.ShowModal()
        dlg.Destroy()

    def set_program_lang(self,lang):
        self.parent.config.set('LANG','program_lang', str(lang))
        # Iterate over all language menu items and check only the selected one
        for code, item in self.language_menu_items.items():
            item.Check(code == lang)  # Check if it's the selected language
        config_manager.save_configuration_OS(self.parent.config)

    def get_program_lang(self):
        return self.parent.config.get('LANG','program_lang')
    
    def settings_to_profile(self,profile):

        profile_text=get_local_text(profile)

        self.parent.state_updating_is_allowed = False
        main_config = self.parent.config

        try:
            
            if profile=="profile_default":
                #Save Language Option and Output Folder
                current_lang=self.get_program_lang()
                current_outputfolder=self.parent.current_selection.get_value('OPTIONS_OUTPUT_PATH','output_folder')
                config_manager.reset_configuration_OS(main_config)
                self.set_program_lang(current_lang)
                main_config.set('OPTIONS_OUTPUT_PATH','output_folder', str(current_outputfolder))
                profile_config = main_config
            else:
                profile_config = config_manager.load_and_apply_profile(profile,main_config)  
            
            self.parent.current_selection.read_config_file(main_config)
            
            for item in self.parent.all_interactive_items:
                section = None
                option = None
                if hasattr(item,'section'):
                    section=item.section
                if hasattr(item,'option'):
                    option=item.option
                if section and option and profile_config.has_option(section, option):
                    cur_state = item.GetValue()
                    cur_enabled =item.IsEnabled()
                    if isinstance(item, wx.CheckBox):
                        state = profile_config.getboolean(section, option, fallback=cur_state)
                    elif isinstance(item, wx.Slider):
                        state = profile_config.getint(section, option, fallback=cur_state)
                    else:
                        state = profile_config.get(section, option, fallback=cur_state)
                    if state!=cur_state:
                        if hasattr(item,'disable_on_manual_change'):
                            if item.disable_on_manual_change:
                                item.Enable(False)
                                item.SetValue(state)
                                item.Enable(cur_enabled)
                            else:
                                item.SetValue(state)
                        else:
                            item.SetValue(state)
                        if isinstance(item, wx.TextCtrl):
                            item.ChangeValue(state)
                        event = wx.CommandEvent(wx.EVT_CHECKBOX.typeId)
                        event.SetEventObject(item)  # Manually set the event object
                        wx.PostEvent(item, event)
            self.parent.log_ctrl.log("config_load_ok",profile_text)
        except Exception as e:
            self.parent.log_ctrl.log("config_load_error",profile_text,e)

        self.parent.state_updating_is_allowed = True
        self.parent.update_global_state()

    def settings_to_default_depricated(self):
        """
        Show a confirmation dialog asking the user if they really want
        to reset the settings to default. If the user confirms, the program
        will restart to apply the changes.
        """
        message = get_local_text('dialog_reset_settings').replace('\\n', '\n')

        # Create the dialog with OK (Confirm) and Cancel buttons
        dlg = wx.MessageDialog(
            self.parent,
            message,
            get_local_text('dialog_reset_settings_title'),
            wx.OK | wx.CANCEL | wx.ICON_QUESTION
        )
        # Ensure the dialog gets focus
        #dlg.SetFocus()

        if dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            current_lang=self.get_program_lang()
            config_manager.reset_configuration_OS(self.parent.config)
            self.set_program_lang(current_lang)
            wx.GetApp().restart()
        else:
            dlg.Destroy()



    def __init__(self, parent):
        
        # Menu Bar
        self.menu_bar = wx.MenuBar()
        self.parent = parent

        # --- File Menu ---
        file_menu = wx.Menu()
        self.file_menu=file_menu

        # Open Image(s)
        open_images_item = file_menu.Append(wx.ID_OPEN, get_local_text("menu_open_image"))
        self.menu_bar.Bind(wx.EVT_MENU, self.on_file_open_images_item, open_images_item)

        # Select Input Folder
        select_folder_item = file_menu.Append(wx.NewId(), get_local_text("menu_select_input_folder"))
        self.menu_bar.Bind(wx.EVT_MENU, self.on_file_select_folder_item, select_folder_item)

        # Close Image/Folder
        close_item = file_menu.Append(wx.ID_CLOSE, get_local_text("menu_close_input"))
        self.menu_bar.Bind(wx.EVT_MENU, self.on_file_close_item, close_item)
        close_item.Enable(False)

        # Separator
        file_menu.AppendSeparator()

        # Run Processing
        run_processing_item = file_menu.Append(wx.ID_SAVE, get_local_text("menu_run_processing"))
        self.menu_bar.Bind(wx.EVT_MENU, self.on_file_run_processing_item, run_processing_item)
        run_processing_item.Enable(False)

        # Abort Processing
        abort_processing_item = file_menu.Append(wx.ID_ABORT, get_local_text("menu_abort_processing"))
        self.menu_bar.Bind(wx.EVT_MENU, self.on_file_abort_processing_item, abort_processing_item)
        abort_processing_item.Enable(False)

        # Separator
        file_menu.AppendSeparator()

        # Exit
        exit_item = file_menu.Append(wx.ID_EXIT, get_local_text("menu_exit"))
        self.menu_bar.Bind(wx.EVT_MENU, self.on_file_exit_item, exit_item)

        self.menu_bar.Append(file_menu, get_local_text("menu_file"))

        self.parent.SetMenuBar(self.menu_bar)

        # --- Settings Menu ---
        settings_menu = wx.Menu()
        self.settings_menu=settings_menu

        self.profiles_menu_items = {}
        profiles_menu = wx.Menu()
        profiles_dir = get_data_subdir("profiles")

        # Reset to Default
        to_default_item = profiles_menu.Append(wx.NewId(), get_local_text("menu_reset_default"))
        self.menu_bar.Bind(wx.EVT_MENU, self.on_settings_to_default_item, to_default_item)
        # Separator
        profiles_menu.AppendSeparator()
        if os.path.isdir(profiles_dir):
            files = os.listdir(profiles_dir)
            # Filter for profiles files (e.g. profile_reforgehd.cfg, etc.)
            profile_files = [f for f in files if f.startswith("profile_") and f.endswith(".cfg")]
            for profile_file in profile_files:
                # Extract profile code from file name: "profile_reforgehd.cfg" -> "reforgehd"
                profile_code = profile_file[0:-len(".cfg")]
                # Create a checkable menu item
                profile_item = profiles_menu.Append(wx.NewId(), get_local_text(profile_code))
                self.profiles_menu_items[profile_code] = profile_item
                # Bind the event, passing the profile code (e.g. "profile_reforgehd")
                self.menu_bar.Bind(
                    wx.EVT_MENU,
                    lambda event, code=profile_code: self.on_profile_item(event, code),
                    profile_item
                )

        profile_submenu_item = settings_menu.AppendSubMenu(profiles_menu, get_local_text("menu_profile"))

        # Separator
        settings_menu.AppendSeparator()
        # Language submenu: dynamically populate from "localisations" folder.
        self.language_menu_items = {}  # Dictionary to hold language file -> menu item mapping

        language_menu = wx.Menu()
        localisation_dir = get_data_subdir("localisations")
        if os.path.isdir(localisation_dir):
            files = os.listdir(localisation_dir)
            # Filter for language files (e.g. local_eng.txt, local_rus.txt, etc.)
            lang_files = [f for f in files if f.startswith("local_") and f.endswith(".txt")]
            # Ensure the default language is always first
            lang_files.sort(key=lambda x: 0 if x == "local_eng.txt" else 1)
            # Assume get_program_lang returns the current language code, e.g., "eng"
            current_lang = self.get_program_lang()  
            
            for lang_file in lang_files:
                # Extract language code from file name: "local_eng.txt" -> "eng"
                lang_code = lang_file[len("local_"):-len(".txt")]
                
                try:
                    with open(os.path.join(localisation_dir, lang_file), "r", encoding="utf-8") as f:
                        first_line = f.readline().strip()
                    if first_line.lower().startswith("language"):
                        # Expecting format: language = English
                        parts = first_line.split("=", 1)
                        lang_name = parts[1].strip() if len(parts) > 1 else lang_file
                    else:
                        lang_name = lang_file
                except Exception:
                    lang_name = lang_file
                
                # Create a checkable menu item
                lang_item = language_menu.AppendCheckItem(wx.NewId(), lang_name)
                if lang_code == current_lang:
                    lang_item.Check(True)
                self.language_menu_items[lang_code] = lang_item
                
                # Bind the event, passing the language code (e.g. "eng", "rus")
                self.menu_bar.Bind(
                    wx.EVT_MENU,
                    lambda event, code=lang_code: self.on_change_language(event, code),
                    lang_item
                )

        language_submenu_item = settings_menu.AppendSubMenu(language_menu, get_local_text("menu_language"))

        """         # Separator
        settings_menu.AppendSeparator()

        # Preferences (disabled)
        preferences_item = settings_menu.Append(wx.NewId(), get_local_text("menu_preferences"))
        preferences_item.Enable(False)
        """
        self.menu_bar.Append(settings_menu, get_local_text("menu_settings")) 

        # --- Custom Frames Menu ---
        custom_frames_menu = CustomFramesMenu(self)
        self.menu_bar.Append(custom_frames_menu, get_local_text("menu_custom_frames"))

        # --- Help Menu ---
        help_menu = wx.Menu()

        # About (disabled)
        about_item = help_menu.Append(wx.ID_ABOUT, get_local_text("menu_about"))
        # Bind the About menu item event to on_about
        self.menu_bar.Bind(wx.EVT_MENU, self.on_about, about_item)

        self.menu_bar.Append(help_menu, get_local_text("menu_help"))

        self.parent.SetMenuBar(self.menu_bar)