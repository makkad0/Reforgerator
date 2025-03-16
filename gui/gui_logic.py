import wx
import os
import subprocess
import sys

import var.global_var as gv
import var.sizes as cs

from gui.gui_validators import SliderSyncValidator
from gui.gui_input_preview import InputImagePanel
from gui.gui_output_preview import OutputPreviewImage
from gui.gui_logwindow import RichLogPanel
from gui.gui_menu import TopMenu
from gui.gui_tooltip import HoverOverlay
from gui.gui_tooltip import update_tooltip
from gui.gui_button_panel import ButtonClass
from gui.gui_input_settings import MultiSelectComboPanel

import src.config_manager as config_manager
from src.stored_var import CurrentSelection
from src.custom_frames import init_CUSTOM_FRAMES_DICT
from src.localisation import get_local_text
from src.localisation import get_tooltip_text
from src.localisation import update_localisation
from src.system import get_data_subdir

from PIL import Image

class NoTabPanel(wx.Panel):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

    def AcceptsFocusFromKeyboard(self):
        return False

class IconConverterGUI(wx.Frame):

    def __init__(self, parent, title):
        super().__init__(parent, title=gv.PROGRAM_FULLNAME, size=cs.WINDOW_SIZE, style=wx.DEFAULT_FRAME_STYLE & ~wx.RESIZE_BORDER & ~wx.MAXIMIZE_BOX)
        
        #It fixes bug with non-working webp after reloading
        Image.init()

        icon_path = os.path.join(get_data_subdir(), "logo.ico")
        if os.path.isfile(icon_path):
            icon = wx.Icon(icon_path, wx.BITMAP_TYPE_ICO)
            self.SetIcon(icon)

        self.image_path = None
        self.image_preview = None
        self.generation_start= False
        self.state_updating_is_allowed=True

        self.overlay_items = []
        self.all_interactive_items = []
        self.delayed_log = []
        self.config = config_manager.init_configuration_from_OS() # attach the config to your main frame

        self.current_selection=CurrentSelection(self)
        self.current_selection.read_config_file(self.config)

        #Try to load custom frames
        try:
            init_CUSTOM_FRAMES_DICT()
        except Exception as e:
            self.delayed_log.append(('program_failed_to_load_list_of_custom_frames',e))

        lang_code=self.config.get('LANG','program_lang', fallback='eng')
        update_localisation(lang_code)

        self.init_ui()
        self.Centre()
        self.Show()

    def ui_generate_standard_checkbox_list(self,OPTION_DICT):
        section = OPTION_DICT["section"]
        output_preview_change = OPTION_DICT['update_preview']
        update_convert_btn_state = OPTION_DICT['update_generate']
        option_list = {}
        available_options= [option for option in OPTION_DICT["options"] if option not in gv.HIDDEN_OPTIONS and option not in gv.NON_CHECKBOX_OPTIONS]
        for option in available_options:
            cb = wx.CheckBox(self.panel, label=get_local_text(option))
            cb.section=section
            cb.option=option
            if isinstance(output_preview_change, dict):
                cb.output_preview_change=output_preview_change.get(option,False)
            else:
                cb.output_preview_change=output_preview_change
            if isinstance(update_convert_btn_state, dict):
                cb.update_convert_btn_state=update_convert_btn_state.get(option,False)
            else:
                cb.update_convert_btn_state=update_convert_btn_state      
            option_list[option] = cb
            # Initialize state from config (defaulting to False if not found)
            state = self.config.getboolean(section, option, fallback=False)
            cb.SetValue(state)
            cb.Bind(wx.EVT_CHECKBOX, self.on_universal_option_change)
            self.all_interactive_items.append(cb)
            tooltip = get_tooltip_text(option,True)
            if tooltip:
                cb.tooltip_overlay = HoverOverlay(
                    parent=self.panel,
                    item = cb,
                    type = "active",
                    tooltip_text=tooltip,
                )
                self.overlay_items.append(cb.tooltip_overlay)

            # Don't add checkboxes to multiline sections
        return option_list

    def ui_generate_standard_section(self,OPTION_DICT,multiline:bool = False):
        section_code = OPTION_DICT['title']
        section_title=section_code
        if not(section_title):
            section_title=""
        else:
            section_title=get_local_text(section_title)
        if multiline:
            alignment=wx.VERTICAL
        else:
            alignment=wx.HORIZONTAL
        section = wx.StaticBoxSizer(alignment, self.panel,section_title)
        section.GetStaticBox().SetFont(self.section_font)
        tooltip = get_tooltip_text(section_code,True)
        if tooltip:
            section.tooltip_overlay = HoverOverlay(
                parent=self.panel,
                item = section,
                type = "section",
                tooltip_text=tooltip,
            )
            self.overlay_items.append(section.tooltip_overlay)
        return section
    
    def ui_generate_standard_section_with_checkboxes(self,OPTION_DICT,multiline:bool = False):
        section = self.ui_generate_standard_section(OPTION_DICT,multiline)
        option_list = self.ui_generate_standard_checkbox_list(OPTION_DICT)
        for cb in option_list.values():
            section.Add(cb, flag=wx.ALL, border=cs.BORDERSIZE_OPTIONS)
        return section, option_list

    def init_ui(self):
        
        panel = wx.Panel(self)
        self.panel = panel 

        self.section_font=wx.Font(cs.STANDARD_SECTION_FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

        main_sizer = wx.GridBagSizer(cs.GUI_MAIN_V_GAP, cs.GUI_MAIN_H_GAP)
        count_v=0
        count_h=0
        
        # Menu Bar
        self.menu=TopMenu(self)
        
        #NEW ROW
        count_v_cur=int(count_v)
        count_h_cur=int(count_h)

        # Universal Left Pad
        count_h +=1

        main_sizer.Add( (cs.BORDERSIZE_LEFTPAD,-1) , pos=(count_v_cur,count_h_cur),  flag=wx.LEFT, border=0)
        count_h_cur +=1
        
        # Create a LogTextCtrl and redirect wx.Log to it.
        self.log_ctrl = RichLogPanel(self.panel)
        span_v=1
        span_h=3
        main_sizer.Add( self.log_ctrl , pos=(count_v_cur,count_h_cur), span=(span_v,span_h), flag=wx.EXPAND | wx.ALL, border=0) 
        count_h_cur +=span_h

        #Right Pad
        main_sizer.Add( (cs.BORDERSIZE_RIGHTPAD,-1) ,pos=(count_v_cur,count_h_cur),  flag=wx.LEFT, border=0) 
        count_h_cur +=1

        #NEW ROW
        count_v +=1
        count_v_cur=int(count_v)
        count_h_cur=int(count_h)

        # Output Border Settings
        self.border_section, self.border_options = self.ui_generate_standard_section_with_checkboxes(gv.OPTIONS_BORDER)
        self.border_section.SetMinSize( (cs.BORDER_SETTINGS_SECTION_MIN_X_SIZE,-1) )
        span_v=1
        span_h=2
        main_sizer.Add(self.border_section,pos=(count_v_cur,count_h_cur), span=(span_v, span_h), flag=wx.ALL | wx.EXPAND, border=cs.BORDERSIZE_SECTIONS) 
        count_h_cur +=span_h

        # Images Preview - Input and Output 
        images_box = wx.BoxSizer(wx.VERTICAL)
        # Input Preview
        inputimage_box_borders = NoTabPanel(panel, size=cs.IMAGE_PREVIEW_BORDER_SIZE, style=wx.BORDER_SIMPLE)
        self.input_panel = InputImagePanel(inputimage_box_borders, size=cs.IMAGE_PREVIEW_SIZE)
        input_image_sizer=wx.BoxSizer()
        input_image_sizer.Add(self.input_panel, 0, wx.ALL, 0)
        inputimage_box_borders.SetSizerAndFit(input_image_sizer)
        inputimage_box = wx.StaticBoxSizer(wx.VERTICAL, panel, get_local_text("images_input_preview"))
        inputimage_box.GetStaticBox().SetFont(self.section_font)
        inputimage_box.GetStaticBox().SetWindowStyleFlag(wx.BORDER_NONE)
        inputimage_box.Add(inputimage_box_borders, proportion=0, flag=wx.FIXED_MINSIZE , border=0)
        images_box.Add(inputimage_box, flag=wx.FIXED_MINSIZE , border=0)

        images_box.AddStretchSpacer()

        # Output Preview
        outputimage_box_borders = NoTabPanel(panel, size=cs.IMAGE_PREVIEW_BORDER_SIZE, style=wx.BORDER_SIMPLE)
        self.output_panel = OutputPreviewImage(outputimage_box_borders, size=cs.IMAGE_PREVIEW_SIZE)
        output_image_sizer=wx.BoxSizer()
        output_image_sizer.Add(self.output_panel, 0, wx.ALL, 0)
        outputimage_box_borders.SetSizerAndFit(output_image_sizer)
        outputimage_box = wx.StaticBoxSizer(wx.VERTICAL, panel, get_local_text("images_output_preview"))
        outputimage_box.GetStaticBox().SetFont(self.section_font)
        outputimage_box.GetStaticBox().SetWindowStyleFlag(wx.BORDER_NONE)
        outputimage_box.Add(outputimage_box_borders, proportion=0, flag=wx.FIXED_MINSIZE , border=0)
        
        images_box.Add(outputimage_box, flag=wx.FIXED_MINSIZE , border=0)

        span_v=5
        span_h=1
        main_sizer.Add(images_box, flag=wx.EXPAND,pos=(count_v_cur,count_h_cur), span=(span_v, span_h), border=cs.BORDERSIZE_SECTIONS)
        count_h_cur +=span_h

        #NEW ROW
        count_v +=1
        count_v_cur=int(count_v)
        count_h_cur=int(count_h)

        # Output Size Settings
        self.size_section, self.size_options = self.ui_generate_standard_section_with_checkboxes(gv.OPTIONS_SIZE)
        main_sizer.Add(self.size_section,pos=(count_v_cur,count_h_cur),  flag=wx.ALL | wx.EXPAND, border=cs.BORDERSIZE_SECTIONS) 
        count_h_cur +=1

        # Output Style Settings
        self.style_section, self.style_options = self.ui_generate_standard_section_with_checkboxes(gv.OPTIONS_STYLE)
        main_sizer.Add(self.style_section,pos=(count_v_cur,count_h_cur),  flag=wx.ALL | wx.EXPAND, border=cs.BORDERSIZE_SECTIONS)
        count_h_cur +=1 
        
        #NEW ROW
        count_v +=1
        count_v_cur=int(count_v)
        count_h_cur=int(count_h)

        #Extras Settings
        self.extras_section, self.extras_options = self.ui_generate_standard_section_with_checkboxes(gv.OPTIONS_EXTRAS)
        span_v=1
        span_h=2
        main_sizer.Add(self.extras_section, pos=(count_v_cur,count_h_cur), span=(span_v, span_h), flag=wx.ALL | wx.EXPAND, border=cs.BORDERSIZE_SECTIONS)
        count_h_cur +=span_h
        self.update_black_frame_status()

        #NEW ROW
        count_v +=1
        count_v_cur=int(count_v)
        count_h_cur=int(count_h)

        # Output Format Settings
        # Subsections should be created before moveable checkboxes! (due to the bug of the display)
        subsections={}
        self.format_subsection_options  = {}
        for option in gv.OPTIONS_FORMAT["options"]:
            if option=="format_dds":
                # Fill row 1
                self.dds_section = self.ui_generate_standard_section(gv.DDS_SETTINGS, True)
                self.dds_section.row1=wx.BoxSizer(wx.HORIZONTAL)
                subsection = self.dds_section
                self.dds_options = {}
                # Create Static Text 1
                self.dds_section.statictext1=wx.StaticText(panel, label=get_local_text("dds_type"))
                self.dds_section.row1.Add(self.dds_section.statictext1, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL , border=0)
                self.dds_section.row1.AddSpacer(1)
                # DDS Compression Type ComboBox
                self.dds_type = wx.ComboBox(panel, choices=gv.DDS_COMPRESSION_TYPES, style=wx.CB_READONLY, size=(cs.DDS_OPTION_TYPEWINDOW_SIZE, -1))
                self.dds_type.section=gv.DDS_SETTINGS["section"]
                self.dds_type.option="dds_type"
                self.dds_type.output_preview_change = True
                self.all_interactive_items.append(self.dds_type)
                self.dds_options[self.dds_type.option] = self.dds_type
                state = self.config.get(self.dds_type.section,self.dds_type.option, fallback="DXT1")
                if state not in gv.DDS_COMPRESSION_TYPES:
                    state = "DXT1"
                self.dds_type.SetValue(state)
                self.dds_type.Bind(wx.EVT_COMBOBOX, self.on_universal_option_change)
                self.dds_section.row1.Add(self.dds_type, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL , border=0)
                self.dds_section.row1.AddStretchSpacer()
                # Create Static Text 2
                self.dds_section.statictext2=wx.StaticText(panel, label=get_local_text("dds_mipmap"))
                tooltip = get_tooltip_text("dds_mipmap",True)
                if tooltip:
                    self.dds_section.statictext2.tooltip_overlay = HoverOverlay(
                        parent=self.panel,
                        item = self.dds_section.statictext2,
                        type = "statictext",
                        tooltip_text=tooltip,
                    )
                    self.overlay_items.append(self.dds_section.statictext2.tooltip_overlay)
                self.dds_section.row1.Add(self.dds_section.statictext2, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL , border=0)
                self.dds_section.row1.AddSpacer(1)
                # DDS Mipmaps ComboBox
                self.dds_mipmap = wx.ComboBox(panel, choices=gv.DDS_MIPMAP_VALUES, style=wx.CB_READONLY, size=(cs.DDS_OPTION_MIPMAPWINDOW_SIZE, -1))
                self.dds_mipmap.section=gv.DDS_SETTINGS["section"]
                self.dds_mipmap.option="dds_mipmap"
                self.dds_options[self.dds_mipmap.option] = self.dds_mipmap
                state = self.config.get(self.dds_mipmap.section,self.dds_mipmap.option, fallback="Auto")
                if state not in gv.DDS_MIPMAP_VALUES:
                    state = "Auto"
                self.dds_mipmap.SetValue(state)
                self.dds_mipmap.Bind(wx.EVT_COMBOBOX, self.on_universal_option_change)
                self.all_interactive_items.append(self.dds_mipmap)
                self.dds_section.row1.Add(self.dds_mipmap, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL , border=0)
                 # First line indent
                self.dds_section.AddSpacer(cs.FORMAT_OPTION_SUBSECTION_DDS_INDENT)                          
                # Add rows to section box
                self.dds_section.Add(self.dds_section.row1, flag=wx.ALL | wx.EXPAND, border=0)
                # Save option list
                self.format_subsection_options[option] = self.dds_options
            elif option == "format_blp":
                self.blp_options = {}
                self.blp_section = self.ui_generate_standard_section(gv.BLP_SETTINGS, True)
                subsection = self.blp_section
                # Fill row 1
                self.blp_section.row1=wx.BoxSizer(wx.HORIZONTAL)
                # Create Static Text 1
                self.blp_section.statictext1=wx.StaticText(panel, label=get_local_text("blp_compression"))
                # Create blp compression slider
                self.blp_compression = wx.Slider(panel, minValue=gv.BLP_MINCOMPRESSION, maxValue=gv.BLP_MAXCOMPRESSION, style=wx.SL_HORIZONTAL, size=(-1, -1))
                self.blp_compression.section=gv.BLP_SETTINGS["section"]
                self.blp_compression.option="blp_compression"
                self.blp_compression.output_preview_change = True
                self.blp_options[self.blp_compression.option] = self.blp_compression
                self.blp_compression.disable_on_manual_change = True
                self.all_interactive_items.append(self.blp_compression)
                state = self.config.getint(self.blp_compression.section,self.blp_compression.option, fallback=gv.BLP_MAXCOMPRESSION)
                self.blp_compression.SetValue(state)
                # Create text field with validator (linked to slider)
                self.blp_compression_value = wx.TextCtrl(panel, size=(cs.BLP_OPTION_NUMERICWINDOW_SIZE, -1), style=wx.TE_RIGHT | wx.TE_PROCESS_ENTER,validator=SliderSyncValidator(self.blp_compression))
                self.blp_compression_value.SetValue(str(state))
                self.blp_compression_value.section=gv.BLP_SETTINGS["section"]
                self.blp_compression_value.option="blp_compression"
                self.blp_compression_value.disable_on_manual_change = True
                self.all_interactive_items.append(self.blp_compression_value)
                # Bind events
                self.blp_compression.Bind(wx.EVT_SLIDER, self.on_blp_compression_slider_change)
                # Add elements to row 1
                self.blp_section.row1.Add(self.blp_section.statictext1,  proportion=0, flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=0)
                self.blp_section.row1.Add(self.blp_compression,proportion=1,flag = wx.ALL | wx.EXPAND, border=0)
                self.blp_section.row1.Add(self.blp_compression_value,proportion=0,flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL , border=0)
                # Fill row 2
                self.blp_section.row2=wx.BoxSizer(wx.HORIZONTAL)
                # Create Checkboxes for row 2
                self.blp_checkboxes = self.ui_generate_standard_checkbox_list(gv.BLP_SETTINGS)
                # Create Static Text 2
                self.blp_section.statictext2=wx.StaticText(panel, label=get_local_text("blp_mipmap"))
                tooltip = get_tooltip_text("blp_mipmap",True)
                if tooltip:
                    self.blp_section.statictext2.tooltip_overlay = HoverOverlay(
                        parent=self.panel,
                        item = self.blp_section.statictext2,
                        type = "statictext",
                        tooltip_text=tooltip,
                    )
                    self.overlay_items.append(self.blp_section.statictext2.tooltip_overlay)
                # BLP Mipmaps ComboBox
                self.blp_mipmap = wx.ComboBox(panel, choices=gv.BLP_MIPMAP_VALUES, style=wx.CB_READONLY, size=(cs.BLP_OPTION_MIPMAPWINDOW_SIZE, -1))
                self.blp_mipmap.section=gv.BLP_SETTINGS["section"]
                self.blp_mipmap.option="blp_mipmap"
                self.blp_options[self.blp_mipmap.option] = self.blp_mipmap
                self.all_interactive_items.append(self.blp_mipmap)
                state = self.config.get(self.blp_mipmap.section,self.blp_mipmap.option, fallback="Auto")
                if state not in gv.BLP_MIPMAP_VALUES:
                    state = "Auto"
                self.blp_mipmap.SetValue(state)
                self.blp_mipmap.Bind(wx.EVT_COMBOBOX, self.on_universal_option_change)
                # Add elements to row 2
                for cb1 in self.blp_checkboxes.values():
                    self.blp_options[cb1.option] = cb1
                    self.blp_section.row2.Add(cb1, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL , border=0)
                self.blp_section.row2.AddStretchSpacer()
                self.blp_section.row2.Add(self.blp_section.statictext2,flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL , border=0)
                self.blp_section.row2.AddSpacer(1)
                self.blp_section.row2.Add(self.blp_mipmap,flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=0)
                # First line indent
                self.blp_section.AddSpacer(cs.FORMAT_OPTION_SUBSECTION_BLP_INDENT)
                # Add rows to section box
                self.blp_section.Add(self.blp_section.row1,flag = wx.ALL | wx.EXPAND, border=0)
                self.blp_section.Add(self.blp_section.row2,flag = wx.ALL | wx.EXPAND, border=0)
                # Save option list
                self.format_subsection_options[option] = self.blp_options
            elif option == "format_tga":
                self.tga_section = self.ui_generate_standard_section(gv.TGA_SETTINGS, False)
                self.tga_section.AddSpacer(cs.FORMAT_EMPTY_SUBSECTION_SIZE)
                subsection = self.tga_section
            elif option == "format_png":
                self.png_section = self.ui_generate_standard_section(gv.PNG_SETTINGS, False)
                self.png_section.AddSpacer(cs.FORMAT_EMPTY_SUBSECTION_SIZE)
                subsection = self.png_section
            subsections[option]=subsection
        
        format_grid_sizer = wx.GridBagSizer(cs.FORMAT_GRID_SIZER_V_GAP, cs.FORMAT_GRID_SIZER_H_GAP)
        format_grid_sizer.AddGrowableCol(0)
        # Add Parent Format Section with each subsections
        self.format_section = self.ui_generate_standard_section(gv.OPTIONS_FORMAT, True)
        self.format_options = self.ui_generate_standard_checkbox_list(gv.OPTIONS_FORMAT)

        count_v_format=0
        count_v_max=1
        count_h_format=0
        for cb in self.format_options.values():
            option=cb.option
            if option in subsections:
                subsection=subsections[option]
                cb.subsection = subsection
                format_grid_sizer.Add(subsection, pos=(count_v_format,count_h_format),flag=wx.ALL | wx.EXPAND, border=0)
                # Ensure all elements are disabled initially if the checkbox is off
                if not cb.IsChecked():
                    self.enable_all_controls(subsection,False)
                count_v_format += 1
                if count_v_format>count_v_max:
                    count_h_format +=1
                    count_v_format = 0

        self.format_section.Add(format_grid_sizer,flag=wx.ALL | wx.EXPAND, border=cs.BORDERSIZE_SUBSECTION)

        # Add the format_box to the main layout
        span_v=1
        span_h=2
        main_sizer.Add(self.format_section, pos=(count_v_cur,count_h_cur), span=(span_v, span_h), flag=wx.ALL | wx.EXPAND, border=cs.BORDERSIZE_SECTIONS)
        count_h_cur +=span_h

        # Rearrange TabOrder
        checkbox_pr=self.border_options['border_none']
        for checkbox_section in self.format_options.values():
            option = checkbox_section.option
            if option in self.format_subsection_options:
                subsection_options = self.format_subsection_options[option]
                first_key = next(iter(subsection_options))
                first_option = subsection_options[first_key]
                checkbox_section.MoveBeforeInTabOrder(first_option)

        #NEW ROW
        count_v +=1
        count_v_cur=int(count_v)
        count_h_cur=int(count_h)

        # Input Settings
        self.input_section, self.input_options = self.ui_generate_standard_section_with_checkboxes(gv.OPTIONS_INPUT)
        self.input_options['input_process_subfolders'].regather_input=True
        self.input_section.statictext1=wx.StaticText(panel, label=get_local_text("input_process_filetypes_title"))
        self.input_section.input_format = MultiSelectComboPanel(panel)
        self.input_section.input_format.section="OPTIONS_INPUT"
        self.input_section.input_format.option="input_process_filetypes"
        self.input_section.input_format.regather_input=True
        tooltip = get_tooltip_text(self.input_section.input_format.option,True)
        if tooltip:
            cb.tooltip_overlay = HoverOverlay(
                parent=self.panel,
                item = self.input_section.statictext1,
                type = "active",
                tooltip_text=tooltip,
            )
            self.overlay_items.append(cb.tooltip_overlay)
        self.all_interactive_items.append(self.input_section.input_format)
        state = self.config.get(self.input_section.input_format.section,self.input_section.input_format.option, fallback=gv.INPUT_IMAGE_DEFAULT_TYPES)
        self.input_section.input_format.SetValue(state,False)
        self.input_section.AddStretchSpacer()
        self.input_section.Add(self.input_section.statictext1,flag=wx.ALL|  wx.ALIGN_CENTER_VERTICAL,border=0)
        self.input_section.AddSpacer(1)
        self.input_section.Add(self.input_section.input_format,flag=wx.ALL|  wx.ALIGN_CENTER_VERTICAL,border=0)

        span_v=1
        span_h=2
        main_sizer.Add(self.input_section, pos=(count_v_cur,count_h_cur), span=(span_v, span_h), flag=wx.ALL | wx.EXPAND, border=cs.BORDERSIZE_SECTIONS)
        count_h_cur +=span_h
        #NEW ROW
        count_v +=1
        count_v_cur=int(count_v)
        count_h_cur=int(count_h)
        self.update_input_gui_state()

        # Output Options
        self.outputset_section = self.ui_generate_standard_section(gv.OPTIONS_OUTPUT, True)
        self.outputset_options = self.ui_generate_standard_checkbox_list(gv.OPTIONS_OUTPUT)
        outputset_firstrow = wx.BoxSizer(wx.HORIZONTAL)
        for cb in self.outputset_options.values():
             outputset_firstrow.Add(cb, flag=wx.ALL| wx.ALIGN_CENTER_VERTICAL, border=cs.BORDERSIZE_OPTIONS)
             if cb.option=="outputset_merged":
                 self.outputset_merged=cb
        self.on_outputset_subfolders_toggle(None)
        outputset_firstrow.AddStretchSpacer(prop=0)  
        # Output Basename
        self.output_basename_title= wx.StaticText(panel, label=get_local_text("outputset_basename_title"))
        tooltip = get_tooltip_text("outputset_basename_title",True)
        if tooltip:
            self.output_basename_title.tooltip_overlay = HoverOverlay(
                parent=self.panel,
                item = self.output_basename_title,
                type = "statictext",
                tooltip_text=tooltip,
            )
            self.overlay_items.append(self.output_basename_title.tooltip_overlay)
        self.output_basename_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.output_basename_text = wx.TextCtrl(panel)
        self.output_basename_sizer.Add(self.output_basename_text, proportion=1,flag=wx.ALL| wx.EXPAND, border=0)
        self.output_basename_text.section = gv.OPTIONS_OUTPUT_PATH["section"]
        self.output_basename_text.option = "output_basename" 
        self.output_basename_text.Bind(wx.EVT_TEXT, lambda evt: self.on_output_basename_text_change())
        outputset_firstrow.Add(self.output_basename_sizer, proportion=1, flag=wx.ALL|wx.EXPAND)
        self.outputset_section.Add(outputset_firstrow, flag=wx.EXPAND)
        self.set_input_image_basename_enable(False)
        # Output Folder
        output_folder_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.output_folder_button = wx.Button(panel, label=get_local_text("outputset_btn_choosefolder"))
        tooltip = get_tooltip_text("outputset_btn_choosefolder",True)
        if tooltip:
            self.output_folder_button.tooltip_overlay = HoverOverlay(
                parent=self.panel,
                item = self.output_folder_button,
                type = "active",
                tooltip_text=tooltip,
            )
            self.overlay_items.append(self.output_folder_button.tooltip_overlay)
        self.output_folder_button.Bind(wx.EVT_BUTTON, self.on_choose_output_folder)
        self.output_folder_text = wx.TextCtrl(panel)
        self.output_folder_text.section = gv.OPTIONS_OUTPUT_PATH["section"]
        self.output_folder_text.option = "output_folder" 
        state = self.config.get(self.output_folder_text.section,self.output_folder_text.option, fallback="")
        self.output_folder_text.SetValue(state)
        self.output_folder_text.Bind(wx.EVT_TEXT, lambda evt: self.on_output_folder_text_change())
        output_folder_sizer.Add(self.output_folder_button, flag=wx.EXPAND)
        output_folder_sizer.Add(self.output_folder_text, proportion=1, flag=wx.EXPAND | wx.RIGHT)
        self.outputset_section.Add(output_folder_sizer, flag=wx.EXPAND)
        span_v=1
        span_h=3
        main_sizer.Add(self.outputset_section,pos=(count_v_cur,count_h_cur), span=(span_v, span_h), flag=wx.ALL | wx.EXPAND, border=cs.BORDERSIZE_SECTIONS) 
        count_h_cur +=span_h

        #NEW ROW
        count_v +=1
        count_v_cur=int(count_v)
        count_h_cur=int(count_h)

        #Button Panel
        self.btn_pannel=ButtonClass(self,panel) 
        self.button_list = self.btn_pannel.button_list
        span_v=1
        span_h=3
        main_sizer.Add(self.btn_pannel.btn_sizer,pos=(count_v_cur,count_h_cur), span=(span_v, span_h), flag=wx.ALIGN_CENTER, border=cs.BORDERSIZE_SECTIONS)
        count_h_cur +=span_h
        self.update_generation_state()
        #NEW ROW
        count_v +=1
        count_v_cur=int(count_v)
        count_h_cur=int(count_h)

        #BOTTOM Pad
        main_sizer.Add( (cs.BORDERSIZE_BOTTOMPAD,-1) ,pos=(count_v_cur,count_h_cur),  flag=wx.LEFT, border=0) 

        panel.SetSizerAndFit(main_sizer)

        # Perform layout first to calculate positions
        panel.Layout()

        # Format Checkboxes Reposition
        for cb in self.format_options.values():
            if  hasattr(cb, 'subsection'):
                static_box_position = cb.subsection.GetPosition()  # Get its position
                cb_position = wx.Point(static_box_position.x + cs.FORMAT_OPTION_CHECKBOX_PAD, static_box_position.y)  # Adjust for overlap
                cb.SetPosition(cb_position)

        # Output Basename Title Reposition
        self.output_basename_title.SetPosition(wx.Point(self.output_basename_text.GetPosition().x+cs.OUTPUT_BASENAME_TITLE_PAD,self.outputset_section.GetPosition().y))
        
        # Place tooltip overlay
        for item in self.overlay_items:
            item.place_tooltip_overlay()

        self.Fit()

        if self.delayed_log:
            for log_entry in self.delayed_log:
                self.log_ctrl.log(*log_entry)  # Unpacks tuple elements as arguments
            self.delayed_log = []
        self.log_ctrl.log("program_load_complete")

    def on_universal_option_change(self,event):
        eo = event.GetEventObject()

        update_global_state = False
        update_output_preview = False
        update_generation_state = False

        if hasattr(eo, 'section') and hasattr(eo, 'option'):
            self.current_selection.set_value(eo.section,eo.option,eo.GetValue())
            self.config.set(eo.section,eo.option, str(eo.GetValue()))
            config_manager.save_configuration_OS(self.config)
            if eo.section==gv.OPTIONS_FORMAT["section"]:
                self.on_format_toggle(event)
            elif eo.section==gv.OPTIONS_OUTPUT["section"] and eo.option=="outputset_subfolders":
                self.on_outputset_subfolders_toggle(event)
            elif eo.section==gv.OPTIONS_STYLE["section"] and eo.option=="style_hd":
                self.update_black_frame_status()

        if hasattr(eo,"regather_input"):
            if eo.regather_input:
                self.current_selection.gather_paths()
                update_global_state = True
        if hasattr(eo,"output_preview_change"):
            if eo.output_preview_change:
                update_output_preview = True
        if (hasattr(eo, 'update_convert_btn_state')):
            if eo.update_convert_btn_state:
                update_generation_state = True

        if update_global_state:
            self.update_global_state()
        else:
            if update_output_preview:
                self.output_panel.update_preview()
            if update_generation_state:
                self.update_generation_state()

    def on_format_toggle(self, event):
        for cb in self.format_options.values():
            enabled = cb.IsChecked()
            if hasattr(cb,"subsection"):
                self.enable_all_controls(cb.subsection,enabled)

    def on_blp_compression_slider_change(self, event):
        # Update the text field immediately
        new_val = self.blp_compression.GetValue()
        self.blp_compression_value.ChangeValue(str(new_val))
        # Debounce the config save: if a pending timer exists, stop it
        if hasattr(self, 'slider_save_timer') and self.slider_save_timer is not None:
            self.slider_save_timer.Stop()
        # Schedule a save after 200ms (only the latest slider value will be saved)
        self.slider_save_timer = wx.CallLater(gv.BLP_SLIDERDELAY_MS, self.save_blp_compression_value)

    def save_blp_compression_value(self):
        """Saves the current slider value into the configuration."""
        eo = self.blp_compression  # Reference to the slider control
        value = eo.GetValue()
        self.current_selection.set_value(eo.section,eo.option,value)
        self.config.set(eo.section,eo.option, str(value))
        config_manager.save_configuration_OS(self.config)
        if hasattr(eo,"output_preview_change"):
            if eo.output_preview_change:
                self.output_panel.update_preview()

    def on_outputset_subfolders_toggle(self, event):
        for outputset_options, cb in self.outputset_options.items():
            if cb.option=="outputset_subfolders":
                enabled = cb.IsChecked()
                self.outputset_merged.Enable(enabled)

    def on_output_folder_text_change(self):
        tb=self.output_folder_text
        text=str(tb.GetValue())
        self.config.set(tb.section,tb.option,text)
        self.current_selection.set_value(tb.section,tb.option,text)
        # Save the updated configuration.
        config_manager.save_configuration_OS(self.config)
        self.update_generation_state()

    def on_output_basename_text_change(self):
        tb=self.output_basename_text
        text=str(tb.GetValue())
        self.current_selection.set_value(tb.section,tb.option,text)

    def on_choose_output_folder(self, event):
        dlg = wx.DirDialog(self, get_local_text("dialog_choose_output_folder"), style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            folder = dlg.GetPath()
            self.output_folder_text.SetValue(folder)
            self.on_output_folder_text_change()  # Execute the change handler after updating the text field.
        dlg.Destroy()

    def set_input_image_basename_enable(self,enabled):
        self.output_basename_text.Enable(enabled)
        self.output_basename_title.Enable(enabled)

    def set_input_image_basename(self):
        if self.current_selection.paths_images and not(self.current_selection.paths_folders):
            if len(self.current_selection.paths_images)==1:
                self.set_input_image_basename_enable(True)
                # Use the first file's path
                first_path = self.current_selection.paths_images[0]
                # Extract the file name without its extension
                basename = os.path.splitext(os.path.basename(first_path))[0]
                # Set the value in the output basename text control
                self.current_selection.set_value(self.output_basename_text.section,self.output_basename_text.option,basename)
                self.output_basename_text.SetValue(basename)
                
    def update_basename_state(self):
        Enable = False
        if self.current_selection.paths_images and not(self.current_selection.paths_folders):
            if len(self.current_selection.paths_images)==1:
                Enable = True
        self.set_input_image_basename_enable(Enable)
            
    def update_input_gui_state(self):
        Enable = False
        if self.current_selection.paths_folders:
            Enable = True
        self.input_options["input_process_subfolders"].Enable(Enable)
        self.input_section.statictext1.Enable(Enable)
        self.input_section.input_format.enable_MultiSelectComboPanel(Enable)

    def update_black_frame_status(self):
        Enable = False
        if self.current_selection.get_value('OPTIONS_STYLE','style_hd'):
            Enable = True
        self.extras_options['extras_blackframe'].Enable(Enable)
        #self.output_basename_title.Enable(enabled)

    def update_generation_state_elements(self, Enable):
        self.button_list['btn_convert'].Enable(Enable)
        self.menu.update_menu_state()

    def custom_border_at_least_one_active(self):
        if hasattr(self,"custom_border"):
            value = self.custom_border.GetValue()
            if value:
                return value!=gv.DEFAULT_OPTION_PLACEHOLDER
            return False
        return False

    def update_generation_state(self):
        """
        Disables self.convert_btn if any of these conditions is true:
        1) All checkboxes in OPTIONS_SIZE are off.
        2) All checkboxes in OPTIONS_STYLE are off.
        3) All checkboxes in OPTIONS_BORDER are off.
        4) All checkboxes in OPTIONS_FORMAT are off.
        5) self.current_selection.paths is empty.
        6) Output folder field is empty.
        Otherwise, enables the button.
        """
        if self.generation_start:
            self.update_generation_state_elements(False)
            return
        
        # Condition 1: Check if all size options are off.
        size_invalid = not any(cb.GetValue() for cb in self.size_options.values())
        
        # Condition 2: Check if all style options are off.
        style_invalid = not any(cb.GetValue() for cb in self.style_options.values())

        # Condition 3: Check if all border options are off.
        border_invalid = not any(cb.GetValue() for cb in self.border_options.values())
        border_invalid = border_invalid and (not self.custom_border_at_least_one_active())

        # Condition 4: Check if all format options are off.
        format_invalid = not any(cb.GetValue() for cb in self.format_options.values())
        
        # Condition 5: Check if no image paths have been selected.
        selection_invalid = not (hasattr(self, 'current_selection') and self.current_selection.paths)
        
        # Condition 6: Check if the output folder text field is empty or whitespace.
        folder_invalid = not self.output_folder_text.GetValue().strip()
        
        Enable = not (size_invalid or style_invalid or border_invalid or format_invalid or 
                selection_invalid or folder_invalid)
        
        self.update_generation_state_elements(Enable)

    def enable_all_controls(self,sizer,enable=True):
        
        for item in sizer.GetChildren():
            # If the item is a window, disable it.
            window = item.GetWindow()
            if window:
                if enable:
                    window.Enable()
                else:
                    window.Disable()
                #Disable custom tooltip
                if hasattr(window,"tooltip_overlay"):
                    if enable:
                        window.tooltip_overlay.Enable()
                    else:
                        window.tooltip_overlay.Disable()
            # If the item is a nested sizer, disable its children recursively.
            child_sizer = item.GetSizer()
            if child_sizer:
                self.enable_all_controls(child_sizer,enable)

    def update_global_state(self):
        if self.state_updating_is_allowed:
            self.output_panel.update_preview()
            self.update_basename_state()
            self.update_input_gui_state()
            self.update_generation_state()