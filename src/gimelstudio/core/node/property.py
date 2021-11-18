# ----------------------------------------------------------------------------
# Gimel Studio Copyright 2019-2021 by Noah Rahm and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ----------------------------------------------------------------------------

import os
import sys
import glob

import wx

from gswidgetkit import (NumberField, EVT_NUMBERFIELD,
                         Button, EVT_BUTTON, TextCtrl,
                         DropDown, EVT_DROPDOWN)
from gimelstudio.constants import PROP_BG_COLOR, SUPPORTED_FT_OPEN_LIST
from gimelstudio.datafiles import ICON_ARROW_DOWN, ICON_ARROW_RIGHT


# Enum-like constants for widgets
SLIDER_WIDGET = "slider"
SPINBOX_WIDGET = "spinbox"


class Property(object):
    """
    The base node Property class.
    """
    def __init__(self, idname, default, label, visible=True):
        self.idname = idname
        self.value = default
        self.label = label
        self.visible = visible
        self.widget_eventhook = None

    def _RunErrorCheck(self):
        """ 
        Add optional error checking to your Property by overriding this method. 
        """
        pass

    @property
    def IdName(self):
        return self.idname

    def GetIdname(self):
        return self.idname

    def GetValue(self):
        return self.value

    def SetValue(self, value, render=True):
        """ Set the value of the node property.

        NOTE: This is only to be used to AFTER the node init.
        Use ``self.EditProperty`` for other cases, instead.
        """
        self.value = value
        self._RunErrorCheck()
        self.WidgetEventHook(self.idname, self.value, render)

    def GetLabel(self):
        return self.label

    def SetLabel(self, label):
        self.label = label

    def GetIsVisible(self):
        return self.visible

    def SetIsVisible(self, is_visible):
        self.visible = is_visible

    def SetWidgetEventHook(self, event_hook):
        self.widget_eventhook = event_hook

    def WidgetEventHook(self, idname, value, render):
        self.widget_eventhook(idname, value, render)

    def CreateFoldPanel(self, panel_bar, label=None):
        images = wx.ImageList(24, 24)
        images.Add(ICON_ARROW_DOWN.GetBitmap())
        images.Add(ICON_ARROW_RIGHT.GetBitmap())

        if label is None:
            lbl = self.GetLabel()
        else:
            lbl = label
        return panel_bar.AddFoldPanel(lbl, foldIcons=images)

    def AddToFoldPanel(self, panel_bar, fold_panel, item, spacing=15):
        # From https://discuss.wxpython.org/t/how-do-you-get-the-
        # captionbar-from-a-foldpanelbar/24795
        fold_panel._captionBar.SetSize(fold_panel._captionBar.DoGetBestSize())
        panel_bar.AddFoldPanelWindow(fold_panel, item, spacing=spacing)

        # Add this here just for 12px of spacing at the bottom
        item = wx.StaticText(fold_panel, size=(-1, 12))
        panel_bar.AddFoldPanelWindow(fold_panel, item, spacing=0)


class ThumbProp(Property):
    """ 
    Shows the current thumbnail image (used internally). 
    """
    def __init__(self, idname, default=None, label="", thumb_img=None, visible=True):
        Property.__init__(self, idname, default, label, visible)
        self.thumb_img = thumb_img

    def GetThumbImage(self):
        return self.thumb_img

    def CreateUI(self, parent, sizer):
        fold_panel = self.CreateFoldPanel(sizer)
        fold_panel.SetBackgroundColour(wx.Colour(PROP_BG_COLOR))
        fold_panel.Collapse()

        self.img = wx.StaticBitmap(fold_panel, bitmap=self.GetThumbImage(), size=(200, 200))

        self.AddToFoldPanel(sizer, fold_panel, self.img)


