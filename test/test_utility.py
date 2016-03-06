import unittest
import utility
from .stubs import sublime

class UtilTests(unittest.TestCase):
    def setUp(self):
        sublime.reset_stub()

    def test_get_relative_filename(self):
        window = sublime.create_window(['/home/user/projects/helloworld'])
        view = window.open_file('/home/user/projects/helloworld/src/Main.hs')
        self.assertEqual('src/Main.hs', utility.relative_view_file_name(view))

    def test_is_haskell_view(self):
        window = sublime.create_window(['/home/user/projects/helloworld'])
        hs_view = window.open_file('/home/user/projects/helloworld/src/Main.hs')
        c_view = window.open_file('/home/user/projects/helloworld/c_bits/lowlevel.c')
        self.assertTrue(utility.is_haskell_view(hs_view))
        self.assertFalse(utility.is_haskell_view(c_view))

    def test_span_from_view_selection(self):
        window = sublime.create_window(['/home/user/projects/helloworld'])
        view = window.open_file('/home/user/projects/helloworld/src/Main.hs')
        span = utility.span_from_view_selection(view)
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

