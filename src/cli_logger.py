import sys
import datetime
from src.log import log as main_log

class TerminalLogger:
    """
    A logger for CLI mode. Mimics the GUI log by writing formatted messages
    to the terminal and updating a live gauge line.
    """
    def __init__(self):
        self.last_length = 0  # Store previous message length
        self.milestone_prc = 100*1/8
        self.last_reported_progress = 0 # Track last reported 12.5% = 1/8 milestone

        isatty = False
        if hasattr(sys,"stdout"): 
            if hasattr(sys.stdout,"isatty"):
                isatty = sys.stdout.isatty()
        self.isatty = isatty

    def log_message(self, message="Unknown message", msg_type=""):
        # Get timestamp
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        msg_type_text = f" [{msg_type}]" if msg_type else ""
        full_message = f"[{timestamp}]{msg_type_text} {message}"
        # Print message on a new line
        print(full_message)

    def log(self, log_key, *args):
        result = main_log(log_key, *args)
        if isinstance(result, tuple):
            self.log_message(*result)
        else:
            self.log_message(result)

    def live_update_gauge(self, msg_type, message, current, total):
        """
        Updates the live gauge line in the terminal.
        Uses carriage return to overwrite the previous line.
        """
        gauge = self.generate_gauge(current, total)
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        live_text = f"[{timestamp}] {gauge} ({current}/{total}) {message}"
        # Write the live text with carriage return so it updates in-place.
        # Clear only up to the last printed message length
        if self.isatty:
            sys.stdout.write("\r" + " " * self.last_length) 
            sys.stdout.write("\r" + live_text)
            sys.stdout.flush()
        else:
            progress_percent = (current / total) * 100 if total else 0
            milestone = progress_percent - self.last_reported_progress >= self.milestone_prc
            if (
                current == 1 or
                msg_type == "ABORT" or msg_type == "SUCCESS" or
                (current!=total and milestone)
            ):
                print(live_text)
                if milestone:
                    self.last_reported_progress = progress_percent  # Update last reported progress
        # Store new message length
        self.last_length = len(live_text)

    def generate_gauge(self, current, total, bar_length=8):
        """
        Generates a fixed-width pseudographic gauge using monospace characters.
        Uses full block (█) for filled portions and light shade (░) for empty portions.
        """
        if self.isatty:
            filled_char =  chr(9608)  # █
            empty_char = chr(9617)    # ░
        else:
            filled_char = "#"
            empty_char  =  "_" 
        filled = int((current / total) * bar_length)
        gauge = "|" + filled_char * filled + empty_char * (bar_length - filled) + "|"
        return gauge

    def clear_pos(self):
        # In terminal, we can clear the current live gauge by printing a newline.
        if self.isatty:
            print("")

    def is_cli(self):
        return True