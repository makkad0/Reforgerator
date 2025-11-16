import os
import subprocess
import wx
import vars.global_var as gv
from src.generator import set_output_folder
from src.localisation import get_local_text

def gui_browse_output(self):
    """Opens self.output_path in the OS file explorer.
    If outputset_samedir is enabled and images are loaded, opens the input folder instead.
    If the folder does not exist, it prompts the user for creation.
    If creation fails, an error message is displayed.
    """
    # Check if "Keep Location" is enabled and input folders/images are selected
    output_suboption_dict = self.current_selection.recieve_suboptions([gv.OPTIONS_OUTPUT, gv.OPTIONS_OUTPUT_PATH])
    output_samedir = output_suboption_dict.get("outputset_samedir", False)
    
    # If Keep Location is enabled and we have input folders or images selected, open the input folder
    if output_samedir and hasattr(self, 'current_selection'):
        folder_path = None
        
        # Check if we have selected folders (even if empty)
        if self.current_selection.paths_folders:
            # Use the first selected folder directly
            folder_path = self.current_selection.paths_folders[0]
        # Check if we have selected images
        elif self.current_selection.paths_images:
            # Get the directory of the first selected image
            folder_path = os.path.dirname(self.current_selection.paths_images[0])
        # Check if we have processed paths (files found in folders)
        elif self.current_selection.paths:
            # Get the first input image's directory
            # paths_rel contains tuples of (full_path, rel_path), paths contains just full paths
            if self.current_selection.paths_rel:
                first_image_path = self.current_selection.paths_rel[0][0]  # Get full path from tuple
            else:
                first_image_path = self.current_selection.paths[0]  # Fallback to paths list
            folder_path = os.path.dirname(first_image_path)
        
        # If we found a folder path, try to open it
        if folder_path:
            # Check if the folder exists
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                # Open the folder in the OS file explorer
                open_folder_in_explorer(folder_path)
                return
            else:
                # Input folder doesn't exist (e.g., it was deleted after being selected)
                self.log_ctrl.log("browse_input_path_not_found", folder_path)
                return
    
    # Normal behavior: open output folder
    folder_path=""
    try:
        folder_path = set_output_folder(output_suboption_dict,False)
        # Check if the folder exists
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            # Open the folder in the OS file explorer
            open_folder_in_explorer(folder_path)
            return
    except Exception as e:
        self.log_ctrl.log("browse_output_error", folder_path, str(e))
        return

    # Folder does not exist, ask the user if they want to create it
    message = get_local_text('message_window_browse_warning').replace('\\n', '\n').format(folder_path)
    dlg = wx.MessageDialog(
        self,
        message,
        get_local_text('message_window_browse_warning_title'),
        wx.YES_NO | wx.ICON_WARNING
    )
    if dlg.ShowModal() == wx.ID_YES:
        dlg.Destroy()
        try:
            os.makedirs(folder_path, exist_ok=True)  # Attempt to create folder (including parents)
            open_folder_in_explorer(folder_path)  # Now open the newly created folder
        except OSError as e:
            message = get_local_text('message_window_browse_fail').replace('\\n', '\n').format(folder_path,e.strerror,e.errno)
            dlg = wx.MessageDialog(
                self,
                message,
                get_local_text('message_window_browse_fail_title'),
                wx.OK | wx.ICON_ERROR
            )
            dlg.ShowModal()
            dlg.Destroy()
    else:
        dlg.Destroy()

def open_folder_in_explorer(path):
    """Opens the given folder in the default OS file explorer."""
    if os.name == 'posix':
        try:
            if "darwin" in os.sys.platform:  # macOS
                subprocess.call(['open', path])
            else:  # Linux
                subprocess.call(['xdg-open', path])
        except Exception as e:
            wx.MessageBox(f"Failed to open folder:\n{path}\n\nError: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
    else:  # Windows
        os.startfile(path)
