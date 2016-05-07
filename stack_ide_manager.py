import traceback
import sys
import os

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

from collections import namedtuple

from stack_ide import StackIDE
from log import Log
from utility import is_haskell_view, expected_cabalfile, get_cabal_files, is_stack_project, complain, reset_complaints
from win import Win
try:
    import sublime
except ImportError:
    from test.stubs import sublime


def send_request(view, request, on_response = None):
    """
    Sends the given request to the view's stack-ide instance,
    optionally handling its response
    """
    if StackIDEManager.is_running(view):
        StackIDEManager.for_view(view).send_request(request, on_response)


# We assign a different ide-backend instance to each library/executable in any cabal project per yaml file
class StackIDEInstanceKey(namedtuple('StackIDEInstanceKey', 'stack_yaml_dir cabal_file_dir component')):
    @classmethod
    def for_filename(cls, filename):
        if filename is None:
            return None

        cabal_dir, cabal_file_name = None, None
        current_path = filename

        while True:
            path = os.path.dirname(current_path)
            if path == current_path:
                return None  # We've searched all the directories up to the root, found nothing

            current_path = path

            cabal_files = get_cabal_files(current_path)

            if len(cabal_files) == 1:
                expected = os.path.basename(expected_cabalfile(current_path))
                cabal_dir, cabal_file_name = current_path, cabal_files[0]
                if cabal_file_name != expected:
                    Log.warning(
                        "Cabal file name doesn't match directory name: ",
                        os.path.join(current_path, cabal_file_name),
                    )
            elif len(cabal_files) > 1:
                    Log.warning("Too many cabal files in {}".format(current_path))

            if is_stack_project(current_path):
                if cabal_dir == None:
                    Log.warning("A stack.yaml found before a cabal file in ", current_path)
                else:
                    # Ideally the component would be a function of the directory in which the
                    # original hs file is found wrt to the cabal file. So it could be the library
                    # part or an executable or a unit-test, etc. For now, it is always the library
                    # (stack-ide doesn't support finer grained specification)
                    component, _ = os.path.splitext(cabal_file_name)
                    return cls(
                        stack_yaml_dir=current_path,
                        cabal_file_dir=cabal_dir,
                        component=component,
                    )


class StackIDEManager:
    ide_backend_instances = {}
    view_mappings = {}

    settings = None

    @classmethod
    def getinstances(cls):
        return cls.ide_backend_instances

    @classmethod
    def check_views(cls):
        """
        Compares the current views on every current window with the known ide-backend instances
          - new views are assigned a (not necessarily new) process of stack-ide, based on their cabal project
          - stale processes are stopped

        NB. This is the only method that updates ide_backend_instances and view_mappings,
        so as long as it is not called concurrently, there will be no race conditions...
        """
        is_relevant_view = lambda v: is_haskell_view(v) and v.file_name() is not None
        get_key = lambda v: cls.find_key_for_file_name(v.file_name())

        current_hs_views = {v.id(): get_key(v) for w in sublime.windows() for v in w.views() if is_relevant_view(v)}
        current_keys = set(current_hs_views.values())
        updated_instances = {}

        # Kill stale instances, keep live ones
        for key, instance in cls.ide_backend_instances.items():
            if key not in current_keys:
                # This instance has no longer a corresponding view, we may need to kill its process
                if instance.is_active:
                    Log.normal("Stopping stale process for ", key)
                    instance.end()
            else:
                # There is still at least one view using this instance. There are three possibilities:
                #  1) the instance is alive and active.
                #  2) the instance is alive but inactive (it is one that failed to init, etc)
                #  3) the instance is dead instance, i.e., one that was killed.
                #
                # Views with dead instances are to be treated like new views, so we will
                # try to launch a new instance for them
                if instance.is_alive:
                    current_keys.remove(key)
                    updated_instances[key] = instance

        cls.ide_backend_instances = updated_instances

        # The views that still have a key in current_keys are new, so they have no instance.
        # We try to create one for them
        for key in current_keys:
            if key:
                cls.ide_backend_instances[key] = cls.launch_instance(key, cls.settings)

        cls.view_mappings = current_hs_views


    @classmethod
    def is_running(cls, view):
        if not view:
            return False
        return cls.for_view(view) is not None


    @classmethod
    def for_view(cls, view):
        key = cls.view_mappings.get(view.id())
        instance = cls.ide_backend_instances.get(key)
        if instance and not instance.is_active:
            instance = None

        return instance

    @classmethod
    def kill_all(cls):
        for window in sublime.windows():
            if any(view.id() in cls.view_mappings for view in window.views()):
                Win(window).hide_error_panel()
        for instance in cls.ide_backend_instances.values():
            instance.end()

    @classmethod
    def reset(cls):
        """
        Kill all instances, and forget about previous notifications.
        """
        Log.normal("Resetting StackIDE")
        cls.kill_all()
        reset_complaints()

    @classmethod
    def configure(cls, settings):
        cls.settings = settings

    @classmethod
    def find_key_for_file_name(cls, file_name):
        return StackIDEInstanceKey.for_filename(file_name)

    @classmethod
    def launch_instance(cls, key, settings):
        Log.normal("Initializing instance for", key.cabal_file_dir)
        try:
            instance = StackIDE(key.cabal_file_dir, settings)
        except FileNotFoundError as e:
            instance = NoStackIDE("instance init failed -- stack not found")
            Log.error(e)
            complain('stack-not-found',
                "Could not find program 'stack'!\n\n"
                "Make sure that 'stack' and 'stack-ide' are both installed. "
                "If they are not on the system path, edit the 'add_to_PATH' "
                "setting in SublimeStackIDE  preferences." )
        except Exception:
            instance = NoStackIDE("instance init failed -- unknown error")
            Log.error("Failed to initialize instance for {}:".format(key.cabal_file_dir))
            Log.error(traceback.format_exc())

        return instance

class NoStackIDE:
    """
    Objects of this class are used for windows that don't have an associated stack-ide process
    (e.g., because initialization failed or they are not being monitored)
    """

    def __init__(self, reason):
        self.is_alive = True
        self.is_active = False
        self.reason = reason

    def end(self):
        self.is_alive = False

    def __str__(self):
        return 'NoStackIDE(' + self.reason + ')'
