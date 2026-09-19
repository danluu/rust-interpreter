"""Isolated imports for this unrun successor and downstream read-only users.

Call load_bundle() after loading this file with importlib under any private
name. No compiler, recipe, preparer, or process runs during these imports.
Generic dependency aliases are restored, including on an import exception.
"""
from contextlib import contextmanager
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

HERE = Path(__file__).resolve().parent
PACKAGE = '_hir_options_run_make_stage_02'
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')


def package():
    if PACKAGE not in sys.modules:
        module = ModuleType(PACKAGE)
        module.__path__ = [str(HERE)]
        module.__package__ = PACKAGE
        sys.modules[PACKAGE] = module
    assert sys.modules[PACKAGE].__path__ == [str(HERE)]
    return PACKAGE


@contextmanager
def aliases(values):
    missing = object()
    before = {name: sys.modules.get(name, missing) for name in values}
    path = list(sys.path)
    sys.modules.update(values)
    try:
        yield
    finally:
        sys.path[:] = path
        for name, value in before.items():
            if value is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def external(name, path, dependencies=None):
    path = Path(path)
    assert path.resolve(strict=True) == path and path.is_file()
    full = package() + '.' + name
    if full in sys.modules:
        result = sys.modules[full]
        assert Path(result.__file__).resolve(strict=True) == path
        return result
    spec = importlib.util.spec_from_file_location(full, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[full] = result
    try:
        with aliases(dependencies or {}):
            spec.loader.exec_module(result)
    except BaseException:
        sys.modules.pop(full, None)
        raise
    return result


def load(name):
    assert name in {'support', 'loader', 'history', 'prerequisite', 'bounded_recipe'}
    return external(name, HERE / (name + '.py'))


def monitor():
    owned = external('x_owned', X / 'experiments/stable-cgu/owned_stage.py')
    return external('shared_monitor', A / 'experiments/hir-options-hash-stage-monitor/monitor.py',
                    {'owned_stage': owned})


def metadata():
    association = external('compiler_association', X / 'scripts/compiler_association.py')
    custom = external('custom_compiler', X / 'scripts/custom_compiler.py',
                      {'compiler_association': association})
    lookup = external('toolchain_lookup', X / 'scripts/toolchain_lookup.py')
    libraries = external('custom_cargo_libraries', X / 'scripts/custom_cargo_libraries.py',
                         {'custom_compiler': custom, 'toolchain_lookup': lookup})
    directory = X / 'experiments/hir-options-hash/compiler-metadata-03'
    parser = external('linker_parser', directory / 'linker_parser.py')
    return external('metadata', directory / 'metadata.py',
                    {'owned_stage': monitor().owned, 'custom_cargo_libraries': libraries,
                     'linker_parser': parser})


def compiler_history():
    directory = A / 'experiments/hir-options-hash-beta-composition-04'
    primitives = external('composition_primitives', directory / 'compose_sysroot.py')
    return external('compiler_history', directory / 'history.py',
                    {'compose_sysroot': primitives})


def support_modules():
    directory = X / 'experiments/hir-options-hash/compiler-build-continuation-03'
    return SimpleNamespace(**{name: external('support_' + name, directory / filename)
        for name, filename in [('source', 'support_source.py'), ('producer', 'support_producer.py'),
                               ('timing', 'timing_context.py'), ('parsers', 'producer_parsers.py')]})


def load_bundle():
    return SimpleNamespace(support=load('support'), loader=load('loader'),
                           history=load('history'), prerequisite=load('prerequisite'))
