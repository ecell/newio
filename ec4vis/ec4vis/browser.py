# coding: utf-8
"""browser.py -- Browser window in visualizer application, by Yasushi Masuda (ymasuda@accense.com)
"""
from logging import debug

import vtk
import wx
from wx.lib.scrolledpanel import ScrolledPanel
from ec4vis import *
from ec4vis.wxVTKRenderWindowInteractor import wxVTKRenderWindowInteractor


class ControlPanel(wx.Panel):
    """Browser control panel.
    """
    def __init__(self, responder, *args, **kwargs):
        """Initializer.
        """
        super(ControlPanel, self).__init__(*args, **kwargs)
        self.responder = responder
        self.SetSize((300, 600))
        # set up sizer
        root_sizer = wx.BoxSizer(wx.VERTICAL)
        root_sizer.SetMinSize((300, -1))
        # root_sizer.Add(wx.StaticText(self, -1, label='Data Inspector'), 0, wx.ALL, 10)
        self.SetSizer(root_sizer)
        # file list
        data_list = wx.ListBox(self, -1, size=(-1, 400))
        self.data_list = data_list
        root_sizer.Add(data_list, 1, wx.ALL|wx.EXPAND, 5)
        self.Layout()
        

class BrowserFrame(wx.Frame):
    """Browser window.
    """
    def __init__(self, responder, *args, **kwargs):
        """Initializer.
        """
        super(BrowserFrame, self).__init__(*args, **kwargs)
        self.responder = responder
        self.setup_menubar()
        self.SetSize((800, 600))
        # set up sizer
        root_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(root_sizer)
        # render window
        render_window = wxVTKRenderWindowInteractor(self, -1)
        self.render_window = render_window
        self.setup_renderer()
        root_sizer.Add(render_window, 1, wx.ALL|wx.EXPAND, 0)
        # control panel
        control_panel = ControlPanel(responder, self, -1)
        self.control_panel = control_panel
        root_sizer.Add(control_panel, 0, wx.ALL, 0)
        self.Layout()

    def setup_renderer(self):
        """Set up vtk renderers.
        """
        self.render_window.Enable(1)
        self.render_window.AddObserver(
            'ExitEvent', lambda o,e,f=self: f.Close())
        self.renderer = vtk.vtkRenderer()
        self.render_window.GetRenderWindow().AddRenderer(self.renderer)

    def setup_menubar(self):
        """Set up menubar.
        """
        menu_bar = wx.MenuBar()
        self.menu_bar = menu_bar
        # file menu
        _menu = wx.Menu()
        _mi = _menu.Append(wx.NewId(), '&Open World File...')
        self.Bind(wx.EVT_MENU, self.responder.OnOpenWorldMenu, id=_mi.GetId())
        _mi = _menu.Append(wx.NewId(), '&Quit')
        self.Bind(wx.EVT_MENU, self.responder.OnQuitMenu, id=_mi.GetId())
        menu_bar.Append(_menu, '&File')
        del _mi, _menu
        # visualizer menu
        _menu = wx.Menu()
        _mi = _menu.Append(wx.NewId(), '&Change...')
        self.Bind(wx.EVT_MENU, self.responder.DummyHandler, id=_mi.GetId())
        _mi = _menu.Append(wx.NewId(), '&Info...')
        self.Bind(wx.EVT_MENU, self.responder.DummyHandler, id=_mi.GetId())
        menu_bar.Append(_menu, '&Visualizer')
        del _mi, _menu
        # animate menu
        _menu = wx.Menu()
        _mi = _menu.Append(wx.NewId(), '&Play...')
        self.Bind(wx.EVT_MENU, self.responder.DummyHandler, id=_mi.GetId())
        _mi = _menu.Append(wx.NewId(), '&Generate movie...')
        self.Bind(wx.EVT_MENU, self.responder.DummyHandler, id=_mi.GetId())
        menu_bar.Append(_menu, '&Animate')
        del _mi, _menu
        self.SetMenuBar(menu_bar)

        
