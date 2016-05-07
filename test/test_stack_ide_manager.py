import contextlib
import os
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch
from stack_ide_manager import NoStackIDE, StackIDEManager, StackIDEInstanceKey
import stack_ide
from . import fake_project_file
from .stubs import sublime
from .fakebackend import patched_stack_ide_manager
from .data import test_settings
from log import Log
from view import View
import req
import watchdog as wd


class WatchdogTests(unittest.TestCase):

    def test_managed_by_plugin_events(self):

        self.assertIsNone(wd.watchdog)

        wd.plugin_loaded()

        self.assertIsNotNone(wd.watchdog)

        wd.plugin_unloaded()

        self.assertIsNone(wd.watchdog)


other_fake_project = '/home/not/the/same/project'
def other_fake_project_file(relative_filename):
    return os.path.join(other_fake_project, relative_filename)

@patched_stack_ide_manager(additional_projects=[other_fake_project])
class StackIDEManagerTests(unittest.TestCase):
    def setUp(self):
        sublime.reset_stub()

    def test_defaults(self):

        StackIDEManager.check_views()
        self.assertEqual(0, len(StackIDEManager.ide_backend_instances))
        self.assertEqual(0, len(StackIDEManager.view_mappings))


    def test_creates_nothing_for_empty_window(self):

        sublime.create_window()
        StackIDEManager.check_views()
        self.assertEqual(0, len(StackIDEManager.ide_backend_instances))
        self.assertEqual(0, len(StackIDEManager.view_mappings))


    def test_creates_instances_only_for_hs_views(self):

        window = sublime.create_window()
        window.open_file(fake_project_file('src/Main.hs'))
        window.open_file(fake_project_file('cbits/h4cker.c'))
        window.open_file(other_fake_project_file('Lib.hs'))
        window.new_file()
        StackIDEManager.check_views()
        self.assertEqual(2, len(StackIDEManager.ide_backend_instances))
        self.assertEqual(2, len(StackIDEManager.view_mappings))


    def test_views_can_share_instances_even_across_windows(self):

        window1, window2 = sublime.create_window(), sublime.create_window([other_fake_project])
        m1 = window1.open_file(fake_project_file('Main.hs'))
        m2 = window1.open_file(fake_project_file('Main.hs'))
        m3 = window2.open_file(fake_project_file('Main.hs'))
        l  = window2.open_file(other_fake_project_file('Lib.hs'))

        StackIDEManager.check_views()
        self.assertEqual(2, len(StackIDEManager.ide_backend_instances))
        self.assertEqual(4, len(StackIDEManager.view_mappings))

        instance_for = lambda v: StackIDEManager.for_view(v)
        self.assertEqual(instance_for(m1), instance_for(m2))
        self.assertEqual(instance_for(m2), instance_for(m3))
        self.assertNotEqual(instance_for(m1), instance_for(l))


    def test_monitors_closed_views(self):

        window = sublime.create_window()
        v1 = window.open_file(fake_project_file('app/Main.hs'))
        v2 = window.open_file(fake_project_file('src/Lib.hs'))
        v3 = window.open_file(other_fake_project_file('src/Lib.hs'))

        StackIDEManager.check_views()
        self.assertEqual(2, len(StackIDEManager.ide_backend_instances))
        self.assertEqual(3, len(StackIDEManager.view_mappings))

        v2.close()
        StackIDEManager.check_views()
        self.assertEqual(2, len(StackIDEManager.ide_backend_instances))
        self.assertEqual(2, len(StackIDEManager.view_mappings))

        v1.close()
        StackIDEManager.check_views()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))
        self.assertEqual(1, len(StackIDEManager.view_mappings))

        sublime.destroy_windows()
        StackIDEManager.check_views()
        self.assertEqual(0, len(StackIDEManager.ide_backend_instances))
        self.assertEqual(0, len(StackIDEManager.view_mappings))


    def test_retains_live_instances(self):

        window = sublime.create_window()
        view = window.open_file(fake_project_file('Main.hs'))

        StackIDEManager.check_views()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))
        original_instance = StackIDEManager.for_view(view)

        # instance should still exist.
        StackIDEManager.check_views()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))
        self.assertEqual(original_instance, StackIDEManager.for_view(view))


    def test_kills_live_orphans(self):

        window = sublime.create_window()
        view = window.open_file(fake_project_file('Main.hs'))
        StackIDEManager.check_views()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))

        instance = StackIDEManager.for_view(view)

        # close the window
        sublime.destroy_windows()

        # instance should be killed
        StackIDEManager.check_views()
        self.assertEqual(0, len(StackIDEManager.ide_backend_instances))
        self.assertFalse(instance.is_alive)
        instance._backend.send_request.assert_called_with(req.get_shutdown())


    def test_retains_existing_instances(self):
        StackIDEManager.check_views()
        self.assertEqual(0, len(StackIDEManager.ide_backend_instances))
        window = sublime.create_window()
        window.open_file(fake_project_file('Main.hs'))
        StackIDEManager.check_views()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))
        StackIDEManager.check_views()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))

    def test_reset(self):
        window = sublime.create_window()
        view = window.open_file(fake_project_file('Main.hs'))

        StackIDEManager.check_views()
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))

        instance = StackIDEManager.for_view(view)

        StackIDEManager.reset()

        # instances should be shut down.
        self.assertEqual(1, len(StackIDEManager.ide_backend_instances))
        self.assertFalse(instance.is_alive)
        instance._backend.send_request.assert_called_with(req.get_shutdown())



