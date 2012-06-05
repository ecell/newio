# coding: utf-8
from collections import OrderedDict

import wx

# exception
class VisualizerError(Exception):
    """Exception class for visualizer
    """
    pass


# Visualizer registry
VISUALIZER_CLASSES = {}
def register(visualizer_class, name=None):
    """Registers a visualizer class into VISUALIZER_CLASSES registry.
    """
    # if no name is given, use name of the class.
    if name is None:
        name = visualizer_class.__name__
    VISUALIZER_CLASSES[name] = visualizer_class


class VisualizerEventResponder(object):
    """Null responder implemnentation.
    """
    def get_ui_root(self):
        """Returns root window for visualizer configuration UI.
        """
        return wx.GetApp().GetTopWindow()

    def process_source_done(self, sender, source, error=None):
        """Hook called on process_source() finished.
        """
        pass

    def process_sources_start(self, sender, sources):
        """Hook called on process_sources() begins. Note sources plural.
        """
        pass

    def process_sources_done(self, sender, sources):
        """Hook called on process_sources() finished. Note sources plural.
        """
        pass

        
class Visualizer(object):
    """
    Base class for visualizers.

    Lifecycle:
    v = Visualizer()               # instantiate
    v.configure()                  # update configuration
    v.initialize()                 # subclass-specific initialization
    for bit in bits:
      data_id = v.register_data(bits)  # register data frame
    for data_id in data_ids:
      v.select_data(data_id)       # select data to render
      # some Render() action.
    v.finalize()                   # finalize.
      
    """
    CONFIGURATION_UI_CLASS = None # Set this if your subclass supports configuration UI.
    
    def __init__(self, responder, renderer, *args, **kwargs):
        """
        Initializer.

        Arguments:
        responder --- Action responder.
        renderer --- VTK renderer.
        
        Attributes:
        responder --- Action responder. Usually an wxApp instance.
        renderer --- VTK renderer.
        visuals --- Dictionary of name => (visual, enabled)
        data_registry --- (Ordered) dictionary of data_id => validated_data
        current_data_id --- Currently selected data's id
        
        """
        if responder is None: # fallback to Null implementation.
            responder = VisualizerEventResponder()
        self.responder = responder
        self.renderer = renderer
        self.visuals = OrderedDict()
        self.data_objects = []
        self.current_data_id = None
        self.configuration_ui = None

    # lifecycle methods
    def initialize(self):
        """
        Visualizer-specific initializer.

        This method is called from application just *before* a visualizer
        is being attached to an application. Any configuration or
        preparation can be done in this method.
        
        """
        # In subclasses, you should update visuals first, then call
        # Visualizer.initialize() to make show(True) called for all visuals.
        self.show(True)

    def reset(self):
        """Reset visualizer. Subclass should override.
        """
        self.initialize()

    def finalize(self):
        """
        Visualizer-specific finalizer.

        This method is called from application just *after* a visualizer
        has been detached from an application. Saving changes,
        releasing resources or any other finalization process can be
        done in this method.

        """
        for visual in self.visuals.values():
            if visual.enabled:
                visual.disable()
        # force clearing all props
        self.renderer.RemoveAllViewProps()
                

    def show(self, status=True):
        """Show/hide all visuals.
        """
        for visual in self.visuals.values():
            visual.show(status)

    def update_visuals(self):
        """Update visuals to current state. Subclass may override.
        """
        current_data = None
        if self.current_data_id:
            # search for info having exact data_id
            for info in self.data_objects:
                if info[0]==self.current_data_id:
                    # assuming last item of the info points data
                    current_data = info[-1]
        for visual in self.visuals.values():
            visual.update(current_data)

    def update(self, data_id=None):
        """Update internal status of the visualizer.
        """
        self.current_data_id = data_id
        self.update_visuals()

    # source handling methods
    def process_source(self, source):
        """
        Process individual source to update data registry.

        You may want to update self.data_objects with generated data.
        Note that each item of data_objects should be a *list* of
        [id, Type, Name, data_object].
        
        """
        pass
    
    def process_sources(self, sources):
        """Process souce to update data registry.
        """
        self.data_objects = []
        self.responder.process_sources_start(self, sources)
        for source in sources:
            error = None
            try:
                self.process_source(source)
            except Exception, e:
                error = e
                pass
            self.responder.process_source_done(self, source, error)
        self.responder.process_sources_done(self, sources)
        # reset current data cursor
        if len(self.data_objects):
            self.current_data_index = 0
        else:
            self.current_data_index = None

    # Configuration-UI-related methods
    @property
    def has_configuration_ui(self):
        """Returns True if visualizer has configuration ui.
        """
        return bool(getattr(self, 'CONFIGURATION_UI_CLASS'))

    def load_configuration_ui(self):
        """Loads configuration ui.
        """
        if self.has_configuration_ui==False:
            return
        ui_root = None
        if self.configuration_ui is None:
            self.ui_root = self.responder.get_ui_root()
        configuration_ui = self.CONFIGURATION_UI_CLASS(self, ui_root)
        configuration_ui.Show(True)
        self.configuration_ui = configuration_ui

    def configure(self, configuration):
        """Configure visualizer.
        """
        pass

    # misc
    def move_data_ordering(self, data_id, offset):
        """Move data in data-object list.
        """
        data_objects = self.data_objects
        for index, record in enumerate(data_objects):
            if data_id==record[0]:
                if 0<=index+offset<len(data_objects):
                    index_from = min(index, index+offset)
                    index_to = max(index, index+offset)+1
                    data_objects[index_from:index_to] = data_objects[index_from:index_to][::-1]
                    break
                

