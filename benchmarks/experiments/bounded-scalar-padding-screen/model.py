"""Explicit integration-target commands and complete-edit accounting."""
import hashlib
import importlib.util
import json
import math
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
CANDIDATE = 'd4aba7b8bc4433ba8201c8a01c0d967dccf15d1e91b557fc77ba6364c4d63f57'
TARGET = 'es8i_semantic_proof'
NAMES = ['every_position_differential_covers_all_edges_and_suffix_borders',
         'seeded_long_random_and_window_differential_is_stable']
MODES = ['native', 'custom', 'duplicate', 'candidate', 'check']
CUSTOM = {'custom', 'duplicate', 'candidate'}
FLAGS = ['-Zmir-opt-level=3', '-Zinline-mir-threshold=400', '-Zinline-mir-hint-threshold=800', '-Zinline-mir-forwarder-threshold=240']
INSTRUCTIONS = 100_000_000_000
ALLOCATIONS = 150_000


def states(original):
    return [*edits.es8_edits(original), ('restored', 'restored-original', original)]


def schedule(original):
    result = []
    for state, label, payload in states(original):
        # Five cyclic rows put every mode in every position across the five edits.
        offset = state-1 if isinstance(state,int) and state > 0 else 0
        order = MODES[offset:]+MODES[:offset]
        if state == -1 or state == 'restored': order = list(reversed(order))
        for mode in order:
            result.append(dict(state=state, label=label, mode=mode, source_sha256=hashlib.sha256(payload).hexdigest()))
    assert len(result) == 40
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
            '--jobs', '2', '--tool-key', CANDIDATE if mode == 'candidate' else KEY, '--cache-namespace', namespace or raw.name+':'+mode,
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
    assert len(records) == 40
    keyed = {(r['state'],r['mode']):r for r in records}
    assert len(keyed) == 40 and set(keyed) == {(state, mode) for state in [0,-1,1,2,3,4,5,'restored'] for mode in MODES}
    pairs = []
    for state in range(1,6):
        rows = {mode:keyed[state,mode] for mode in MODES}
        pair = dict(state=state)
        for field in ['wall_seconds','cpu_seconds']:
            assert all(type(r[field]) in [int,float] and math.isfinite(r[field]) and r[field] > 0 for r in rows.values())
            pair[field] = dict(candidate_baseline=rows['candidate'][field]/rows['custom'][field],
                candidate_native=rows['candidate'][field]/rows['native'][field],
                candidate_check=rows['candidate'][field]/rows['check'][field], custom_native=rows['custom'][field]/rows['native'][field],
                custom_check=rows['custom'][field]/rows['check'][field],
                duplicate_custom=rows['duplicate'][field]/rows['custom'][field])
        pairs.append(pair)
    totals = {mode:{field:sum(r[field] for r in records if r['mode']==mode)
                   for field in ['wall_seconds','cpu_seconds']} for mode in MODES}
    medians = {field:{ratio:statistics.median(p[field][ratio] for p in pairs)
        for ratio in ['candidate_baseline','candidate_native','candidate_check','custom_native','custom_check','duplicate_custom']}
        for field in ['wall_seconds','cpu_seconds']}
    envelope = {field:max(abs(p[field]['duplicate_custom']-1) for p in pairs) for field in ['wall_seconds','cpu_seconds']}
    wall,cpu = medians['wall_seconds']['candidate_baseline'],medians['cpu_seconds']['candidate_baseline']
    passed = wall <= .99 and wall+envelope['wall_seconds'] < 1 and cpu <= 1+envelope['cpu_seconds']
    return dict(pairs=pairs,medians=medians,aa_envelope=envelope,all_commands_totals=totals,
        minimum_wall_gain=.01,wall_rule='ratio <= .99 and ratio + full absolute A/A envelope < 1',cpu_rule='ratio <= 1 + full absolute A/A envelope',
        gate_passed=passed,verdict='passed' if passed else ('unmeasurable' if max(envelope.values()) > .08 else 'failed'),
        candidate=True,adoption=False,edited_pairs=5)
