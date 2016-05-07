import contextlib
from unittest.mock import Mock, patch
from . import fake_project_dir
from .data import exp_types_response, test_settings
import stack_ide
from stack_ide_manager import StackIDEInstanceKey, StackIDEManager

def patched_stack_ide_manager(additional_projects=None):
    known_projects = [fake_project_dir] + (additional_projects or [])
    keys_by_projects = {dir: StackIDEInstanceKey(dir, dir, 'a_component') for dir in known_projects}

    def fake_find_key_for_file_name(file_name):
        for dir, key in keys_by_projects.items():
            if file_name.startswith(dir):
                return key

    def fake_launch_instance(key, settings):
        return stack_ide.StackIDE(key.cabal_file_dir, test_settings, FakeBackend())

    def decorator(klass):
        patch_1 = patch('stack_ide_manager.StackIDEManager.find_key_for_file_name', new=fake_find_key_for_file_name)
        patch_2 = patch('stack_ide_manager.StackIDEManager.launch_instance', new=fake_launch_instance)
        return patch_1(patch_2(klass))

    return decorator

@contextlib.contextmanager
def responses_for(view, responses):
    """
    Overrides the responses the fake backend send to the given window
    """
    backend, previous = None, None
    stack_ide = StackIDEManager.for_view(view)
    if stack_ide:
        backend = stack_ide._backend

    if backend:
        previous = backend.responses
        backend.responses = dict(previous, **responses)

    yield

    if backend:
        backend.responses = previous

def add_seq(seq_id, contents):
    return dict(contents, seq=seq_id)

def make_response(seq_id, contents):
    return {'seq': seq_id, 'contents': contents}

class FakeBackend():
    """
    Fakes responses from the stack-ide process
    Override responses by passing in a dict keyed by tag
    """

    def __init__(self, responses={}):
        self.responses = responses
        if self.responses is None:
            raise Exception('stopthat!')

        self.handler = None
        self.send_request = Mock(wraps=self._send_request)

    def _send_request(self, req):

        if self.handler:
            self.return_test_data(req)

    def return_test_data(self, req):

        tag = req.get('tag')
        seq_id = req.get('seq')

        # overrides
        if self.responses is None:
            raise Exception('wtf!')
        override = self.responses.get(tag)
        if override:
            self.handler(add_seq(seq_id, override))
            return

        # default responses
        if tag == 'RequestUpdateSession':
            return
        if tag == 'RequestShutdownSession':
            return
        if tag == 'RequestGetSourceErrors':
            self.handler(make_response(seq_id, []))
            return
        if tag == 'RequestGetExpTypes':
            self.handler(add_seq(seq_id, exp_types_response))
            return
        else:
            raise Exception(tag)

    def fake_loadtargets_response(self, project_path, package):
        return ['app/Main.hs', 'src/Lib.hs']
