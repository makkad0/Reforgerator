import wx
import vars.log_var as lv
from src.localisation import get_local_text


def log(log_key, *args):
    """
    Retrieves log message and type from LOG_DATA.
    Args:
        log_key (str): The key to look up in LOG_DATA.
    Returns:
        tuple: (message, msg_type) if Type exists, otherwise (message,)
    """
    log_entry = lv.LOG_DATA.get(log_key, {})  # Get log entry or empty dict

    # Get localized message or empty string if not defined
    local_message = log_entry.get("local_message", "")
    message = get_local_text(local_message) if local_message else log_key

    # Substitute arguments if there are any
    message = message.format(*args) if args else message

    # Get type if available
    msg_type = log_entry.get("Type", None)

    if msg_type:
        return message, msg_type
    else:
        return message
    
class LogOutputStream:
    def __init__(self, stream: None):
        self.gui_mode = False
        self.cli_mode = False
        self.stream = stream
        if hasattr(stream,'log_ctrl'):
            self.gui_mode = bool(self.stream.log_ctrl)
            self.gui_log = stream.log_ctrl
        if hasattr(stream,'is_cli'):
            self.cli_mode = self.stream.is_cli()
            self.cli_log = stream

    def msg(self,log_key, *args):
        if self.gui_mode:
            self.gui_log.log(log_key, *args)
        elif self.cli_mode:
            self.cli_log.log(log_key, *args)

    def update_live_log(self, log_key, message, current, total):
         message_new, msg_type=log(log_key,message)
         if self.gui_mode:
            wx.CallAfter( self.gui_log.live_update_gauge,
                         msg_type=msg_type,
                         message=message_new,
                         current=current,
                         total = total,)
         elif self.cli_mode:
            self.cli_log.live_update_gauge(msg_type, message_new, current, total)

    def clear_pos(self):
        if self.gui_mode:
            wx.CallAfter(self.gui_log.clear_pos)
        elif self.cli_mode:
            self.cli_log.clear_pos()