# XXX These interfaces are prepared for future development.
#
#
#     def clear_data(self):
#         """Clears all data registered so far.
#         """
#         self.current_data = None
#         self.data_registry.clear()
#         self.update_visuals()

#     def validate_data(self, data):
#         """Validate data and return validated result. Otherwise raise exception.
#         """
#         return data

#     def unregister_data(self, data_id):
#         """Unregister data and return.
#         """
#         if (self.current_data and
#             self.data_registry.get(data_id, None)==self.current_data):
#             self.current_data = None
#             self.update_visuals()
#         return self.data_registry.pop(data_id, None)

#     def register_data(self, data_id, data):
#         """Register data to internal registry. May raise exception in error.
#         """
#         self.data_registry[data_id] = self.validate_data(data)
#         self.update_visuals()

#     def select_data(self, data_id):
#         """Select data frame to reflect current visual state.
#         """
#         self.current_data = self.data_registry.get(data_id, None)
#         self.update_visuals()


class VisualizerConfigurationUi(wx.Frame):
    """Base class for configuration panel.
    """
    def __init__(self, visualizer, *args, **kwargs):
        """Initializer.
        """
        self.visualizer = visualizer
        wx.Frame.__init__(self, *args, **kwargs)


if __name__=='__main__':
    """Demonstrative app.
    """
    import vtk
    from render_window import RenderWindowPanel
    from visual import StaticActorsVisual

    class DemoVisual(StaticActorsVisual):
        def _create_actors(self):
            """Creates demo cone actors.
            """
            cone = vtk.vtkConeSource()
            cone.SetResolution(8)
            coneMapper = vtk.vtkPolyDataMapper()
            coneMapper.SetInput(cone.GetOutput())
            coneActor = vtk.vtkActor()
            coneActor.SetMapper(coneMapper)
            self._actors['Cone'] = coneActor

    class DemoVisualizer(Visualizer):
        def initialize(self):
            Visualizer.initialize(self)
            self.visuals = {'Cone': DemoVisual(self.renderer)}

    class VisualizerDemoApp(wx.App):
        """Demonstrative application.
        """
        def OnInit(self):
            frame = wx.Frame(None, -1, u'RenderWindowPanel demo',
                             size=(400, 400))
            render_window_panel = RenderWindowPanel(frame, -1)
            self.renderer = render_window_panel.renderer
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(render_window_panel, 1, wx.ALL|wx.EXPAND, 5)
            frame.SetSizer(sizer)
            frame.Layout()
            frame.Show(True)
            visualizer = DemoVisualizer(self, self.renderer)
            visualizer.initialize()
            visualizer.show()
            self.SetTopWindow(frame)
            return True

    app = VisualizerDemoApp(0)
    app.MainLoop()
