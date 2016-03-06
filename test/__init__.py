from .stubs import sublime
from stack_ide_manager import StackIDEManager

def fake_window_and_hs_view():
    window = sublime.create_window(['/home/user/some/project'])
    view = window.open_file('/home/user/some/project/Main.hs')
    StackIDEManager.check_windows()
    return window, view
