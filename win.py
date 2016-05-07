class Win(object):
    """
    Operations on Sublime windows that are relevant to us
    """

    def __init__(self, window):
        self._window = window

    def reset_error_panel(self, base_dir):
        """
        Creates and configures the error panel for this window
        """
        panel = self._window.create_output_panel("hide_errors")
        panel.set_read_only(False)

        # This turns on double-clickable error/warning messages in the error panel
        # using a regex that looks for the form file_name:line:column: error_message
        # The error_message could be improved as currently it says KindWarning: or KindError:
        # Perhaps grabbing the next line? Or the whole message?
        panel.settings().set("result_file_regex", "^(..[^:]*):([0-9]+):?([0-9]+)?:? (.*)$")
        panel.settings().set("result_base_dir", base_dir)

        # Seems to force the panel to refresh after we clear it:
        self.hide_error_panel()

        # Clear the panel. TODO: should be unnecessary? https://www.sublimetext.com/forum/viewtopic.php?f=6&t=2044
        panel.run_command("clear_error_panel")

        # TODO store the panel somewhere so we can reuse it.
        return panel

    def hide_error_panel(self):
        self._window.run_command("hide_panel", {"panel": "output.hide_errors"})

    def show_error_panel(self):
        self._window.run_command("show_panel", {"panel":"output.hide_errors"})
