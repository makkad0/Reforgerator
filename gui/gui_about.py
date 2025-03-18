import wx
from wx.adv import HyperlinkCtrl 
import os
import var.global_var as gv
import var.sizes as cs
from src.localisation import get_local_text
from src.system import get_data_subdir

class AboutDialog(wx.Dialog):
    def __init__(self, parent, id=wx.ID_ANY, title=None):
        if title is None:
            title = get_local_text('credit_dialog_title')
        super(AboutDialog, self).__init__(
            parent, id, title, style=wx.DEFAULT_DIALOG_STYLE
        )
        self.SetBackgroundColour("#FFFFFF")  # Bright white background

        # Determine if wx.adv is available for hyperlinks
        has_adv = True
        
        # Load credits data from credits.txt
        credits_data = {}
        credits_file = os.path.join(get_data_subdir("credits"), "credits.txt")
        if os.path.isfile(credits_file):
            with open(credits_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        key, value = line.split("=", 1)
                        credits_data[key.strip()] = value.strip()

        # Process credit entries (split values by semicolon and remove empties)
        contributors = [x.strip() for x in credits_data.get("credit_contributors", "").split(";") if x.strip()]
        thanks       = [x.strip() for x in credits_data.get("credit_thanks_to", "").split(";") if x.strip()]
        community_links    = [x.strip() for x in credits_data.get("credit_community_links", "").split(";") if x.strip()]
        community_texts    = [x.strip() for x in credits_data.get("credit_community", "").split(";") if x.strip()]
        support      = [x.strip() for x in credits_data.get("credit_donat", "").split(";") if x.strip()]

        # Main vertical sizer with minimal margins
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # --- Header Section: Logo & Basic Info ---
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        logo_path = os.path.join(get_data_subdir("credits"), "logo.png")
        if os.path.isfile(logo_path):
            img = wx.Image(logo_path, wx.BITMAP_TYPE_ANY)
            img = img.Scale(128, 128, wx.IMAGE_QUALITY_HIGH)
            logo = wx.Bitmap(img)
            logo_ctrl = wx.StaticBitmap(self, wx.ID_ANY, logo)
        else:
            logo_ctrl = wx.StaticText(self, wx.ID_ANY, get_local_text('credit_logo_not_found'))
            logo_ctrl.SetForegroundColour(wx.Colour(255, 0, 0))
        header_sizer.Add(logo_ctrl, 0, wx.ALL, 5)

        # Program Info (Name, Version, Author)
        info_sizer = wx.BoxSizer(wx.VERTICAL)
        prog_name = wx.StaticText(self, wx.ID_ANY, gv.PROGRAM_NAME)
        font_title = wx.Font(16, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        prog_name.SetFont(font_title)
        prog_name.SetForegroundColour(wx.Colour(0, 102, 204))
        info_sizer.Add(prog_name, 0, wx.BOTTOM, 2)
        font_info = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        version = wx.StaticText(self, wx.ID_ANY, f"{get_local_text('credit_version')} {gv.PROGRAM_VERSION}")
        version.SetFont(font_info)
        author = wx.StaticText(self, wx.ID_ANY, f"{get_local_text('credit_author')} {gv.PROGRAM_AUTHOR}")
        author.SetFont(font_info)
        info_sizer.Add(version, 0, wx.BOTTOM, 1)
        info_sizer.Add(author, 0, wx.BOTTOM, 1)
        # Do not let info_sizer expand horizontally beyond its natural width
        header_sizer.Add(info_sizer, 0, wx.ALL, 5)
        main_sizer.Add(header_sizer, 0, wx.EXPAND)

        # --- Separator ---
        main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 3)

        # --- Details Section (Compact Layout) ---
        details_sizer = wx.BoxSizer(wx.VERTICAL)
        font_subtitle = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

        # Contributors Section
        contrib_title = wx.StaticText(self, wx.ID_ANY, f"{get_local_text('credit_contributors')}")
        contrib_title.SetFont(font_subtitle)
        details_sizer.Add(contrib_title, 0, wx.LEFT | wx.TOP, 5)
        # Join entries with a bullet symbol
        contrib_str = " \u2022 ".join(contributors)
        contrib_ctrl = wx.StaticText(self, wx.ID_ANY, contrib_str)
        contrib_ctrl.SetFont(font_info)
        details_sizer.Add(contrib_ctrl, 0, wx.LEFT, 10)

        # Thanks Section
        thanks_title = wx.StaticText(self, wx.ID_ANY, f"{get_local_text('credit_thanks_to')}")
        thanks_title.SetFont(font_subtitle)
        details_sizer.Add(thanks_title, 0, wx.LEFT | wx.TOP, 5)
        thanks_str = " \u2022 ".join(thanks)
        thanks_ctrl = wx.StaticText(self, wx.ID_ANY, thanks_str, style=wx.ST_NO_AUTORESIZE)
        thanks_ctrl.SetFont(font_info)
        thanks_ctrl.Wrap(cs.AW_MAX_THANKS_WIDTH)  # Adjust 320 to your layout's constraints
        details_sizer.Add(thanks_ctrl, 0, wx.LEFT, 10)

        # Community Section
        community_text=get_local_text('credit_community_support')
        community_text=community_text.format('&&')
        community_title = wx.StaticText(self, wx.ID_ANY,community_text )
        community_title.SetFont(font_subtitle)
        details_sizer.Add(community_title, 0, wx.LEFT | wx.TOP, 5)
        count=0
        count_max=len(community_texts)
        # Create a horizontal sizer for the links
        community_sizer = wx.BoxSizer(wx.HORIZONTAL)
        if community_texts:
            for url in community_links:
                if count<count_max:
                    if has_adv:
                        comm_link = HyperlinkCtrl(self, wx.ID_ANY, community_texts[count], url)
                    else:
                        comm_link = wx.StaticText(self, wx.ID_ANY, f"{community_texts[count]}: {url}")
                    comm_link.SetFont(font_info)
                    community_sizer.Add(comm_link, 0, wx.LEFT, 5)
                    # Add separator " • " if there are more links coming
                    if count < count_max - 1:
                        separator = wx.StaticText(self, wx.ID_ANY, " \u2022 ")
                        separator.SetFont(font_info)
                        community_sizer.Add(separator, 0, wx.LEFT | wx.RIGHT, 5)

                    count += 1

        # Add the horizontal sizer to the main details sizer
        details_sizer.Add(community_sizer, 0, wx.LEFT, 10)

        # Support (donat) Section – each entry on its own row
        if support:
            support_title = wx.StaticText(self, wx.ID_ANY, f"{get_local_text('credit_donat')}")
            support_title.SetFont(font_subtitle)
            details_sizer.Add(support_title, 0, wx.LEFT | wx.TOP, 5)
            for url in support:
                if not url.startswith("http"):
                    url = "https://" + url
                if has_adv:
                    link = HyperlinkCtrl(self, wx.ID_ANY, url, url)
                else:
                    link = wx.StaticText(self, wx.ID_ANY, url)
                link.SetFont(font_info)
                details_sizer.Add(link, 0, wx.LEFT, 10)

        main_sizer.Add(details_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # --- Button Section ---
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        close_btn = wx.Button(self, wx.ID_OK, "OK")
        close_btn.SetDefault()
        btn_sizer.Add(close_btn, 0, wx.ALL, 5)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER)

        self.SetSizer(main_sizer)
        main_sizer.Fit(self)