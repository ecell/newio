# coding: utf-8
"""hdfview.py --- quick hdf viewer
"""
import os
import wx

from h5py import File, Group, Dataset
from wx.lib import mvctree


class HdfViewFrame(wx.Frame):

    def __init__(self, responder, *args, **kwargs):
        super(HdfViewFrame, self).__init__(*args, **kwargs)
        self.responder = responder
        sizer = wx.BoxSizer(wx.VERTICAL)
        mt= mvctree.MVCTree(self, -1, style=wx.BORDER_SUNKEN)
        self.mt = mt
        sizer.Add(mt, 1, wx.ALL|wx.EXPAND, 0)
        # menu
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        file_open = file_menu.Append(-1, u'開く\tCtrl+o')
        # file_close = file_menu.Append(-1, u'閉じる\tCtrl+w')
        file_quit = file_menu.Append(-1, u'終了\tCtrl+q')
        self.Bind(
            wx.EVT_MENU, self.responder.OnFileOpenMenu,
            id=file_open.GetId())
        # self.Bind(
        # wx.EVT_MENU, self.responder.OnFileCloseMenu,
        # id=file_close.GetId())
        self.Bind(
            wx.EVT_MENU, self.responder.OnFileQuitMenu,
            id=file_quit.GetId())
        menubar.Append(file_menu, u'ファイル')
        self.SetMenuBar(menubar)
        self.SetSizer(sizer)
        self.Fit()


class HdfTreeModel(mvctree.BasicTreeModel):

    def __init__(self, path):
        mvctree.BasicTreeModel.__init__(self)
        root = File(path)
        self.SetRoot(root)
        self._Build(root)

    def _Build(self, node):
        for key, value in node.items():
            child = node[key]
            self.AddChild(node, child)

    def GetChildCount(self, node):
        if isinstance(node, Group):
            return len(node)
        else:
            return 0

    def GetChildAt(self, node, index):
        return node.values()[index]
        
    def IsLeaf(self, node):
        if isinstance(node, Group):
            return len(node)<1
        else:
            return False


class HdfViewApp(wx.App):

    def OnInit(self):
        """
        """
        self.frame = HdfViewFrame(self, None, -1, title='HDF Viewer')
        self.SetTopWindow(self.frame)
        self.frame.SetSize((800, 600))
        self.frame.Show(True)
        self.document = None
        return True

    def OnFileOpenMenu(self, evt):
        dialog = wx.FileDialog(
            self.frame, message=u'HDFファイルを選んでください',
            defaultDir=os.getcwd(),
            defaultFile='',
            wildcard=('HDF5ファイル|*.*'),
            style=wx.OPEN|wx.CHANGE_DIR)
        ret = dialog.ShowModal()
        if ret==wx.ID_OK:
            path = dialog.GetPath()
            self.document = File(path)
            treemodel = HdfTreeModel(path)
            treemodel.root = self.document
            self.frame.mt.SetModel(treemodel)
    
    def OnFileCloseMenu(self, evt):
        pass

    def OnFileQuitMenu(self, evt):
        self.ExitMainLoop()


if __name__=='__main__':
    app = HdfViewApp(0)
    app.MainLoop()
