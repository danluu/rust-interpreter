"""Render the two ordinary direct run-make commands; never execute them.

The Rust runner in fixtures/rmake.rs is the qualification implementation.
This file only applies explicit fresh output/compiler routes to the retained
successful recipe. Its output is not a prepared or qualified execution packet.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
OLD_NAMESPACE = X / '.work/hir-options-hash-compiler-01'
OLD_SOURCE = OLD_NAMESPACE / 'source'
NAMESPACE = X / '.work/hir-probe-single-walk-audit-compiler-01'
SOURCE = NAMESPACE / 'source'
BASE = NAMESPACE / 'run-make-01'
HOST = 'aarch64-apple-darwin'


def commands(historical):
    """Retain D2/support providers; select only the new audit E2 as test rustc."""
    assert historical['status'] == 'saved-passed-route-only'
    rows = copy.deepcopy(historical['children'])
    assert len(rows) == 2
    compile_row, run_row = rows
    assert compile_row['argv'][0] == str(OLD_SOURCE / 'build' / HOST / 'stage0/bin/rustc')
    assert run_row['argv'] == [str(OLD_NAMESPACE / 'run-make-01/rmake')]
    assert compile_row['argv'].count(str(OLD_SOURCE / 'tests/run-make/hir-body-cache-capture/rmake.rs')) == 1
    assert compile_row['argv'][1:3] == ['-o', str(OLD_NAMESPACE / 'run-make-01/rmake')]
    compile_row['argv'][2] = str(BASE / 'rmake')
    compile_row['argv'] = [str(HERE / 'fixtures/rmake.rs') if value ==
        str(OLD_SOURCE / 'tests/run-make/hir-body-cache-capture/rmake.rs') else value
        for value in compile_row['argv']]
    compile_row['cwd'] = str(SOURCE)
    run_row['argv'] = [str(BASE / 'rmake')]
    run_row['cwd'] = str(BASE / 'rmake_out')
    for row in rows:
        env = row['environment']
        assert env['TARGET'] == HOST and env['CARGO_BUILD_JOBS'] == '2'
        assert env['SOURCE_ROOT'] == str(OLD_SOURCE)
        assert env['BUILD_ROOT'] == str(OLD_SOURCE / 'build' / HOST)
        assert env['TMPDIR'] == str(OLD_NAMESPACE / 'run-make-01/tmp')
        assert env['RUST_TEST_TMPDIR'] == str(OLD_SOURCE / 'build/tmp')
        assert env['CARGO_HOME'] == str(OLD_NAMESPACE / 'cargo-home')
        env.update(SOURCE_ROOT=str(SOURCE), BUILD_ROOT=str(SOURCE / 'build' / HOST),
            TMPDIR=str(BASE / 'tmp'), RUST_TEST_TMPDIR=str(SOURCE / 'build/tmp'),
            CARGO_HOME=str(NAMESPACE / 'cargo-home'))
    audit_e2 = SOURCE / 'build' / HOST / 'stage1'
    run_row['environment'].update(RUSTC=str(audit_e2 / 'bin/rustc'),
        HOST_RUSTC_DYLIB_PATH=str(audit_e2 / 'lib'),
        TARGET_EXE_DYLIB_PATH=str(audit_e2 / 'lib/rustlib' / HOST / 'lib'))
    assert compile_row['environment']['RUSTC_BOOTSTRAP'] == '-1'
    assert run_row['environment']['RUSTC_BOOTSTRAP'] == '1'
    assert run_row['environment']['RUSTC_FORCE_RUSTC_VERSION'] == 'compiletest'
    assert run_row['environment']['__RMAKE_VERBOSE_SUBPROCESS_OUTPUT'] == '1'
    # No global loader tracing: info-off JSON diagnostics must stay lossless.
    assert not any(key.startswith('DYLD_') and key != 'DYLD_LIBRARY_PATH'
        for row in rows for key in row['environment'])
    return rows


def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    manifest = json.loads((HERE / 'manifest.json').read_bytes())
    # Authenticate every local source/fixture before rendering the recipe.
    for name, row in manifest['files'].items():
        path = HERE / name
        assert not path.is_symlink()
        data = path.read_bytes()
        assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
    original = json.loads((HERE / 'historical-recipe.json').read_bytes())
    comparison = json.loads((HERE / 'source-comparison.json').read_bytes())
    print(json.dumps(dict(status='source-only-unbound-unrun', timing_eligible=False,
        compiler_source_identity=comparison['source_identity'],
        actual_compiler_build=None, actual_native_compiler_identity=None,
        actual_current_provider_closure=None, actual_qualification=None,
        children=commands(original),
        copies_before_compile={name: str(HERE / 'fixtures' / name)
            for name in comparison['fixtures'] if name != 'rmake.rs'},
        copy_destination=str(BASE / 'rmake_out'),
        source_derived_nested_schedule=dict(commands=309, compiler_calls=188,
            native_runs=121, expected_compiler_failures=48, inherited_commands=230),
        prerequisite='Bind the actual closed audit build and current D2/support/audit-E2 identities; prepare with the existing bounded direct-run-make monitor before execution.'),
        sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
