# coding: utf-8
"""app.py -- Visualizer Application implementation by Yasushi Masuda (ymasuda@accense.com)
"""
from logging import debug

import wx

from browser import BrowserFrame
from ecell4.utils import find_hdf5
from ecell4.world import World
from ecell4.particle import ParticleSpace
from ecell4.lattice import LatticeSpace

# this is a hack
class ParticleWorld(World):
    SPACE_REGISTRY = (('ParticleSpace', ParticleSpace),)
class LatticeWorld(World): 
    SPACE_REGISTRY = (('LatticeSpace', LatticeSpace),)

VERSION = (0, 0, 1)
APP_TITLE_NAME = 'E-Cell 4 Visualization Browser Version (%d.%d.%d)' %VERSION

SUPPORTED_WORLDS = dict(
    world=World, particleworld=ParticleWorld, latticeworld=LatticeWorld)


class BrowserApp(wx.App):
    """Application object for browser.
    """

    def OnInit(self):
        """Integrated initialization hook.
        """
        # UI stuff
        browser = BrowserFrame(self, None, -1, APP_TITLE_NAME)
        self.SetTopWindow(browser)
        browser.Show(True)
        self.browser = browser

        # application status
        self.world = None
        self.visualizer = None
        
        return True

    def OnOpenWorldMenu(self, evt):
        """Handler for 'File'->'Open World File' menu.
        """
        dlg = wx.FileDialog(
            self.browser, message='Select world datafiles',
            style=wx.OPEN|wx.MULTIPLE)
        paths = []
        if dlg.ShowModal()==wx.ID_OK:
            paths = dlg.GetPaths()
        dlg.Destroy()
        for path in paths:
            try:
                h5data = find_hdf5(path, new=False)
                format_ = h5data.attrs.get('format', '(nonexistent)')
                WorldClass = SUPPORTED_WORLDS[format_]
                world = WorldClass.Load(path)
                name = world.name
                self.browser.control_panel.data_list.Append(name, world)
            except Exception, e:
                wx.MessageBox(
                    'Failed to load %s: %s' %(path, str(e)),
                    'Oops!', wx.OK)

    def OnQuitMenu(self, evt):
        """Handler for 'File'->'Quit' menu.
        """
        self.ExitMainLoop()

    def DummyHandler(self, evt):
        """Dummy Handler.
        """
        pass
