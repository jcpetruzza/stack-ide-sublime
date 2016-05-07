import os
from .stubs import sublime
from stack_ide_manager import StackIDEManager

fake_project_dir = '/home/user/projects/helloworld'

def fake_project_file(relative_path):
    return os.path.join(fake_project_dir, relative_path)

def fake_window_and_hs_view():
    window = sublime.create_window()
    view = window.open_file(fake_project_file('src/Main.hs'))
    StackIDEManager.check_views()
    return window, view