class FindKeyForFileNameTests(unittest.TestCase):


    # Function find_key_for_file_name takes a path to a file and returns
    # either information about cabal and stack directories that contain the
    # file or None if these are not found.
    def setUp(self):
        sublime.reset_stub()
        Log._set_verbosity("none")

    def test_file_on_empty_project(self):
        # no cabal nor stack file
        with fake_project(['empty_project/Lib.hs']) as prj:
            result = StackIDEManager.find_key_for_file_name(prj('empty_project/Lib.hs'))
            self.assertEqual(result, None)

    def test_file_on_cabal_project(self):
        # no stack file
        cabal_project = [
            'cabal_project/cabal_project.cabal',
            'cabal_project/Main.hs',
        ]
        with fake_project(cabal_project) as prj:
            result = StackIDEManager.find_key_for_file_name(prj('cabal_project/Main.hs'))
            self.assertEqual(result, None)

    def test_file_on_bad_stack_project(self):
        # stack file but missing cabal
        broken_stack_project = [
            'stack_project/stack.yaml',
            'stack_project/App.hs',
        ]
        with fake_project(broken_stack_project) as prj:
            result = StackIDEManager.find_key_for_file_name(prj('stack_project/App.hs'))
            self.assertEqual(result, None)

    def test_file_on_singleton_project(self):
        project = [
            'project/stack.yaml',
            'project/project.cabal',
            'project/src/Main.hs',
        ]
        with fake_project(project) as prj:
            result = StackIDEManager.find_key_for_file_name(prj('project/src/Main.hs'))
            self.assertEqual(result, StackIDEInstanceKey(
                stack_yaml_dir=prj('project'),
                cabal_file_dir=prj('project'),
                component='project',
            ))

    def test_files_on_multi_project(self):
        multiproject = [
            'multi/stack.yaml',
            'multi/prj1/prj1.cabal',
            'multi/prj1/src/Lib.hs',
            'multi/prj2/prj2.cabal',
            'multi/prj2/src/Main.hs',
        ]
        with fake_project(multiproject) as prj:
            result1 = StackIDEManager.find_key_for_file_name(prj('multi/prj1/src/Lib.hs'))
            result2 = StackIDEManager.find_key_for_file_name(prj('multi/prj2/src/Main.hs'))
            self.assertEqual(result1, StackIDEInstanceKey(
                stack_yaml_dir=prj('multi'),
                cabal_file_dir=prj('multi/prj1'),
                component='prj1',
            ))
            self.assertEqual(result2, StackIDEInstanceKey(
                stack_yaml_dir=prj('multi'),
                cabal_file_dir=prj('multi/prj2'),
                component='prj2',
            ))

    def test_file_non_matching_cabal_file_name(self):
        project = [
            'prj/stack.yaml',
            'prj/a/not_a.cabal',
            'prj/a/Lib.hs',
        ]
        with fake_project(project) as prj:
            result = StackIDEManager.find_key_for_file_name(prj('prj/a/Lib.hs'))
            self.assertEqual(result, StackIDEInstanceKey(
                stack_yaml_dir=prj('prj'),
                cabal_file_dir=prj('prj/a'),
                component='not_a',
            ))

    def test_file_ambiguous_cabal_file_name(self):
        project = [
            'prj/stack.yaml',
            'prj/a/a.cabal',
            'prj/a/not_a.cabal',
            'prj/a/Lib.hs',
        ]
        with fake_project(project) as prj:
            result = StackIDEManager.find_key_for_file_name(prj('prj/a/Lib.hs'))
            self.assertEqual(result, None)

    def test_skips_bogus_stack_yaml(self):
        project = [
            'prj/stack.yaml',
            'prj/a/a.cabal',
            'prj/a/src/x/stack.yaml',  # <-- bogus
            'prj/a/src/x/y/Lib.hs',
        ]
        with fake_project(project) as prj:
            result = StackIDEManager.find_key_for_file_name(prj('prj/a/src/x/y/Lib.hs'))
            self.assertEqual(result, StackIDEInstanceKey(
                stack_yaml_dir=prj('prj'),
                cabal_file_dir=prj('prj/a'),
                component='a',
            ))

    def test_cabal_can_be_further_apart(self):
        project = [
            'prj/stack.yaml',
            'prj/a/b/c/d/d.cabal',
            'prj/a/b/c/d/Lib.hs',
        ]
        with fake_project(project) as prj:
            result = StackIDEManager.find_key_for_file_name(prj('prj/a/b/c/d/Lib.hs'))
            self.assertEqual(result, StackIDEInstanceKey(
                stack_yaml_dir=prj('prj'),
                cabal_file_dir=prj('prj/a/b/c/d'),
                component='d',
            ))


