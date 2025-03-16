import os
import wx
import var.global_var as gv
from src.generator import set_output_folder
from src.localisation import get_local_text

def gui_browse_output(self):
    """Opens self.output_path in the OS file explorer.
    If the folder does not exist, it prompts the user for creation.
    If creation fails, an error message is displayed.
    """
    folder_path=""
    output_suboption_dict = self.current_selection.recieve_suboptions([gv.OPTIONS_OUTPUT_PATH])
    try:
        folder_path = set_output_folder(output_suboption_dict,False)
        # Check if the folder exists
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            # Open the folder in the OS file explorer
            open_folder_in_explorer(folder_path)
            return
    except Exception as e:
        self.log_ctrl.log("browse_output_error",folder_path)
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
