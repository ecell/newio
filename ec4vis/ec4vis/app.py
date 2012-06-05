# coding: utf-8
"""app.py -- Visualizer Application implementation by Yasushi Masuda (ymasuda@accense.com)
"""
from logging import debug

import wx, wx.dataview

from ec4vis.browser import BrowserFrame
from ec4vis.plugins import PluginLoader
from ec4vis.settings import settings
from ec4vis.visualizer import VISUALIZER_CLASSES, VisualizerEventResponder
from ec4vis.visualizer_panel import SourceDataViewModel, DataDataViewModel

VERSION = (0, 0, 1)
APP_TITLE_NAME = 'E-Cell 4 Visualization Browser Version (%d.%d.%d)' %VERSION


class BrowserApp(wx.App, VisualizerEventResponder):
    """Application object for browser.
    """
    def __init__(self, *args, **kwargs):
        
        # application status
        self.visualizer = None # current visualizer
        self.settings = kwargs.pop('settings', None)
        wx.App.__init__(self, *args, **kwargs)

    def OnInit(self):
        """Integrated initialization hook.
        """
        # UI stuff
        self.init_ui()
        # plugins
        self.init_plugins()
        self.render_window.Render()
        return True

    def init_ui(self):
        """Initialize UI.
        """
        # browser
        browser = BrowserFrame(None, -1, APP_TITLE_NAME, size=(1000, 600))

        # outlet bindings
        self.browser = browser
        render_window_panel = self.browser.render_window_panel
        if self.settings:
            render_window_panel.configure_renderer(self.settings)
        self.render_window = render_window_panel.render_window
        self.renderer = render_window_panel.renderer
        control_panel = self.browser.control_panel
        visualizer_panel = control_panel.visualizer_panel
        self.visualizer_choice = visualizer_panel.visualizer_choice
        self.visualizer_reset_button = visualizer_panel.reset_button
        self.visualizer_configure_button = visualizer_panel.configure_button
        self.source_list = visualizer_panel.source_list
        self.source_add_button = visualizer_panel.add_button
        self.source_remove_button = visualizer_panel.remove_button
        self.data_list = visualizer_panel.data_list
        self.data_up_button = visualizer_panel.up_button
        self.data_down_button = visualizer_panel.down_button
        # dynamically generated dialog
        self.data_loader_dialog = None

        # outlet configurations
        self.sources = []
        source_model = SourceDataViewModel(self.sources)
        # data_model = DataDataViewModel([])
        self.update_visualizer_buttons_status()
        self.source_list.AssociateModel(source_model)
        self.update_source_remove_ui_status()
        # self.data_list.AssociateModel(data_model)
        self.update_data_list_buttons_status()

        # event bindings
        menu_bar = browser.menu_bar
        file_add = menu_bar.file_add
        file_quit = menu_bar.file_quit
        # menu commands
        browser.Bind(wx.EVT_MENU, self.OnFileAddMenu, file_add)
        browser.Bind(wx.EVT_MENU, self.OnFileQuitMenu, file_quit)
        # ui commands
        self.visualizer_reset_button.Bind(
            wx.EVT_BUTTON, self.OnVisualizerResetButton)
        self.visualizer_configure_button.Bind(
            wx.EVT_BUTTON, self.OnVisualizerConfigureButton)
        self.source_add_button.Bind(
            wx.EVT_BUTTON, self.OnSourceAddButton)
        self.source_remove_button.Bind(
            wx.EVT_BUTTON, self.OnSourceRemoveButton)
        self.visualizer_choice.Bind(
            wx.EVT_CHOICE, self.OnVisualizerChoice)
        self.source_list.Bind(
            wx.dataview.EVT_DATAVIEW_SELECTION_CHANGED,
            self.OnSourceListSelectionChanged)
        self.data_list.Bind(
            wx.dataview.EVT_DATAVIEW_SELECTION_CHANGED,
            self.OnDataListSelectionChanged)
        self.data_up_button.Bind(
            wx.EVT_BUTTON, self.OnDataUpButton)
        self.data_down_button.Bind(
            wx.EVT_BUTTON, self.OnDataDownButton)

        # renderer event binding --- this is bad hack
        def render_window_render_observer(o, e, f=render_window_panel):
            # hasattr() is to prevent AttributeError.
            """ # This is kept for demonstration use.
            if hasattr(self, 'visualizer'):
                if self.visualizer:
                    self.visualizer.update()"""
            pass
        self.render_window.AddObserver(
            "RenderEvent", render_window_render_observer)

        # assign and show top window
        self.SetTopWindow(browser)
        self.browser.Show(True)

    def init_plugins(self):
        """Initialize plugins
        """
        # load plugins
        plugin_loader = PluginLoader()
        dlg = wx.ProgressDialog(
            u'Loading plugins...',
            u'',
            maximum=len(plugin_loader.modules_info),
            parent=self.browser,
            style=wx.PD_AUTO_HIDE)
        for i, (modpath, status) in enumerate(plugin_loader.load_iterative()):
            message = '%s ... %s' %(modpath, 'OK' if status else 'FAILED')
            wx.Yield()
            dlg.Update(i+1, message)
        dlg.Destroy()
        wx.Yield()
        # set plugin choice
        visualizer_choices = (
            ['Select Visualizer']+sorted(VISUALIZER_CLASSES.keys()))
        self.visualizer_choice.SetItems(visualizer_choices)

    def finalize(self):
        """Finalizer.
        """
        pass # just a placeholder now.

    def add_file_source(self):
        dlg = wx.FileDialog(self.browser, u'Choose file to add', style=wx.FD_MULTIPLE)
        ret = dlg.ShowModal()
        if ret==wx.ID_OK:
            filenames = dlg.GetPaths()
            present_uris = [uri for use, uri in self.sources]
            updated = False
            for fn in filenames:
                uri = 'file://%s' %(fn)
                if uri not in present_uris:
                    self.sources.append([True, uri])
                    updated = True
            if updated:
                # this is required for yielding
                self.source_list.GetModel().AfterReset()

    def OnFileAddMenu(self, event):
        """Called on 'File'->'Add source...' menu.
        """
        self.add_file_source()

    def OnFileQuitMenu(self, event):
        """Called on 'File'->'Quit' menu.
        """
        self.ExitMainLoop()

    def update_visualizer_buttons_status(self):
        """Updates enable/disable status of Reset/Configure buttons.
        """
        visualizer = self.visualizer
        can_reset = not (visualizer is None)
        has_config_ui = bool(visualizer) and visualizer.has_configuration_ui
        # self.visualizer_reset_button.Enable(can_reset)
        self.visualizer_configure_button.Enable(has_config_ui)

    def update_source_remove_ui_status(self):
        """Updates enable/disable status of UIs related removing source.
        """
        selected = self.source_list.GetSelection()
        self.source_remove_button.Enable(bool(selected))

    def update_data_list_buttons_status(self):
        """Updates enable/disable status of UIs related removing source.
        """
        data_list = self.data_list 
        model = data_list.GetModel()
        selected = data_list.GetSelection()
        # this is hack: wxPython's DVLC lacks way-to-count-rows or something.
        n_rows = 0
        selected_row = wx.NOT_FOUND
        if selected and self.visualizer:
            # this is dirty because DVLC lacks functionality to count rows.
            selected_data_id = model.GetValue(selected, 0)
            data_objects = self.visualizer.data_objects
            n_rows = len(data_objects)
            for row_id, info in enumerate(data_objects):
                if selected_data_id==info[0]:
                    selected_row = row_id
                    break
        self.data_up_button.Enable(bool(selected and selected_row>0))
        self.data_down_button.Enable(bool(selected and (0<=selected_row<(n_rows-1))))

    def do_process_sources(self):
        self.visualizer.process_sources([uri for use, uri in self.sources])
        data_objects = self.visualizer.data_objects
        data_list = self.data_list
        new_data_model = DataDataViewModel(data_objects)
        new_data_model.AfterReset()
        old_data_model = data_list.GetModel()
        data_list.AssociateModel(new_data_model)
        del old_data_model

    def OnVisualizerResetButton(self, event):
        """Handles visualizer 'Reset' button.
        """
        if self.visualizer is None:
            return
        self.visualizer.reset()
        self.do_process_sources()

    def OnVisualizerConfigureButton(self, event):
        """Handles visualizer 'Configure' button.
        """
        self.visualizer.load_configuration_ui()

    def OnSourceAddButton(self, event):
        """Called on Add source boutton.
        """
        self.add_file_source()

    def OnSourceRemoveButton(self, event):
        """Called on Add source boutton.
        """
        selected = self.source_list.GetSelection()
        if selected:
            selected_uri = self.source_list.GetModel().GetValue(selected, 1)
            popped = None
            for i, (use, uri) in enumerate(self.sources):
                if uri==selected_uri:
                    popped = self.sources.pop(i)
                    break
            if popped:
                # this is required for yielding
                self.source_list.GetModel().AfterReset()
        self.update_source_remove_ui_status()

    def OnVisualizerChoice(self, event):
        """Called on selection of visualizer_choice changed.
        """
        selected_idx = event.GetSelection()
        if selected_idx: # not 'Select Visualizer'
            key = event.GetString()
            visualizer_class = VISUALIZER_CLASSES[key]
        else:
            visualizer_class = None
        if self.visualizer.__class__==visualizer_class:
            # do nothing if visualizer class not chaged
            return
        # detach old visualizer from application
        old_visualizer, self.visualizer = self.visualizer, None
        if old_visualizer:
            old_visualizer.finalize()
            del old_visualizer
        if visualizer_class:
            # attach new visualizer to application
            new_visualizer = visualizer_class(self, self.renderer)
            new_visualizer.initialize() # implies show()
            self.visualizer = new_visualizer
            self.do_process_sources()
            self.render_window.Render()
        self.update_visualizer_buttons_status()
        
    def OnSourceListSelectionChanged(self, event):
        """Called on selection of soruce list changed.
        """
        self.update_source_remove_ui_status()

    def OnDataListSelectionChanged(self, event):
        """Called on selection of data list changed.
        """
        model = self.data_list.GetModel()
        if model is None:
            return
        selected = self.data_list.GetSelection()
        data_id = model.GetValue(selected, 0)
        if self.visualizer is None:
            return
        self.visualizer.update(data_id)
        self.render_window.Render()
        self.update_data_list_buttons_status()

    def move_current_data(self, offset):
        """Do real job for OnDataUp/DownButton.
        """
        model = self.data_list.GetModel()
        if model is None:
            return
        selected = self.data_list.GetSelection()
        if selected is None:
            return
        if self.visualizer is None:
            return
        data_id = model.GetValue(selected, 0)
        self.visualizer.move_data_ordering(data_id, offset)
        # model.ValueChanged()
        model.AfterReset() # yield
            
    def OnDataUpButton(self, event):
        """Called on data list up button.
        """
        self.move_current_data(-1)
        
    def OnDataDownButton(self, event):
        """Called on data list down button.
        """
        self.move_current_data(+1)

    # Visualizer Event Responder methods
    def get_ui_root(self):
        # just returns browser as toplevel window
        return self.browser

    def process_sources_start(self, sender, sources):
        # show data-loading dialog
        if self.data_loader_dialog is None:
            self.data_loader_dialog = wx.ProgressDialog(
                u'Loading data...',
                u'',
                maximum=len(sources),
                parent=self.browser,
            style=wx.PD_AUTO_HIDE)
    
    def process_sources_done(self, sender, sources):
        # withdraw data-loading dialog
        if self.data_loader_dialog:
            self.data_loader_dialog.Destroy()
            wx.Yield()
            self.data_loader_dialog = None

    def process_source_done(self, sender, source, error):
        # update data-loading dialog
        print error
        if self.data_loader_dialog is None:
            return
        sources = [uri for use, uri in self.sources]
        if source in sources:
            index = sources.index(source)
            message = 'Processing %s ... %s' %(source, 'OK' if (error is None) else 'FAILED')
            self.data_loader_dialog.Update(index, message)
        

if __name__=='__main__':
    app = BrowserApp(0)
    app.MainLoop()
