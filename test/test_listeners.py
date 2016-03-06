import unittest
from unittest.mock import Mock, ANY
from event_listeners import StackIDESaveListener, StackIDETypeAtCursorHandler, StackIDEAutocompleteHandler
from stack_ide_manager import StackIDEManager
from req import Req
from . import fake_window_and_hs_view
from .fakebackend import patched_stack_ide_manager, responses_for
from .stubs import sublime
from settings import Settings
import stack_ide
import utility as util
from .data import many_completions


test_settings = Settings("none", [], False)
type_info = "FilePath -> IO String"
span = {
    "spanFromLine": 1,
    "spanFromColumn": 1,
    "spanToLine": 1,
    "spanToColumn": 5
}
exp_types_response = {"tag": "", "contents": [[type_info, span]]}
request_include_targets = {'contents': [{'contents': {'contents': ['src/Main.hs'], 'tag': 'TargetsInclude'}, 'tag': 'RequestUpdateTargets'}], 'tag': 'RequestUpdateSession'}

@patched_stack_ide_manager
class ListenerTests(unittest.TestCase):
    def setUp(self):
        sublime.reset_stub()

    def test_requests_update_on_save(self):
        listener = StackIDESaveListener()
        window, view = fake_window_and_hs_view()

        backend = StackIDEManager.for_window(window)._backend
        backend.send_request.reset_mock()

        listener.on_post_save(view)
        backend.send_request.assert_called_with(ANY)


    def test_ignores_non_haskell_views(self):
        listener = StackIDESaveListener()
        window, hs_view = fake_window_and_hs_view()
        non_hs_view = window.open_file('low_level.c')

        backend = StackIDEManager.for_window(window)._backend

        backend.send_request.reset_mock()
        listener.on_post_save(non_hs_view)
        backend.send_request.assert_not_called()


    def test_type_at_cursor_tests(self):
        listener = StackIDETypeAtCursorHandler()
        window, view = fake_window_and_hs_view()

        with responses_for(window, exp_types_response):
            listener.on_selection_modified(view)
            view.set_status.assert_called_with("type_at_cursor", type_info)
            view.add_regions.assert_called_with("type_at_cursor", ANY, "storage.type", "", sublime.DRAW_OUTLINED)

    def test_request_completions(self):

        listener = StackIDEAutocompleteHandler()
        window, view = fake_window_and_hs_view()

        backend = StackIDEManager.for_window(window)._backend

        with responses_for(window, {'RequestGetAutocompletion': many_completions}):
            listener.on_query_completions(view, 'm', []) #locations not used.

            req = Req.get_autocompletion(filepath=util.relative_view_file_name(view),prefix="m")
            req['seq'] = ANY
            backend.send_request.assert_called_with(req)

    def test_returns_completions(self):
        listener = StackIDEAutocompleteHandler()
        window, view = fake_window_and_hs_view()

        with responses_for(window, {'RequestGetAutocompletion': many_completions}):
            completions = listener.on_query_completions(view, 'm', []) #locations not used.

            self.assertEqual(8, len(completions))
            self.assertEqual(['!!\t\tData.List', '!!'], completions[0])

            # in live situations on_query_completions returns [] first while we retrieve results
            # here we make sure that the re-trigger calls are still in place
            view.run_command.assert_any_call('hide_auto_complete')
            view.run_command.assert_any_call('auto_complete', ANY)

