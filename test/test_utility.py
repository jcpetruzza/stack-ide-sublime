import os
import unittest
import utility
from .stubs import sublime

class UtilTests(unittest.TestCase):
    def setUp(self):
        sublime.reset_stub()

    def test_is_haskell_view(self):
        window = sublime.create_window(['/home/user/projects/helloworld'])
        hs_view = window.open_file('/home/user/projects/helloworld/src/Main.hs')
        c_view = window.open_file('/home/user/projects/helloworld/c_bits/lowlevel.c')
        self.assertTrue(utility.is_haskell_view(hs_view))
        self.assertFalse(utility.is_haskell_view(c_view))

    def test_span_from_view_selection(self):
        project_dir = '/home/user/projects/helloworld'
        window = sublime.create_window()
        view = window.open_file(os.path.join(project_dir, 'src/Main.hs'))
        get_rel_file_name = lambda view: view.file_name()[len(project_dir)+1:]

        span = utility.span_from_view_selection(view, get_rel_file_name)
        self.assertEqual(1, span['spanFromLine'])
        self.assertEqual(1, span['spanToLine'])
        self.assertEqual(1, span['spanFromColumn'])
        self.assertEqual(1, span['spanToColumn'])
        self.assertEqual('src/Main.hs', span['spanFilePath'])

    def test_complaints_not_repeated(self):
        utility.complain('complaint', 'waaaah')
        self.assertEqual(sublime.current_error, 'waaaah')
        utility.complain('complaint', 'waaaah 2')
        self.assertEqual(sublime.current_error, 'waaaah')
        utility.reset_complaints()
        utility.complain('complaint', 'waaaah 2')
        self.assertEqual(sublime.current_error, 'waaaah 2')

