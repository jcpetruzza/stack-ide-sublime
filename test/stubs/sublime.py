import uuid
from unittest.mock import MagicMock, Mock

current_status = ""
current_error = ""

def status_message(msg):
    global current_status
    current_status = msg

def error_message(msg):
    global current_error
    current_error = msg

def set_timeout_async(fn, delay):
    fn()

def set_timeout(fn, delay):
    fn()

def load_settings(name):
    return Settings()

class Settings():

    def add_on_change(self, key, func):
        pass

    def get(self, key, default):
        return default


class FakeView():
    def __init__(self, parent_window, file_name=None):
        self._id = uuid.uuid4()
        self._window = parent_window
        self._file_name = file_name
        self._selection = FakeSelection()
        self.show_popup = Mock()
        self.add_regions = Mock()
        self.set_status = Mock()
        self.set_read_only = Mock()
        self.run_command = Mock()

    def id(self):
        return self._id

    def window(self):
        return self._window

    def file_name(self):
        return self._file_name

    def sel(self):
        return self._selection

    def match_selector(self, point, selector):
        if selector == "source.haskell":
            name = self._file_name
            return name and name.endswith('.hs')

    def is_loading(self):
        return False

    def close(self):
        if self._window:
            self._window._views.remove(self)
            self._window = None

    def settings(self):
        return MagicMock()

    def rowcol(self, x):
        return (x, 0)

    def text_point(self, row, col):
        return row * 80 + col


class FakeWindow():

    def __init__(self, folders):
        self._views = []
        self._folders = folders
        self._active_view = None
        self._output_panels = {}
        self._id = uuid.uuid4()
        self.open_file = Mock(wraps=self._open_file)
        self.run_command = Mock(wraps=self._run_command)

    def id(self):
        return self._id

    def folders(self):
        return self._folders

    def new_file(self):
        return self.open_file(None)

    def _open_file(self, file_name, flags=None):
        view = FakeView(parent_window=self, file_name=file_name)
        self._views.append(view)
        self._active_view = view
        return view

    def find_open_file(self, file_name):
        for view in self.views():
            if file_name == view.file_name():
                return view
        return None

    def views(self):
        return self._views

    def active_view(self):
        return self._active_view

    def _run_command(self, command, args):
        pass

    def create_output_panel(self, name, unlisted=False):
        if name not in self._output_panels:
            self._output_panels[name] = FakeView(parent_window=self)
        return self._output_panels[name]



fake_windows = []

ENCODED_POSITION = 1 #flag used for window.open_file
DRAW_OUTLINED = 2 # flag used for view.add_regions

clipboard = None

def reset_stub():
    """
    Reset the stub to a pristine state, to be called between tests
    """
    global fake_windows, clipboard
    fake_windows = []
    clipboard = None

def create_window(folders):
    global fake_windows
    window = FakeWindow(folders)
    fake_windows.append(window)
    return window

def add_window(window):
    global fake_windows
    fake_windows.append(window)

def destroy_windows():
    global fake_windows
    fake_windows = []

def set_clipboard(text):
    global clipboard
    clipboard = text

def windows():
    global fake_windows
    return fake_windows

class Region():

    def __init__(self, begin, end):
        self._begin = begin
        self._end = end

    def begin(self):
        return self._begin

    def end(self):
        return self._end


class FakeSelection():
    def __init__(self, regions=None):
        self._regions = regions or [Region(0,0)]

    def __getitem__(self, pos):
        return self._regions[pos]

    def __sizeof__(self):
        return len(self._regions)
