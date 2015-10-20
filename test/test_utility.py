import os
import unittest
from unittest.mock import MagicMock, Mock

import utility

cur_dir = os.path.dirname(os.path.realpath(__file__))

def mock_window(paths=[]):
    window = MagicMock()
    window.folders = Mock(return_value=paths)
    window.id = Mock(return_value=1234)
    return window

def mock_view(file_path, window):
    view = MagicMock()
    view.file_name = Mock(return_value=os.path.join(window.folders()[0], file_path))
    view.match_selector = Mock(return_value=True)
    window.active_view = Mock(return_value=view)
    window.find_open_file = Mock(return_value=view)
    window.views = Mock(return_value=[view])
    view.window = Mock(return_value=window)
    region = MagicMock()
    region.begin = Mock(return_value=1)
    region.end = Mock(return_value=2)
    view.sel = Mock(return_value=[region])
    view.rowcol = Mock(return_value=(0, 0))
    view.text_point = Mock(return_value=20)
    return view


class UtilTests(unittest.TestCase):

    def test_get_relative_filename(self):
        window = mock_window([cur_dir + '/mocks/helloworld'])
        view = mock_view('src/Main.hs', window)
        self.assertEqual('src/Main.hs', utility.relative_view_file_name(view))