class LaunchTests(unittest.TestCase):

    ok_project = [
        'ok_project/ok_project.cabal',
        'ok_project/stack.yaml',
        'ok_project/src/Main.hs',
    ]

    def setUp(self):
        sublime.reset_stub()

    @patch('stack_ide.stack_ide_start', Mock(side_effect=FileNotFoundError()))
    def test_launch_window_stack_not_found(self):
        with fake_project(self.ok_project) as prj:
            key = StackIDEManager.find_key_for_file_name(prj('ok_project/src/Main.hs'))
            instance = StackIDEManager.launch_instance(key, test_settings)
            self.assertIsInstance(instance, NoStackIDE)
            self.assertRegex(instance.reason, "instance init failed -- stack not found")
            self.assertRegex(sublime.current_error, "Could not find program 'stack'!")

    @patch('stack_ide.stack_ide_start', Mock(side_effect=Exception()))
    def test_launch_window_stack_unknown_error(self):
        with fake_project(self.ok_project) as prj:
            key = StackIDEManager.find_key_for_file_name(prj('ok_project/src/Main.hs'))
            instance = StackIDEManager.launch_instance(key, test_settings)
            self.assertIsInstance(instance, NoStackIDE)
            self.assertRegex(instance.reason, "instance init failed -- unknown error")

    @patch('stack_ide.stack_ide_start', Mock())
    def test_launch_window_success(self):
        with fake_project(self.ok_project) as prj:
            window = sublime.create_window(prj('ok_project'))
            view = window.open_file(prj('ok_project/src/Main.hs'))
            StackIDEManager.check_views()
            self.assertEqual(View(view).file_name_relative_to_cabal_dir(), 'src/Main.hs')

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
