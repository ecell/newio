# coding: utf-8
"""browser.py -- Browser window in visualizer application
"""
from logging import debug

import wx
from ec4vis import *

from render_window import RenderWindowPanel
from control_panel import ControlPanel
from menu_bar import AppMenuBar
        

class BrowserFrame(wx.Frame):
    """Browser window.
    """
    def __init__(self, *args, **kwargs):
        """Initializer.
        """
        wx.Frame.__init__(self, *args, **kwargs)
        # render window
        render_window_panel = RenderWindowPanel(self, -1)
        # control panel
        control_panel = ControlPanel(self, -1)
        # menu
        menu_bar = AppMenuBar(self)
        # bindings
        self.render_window_panel = render_window_panel
        self.control_panel = control_panel
        self.menu_bar = menu_bar
        # sizer
        root_sizer = wx.BoxSizer(wx.HORIZONTAL)
        root_sizer.Add(render_window_panel, 1, wx.ALL|wx.EXPAND, 0)
        root_sizer.Add(control_panel, 0, wx.ALL|wx.EXPAND, 0)
        self.SetSizer(root_sizer)
        self.Layout()


if __name__=='__main__':
    class App(wx.App):
        """Demonstrative application.
        """
        def OnInit(self):
            """Initializer.
            """
            frame = BrowserFrame(None, -1, u'Browser Frame Demo')
            frame.Show(True)
            self.SetTopWindow(frame)
            return True
    app = App(0)
    app.MainLoop()
