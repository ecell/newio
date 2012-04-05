"""Code fragments just thrown in attic.
"""
# ATTIC: from app.py, for multidoc
#     def OnWorldListItemClose(self, evt):
#         """Remove UI entry from world list.
#         """
#         item_id_to_delete = evt.GetEventObject().GetParent().GetId()
#         self.browser.world_list.pop_world(item_id_to_delete)
#         self.browser.Refresh()

#     def OnWorldListItemShow(self, evt):
#         """Open new visualizer window.
#         """
#         item_id = evt.GetEventObject().GetParent().GetId()
#         list_item = self.browser.world_list.find_world_list_item(item_id)
#         if list_item:
#             # invoke visualizer
#             """
#             visualizer_window = VisualizerFrame(
#                 self, list_item.world, list_item.visualizer,
#                 self.browser, -1)
#             visualizer_window.Show(True)
#             visualizer_window.render_window.Render()"""
#             import vtk
#             cone = vtk.vtkConeSource()
#             cone.SetResolution(8)

#             coneMapper = vtk.vtkPolyDataMapper()
#             coneMapper.SetInput(cone.GetOutput())

#             coneActor = vtk.vtkActor()
#             coneActor.SetMapper(coneMapper)

#             self.browser.ren.AddActor(coneActor)
#             self.browser.render_window.Render()
    
#     def OnAddDummyEntry(self, evt):
#         """Add dummy world entry to the world list.
#         """
#         self.browser.world_list.add_world('foo', 'bar')
#         self.browser.world_list.add_world('baz', 'qux')

# ATTIC: from browser.py, for multidoc
# 
# class WorldListScrolledPanel(ScrolledPanel):
#     """Scrolled panel in browser window, shows a list of worlds.
#     """
#     LIST_ITEM_MARGIN = 0
    
#     def __init__(self, responder, *args, **kwargs):
#         kwargs['style']  = kwargs.get('style', 0)|wx.SUNKEN_BORDER
#         super(WorldListScrolledPanel, self).__init__(*args, **kwargs)
#         self.responder = responder
#         sizer = wx.BoxSizer(wx.VERTICAL)
#         self.SetSizer(sizer)
#         self.SetAutoLayout(True)
#         self.SetupScrolling()

#     def add_world(self, world, visualizer):
#         """Add world to entries.
#         """
#         world_list_item = WorldListItem(self.responder, world, visualizer, self, -1)
#         self.GetSizer().Add(world_list_item, 0, wx.ALL, self.LIST_ITEM_MARGIN)
#         # redo layout
#         self.GetSizer().Layout()
#         self.GetSizer().Show(self, True, True)
#         self.SetupScrolling()
#         return world_list_item

#     def find_world_list_item(self, id_to_find):
#         """Find world from entries. Returns None if not found.
#         """
#         # find world_list_item
#         found = None
#         for sizeritem in self.GetSizer().GetChildren():
#             wli = sizeritem.GetWindow()
#             if wli.GetId() == id_to_find:
#                 found = wli
#                 break
#         return found

#     def pop_world(self, id_to_delete):
#         """Remove world from entries.
#         """
#         # detach it if found
#         world_list_item = self.find_world_list_item(id_to_delete)
#         if world_list_item:
#             self.GetSizer().Detach(world_list_item)
#             world_list_item.Hide()
#             del world_list_item
#         else:
#             # TODO: log that world is not found.
#             pass
#         # redo layout
#         self.GetSizer().Layout()
#         self.GetSizer().Show(self, True, True)
#         self.SetupScrolling()

# class WorldListItem(wx.Panel):
#     """An item in a world list panel.
#     """
#     def __init__(self, responder, world, visualizer, *args, **kwargs):
#         super(WorldListItem, self).__init__(*args, **kwargs)
#         self.responder = responder
#         self.world = world
#         self.visualizer = visualizer
#         # sizer stuff
#         root_sizer = wx.BoxSizer(wx.VERTICAL)
#         button_sizer = wx.BoxSizer(wx.HORIZONTAL)
#         # widgets
#         file_line = wx.StaticText(self, -1, label=world)
#         visualizer_line = wx.StaticText(self, -1, label=visualizer)
#         close_button = wx.Button(self, -1, label='Close')
#         show_button = wx.Button(self, -1, label='Show')
#         # binding
#         close_button.Bind(wx.EVT_BUTTON, self.responder.OnWorldListItemClose)
#         show_button.Bind(wx.EVT_BUTTON, self.responder.OnWorldListItemShow)
#         # packing
#         root_sizer.Add(file_line, 0, wx.ALL, 5)
#         root_sizer.Add(visualizer_line, 0, wx.ALL, 5)
#         root_sizer.Add(button_sizer, 0, wx.ALL, 5)
#         button_sizer.Add(close_button, 0, wx.LEFT, 5)
#         button_sizer.Add(show_button, 0, wx.LEFT, 5)
#         self.SetSizer(root_sizer)


# import wx, vtk
# from wx.lib.scrolledpanel import ScrolledPanel

# from ec4vis.wxVTKRenderWindowInteractor import wxVTKRenderWindowInteractor # as VRWI


# class VisualizerFrame(wx.Frame):
#     """Visualizer window.
#     """

#     def __init__(self, responder, world, visualizer, *args, **kwargs):
#         """Initializer.
#         """
#         super(VisualizerFrame, self).__init__(*args, **kwargs)
#         self.responder = responder
#         self.world = world
#         self.visualizer = visualizer
#         self.SetSize((600, 600))

#         sizer = wx.BoxSizer(wx.HORIZONTAL)
#         render_window = wxVTKRenderWindowInteractor(self, -1)
#         sizer.Add(render_window, 1, wx.ALL|wx.EXPAND, 0)
#         self.SetSizer(sizer)
#         self.Layout()

#         render_window.Enable(1)
#         ren = vtk.vtkRenderer()
#         render_window.GetRenderWindow().AddRenderer(ren)

#         cone = vtk.vtkConeSource()
#         cone.SetResolution(8)
        
#         coneMapper = vtk.vtkPolyDataMapper()
#         coneMapper.SetInput(cone.GetInput())

#         coneActor = vtk.vtkActor()
#         coneActor.SetMapper(coneMapper)

#         ren.AddActor(coneActor)
#         self.render_window = render_window
        
        
