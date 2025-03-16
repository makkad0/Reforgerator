import wx
import var.sizes as cs
from src.localisation import get_tooltip_text


def update_tooltip(item,text:str="",use_as_code:bool=False,use_for_format:bool=False):
    if hasattr(item,'tooltip_overlay'):
        if not(use_for_format):
            new_text=text
            if use_as_code:
                new_text=get_tooltip_text("new_text")
            item.tooltip_overlay.tooltip_text=new_text
        elif use_for_format:
            item.tooltip_overlay.tooltip_text=item.tooltip_overlay.tooltip_text.format(text)


class CustomTooltip(wx.PopupTransientWindow):
    # Global tooltip settings
    enabled = True
    delay = 750       # time in ms before showing tooltip
    autopop = 60000   # time in ms tooltip remains visible
    reshow = 100       # time in ms before tooltip shows again

    @classmethod
    def Enable(cls, flag):
        cls.enabled = flag

    @classmethod
    def SetDelay(cls, delay_ms):
        cls.delay = delay_ms

    @classmethod
    def SetAutoPop(cls, autopop_ms):
        cls.autopop = autopop_ms

    @classmethod
    def SetReshow(cls, reshow_ms):
        cls.reshow = reshow_ms

    def __init__(
        self,
        parent,
        text,
        max_width=300,                 # Wrap text if it exceeds this width
        use_system_tooltip_colors=False,  
        border_style=wx.BORDER_THEME
    ):
        """
        :param parent:                   The parent window.
        :param text:                     The tooltip text.
        :param max_width:                Maximum width (in px) before wrapping text.
        :param use_system_tooltip_colors: If True, use system 'tooltip' colors (if available).
        :param border_style:             Border style for the popup's panel (e.g. wx.BORDER_THEME).
        """
        super().__init__(parent)
        self.parent = parent
        self.text = text
        self.max_width = max_width

        if use_system_tooltip_colors:
            # On most platforms: SYS_COLOUR_INFOBK = tooltip background, SYS_COLOUR_INFOTEXT = tooltip text
            bg_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK)
            text_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOTEXT)
        else:
            # A typical light-yellow background and dark text
            bg_color = wx.Colour(255, 255, 224)
            text_color = wx.Colour(60, 60, 60)

        # Create a panel with the chosen border style
        panel = wx.Panel(self, style=border_style)
        panel.SetBackgroundColour(bg_color)

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Create the label for the tooltip text
        self.label = wx.StaticText(panel, label=self.text)
        self.label.SetForegroundColour(text_color)

        # Add some padding around the text
        sizer.Add(self.label, 0, wx.ALL, cs.TOOLTIP_BORDER)
        panel.SetSizer(sizer)

        # Wrap the text if it exceeds max_width
        # NOTE: Wrap() must be called after the label is created/added
        self.label.Wrap(self.max_width)

        # Re-fit panel after wrapping
        panel.SetSizerAndFit(sizer)
        self.SetSize(panel.GetSize())

        # Timer to auto-dismiss the tooltip
        self._autopop_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_autopop_timer, self._autopop_timer)

    def ShowAt(self, pos):
        """Positions the tooltip at a given screen coordinate and shows it."""
        if not CustomTooltip.enabled:
            return
        self.Position(pos, (0, 0))
        self.Popup()
        if CustomTooltip.autopop > 0:
            self._autopop_timer.StartOnce(CustomTooltip.autopop)

    def _on_autopop_timer(self, event):
        self.Dismiss()


class HoverOverlay(wx.Window):
    """An invisible overlay that can show tooltips or capture mouse events."""
    def __init__(self, parent, item, type="regular", tooltip_text="", pos=(0,0), size=(1,1)):
        super().__init__(parent, style=wx.NO_BORDER | wx.BG_STYLE_TRANSPARENT | wx.TRANSPARENT_WINDOW)
        self.SetPosition(pos)
        self.SetSize(size)
        self.item = item
        self.type = type
        self.tooltip_text = tooltip_text 
        # Bind mouse events to control tooltip appearance
        if type!="active":
            self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
            self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
            self.Lower()
        else:
            item.Bind(wx.EVT_ENTER_WINDOW, self.on_enter)
            item.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
            self.Raise()
        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        # Timer for handling tooltip delay
        self._delay_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_delay_timer, self._delay_timer)
        self._tooltip = None
        self.Show()

    def on_enter(self, event):
        """Starts a delay timer when the mouse enters the widget."""
        # Use the globally set delay from CustomTooltip.delay
        self._delay_timer.StartOnce(CustomTooltip.delay)
        event.Skip()

    def _on_delay_timer(self, event):
        """Called when the delay expires - positions the tooltip near the element."""
        # Get the widget's screen position.
        screen_pos = self.GetScreenPosition()
        # Compute a position just below the widget.
        widget_size = self.GetSize()
        tooltip_pos = wx.Point(screen_pos.x, screen_pos.y + widget_size.height)
        self._tooltip = CustomTooltip(self,self.tooltip_text)
        self._tooltip.ShowAt(tooltip_pos)

    def on_leave(self, event):
        # Stop the delay timer and dismiss any active tooltip.
        if self._delay_timer.IsRunning():
            self._delay_timer.Stop()
        if self._tooltip:
            self._tooltip.Dismiss()
            self._tooltip = None
        event.Skip()

    def on_click(self, event):
        event.Skip()  # Allows clicks to pass through

    def AcceptsFocusFromKeyboard(self):
        return False

    def place_tooltip_overlay(self):
        # For demonstration, let's approximate the label area:
        if self.type == "section":
            static_box = self.item.GetStaticBox()
            label_text = static_box.GetLabel()
            # Compute text width, height
            dc = wx.ClientDC(static_box)
            tw, th = dc.GetTextExtent(label_text)
            th += cs.TOOLTIP_HOVER_PANEL_ADD_MARGIN_X
            tw += cs.TOOLTIP_HOVER_PANEL_ADD_MARGIN_Y
            # The label in a default theme is typically drawn near the top-left,
            # with some internal border. We'll guess an offset to position overlay:
            label_x_offset = 9
            label_y_offset = 0

            # If you need to refine these offsets, check your platform or style metrics:
            pos = static_box.ClientToScreen((label_x_offset, label_y_offset))
            pos = self.ScreenToClient(pos)  # convert to this panel's coordinates

            # Create the overlay the first time (or move it if it already exists)
            overlay_size = (tw, th)
        else:
            pos = self.item.GetScreenPosition()
            pos = self.ScreenToClient(pos)
            overlay_size = self.item.GetSize()
            #tw= overlay_size.width
            #th= overlay_size.height
            #overlay_size = (tw, th)
        # Update position and size
        self.SetPosition(pos)
        self.SetSize(overlay_size)
        if self.type=="active":
            self.Lower()
        else:
            self.Raise()