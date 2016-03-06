import contextlib
import os
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock
from stack_ide_manager import NoStackIDE, StackIDEManager, configure_instance
import stack_ide
from .mocks import mock_window, cur_dir
from .stubs import sublime
from .fakebackend import FakeBackend
from .data import test_settings
from log import Log
from req import Req
import watchdog as wd


class WatchdogTests(unittest.TestCase):

    def test_managed_by_plugin_events(self):

        self.assertIsNone(wd.watchdog)

        wd.plugin_loaded()

        self.assertIsNotNone(wd.watchdog)

        wd.plugin_unloaded()

        self.assertIsNone(wd.watchdog)


class StackIDEManagerTests(unittest.TestCase):


    def test_defaults(self):

        StackIDEManager.check_windows()
        self.assertEqual(0, len(StackIDEManager.ide_backend_instances))


    def test_creates_initial_window(self):

        sublime.create_window('.')
        StackIDEManager.check_windows()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))
        sublime.destroy_windows()

    def test_monitors_closed_windows(self):

        sublime.create_window('.')
        StackIDEManager.check_windows()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))
        sublime.destroy_windows()
        StackIDEManager.check_windows()
        self.assertEqual(0, len(StackIDEManager.ide_backend_instances))

    def test_monitors_new_windows(self):

        StackIDEManager.check_windows()
        self.assertEqual(0, len(StackIDEManager.ide_backend_instances))
        sublime.create_window('.')
        StackIDEManager.check_windows()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))
        sublime.destroy_windows()

    def test_retains_live_instances(self):

        window = mock_window(['.'])
        sublime.add_window(window)

        StackIDEManager.check_windows()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))

        # substitute a 'live' instance
        instance = stack_ide.StackIDE(window, test_settings, FakeBackend())
        StackIDEManager.ide_backend_instances[window.id()] = instance

        # instance should still exist.
        StackIDEManager.check_windows()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))
        self.assertEqual(instance, StackIDEManager.ide_backend_instances[window.id()])

        sublime.destroy_windows()

    def test_kills_live_orphans(self):
        window = sublime.create_window('.')
        StackIDEManager.check_windows()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))

        # substitute a 'live' instance
        backend = MagicMock()
        instance = stack_ide.StackIDE(window, test_settings, backend)
        StackIDEManager.ide_backend_instances[window.id()] = instance

        # close the window
        sublime.destroy_windows()

        # instance should be killed
        StackIDEManager.check_windows()
        self.assertEqual(0, len(StackIDEManager.ide_backend_instances))
        self.assertFalse(instance.is_alive)
        backend.send_request.assert_called_with(Req.get_shutdown())


    def test_retains_existing_instances(self):
        StackIDEManager.check_windows()
        self.assertEqual(0, len(StackIDEManager.ide_backend_instances))
        sublime.create_window('.')
        StackIDEManager.check_windows()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))
        StackIDEManager.check_windows()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))
        sublime.destroy_windows()

    def test_reset(self):
        window = mock_window(['.'])
        sublime.add_window(window)

        StackIDEManager.check_windows()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))

        # substitute a 'live' instance
        backend = MagicMock()
        instance = stack_ide.StackIDE(window, test_settings, backend)
        StackIDEManager.ide_backend_instances[window.id()] = instance

        StackIDEManager.reset()

        # instances should be shut down.
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))
        self.assertFalse(instance.is_alive)
        backend.send_request.assert_called_with(Req.get_shutdown())

        sublime.destroy_windows()




class LaunchTests(unittest.TestCase):

    # launching Stack IDE is a function that should result in a
    # Stack IDE instance (null object or live)
    # the null object should contain the reason why the launch failed.
    def setUp(self):
        Log._set_verbosity("none")


    def test_launch_window_without_folder(self):
        instance = configure_instance(mock_window([]), test_settings)
        self.assertIsInstance(instance, NoStackIDE)
        self.assertRegex(instance.reason, "No folder to monitor.*")

    def test_launch_window_with_empty_folder(self):
        with fake_project(['empty_project/Main.hs']) as prj:
            instance = configure_instance(
                mock_window([prj('hempty_project')]), test_settings)
            self.assertIsInstance(instance, NoStackIDE)
            self.assertRegex(instance.reason, "No cabal file found.*")

    def test_launch_window_with_cabal_folder(self):
        cabal_project = [
            'cabal_project/cabal_project.cabal',
            'cabal_project/Main.hs',
        ]
        with fake_project(cabal_project) as prj:
            instance = configure_instance(
                mock_window([prj('cabal_project')]), test_settings)
            self.assertIsInstance(instance, NoStackIDE)
            self.assertRegex(instance.reason, "No stack.yaml in path.*")

    def test_launch_window_with_wrong_cabal_file(self):
        cabalfile_wrong_project = [
            'cabal_project/badly_name_cabal_file.cabal',
            'cabal_project/stack.yaml',
            'cabal_project/Main.hs',
        ]
        with fake_project(cabalfile_wrong_project) as prj:
            instance = configure_instance(
                mock_window([prj('cabal_project')]), test_settings)
            self.assertIsInstance(instance, NoStackIDE)
            self.assertRegex(instance.reason, "cabal_project.cabal not found.*")

    @unittest.skip("Actually starts a stack ide, slow and won't work on Travis")
    def test_launch_window_with_helloworld_project(self):
        instance = configure_instance(
            mock_window([cur_dir + '/projects/helloworld']), test_settings)
        self.assertIsInstance(instance, stack_ide.StackIDE)
        instance.end()

    ok_project = [
        'ok_project/ok_project.cabal',
        'ok_project/stack.yaml',
        'ok_project/src/Main.hs',
    ]
    def test_launch_window_stack_not_found(self):
        stack_ide.stack_ide_start = Mock(side_effect=FileNotFoundError())
        with fake_project(self.ok_project) as prj:
            instance = configure_instance(mock_window([prj('ok_project')]), test_settings)
            self.assertIsInstance(instance, NoStackIDE)
            self.assertRegex(instance.reason, "instance init failed -- stack not found")
            self.assertRegex(sublime.current_error, "Could not find program 'stack'!")

    def test_launch_window_stack_unknown_error(self):
        stack_ide.stack_ide_start = Mock(side_effect=Exception())
        with fake_project(self.ok_project) as prj:
            instance = configure_instance(mock_window([prj('ok_project')]), test_settings)
            self.assertIsInstance(instance, NoStackIDE)
            self.assertRegex(instance.reason, "instance init failed -- unknown error")



@contextlib.contextmanager
def fake_project(files):
    with TemporaryDirectory() as dir:
        for file in files:
            if os.path.isabs(file):
                raise Exception("Can't accept absolute paths: {}".format(file))
            full_name = os.path.join(dir, file)
            full_dir = os.path.dirname(full_name)
            if not os.path.exists(full_dir):
                os.makedirs(full_dir)
            open(full_name, 'w').close()
        yield lambda file: os.path.join(dir, file)
