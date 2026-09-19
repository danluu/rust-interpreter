#!/usr/bin/env python3
"""Select the authenticated runtime07 module for the unchanged ordinary std CLI."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
HERE = Path(__file__).resolve().parent
PLAN = HERE/'plan.json'
FROZEN = HERE/'inputs.json'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    path = Path(path)
    require(path.resolve(strict=True) == path and path.is_file() and not path.is_symlink(),
            'indirect std source/proof input')
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def invoke(std, factory, public, arguments):
    """Only argument transport and selected aliases; the ordinary main stays intact."""
    before = list(sys.argv)
    try:
        sys.argv[:] = [std.__file__, *arguments]
        with factory.aliases(public):
            return std.main()
    finally:
        sys.argv[:] = before


def main():
    parser = argparse.ArgumentParser(__doc__, allow_abbrev=False)
    parser.add_argument('--frozen-sha', required=True)
    args, ordinary = parser.parse_known_args()
    require(Path.cwd() == ROOT and sys.dont_write_bytecode and sys.flags.optimize == 0,
            'fixed owner and unoptimized Python -B required')
    require(sha(FROZEN) == args.frozen_sha, 'std source freeze differs')
    frozen = json.loads(FROZEN.read_bytes())
    def check_source(path):
        path = Path(path)
        digest = sha(path)
        require(frozen['files'].get(str(path)) == digest, 'unfrozen std source/proof: '+str(path))
        return digest
    def sources():
        require(sha(FROZEN) == args.frozen_sha, 'std source freeze changed')
        for path in frozen['files']:
            check_source(path)
        require(str(Path(sys.executable).resolve()) == frozen['python']['resolved']
                and sha(Path(sys.executable).resolve()) == frozen['python']['sha256'], 'std Python differs')
    sources()
    for path in (Path(__file__).resolve(), PLAN, HERE/'imports.py'):
        check_source(path)
    plan = json.loads(PLAN.read_bytes())
    require(dict(os.environ) == plan['environment'], 'std CLI passed/observed environment differs')
    spec = importlib.util.spec_from_file_location('_std07_cli_factory', HERE/'imports.py')
    factory = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = factory
    spec.loader.exec_module(factory)
    factory.validate_plan(plan, args.frozen_sha)
    require(ordinary == factory.ordinary_arguments(plan), 'ordinary std CLI arguments differ')
    factory.runtime_proof(plan, check_source)
    modules = factory.definitions(check_source)
    require(Path(modules.std.__file__).resolve() == ROOT/'scripts/std_mir_source_paths.py'
            and modules.std.ROOT == ROOT, 'ordinary std source/root changed')
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename and filename.startswith('/Users/danluu/dev/rust-interp'):
            check_source(Path(filename).resolve())
    try:
        return invoke(modules.std, factory, modules.public_aliases, ordinary)
    finally:
        sources()


if __name__ == '__main__':
    main()
