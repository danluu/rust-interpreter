"""Validate retained outcomes and fresh compilation without executing guests."""
import json
from pathlib import Path
from common import ROOT, SOURCE, read, sha
from model import KEY, TARGET, NAMES, CUSTOM, INSTRUCTIONS, ALLOCATIONS, native_outcomes
from suite_reports import read_report, validate_report, validate_runtime_limits
from test_discovery import read_selection
from workflow_controls import exporter_seconds


def expected_status(state, mode):
    return 0 if state != -1 or mode == 'check' else 1 if mode in CUSTOM else 101


def validate_options(launch):
    assert launch['tool_key'] == KEY and launch['engine'] == 'jit'
    for name in ['jit_resumable_calls', 'jit_persistent_registers', 'jit_scalar_calls',
                 'inline_leaves', 'trap_unsupported_calls', 'run_try_callbacks']:
        assert launch[name] is True, name
    for name in ['jit_indirect_calls', 'jit_native_calls', 'jit_native_call_stubs']:
        assert launch[name] is False, name
    assert launch['function_cache'] == 'auto' and launch['borrowck_cache'] == 'off'
    assert launch['host_proc_macro_opt'] == 'off'
    assert launch['toolchain_lookup']['mode'] == 'cached'
    assert launch['toolchain_lookup']['outcome'] in ['hit', 'miss']
    assert launch['isolated_batch'] == 'prepared'
    assert launch['suite_workers_requested'] == launch['suite_workers'] == 2
    assert launch['allocation_limit'] == ALLOCATIONS
    assert not any(k in launch for k in ['template_session', 'profile', 'custom_compiler'])


def fresh_native_units(stdout):
    """Native/check JSON must identify fresh production and integration units."""
    units = []
    for line in stdout.splitlines():
        if not line.startswith('{'):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get('reason') == 'compiler-artifact':
            units.append(row)
    for kind, name, suffix in [('lib', 'fre_kernels', 'src/lib.rs'),
                               ('test', TARGET, 'tests/'+TARGET+'.rs')]:
        row, = [u for u in units if u['target']['kind'] == [kind] and u['target']['name'] == name]
        assert row['fresh'] is False
        assert Path(row['target']['src_path']).resolve() == (SOURCE/'crates/fre-kernels'/suffix).resolve()
        if kind == 'test':
            assert row['profile']['test'] is True


def validate_row(row, raw):
    index, mode = row['index'], row['mode']
    success = row['state'] != -1
    assert row['returncode'] == expected_status(row['state'], mode)
    for stream in ['stdout', 'stderr']:
        assert sha(raw/(str(index)+'.'+stream)) == row[stream+'_sha256']
    out = (raw/(str(index)+'.stdout')).read_text()
    err = (raw/(str(index)+'.stderr')).read_text()
    assert ('Compiling ' if mode == 'native' else 'Checking ')+'fre-kernels' in err
    for field in ['artifact', 'catalog', 'selection', 'executable', 'call_report']:
        if field in row:
            p = ROOT/row[field]['path']
            assert p.is_relative_to(raw/'artifacts') and not p.is_symlink()
            assert sha(p) == row[field]['sha256']
    if mode in CUSTOM:
        launch, = [json.loads(line.split(': ', 1)[1]) for line in err.splitlines()
                   if line.startswith('rust-interp-launch: ')]
        assert launch == row['launch']
        validate_options(launch)
        assert sum(l.startswith('rust-interp-export: ') for l in err.splitlines()) == 1
        assert row['stages'] == exporter_seconds(err)
        suite, digest = read_report(raw/(str(index)+'-suite.json'), launch['suite_report_sha256'])
        assert digest == row['suite_sha256']
        outcomes = validate_report(suite, NAMES, 'prepared', success)
        validate_runtime_limits(suite, INSTRUCTIONS, ALLOCATIONS, required=True)
        assert suite['workers'] == suite['requested_workers'] == 2
        assert all(type(t['worker']) is int and 0 <= t['worker'] < 2 for t in suite['tests'])
        # The shared work queue can assign both short failing tests to one
        # worker. Record the actual assignments, without inventing a scheduler
        # guarantee that the two-worker implementation does not make.
        assert launch['runtime_limits'] == suite['runtime_limits']
        assert Path(launch['suite_report_path']) == raw/(str(index)+'-suite.json')
        assert row['artifact']['sha256'] == launch['artifact_sha256']
        assert row['catalog']['sha256'] == launch['entry_catalog_sha256']
        entries = read(ROOT/row['catalog']['path'])['entries']
        assert [e['name'] for e in entries] == NAMES
        assert [e['function'] for e in entries] == [t['function'] for t in suite['tests']]
        selection, digest = read_selection(ROOT/row['selection']['path'], ROOT/row['artifact']['path'], '', False)
        assert digest == launch['test_selection_sha256'] and selection['selected'] == NAMES
        assert selection['skipped_ignored'] == []
        assert row['outcomes'] == [list(x) for x in outcomes]
    else:
        assert 'rust-interp-launch: ' not in err and 'rust-interp-export: ' not in err
        fresh_native_units(out)
        if mode == 'native':
            assert row['outcomes'] == [list(x) for x in native_outcomes(out, success)]
        else:
            assert 'outcomes' not in row and 'test result:' not in out


def validate_group(group):
    assert len(group) == 4 and {r['mode'] for r in group} == {'native', 'custom', 'duplicate', 'check'}
    assert len({tuple(map(tuple, r['outcomes'])) for r in group if r['mode'] != 'check'}) == 1
    for field in ['artifact', 'catalog']:
        assert len({r[field]['sha256'] for r in group if r['mode'] in CUSTOM}) == 1
