"""Isolated definitions-only imports for candidate runtime stages.

Every directly selected source is checked before loading; the enclosing complete
freeze guards the transitive hash-stage imports before calling its dependencies.
No module constructor, prepare/main, compiler, probe or workload is invoked.
"""
from contextlib import contextmanager
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
QUALIFIED = HERE.with_name('runtime-installation-01')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')


@contextmanager
def aliases(values):
    missing = object()
    before = {name:sys.modules.get(name, missing) for name in values}
    path = list(sys.path)
    sys.modules.update(values)
    try:
        yield
    finally:
        sys.path[:] = path
        for name,value in before.items():
            if value is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def load(name, path, check_source, dependencies=None):
    path = Path(path)
    check_source(path)
    full = '_runtime_options_02_'+name
    if full in sys.modules:
        value = sys.modules[full]
        if Path(value.__file__).resolve(strict=True) != path:
            raise RuntimeError('private runtime import route changed')
        return value
    spec = importlib.util.spec_from_file_location(full, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[full] = value
    try:
        with aliases(dependencies or {}):
            spec.loader.exec_module(value)
    except BaseException:
        sys.modules.pop(full, None)
        raise
    return value


def definitions(hash_source, check_source):
    """Caller has already validated the actual hash audit and full source freeze."""
    stage = load('hash_stage', Path(hash_source)/'stage.py', check_source)
    binding_path = Path(hash_source)/'snapshot_bindings.py'
    check_source(binding_path)
    modules = stage.dependencies()
    if ('snapshot_bindings' not in modules
            or Path(modules['snapshot_bindings'].__file__).resolve(strict=True) != binding_path.resolve(strict=True)):
        raise RuntimeError('hash v2 snapshot binding module route differs')
    check_source(binding_path)
    collector = load('hash_discovery', Path(hash_source)/'prepare.py', check_source, {'stage':stage})
    scripts = R/'scripts'
    public = {}
    for name in ['custom_compiler','workflow_io','std_mir','compare_saved_runtime','toolchain_lookup',
                 'runtime_compiler','std_mir_source_paths','verified_std_diagnostics']:
        public[name] = load('r_'+name, scripts/(name+'.py'), check_source, public)
    q = load('source_qualification', R/'experiments/runtime-compiler-installation/source_qualification.py',
             check_source, public)
    own = {'prerequisites':load('prerequisites', HERE/'prerequisites.py', check_source)}
    own.update({name:load(name, QUALIFIED/(name+'.py'), check_source)
                for name in ['recipe','discovery','controller']})
    monitor = load('private_monitor', QUALIFIED/'monitor.py', check_source, {'owned_stage':modules['monitor'].owned})
    if monitor is modules['monitor']:
        raise RuntimeError('runtime monitor is not an isolated module instance')
    return SimpleNamespace(stage=stage, hash_modules=modules, collector=collector,
                           q=q, public_aliases=public, monitor=monitor, **own)
