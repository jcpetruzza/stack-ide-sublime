from itertools import groupby
import os

try:
    import sublime
except ImportError:
    from test.stubs import sublime
from utility import view_region_from_span, filter_enclosing, format_type
from win import Win
from response import parse_source_errors, parse_exp_types
from stack_ide_manager import StackIDEManager
import webbrowser

class View(object):
    """
    Operations on Sublime views that are relevant to us
    """

    show_popup = False

    def __init__(self, view):
        self._view = view

    @property
    def view(self):
        return self._view

    @property
    def window(self):
        return self.view.window()

    @property
    def cabal_file_dir(self):
        view_key = StackIDEManager.view_mappings.get(self.view.id())
        if view_key:
            return view_key.cabal_file_dir

    def file_name_relative_to_cabal_dir(self):
        """
        The view filename as relative to the cabal project root (as ide-backend wants it)
        """
        cabal_dir = self.cabal_file_dir
        if cabal_dir:
            return self.view.file_name().replace(cabal_dir + os.path.sep, "")

    def find_view_for_path(self, relative_path):
        full_path = os.path.join(self.cabal_file_dir, relative_path)
        return self.window.find_open_file(full_path)

    def open_view_for_path(self, relative_path, flags=0):
        full_path = os.path.join(self.cabal_file_dir, relative_path)
        self.window.open_file(full_path, flags)

    def highlight_type(self, exp_types):
        """
        ide-backend gives us a wealth of type info for the cursor. We only use the first,
        most specific one for now, but it gives us the types all the way out to the topmost
        expression.
        """
        type_spans = list(parse_exp_types(exp_types))
        if type_spans:
            view = self.view
            type_span = next(filter_enclosing(view, view.sel()[0], type_spans), None)
            if type_span is not None:
                (_type, span) = type_span
                view.set_status("type_at_cursor", _type)
                view.add_regions("type_at_cursor", [view_region_from_span(view, span)], "storage.type", "", sublime.DRAW_OUTLINED)
                if self.show_popup:
                    view.show_popup(format_type(_type), on_navigate= (lambda href: webbrowser.open(view.hoogle_url + href)))
                return

        # Clear type-at-cursor display
        for view in self.window.views():
            view.set_status("type_at_cursor", "")
            view.add_regions("type_at_cursor", [], "storage.type", "", sublime.DRAW_OUTLINED)

    def handle_source_errors(self, source_errors):
        """
        Makes sure views containing errors are open and shows error messages + highlighting
        """

        errors = list(parse_source_errors(source_errors))

        # TODO: we should pass the errorKind too if the error has no span
        error_panel = Win(self.window).reset_error_panel(self.cabal_file_dir)
        for error in errors:
            error_panel.run_command("append_to_error_panel", {"message": repr(error)})

        if errors:
            Win(self.window).show_error_panel()
        else:
            Win(self.window).hide_error_panel()

        error_panel.set_read_only(True)

        file_errors = list(filter(lambda error: error.span, errors))
        # First, make sure we have views open for each error
        need_load_wait = False
        paths = set(error.span.filePath for error in file_errors)
        for path in paths:
            view = self.find_view_for_path(path)
            if not view:
                need_load_wait = True
                self.open_view_for_path(path)

        # If any error-holding files need to be opened, wait briefly to
        # make sure the file is loaded before trying to annotate it
        if need_load_wait:
            sublime.set_timeout(lambda: self.highlight_errors(file_errors), 100)
        else:
            self.highlight_errors(file_errors)

    def highlight_errors(self, errors):
        """
        Highlights the relevant regions for each error in open views
        """

        # We gather each error by the file view it should annotate
        # so we can add regions in bulk to each view.
        error_regions_by_view_id = {}
        warning_regions_by_view_id = {}
        for path, errors_by_path in groupby(errors, lambda error: error.span.filePath):
            view = self.find_view_for_path(path)
            for kind, errors_by_kind in groupby(errors_by_path, lambda error: error.kind):
                if kind == 'KindWarning':
                    warning_regions_by_view_id[view.id()] = list(view_region_from_span(view, error.span) for error in errors_by_kind)
                else:
                    error_regions_by_view_id[view.id()] = list(view_region_from_span(view, error.span) for error in errors_by_kind)

        # Add error/warning regions to their respective views
        for view in self.window.views():
            view.add_regions("errors", error_regions_by_view_id.get(view.id(), []), "invalid", "dot", sublime.DRAW_OUTLINED)
            view.add_regions("warnings", warning_regions_by_view_id.get(view.id(), []), "comment", "dot", sublime.DRAW_OUTLINED)
