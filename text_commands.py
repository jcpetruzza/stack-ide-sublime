try:
    import sublime, sublime_plugin
except ImportError:
    from test.stubs import sublime, sublime_plugin

import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import req
from utility import span_from_view_selection, filter_enclosing
from stack_ide_manager import send_request, StackIDEManager
from response import parse_span_info_response, parse_exp_types
from view import View

def _span_from_selection(view):
    return span_from_view_selection(view, lambda view: View(view).file_name_relative_to_cabal_dir())

class UpdateInIdeBackendCommand(sublime_plugin.TextCommand):
    """
    An update_in_ide_backend command that requests the ide-backend instance
    associated with this view to reload it, reporting all errors.
    """
    def run(self, args):
        view = self.view

        if not StackIDEManager.is_running(view):
            return

        key = StackIDEManager.view_mappings[view.id()]
        all_views = (view for window in sublime.windows() for view in window.views())
        views_for_key = (view for view in all_views if StackIDEManager.view_mappings.get(view.id()) == key)
        filenames = set(View(v).file_name_relative_to_cabal_dir() for v in views_for_key)

        StackIDEManager.for_view(view).update_files(filenames)
        send_request(self.view, req.get_source_errors(), View(view).handle_source_errors)

class ClearErrorPanelCommand(sublime_plugin.TextCommand):
    """
    A clear_error_panel command to clear the error panel.
    """
    def run(self, edit):
        self.view.erase(edit, sublime.Region(0, self.view.size()))

class AppendToErrorPanelCommand(sublime_plugin.TextCommand):
    """
    An append_to_error_panel command to append text to the error panel.
    """
    def run(self, edit, message):
        self.view.insert(edit, self.view.size(), message + "\n\n")

class ShowHsTypeAtCursorCommand(sublime_plugin.TextCommand):
    """
    A show_hs_type_at_cursor command that requests the type of the
    expression under the cursor and, if available, shows it as a pop-up.
    """
    def run(self,edit):
        request = req.get_exp_types(_span_from_selection(self.view))
        send_request(self.view, request, self._handle_response)

    def _handle_response(self,response):
        type_spans = list(parse_exp_types(response))
        if type_spans:
            type_span = next(filter_enclosing(self.view, self.view.sel()[0], type_spans), None)
            if type_span is not None:
                _type, span = type_span
                self.view.show_popup(_type)


class ShowHsInfoAtCursorCommand(sublime_plugin.TextCommand):
    """
    A show_hs_info_at_cursor command that requests the info of the
    expression under the cursor and, if available, shows it as a pop-up.
    """
    def run(self,edit):
        request = req.get_exp_info(_span_from_selection(self.view))
        send_request(self.view, request, self._handle_response)

    def _handle_response(self,response):

        if len(response) < 1:
           return

        infos = parse_span_info_response(response)
        (props, scope), span = next(infos)

        if not props.defSpan is None:
            source = "(Defined in {}:{}:{})".format(props.defSpan.filePath, props.defSpan.fromLine, props.defSpan.fromColumn)
        elif scope.importedFrom:
            source = "(Imported from {})".format(scope.importedFrom.module)

        self.view.show_popup("{} :: {}  {}".format(props.name,
                                                    props.type,
                                                    source))


class GotoDefinitionAtCursorCommand(sublime_plugin.TextCommand):
    """
    A goto_definition_at_cursor command that requests the info of the
    expression under the cursor and, if available, navigates to its location
    """
    def run(self,edit):
        request = req.get_exp_info(_span_from_selection(self.view))
        send_request(self.view, request, self._handle_response)

    def _handle_response(self,response):

        if len(response) < 1:
            return

        infos = parse_span_info_response(response)
        (props, scope), span = next(infos)
        defSpan = props.defSpan
        if defSpan:
            path_and_pos = '{}:{}:{}'.format(defSpan.filePath, defSpan.fromLine or 0, defSpan.fromColumn or 0)
            View(self.view).open_view_for_path(path_and_pos, sublime.ENCODED_POSITION)
        elif scope.importedFrom:
            sublime.status_message("Cannot navigate to {}, it is imported from {}".format(props.name, scope.importedFrom.module))
        else:
            sublime.status_message("{} not found!", props.name)

class CopyHsTypeAtCursorCommand(sublime_plugin.TextCommand):
    """
    A copy_hs_type_at_cursor command that requests the type of the
    expression under the cursor and, if available, puts it in the clipboard.
    """
    def run(self,edit):
        request = req.get_exp_types(_span_from_selection(self.view))
        send_request(self.view, request, self._handle_response)

    def _handle_response(self,response):
        types = list(parse_exp_types(response))
        if types:
            (type, span) = types[0] # types are ordered by relevance?
            sublime.set_clipboard(type)