class PositiveIntegerProp(Property):
    """ 
    Allows the user to select a positive integer via a Number Field. 
    """
    def __init__(self, idname, default=0, lbl_suffix="", min_val=0,
                 max_val=10, widget=SLIDER_WIDGET, label="", visible=True):
        Property.__init__(self, idname, default, label, visible)
        self.min_value = min_val
        self.max_value = max_val
        self.widget = widget
        self.lbl_suffix = lbl_suffix

        self._RunErrorCheck()

    def _RunErrorCheck(self):
        if self.value > self.max_value:
            raise TypeError(
                "PositiveIntegerField value must be set to an integer less than 'max_val'"
            )
        if self.value < self.min_value:
            raise TypeError(
                "PositiveIntegerField value must be set to an integer greater than 'min_val'"
            )

    def GetMinValue(self):
        return self.min_value

    def GetMaxValue(self):
        return self.max_value

    def CreateUI(self, parent, sizer):
        fold_panel = self.CreateFoldPanel(sizer)
        fold_panel.SetBackgroundColour(wx.Colour(PROP_BG_COLOR))

        self.numberfield = NumberField(fold_panel,
                                       default_value=self.GetValue(),
                                       label=self.GetLabel(),
                                       min_value=self.GetMinValue(),
                                       max_value=self.GetMaxValue(),
                                       suffix=self.lbl_suffix, show_p=False,
                                       size=(-1, 32))

        self.AddToFoldPanel(sizer, fold_panel, self.numberfield)

        self.numberfield.Bind(EVT_NUMBERFIELD, self.WidgetEvent)

    def WidgetEvent(self, event):
        self.SetValue(event.value)


class ChoiceProp(Property):
    """ 
    Allows the user to select from a list of choices via a Drop-down widget. 
    """
    def __init__(self, idname, default="", choices=[], label="", visible=True):
        Property.__init__(self, idname, default, label, visible)
        self.choices = choices

    def GetChoices(self):
        return self.choices

    def SetChoices(self, choices=[]):
        self.choices = choices

    def CreateUI(self, parent, sizer):
        fold_panel = self.CreateFoldPanel(sizer)
        fold_panel.SetBackgroundColour(wx.Colour(PROP_BG_COLOR))

        self.dropdown = DropDown(fold_panel, default=self.GetValue(),
                                 items=self.GetChoices(), size=(-1, 32))

        self.AddToFoldPanel(sizer, fold_panel, self.dropdown)
        self.dropdown.Bind(EVT_DROPDOWN, self.WidgetEvent)

    def WidgetEvent(self, event):
        value = event.value
        if not value:
            print("Value is null!")
        self.SetValue(value)


class OpenFileChooserProp(Property):
    """ Allows the user to select a file to open.

    (e.g: use this to open an .PNG, .JPG, .JPEG image, etc.)
    """
    def __init__(self, idname, default="", dlg_msg="Choose file...",
                 wildcard="All files (*.*)|*.*", btn_lbl="Choose...",
                 label="", visible=True):
        Property.__init__(self, idname, default, label, visible)
        self.dlg_msg = dlg_msg
        self.wildcard = wildcard
        self.btn_lbl = btn_lbl

        self._RunErrorCheck()

    def _RunErrorCheck(self):
        if type(self.value) != str:
            raise TypeError("Value must be a string!")

    def GetDlgMessage(self):
        return self.dlg_msg

    def GetWildcard(self):
        return self.wildcard

    def GetBtnLabel(self):
        return self.btn_lbl

    def CreateUI(self, parent, sizer):
        fold_panel = self.CreateFoldPanel(sizer)
        fold_panel.SetBackgroundColour(wx.Colour(PROP_BG_COLOR))

        pnl = wx.Panel(fold_panel)
        pnl.SetBackgroundColour(wx.Colour(PROP_BG_COLOR))

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.textcontrol = TextCtrl(pnl, default=self.GetValue(), size=(-1, 32))
        hbox.Add(self.textcontrol, proportion=1, flag=wx.EXPAND | wx.BOTH)

        self.button = Button(pnl, label=self.GetBtnLabel(), size=(-1, 32))
        hbox.Add(self.button, flag=wx.LEFT, border=5)
        self.button.Bind(EVT_BUTTON, self.WidgetEvent)

        vbox.Add(hbox, flag=wx.EXPAND | wx.BOTH)

        vbox.Fit(pnl)
        pnl.SetSizer(vbox)

        self.AddToFoldPanel(sizer, fold_panel, pnl)

    def WidgetEvent(self, event):
        style = wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW
        dlg = wx.FileDialog(None, message=self.GetDlgMessage(), defaultDir=os.getcwd(),
                            defaultFile="", wildcard=self.GetWildcard(), style=style)

        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
            filetype = os.path.splitext(paths[0])[1]

            if filetype not in SUPPORTED_FT_OPEN_LIST:
                dlg = wx.MessageDialog(None, _("That file type isn't currently supported!"),
                                       _("Cannot Open Image!"), style=wx.ICON_EXCLAMATION)
                dlg.ShowModal()

            else:
                self.SetValue(paths[0])
                self.textcontrol.SetValue(self.GetValue())
