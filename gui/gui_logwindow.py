import wx
import wx.richtext as rt
import datetime
import vars.sizes as cs
import src.log as lg


class RichLogPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        self.font_size = cs.LOGWINDOW_TEXT_FONT_SIZE

        # Create sizer for log panel
        log_sizer = wx.BoxSizer(wx.VERTICAL)

        # RichTextCtrl for logging with monospace font
        self.log_ctrl = rt.RichTextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.VSCROLL, size=(-1,cs.LOGWINDOW_VERTICAL_SIZE))
        self.SetFontSize(self.font_size)
        log_sizer.Add(self.log_ctrl, 1, wx.EXPAND | wx.ALL, 5)

        # Store last status message for updates
        self.clear_pos()

        self.SetSizer(log_sizer)

    def AcceptsFocusFromKeyboard(self):
        return False

    def clear_pos(self):
        # Store last status message for updates
        self.live_pos_start = None
        self.live_pos_end = None

    def SetFontSize(self, size):
        """Set the log control's font to a monospace font with the specified size."""
        self.font_size = size
        font = wx.Font(self.font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.log_ctrl.SetFont(font)

    def WriteTextUpdate(self,message):
        start = self.log_ctrl.GetInsertionPoint()
        if start!=0:
            message=f"\n{message}"
        self.log_ctrl.WriteText(message)

    def apply_formatting_type(self,msg_type=""):
    # Apply formatting based on message type
        if msg_type == "INFO":
            self.log_ctrl.BeginTextColour(wx.Colour(0, 128, 255))  # Blue
        elif msg_type == "WARNING":
            self.log_ctrl.BeginTextColour(wx.Colour(255, 165, 0))  # Orange
            #self.log_ctrl.BeginBold()
        elif msg_type == "ERROR":
            self.log_ctrl.BeginTextColour(wx.Colour(255, 0, 0))  # Red
            #self.log_ctrl.BeginBold()
            #self.log_ctrl.BeginUnderline()
        elif msg_type == "SUCCESS":
            self.log_ctrl.BeginTextColour(wx.Colour(0, 180, 0))  # Green
            #self.log_ctrl.BeginBold()
        elif msg_type == "ABORT":
            self.log_ctrl.BeginTextColour(wx.Colour(139, 0, 0))  # Dark Red
            #self.log_ctrl.BeginBold()
        elif msg_type == "PROCESSING":
            self.log_ctrl.BeginTextColour(wx.Colour(75, 0, 130))  # Indigo
            #self.log_ctrl.BeginBold()
        elif msg_type == "UPDATE":
            self.log_ctrl.BeginTextColour(wx.Colour(0, 128, 128))  # Teal
            #self.log_ctrl.BeginBold()
        elif msg_type == "DEBUG":
            self.log_ctrl.BeginTextColour(wx.Colour(128, 128, 128))  # Gray
        elif msg_type == "NOTICE":
            self.log_ctrl.BeginTextColour(wx.Colour(138, 43, 226))  # BlueViolet
            #self.log_ctrl.BeginBold()
        elif msg_type == "INPUT":
            self.log_ctrl.BeginTextColour(wx.Colour(0, 0, 0))  # Black
        else:
            self.log_ctrl.BeginTextColour(wx.Colour(0, 0, 0))  # Black

    def end_formatting_type(self):
        #self.SetFontSize(self.font_size)
        # Reset text attributes
        self.log_ctrl.EndTextColour()
        #self.log_ctrl.EndBold()
        #self.log_ctrl.EndUnderline()
        

    def log_message(self, message="Unknown message", msg_type=""):
        """Logs a standard message with formatting based on msg_type."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        msg_type_text=f" [{msg_type}]" if msg_type else ""
        full_message = f"[{timestamp}]{msg_type_text} {message}"

        self.log_ctrl.SetInsertionPointEnd()  
        lastpoint = self.log_ctrl.GetInsertionPoint()

        self.apply_formatting_type(msg_type)

        # Write the message
        self.WriteTextUpdate(full_message)

        self.end_formatting_type()

        # Scroll to the end using the current insertion point.
        self.log_ctrl.ShowPosition(lastpoint+1)

    def log(self,log_key,*args):
        result = lg.log(log_key,*args)
        if isinstance(result, tuple):
        # If result is a tuple, expand it into message and msg_type
            return self.log_message(*result)
        else:
        # If result is just a string, pass it as the message
            return self.log_message(result)

    def clear_log(self, event=None):
        """Clears the log."""
        self.log_ctrl.Clear()

    def trim_to_width(self, text):
        """
        Trims the given text from the end (adding ellipsis) so that its width does not exceed the client width.
        Assumes the control uses a monospace font.
        """
        # Create a ClientDC for the log control.
        dc = wx.ClientDC(self.log_ctrl)
        dc.SetFont(self.log_ctrl.GetFont())
        available_width = self.log_ctrl.GetClientSize().width

        # If the text fits, return it unchanged.
        text_width, _ = dc.GetTextExtent(text)
        if text_width <= available_width:
            return text

        # Otherwise, trim characters from the end until the text (with ellipsis) fits.
        ellipsis = "..."
        while text and dc.GetTextExtent(text + ellipsis)[0] > available_width:
            text = text[:-1]
        return text + ellipsis

    def live_update_gauge(self, msg_type, message, current, total):
        """
        Updates the last log line (live status) with a message and a gauge.
        This method calculates a gauge string (constant width) and overwrites
        the last line in the log with the updated status.
        """
        # Generate the gauge string using a monospace block gauge.
        gauge = self.generate_gauge(current, total)

        # Compose the live update text (without trailing newline)
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        live_text = f"[{timestamp}] {gauge} ({current}/{total}) {message}"
        #live_text =self.trim_to_width(live_text)

        # Set insertion point to start
        if self.live_pos_start is not None:
            start = self.live_pos_start
            end = self.live_pos_end
            self.log_ctrl.Remove(start,end)
            self.log_ctrl.SetInsertionPoint(start)
        else:
            self.log_ctrl.SetInsertionPointEnd()
            start = self.log_ctrl.GetInsertionPoint()

        self.apply_formatting_type(msg_type)
        # Write the live update text (without newline)
        self.WriteTextUpdate(live_text)
        
        self.live_pos_start = start
        self.log_ctrl.SetInsertionPointEnd()
        self.live_pos_end = self.log_ctrl.GetInsertionPoint()
        self.end_formatting_type()
        # Scroll so that the live line is visible.
        self.log_ctrl.ShowPosition(start+1)

    def generate_gauge(self, current, total, bar_length=8):
        """
        Generates a fixed-width pseudographic gauge using monospaced characters.
        Uses full block (█) for filled portions and light shade (░) for empty portions.
        """
        filled_char = chr(9608)  # █
        empty_char = chr(9617)   # ░
        filled = int((current / total) * bar_length)
        gauge = "|" + filled_char * filled + empty_char * (bar_length - filled) + "|"
        return gauge