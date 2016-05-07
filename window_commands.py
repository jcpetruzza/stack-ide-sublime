try:
    import sublime_plugin
except ImportError:
    from test.stubs import sublime_plugin

from stack_ide_manager import StackIDEManager


class SendStackIdeRequestCommand(sublime_plugin.WindowCommand):
    """
    Allows sending commands via
    window.run_command("send_stack_ide_request", {"request":{"my":"request"}})
    (Sublime Text uses the class name to determine the name of the command
    the class executes when called)
    """

    def __init__(self, window):
        super(SendStackIdeRequestCommand, self).__init__(window)

    def run(self, view, request):
        """
        Pass a request to stack-ide for a given view.
        Called via run_command("send_stack_ide_request", view, {"request": ...})
        """
        instance = StackIDEManager.for_view(view)
        if instance:
            instance.send_request(request)

