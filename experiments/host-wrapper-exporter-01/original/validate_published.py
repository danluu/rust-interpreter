#!/usr/bin/env python3
"""Run the ordinary installed-tool readers against the current runtime composition."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import stat
import sys

HERE = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-exporter-after-installation07-02')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
OPTIONS = ('stable-cgu-partitioning', 'compiler-argv-record-v1', 'function-cache-auto',
           'inline-leaves', 'trap-unsupported-calls', 'run-try-callbacks',
           'host-proc-macro-opt-v1', 'entry-catalog', 'list-tests')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def source(path, expected):
    path = Path(path)
    require(type(expected) is str and re.fullmatch('[0-9a-f]{64}', expected),
            'source SHA required')
    require(path.resolve(strict=True) == path, 'canonical source path required')
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= 32 * 2**20,
            'bounded ordinary source required')
    data = path.read_bytes()
    after = path.lstat()
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')
    require(all(getattr(before, n) == getattr(after, n) for n in fields)
            and len(data) == before.st_size and hashlib.sha256(data).hexdigest() == expected,
            'authenticated source changed: ' + str(path))
    return data


def load(name, path):
    require(name not in sys.modules, 'private reader module already exists')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def bootstrap(args):
    require(Path(__file__).resolve() == HERE / 'validate_published.py',
            'fixed installed-reader source path required')
    path = HERE / 'publication-sources.json'
    inventory = json.loads(source(path, args.publication_sources_sha256))
    require(type(inventory) is dict and set(inventory) == {'policy', 'frontend_sources', 'files'}
            and inventory['policy'] == 'runtime-exporter07-publication-sources-v1',
            'publication source declaration differs')
    front = HERE / 'frontend-sources.json'
    ref = inventory['frontend_sources']
    require(type(ref) is dict and set(ref) == {'path', 'sha256'} and ref['path'] == str(front),
            'fixed frontend source declaration required')
    selected = json.loads(source(front, ref['sha256']))
    require(type(selected) is dict and set(selected) == {'files'}
            and type(selected['files']) is dict and len(selected['files']) == 20,
            'complete frontend source selection required')
    files = inventory['files']
    extra = {str(HERE / name) for name in ('publish.py', 'validate_published.py')}
    extra |= {str(R / 'scripts' / name) for name in ('interpreter.py', 'workspace_cache.py')}
    require(type(files) is dict and len(files) == 25
            and set(files) == set(selected['files']) | extra | {str(front)}
            and files[str(front)] == ref['sha256']
            and all(files.get(name) == digest for name, digest in selected['files'].items()),
            'complete publication and ordinary reader closure required')
    # No local module executes until the complete selected source closure is checked.
    for name, digest in files.items():
        source(name, digest)
    common = load('_exporter07_installed_reader_common', HERE / 'common.py')
    require(common.HERE == HERE and common.R == R and args.runtime_compiler_key == common.KEY,
            'current reader root or runtime key differs')
    return common, common.modules(files), files


def main():
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == R,
            'ordinary installed reader requires Python -B and original R cwd')
    parser = argparse.ArgumentParser()
    for name in ('publication-sources-sha256', 'tool-key', 'runtime-compiler-key'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    for value in vars(args).values():
        require(re.fullmatch('[0-9a-f]{64}', value), 'exact SHA/key argument required')
    c, mods, files = bootstrap(args)
    cache = load('_exporter07_installed_reader_workspace_cache', R / 'scripts/workspace_cache.py')
    with c.aliases(mods.public | {'workspace_cache': cache}):
        interpreter = load('_exporter07_installed_reader_interpreter', R / 'scripts/interpreter.py')
        require(interpreter.ROOT == R, 'ordinary interpreter root changed')
        compiler = mods.runtime.load_runtime_compiler(R, args.runtime_compiler_key)
        directory, key = interpreter.installed_tools(args.tool_key)
        require(key == args.tool_key and directory == R / '.work/interpreter-tools' / key,
                'ordinary installed-tool directory differs')
        for option in OPTIONS:
            interpreter.require_export_option(directory, key, option)
        mods.tools.validate_tool_runtime(directory, key, compiler)
    source(HERE / 'publication-sources.json', args.publication_sources_sha256)
    for name, digest in files.items():
        source(name, digest)
    print(json.dumps(dict(status='passed', tool_key=key, runtime_key=compiler.key,
                          directory=str(directory)), sort_keys=True))


if __name__ == '__main__':
    main()
