"""Place a side-by-side runner inside its existing provider owner's repository.

Only script paths/import metadata are inspected. This module never imports an
interpreter or provider, changes a provider root, or creates a file/directory.
"""
import importlib.util
from pathlib import Path
import sys

DIRECTORY = 'workflow-runtime-arms-01'
ENTRIES = ('bench_e2e_workflow.py', 'verify_repeated_workflow.py')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def routes(entry):
    entry = Path(entry)
    require(entry.is_absolute() and '..' not in entry.parts
            and entry.name in ENTRIES and entry.parent.name == DIRECTORY
            and entry.parent.parent.name == 'experiments',
            'runner must use its declared side-by-side experiment placement')
    owner = entry.parents[2]
    require(owner != Path('/'), 'invalid provider owner')
    return owner, entry.parent, owner/'scripts'


def check_module(name, expected_path, *, root=None):
    module = sys.modules.get(name)
    require(module is not None and getattr(module, '__file__', None) is not None,
            'selected source module is not loaded: '+name)
    require(Path(module.__file__) == expected_path
            and expected_path.resolve(strict=True) == expected_path,
            'selected source module differs: '+name)
    if root is not None:
        require(getattr(module, 'ROOT', None) == root,
                'selected source module has another provider owner: '+name)


def configure(entry_file):
    entry = Path(entry_file)
    require(entry.resolve(strict=True) == entry, 'runner path is indirect')
    owner, adjacent, scripts = routes(entry)
    require(scripts.resolve(strict=True) == scripts and scripts.is_dir(),
            'provider scripts directory is indirect or missing')
    own = adjacent/'workflow_placement.py'
    require(Path(__file__) == own and own.resolve(strict=True) == own,
            'placement helper is not adjacent to the selected runner')
    expected = dict(interpreter=scripts/'interpreter.py',
        bench_e2e_workflow=adjacent/'bench_e2e_workflow.py',
        workflow_runtime_arms=adjacent/'workflow_runtime_arms.py',
        workflow_placement=own)
    for name, path in expected.items():
        require(path.is_file() and path.resolve(strict=True) == path,
                'selected source route is missing or indirect: '+name)
        if name in sys.modules:
            check_module(name, path, root=owner if name == 'interpreter' else None)
    # The adjacent runner/helper must precede the original scripts. Remaining
    # standard-library paths keep their existing order; PYTHONPATH is not used.
    first = [str(adjacent), str(scripts)]
    sys.path[:] = first + [p for p in sys.path if p not in first]
    for name, path in expected.items():
        if name not in sys.modules:
            spec = importlib.util.find_spec(name)
            require(spec is not None and spec.origin == str(path),
                    'import search selects another source: '+name)
    return owner
