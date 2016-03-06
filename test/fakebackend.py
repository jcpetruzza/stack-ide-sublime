import contextlib
from unittest.mock import Mock, patch
from .data import exp_types_response, test_settings
import stack_ide
from stack_ide_manager import StackIDEManager

def patched_stack_ide_manager(klass):
    def fake_configure_instance(window, settings):
        return stack_ide.StackIDE(window, test_settings, FakeBackend())

    return patch('stack_ide_manager.StackIDEManager.configure_instance', new=fake_configure_instance)(klass)

@contextlib.contextmanager
def responses_for(window, responses):
    """
    Overrides the responses the fake backend send to the given window
    """
    backend, previous = None, None
    stack_ide = StackIDEManager.for_window(window)
    if stack_ide:
        backend = stack_ide._backend

    if backend:
        previous = backend.responses
        backend.responses = dict(previous, **responses)

    yield

    if backend:
        backend.responses = previous

def seq_response(seq_id, contents):
    contents['seq']= seq_id
    return contents


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
            self.handler(seq_response(seq_id, override))
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
            self.handler(seq_response(seq_id, exp_types_response))
            return
        else:
            raise Exception(tag)

    def fake_loadtargets_response(self, project_path, package):
        return ['app/Main.hs', 'src/Lib.hs']
