import unittest
from unittest.mock import Mock, MagicMock
import stack_ide as stackide
import req
from .stubs import sublime
from .fakebackend import FakeBackend
from settings import Settings
from .data import status_progress_1

_test_settings = Settings("none", [], False)

class StackIDETests(unittest.TestCase):
    def setUp(self):
        sublime.reset_stub()
        self.window = sublime.create_window(['/home/user/some/project'])
        self.view = self.window.open_file('/home/user/some/project/Main.hs')

    def test_can_create(self):
        instance = stackide.StackIDE(self.window, _test_settings, FakeBackend())
        self.assertIsNotNone(instance)
        self.assertTrue(instance.is_active)
        self.assertTrue(instance.is_alive)

    def test_can_send_source_errors_request(self):
        backend = FakeBackend()
        instance = stackide.StackIDE(self.window, _test_settings, backend)
        self.assertIsNotNone(instance)
        self.assertTrue(instance.is_active)
        self.assertTrue(instance.is_alive)
        request = req.get_source_errors()
        instance.send_request(request)
        backend.send_request.assert_called_with(request)

    def test_handle_welcome_stack_ide_outdated(self):

        backend = MagicMock()
        welcome = {
                  "tag": "ResponseWelcome",
                  "contents": [0, 0, 0]
                  }

        instance = stackide.StackIDE(self.window, _test_settings, backend)
        instance.handle_response(welcome)
        self.assertEqual(sublime.current_error, "Please upgrade stack-ide to a newer version.")


    def test_handle_progress_update(self):
        backend = MagicMock()
        instance = stackide.StackIDE(self.window, _test_settings, backend)
        instance.handle_response(status_progress_1)
        self.assertEqual(sublime.current_status, "Compiling Lib")


    def test_can_shutdown(self):
        backend = FakeBackend()
        instance = stackide.StackIDE(self.window, _test_settings, backend)
        self.assertIsNotNone(instance)
        self.assertTrue(instance.is_active)
        self.assertTrue(instance.is_alive)
        instance.end()
        self.assertFalse(instance.is_active)
        self.assertFalse(instance.is_alive)
        backend.send_request.assert_called_with(
            req.get_shutdown())

