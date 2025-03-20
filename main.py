import wx
import os
import sys
from gui.gui_logic import IconConverterGUI
from src.cli import parse_arguments
from src.cli import cli_mode
import vars.global_var as gv

class MyApp(wx.App):

    def OnInit(self):
        # Create and show the main frame
        self.frame = IconConverterGUI(None, gv.PROGRAM_FULLNAME)
        self.frame.Show()
        return True

    def restart(self):
        """
        Restart the current program using os.execl,
        which replaces the current process with a new one.
        """
        # The warning comes from PyInstaller’s bootloader for one‐file executables.
        # When your app is restarted (via os.execl), the bootloader creates a temporary “_MEI…” folder to unpack its files. 
        # Normally that folder is removed when the process ends,
        # but in some cases—especially on Windows with splash screens or when DLLs remain in use—the folder isn’t deleted, 
        # and you see a warning. This is a known issue in some PyInstaller versions. 
        # Updating to a version that has addressed the problem (for example, v5.3 or later) 
        # or setting the environment variable PYINSTALLER_RESET_ENVIRONMENT to "1" before restarting can help. 
        # If the warning doesn’t affect your application’s functionality, it can also be safely ignored
        os.environ["PYINSTALLER_RESET_ENVIRONMENT"] = "1" 
        python = sys.executable
        os.execl(python, *sys.argv)
        
def main():
    args = parse_arguments()
    if args.cli:
        run_cli_mode(args)
    else:
        run_gui_mode()

def run_cli_mode(args):
    cli_mode(args)

def run_gui_mode(): 
    app = MyApp(False)
    app.MainLoop()

if __name__ == "__main__":
    main()