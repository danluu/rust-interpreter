"""Refresh whole-process counters for two unchanged original assertions."""
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/cross-program-template-model'))
import focus
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write

KEY = 'df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
BASE = 'fca687ebac0ea9374a1426addd01169fe707f608'
CONTROL = 'adopted-process-counter-controls-01'
MEASURE = 'adopted-process-counters-01'
NAMES = [
    'token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart',
    'token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex',
]
read = focus.read


def inputs(stage):
    frozen = {}

    def bind(path, expected=None):
        digest = sha(path)
        if expected is not None:
            assert digest == expected, path
        frozen[str(path.relative_to(ROOT))] = digest
        return read(path) if path.suffix == '.json' else digest

    launcher = ROOT / '.work/process-instruction-counts-01/launch'
    source = ROOT / 'benchmarks/experiments/process-instruction-counts/launch.c'
    old = launcher.parent
    plan = bind(old / 'plan.json')
    previous = bind(old / 'frozen.json')
    build = bind(old / 'compile.json')
    assert plan['owner'] == str(ROOT) and build['returncode'] == 0
    assert build['command'] == ['xcrun', 'clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(launcher)]
    bind(source, '9060a3a0cb5c3ffb856b370decc30fa4b2dfb26208f049f5904515c5edb49345')
    bind(launcher, 'da3ed153ae68e1869ef2ca93c99c4755b9b4f00fb47cfa02b7d0900659f843ed')
    assert previous[str(source)] == plan['frozen'][str(source)] == sha(source)
    assert previous[str(launcher)] == sha(launcher)
    committed = subprocess.check_output(['git', 'show', plan['source_commit'] + ':' + str(source.relative_to(ROOT))], cwd=ROOT)
    assert hashlib.sha256(committed).hexdigest() == sha(source)
    cases = []
    if stage == 'controls':
        for label, args, code in [('probe-small', ['--spin', '200000'], 0),
                                  ('probe-large', ['--spin', '2000000'], 0),
                                  ('probe-exit', ['--exit-seven'], 7)]:
            cases.append(dict(label=label, command=[str(launcher), *args], expected_exit=code))
    else:
        control = ROOT / 'results' / CONTROL
        closure = bind(control / 'closure.json')
        assert closure['status'] == 'closed' and closure['all_hashes_verified']
        summary = bind(control / 'summary.json', closure['summary_sha256'])
        terminal = bind(control / 'terminal.json', closure['terminal_sha256'])
        assert summary['status'] == 'passed' and summary['commands'] == 3 and terminal['returncode'] == 0
        evidence = bind(ROOT / closure['evidence'], closure['evidence_sha256'])
        for p, h in evidence.items():
            bind(ROOT / p, h)
        prior = ROOT / 'results/heap-layout-screen-token-01'
        closed = bind(prior / 'closure.json')
        assert closed['status'] == 'closed' and closed['all_hashes_verified']
        screen = bind(prior / 'summary.json', closed['summary_sha256'])
        terminal = bind(prior / 'terminal.json', closed['terminal_sha256'])
        assert screen['status'] == 'passed' and screen['source_restored'] and terminal['returncode'] == 0
        raw = ROOT / screen['raw']
        plan = bind(raw / 'plan.json', screen['plan_sha256'])
        records = bind(raw / 'records.json', screen['records_sha256'])
        native, jit = records[38:40]
        assert native['mode'] == 'native' and jit['mode'] == 'baseline'
        assert native['state'] == jit['state'] == 0 and native['cycle'] == jit['cycle'] == 1
        assert native['source_sha256'] == jit['source_sha256'] == plan['original_source_sha256']
        assert native['returncode'] == jit['returncode'] == 0
        assert screen['tool_keys']['baseline'] == KEY
        executable, artifact, catalog = [ROOT / r['path'] for r in [native['executable'], jit['artifact'], jit['catalog']]]
        for p, r in zip([executable, artifact, catalog], [native['executable'], jit['artifact'], jit['catalog']]):
            bind(p, r['sha256'])
        qualified = ROOT / 'results/scratch-scalar-main-qualification-01'
        closed = bind(qualified / 'closure.json')
        assert closed['status'] == 'closed' and closed['all_frozen_inputs_verified']
        tool = bind(qualified / 'summary.json', closed['summary_sha256'])
        bind(qualified / 'terminal.json', closed['terminal_sha256'])
        assert tool['status'] == 'passed' and tool['tool_key'] == KEY
        vm = ROOT / '.work/interpreter-tools' / KEY / 'rust-interp-vm'
        bind(vm, tool['binaries']['rust-interp-vm'])
        for index, name in enumerate(NAMES):
            selected, = [e for e in read(catalog)['entries'] if e['name'] == name]
            commands = {
                'native': [str(executable), '--exact', name, '--test-threads=1'],
                'jit': [str(vm), '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                        '--jit-scalar-calls', '--select-test', name, '--suite-catalog', str(catalog),
                        '--instruction-limit', str(plan['reference']['instruction_limit']),
                        '--allocation-limit', str(plan['reference']['allocation_limit']), str(artifact)],
            }
            for pair in range(3):
                for mode in (['native', 'jit'] if (index + pair) % 2 == 0 else ['jit', 'native']):
                    cases.append(dict(label=f'{index}-{pair}-{mode}', command=commands[mode], expected_exit=0,
                        name=name, pair=pair, mode=mode, function=selected['function'],
                        artifact_sha256=sha(artifact), catalog_sha256=sha(catalog)))
    assert not subprocess.check_output(['git', 'diff', '--name-only', BASE, '--', 'crates'], cwd=ROOT).strip()
    for path in [*HERE.glob('*.py'), *HERE.glob('*.md'), Path(focus.__file__),
                 *[ROOT / 'scripts' / p for p in ['compare_saved_runtime.py', 'workflow_io.py', 'supervise_experiment.py']]]:
        bind(path)
    return frozen, launcher, cases


def validate(raw, row, spec):
    assert row['label'] == spec['label'] and row['returncode'] == 0
    counts = read(raw / (row['label'] + '.counts.json'))
    identity = read(raw / (row['label'] + '.identity.json'))
    assert counts == row['counts'] and counts['parent_pid'] == identity['parent_pid'] == row['pid']
    assert counts['pid'] == identity['pid'] == counts['waitid_pid'] == counts['reaped_pid'] > 0
    assert counts['waitid_code'] == 1  # CLD_EXITED, also verified by the exit-seven control.
    receipt = read(raw / (row['label'] + '.active.json'))
    assert receipt['pid'] == row['pid'] and receipt['command'] == row['command']
    assert receipt['cwd'] == str(ROOT) and receipt['status'] == 'finished' and receipt['returncode'] == 0
    assert all(counts[k] == 0 for k in ['wait_error', 'query_error', 'second_query_error', 'signal'])
    assert counts['exit_code'] == counts['waitid_status'] == spec['expected_exit']
    assert counts['stable_after_exit'] and 0 < counts['start_abstime'] < counts['exit_abstime']
    assert counts['instructions'] > 0 and counts['cycles'] > 0
    out = (raw / (row['label'] + '.stdout')).read_text()
    err = (raw / (row['label'] + '.stderr')).read_text()
    if spec.get('mode') == 'native':
        assert re.findall(r'^test (.+) \.\.\. ok$', out, re.M) == [spec['name']]
        assert 'test result: ok. 1 passed; 0 failed; 0 ignored;' in out
    elif spec.get('mode') == 'jit':
        assert out == '0\n'
        selection, = re.findall(r'^rust-interp-test-selection: (.+)$', err, re.M)
        selection = json.loads(selection)
        for k in ['name', 'function', 'artifact_sha256', 'catalog_sha256']:
            assert selection[k] == spec[k], (k, selection)
    elif spec['label'] == 'probe-exit':
        assert out == err == ''
    else:
        assert re.fullmatch(r'\d+\n', out) and err == ''


def derive(stage, rows, cases):
    assert len(rows) == len(cases)
    if stage == 'controls':
        assert rows[1]['counts']['instructions'] > rows[0]['counts']['instructions']
        return dict(larger_spin_retires_more=True, intentional_exit_seven_preserved=True)
    result = []
    for name in NAMES:
        pairs = []
        for pair in range(3):
            a, b = [next(r['counts'] for r, s in zip(rows, cases)
                         if s.get('name') == name and s.get('pair') == pair and s.get('mode') == mode)
                    for mode in ['native', 'jit']]
            pairs.append(dict(pair=pair, instruction_ratio=b['instructions'] / a['instructions'],
                cycle_ratio=b['cycles'] / a['cycles'], native_cycles_per_instruction=a['cycles'] / a['instructions'],
                jit_cycles_per_instruction=b['cycles'] / b['instructions']))
        ratios = {k: dict(median=statistics.median(p[k] for p in pairs), minimum=min(p[k] for p in pairs),
                          maximum=max(p[k] for p in pairs)) for k in ['instruction_ratio', 'cycle_ratio']}
        result.append(dict(name=name, pairs=pairs, ratios=ratios))
    return dict(cases=result)


def main(stage):
    run = CONTROL if stage == 'controls' else MEASURE
    frozen, launcher, cases = inputs(stage)
    assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT).strip()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    raw = ROOT / '.work' / run
    raw.mkdir(exist_ok=False)
    rows = []
    write(raw / 'records.json', rows)
    write(raw / 'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
        controller_command=[sys.executable, *sys.orig_argv[1:]], expected_commands=len(cases), cases=cases,
        original_project_guest_commands=12 if stage == 'measure' else 0,
        performance_measurement=False, source_builds=0, tool_key=KEY, stage=stage))
    env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
    env.pop('RUST_TEST_THREADS', None)
    assert not any(k.startswith('DYLD_') for k in env)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        for spec in cases:
            require_space(ROOT, 8)
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            label = spec['label']
            counts, identity, out, err = [raw / (label + '.' + s) for s in ['counts.json', 'identity.json', 'stdout', 'stderr']]
            command = [str(launcher), str(counts), str(identity), str(out), str(err), '--', *spec['command']]
            start = time.time()
            child, stdout, stderr = capture(command, cwd=ROOT, env=env,
                receipt_path=raw / (label + '.active.json'), receipt=dict(stage=stage, label=label))
            (raw / (label + '.launcher.stdout')).write_text(stdout)
            (raw / (label + '.launcher.stderr')).write_text(stderr)
            row = dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
                seconds=time.time() - start, counts=read(counts) if counts.exists() and counts.stat().st_size else None)
            # Preserve every completed child before outcome/counter validation.
            row['outputs'] = {str(p.relative_to(ROOT)): sha(p) for p in raw.glob(label + '.*')}
            for stream in ['stdout', 'stderr']:
                path = raw / (label + '.' + stream)
                row[stream + '_sha256'] = sha(path) if path.exists() else None
            rows.append(row)
            write(raw / 'records.json', rows)
            validate(raw, row, spec)
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            print(label, row['counts']['instructions'], row['counts']['cycles'], flush=True)
        derived = derive(stage, rows, cases)
        output = ROOT / 'results' / run
        output.mkdir(exist_ok=False)
        write(output / 'summary.json', dict(status='passed', source_revision=revision, raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw / 'plan.json'), records_sha256=sha(raw / 'records.json'), commands=len(rows),
            original_project_guest_commands=12 if stage == 'measure' else 0, source_builds=0,
            tool_key=KEY, whole_process_counts=True, pure_guest_counts=False, ordinary_os_entropy=True,
            performance_measurement=False, default_runtime_adoption=False, derived=derived))


def close(stage):
    run = CONTROL if stage == 'controls' else MEASURE
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        raw = ROOT / '.work' / run
        terminal = read(ROOT / '.work/experiments' / run / 'status.json')
        if terminal['returncode'] == 0:
            frozen, launcher, cases = inputs(stage)
            plan = read(raw / 'plan.json')
            assert frozen == plan['frozen'] and cases == plan['cases']
            rows = read(raw / 'records.json')
            for row, spec in zip(rows, cases):
                assert row['command'] == [str(launcher), *[str(raw / (row['label'] + '.' + s))
                    for s in ['counts.json', 'identity.json', 'stdout', 'stderr']], '--', *spec['command']]
                validate(raw, row, spec)
            assert derive(stage, rows, cases) == read(ROOT / 'results' / run / 'summary.json')['derived']
    focus.RUN = run
    focus.close()


if __name__ == '__main__':
    assert sys.argv[1:2] in [['controls'], ['measure']]
    stage = sys.argv[1]
    if sys.argv[2:] == ['--close']:
        close(stage)
    else:
        assert len(sys.argv) == 2
        main(stage)
