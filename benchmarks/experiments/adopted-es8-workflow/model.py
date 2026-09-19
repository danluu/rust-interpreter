"""Explicit integration-target commands and complete-edit accounting."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('retained_integration_edits', ROOT / 'benchmarks/experiments/test-targets/edit.py')
edits = importlib.util.module_from_spec(spec)
spec.loader.exec_module(edits)

KEY = 'df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
TARGET = 'es8i_semantic_proof'
NAMES = ['every_position_differential_covers_all_edges_and_suffix_borders',
         'seeded_long_random_and_window_differential_is_stable']
MODES = ['native', 'custom', 'duplicate', 'check']
CUSTOM = {'custom', 'duplicate'}
FLAGS = ['-Zmir-opt-level=3', '-Zinline-mir-threshold=400', '-Zinline-mir-hint-threshold=800', '-Zinline-mir-forwarder-threshold=240']
INSTRUCTIONS = 100_000_000_000
ALLOCATIONS = 150_000


def states(original):
    return [*edits.es8_edits(original), ('restored', 'restored-original', original)]


def schedule(original):
    result = []
    for state, label, payload in states(original):
        for mode in edits.integration_order(MODES, 6 if state == 'restored' else state):
            result.append(dict(state=state, label=label, mode=mode, source_sha256=hashlib.sha256(payload).hexdigest()))
    assert len(result) == 32
    return result


def command(source, raw, index, mode, namespace=None):
    assert mode in MODES
    if mode not in CUSTOM:
        result = ['cargo', '+nightly-2026-09-08', 'check' if mode == 'check' else 'test',
            '--manifest-path', source / 'Cargo.toml', '--package', 'fre-kernels', '--test', TARGET,
            '--locked', '--offline', '--jobs', '2', '--target-dir', raw / mode, '--message-format=json']
        if mode == 'check':
            result += ['--profile', 'test']
        else:
            result += ['--', '--exact', '--test-threads=2', *NAMES]
    else:
        result = [sys.executable, ROOT / 'scripts/interpreter.py', '--manifest-path', source / 'Cargo.toml',
            '--package', 'fre-kernels', '--test-body', '--test-target', TARGET, '--test-filter', '',
            '--jobs', '2', '--tool-key', KEY, '--cache-namespace', namespace or raw.name+':'+mode,
            '--std-mir', '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
            '--jit-scalar-calls', '--inline-leaves', '--trap-unsupported-calls', '--run-try-callbacks',
            '--instruction-limit', str(INSTRUCTIONS), '--allocation-limit', str(ALLOCATIONS),
            '--isolated-batch', 'prepared', '--suite-workers', '2', '--suite-report', raw / (str(index)+'-suite.json'),
            '--function-cache', 'auto', '--toolchain-lookup', 'cached']
    return list(map(str, result))


def native_outcomes(stdout, success):
    found = re.findall(r'^test (.+) \.\.\. (ok|FAILED|ignored)$', stdout, re.M)
    assert len(found) == len(NAMES) and set(dict(found)) == set(NAMES)
    assert all(s != 'ignored' for _,s in found)
    failures = sum(s == 'FAILED' for _,s in found)
    summary = re.findall(r'test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;', stdout)
    assert summary == [('ok' if success else 'FAILED', str(len(NAMES)-failures), str(failures), '0')]
    assert (failures == 0) == success
    return [(name, 'passed' if dict(found)[name] == 'ok' else 'failed') for name in NAMES]


def native_executable(stdout, source, target):
    matches = []
    for line in stdout.splitlines():
        if not line.startswith('{'):
            continue
        try:
            unit = json.loads(line)
        except json.JSONDecodeError:
            continue
        if unit.get('reason') != 'compiler-artifact' or not unit.get('profile',{}).get('test') or not unit.get('executable'):
            continue
        if unit['target']['kind'] != ['test'] or unit['target']['name'] != TARGET:
            continue
        assert Path(unit['target']['src_path']).resolve() == (source / 'crates/fre-kernels/tests' / (TARGET+'.rs')).resolve()
        executable = Path(unit['executable']).resolve(strict=True)
        assert executable.is_relative_to(target.resolve())
        matches.append(executable)
    assert len(matches) == 1, 'missing or ambiguous original integration executable'
    return matches[0]


def accounting(records):
    assert len(records) == 32
    keyed = {(r['state'],r['mode']):r for r in records}
    assert len(keyed) == 32 and set(keyed) == {(state, mode) for state in [0,-1,1,2,3,4,5,'restored'] for mode in MODES}
    pairs = []
    for state in range(1,6):
        rows = {mode:keyed[state,mode] for mode in MODES}
        pair = dict(state=state)
        for field in ['wall_seconds','cpu_seconds']:
            assert all(r[field] > 0 for r in rows.values())
            pair[field] = dict(custom_native=rows['custom'][field]/rows['native'][field],
                custom_check=rows['custom'][field]/rows['check'][field],
                duplicate_custom=rows['duplicate'][field]/rows['custom'][field])
        pairs.append(pair)
    totals = {mode:{field:sum(r[field] for r in records if r['mode']==mode)
                   for field in ['wall_seconds','cpu_seconds']} for mode in MODES}
    return dict(pairs=pairs, medians={field:{ratio:statistics.median(p[field][ratio] for p in pairs)
        for ratio in ['custom_native','custom_check','duplicate_custom']} for field in ['wall_seconds','cpu_seconds']},
        aa_envelope={field:max(abs(p[field]['duplicate_custom']-1) for p in pairs)
                     for field in ['wall_seconds','cpu_seconds']}, all_commands_totals=totals,
        candidate=False, adoption=False, edited_pairs=5)
