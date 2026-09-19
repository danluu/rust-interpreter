"""Join conservative dead-definition scope to retained current native samples."""
from array import array
from collections import Counter
import gc
import os
from pathlib import Path
import re
import subprocess
import sys
from model import analyze_span, direct_target, words

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/cross-program-template-model'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/scalar-runtime-sampling'))
import focus
import attribute
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write
from summarize_owned_sample import parse_tree, self_samples
from native_observation import validate, locate

RUN = 'ordinary-dead-scratch-01'
BASE = 'fca687ebac0ea9374a1426addd01169fe707f608'
read = focus.read


def inputs():
    frozen = {}

    def bind(path, expected=None, load=True):
        digest = sha(path)
        if expected is not None:
            assert digest == expected, path
        frozen[str(path.relative_to(ROOT))] = digest
        return read(path) if load and path.suffix == '.json' else digest

    prior = ROOT / 'results/scalar-word-census-03'
    closure = bind(prior / 'closure.json')
    assert closure['status'] == 'passed' and closure['all_frozen_inputs_verified']
    plan = bind(ROOT / closure['raw'] / 'plan.json', closure['plan_sha256'])
    for p in [Path(words.__file__), Path(words.__file__).with_name('test_words.py')]:
        bind(p, plan['frozen'][str(p.relative_to(ROOT))])
    prior = ROOT / 'results/adopted-current-runtime-sampling-02'
    closure = bind(prior / 'closure.json')
    assert closure['status'] == 'closed' and closure['all_hashes_verified']
    summary = bind(prior / 'summary.json', closure['summary_sha256'])
    terminal = bind(prior / 'terminal.json', closure['terminal_sha256'])
    assert summary['status'] == 'passed' and summary['ordinary_entropy'] and terminal['returncode'] == 0
    cases = []
    for case in summary['cases']:
        report = bind(ROOT / case['report'], case['report_sha256'])
        assert report['unassigned_generated_samples'] == 0
        for p, h in report['evidence'].items():
            bind(ROOT / p, h, load=False)
        profiles = [p for p in report['evidence'] if p.endswith('-profile.json')]
        assert len(profiles) == 1
        cases.append(dict(label=case['case'], run=case['run_id'], profile=profiles[0],
            generated_samples=report['attributed_generated_samples'], by_label=report['by_label']))
    assert not subprocess.check_output(['git', 'diff', '--name-only', BASE, '--', 'crates'], cwd=ROOT).strip()
    for p in [*HERE.glob('*.py'), *HERE.glob('*.md'), Path(focus.__file__),
              *[ROOT / 'scripts' / n for n in ['compare_saved_runtime.py', 'workflow_io.py',
                    'supervise_experiment.py', 'summarize_owned_sample.py']]]:
        bind(p)
    return frozen, cases


def analyze(case):
    require_space(ROOT, 8)
    folder = ROOT / '.work' / case['run'] / '0'
    native = read(folder / 'jit-code/map.json')
    operations = read(folder / 'jit-code/operations.json')
    profile = read(ROOT / case['profile'])
    code = (folder / 'jit-code/code.bin').read_bytes()
    assert not native['profiled']
    checked = validate(operations, native, code, profile, native['pid'])
    machine = array('I')
    machine.frombytes(code)
    assert machine.itemsize == 4
    if sys.byteorder != 'little':
        machine.byteswap()
    incoming = set()
    for pc, word in enumerate(machine):
        target = direct_target(word, pc)
        if target is not None and 0 <= target < len(machine):
            incoming.add(target)
    dead = set()
    static, kinds = Counter(), Counter()
    spans = []
    excluded = unknown = admitted = 0
    for row in checked['rows']:
        start, end = row['offset'] // 4, row['end'] // 4
        if row['kind'] == 'scalar_leaf':
            excluded += end-start
            continue
        found = analyze_span(machine, start, end, incoming)
        unknown += found['unknown']
        if found['declined']:
            excluded += end-start
            continue
        admitted += end-start
        dead.update(found['dead'])
        static[row['label']] += len(found['dead'])
        kinds.update(found['kinds'])
        if found['dead']:
            spans.append(dict(row, dead_word_offsets=[pc*4 for pc in found['dead']],
                dead_word_encodings=[f'{machine[pc]:08x}' for pc in found['dead']]))
    assert admitted + excluded == len(machine)
    frames = [frame for root in parse_tree((folder / 'sample.txt').read_text()) for frame in self_samples(root)]
    labels, _, unresolved = attribute.assign(checked, native['arena_base'], frames)
    assert not unresolved and dict(labels) == case['by_label']
    sampled, sampled_labels, affected = Counter(), Counter(), []
    for count, frame, _ in frames:
        if '<unknown binary>' not in frame:
            continue
        assert '...' not in frame
        offsets = [int(a, 16)-native['arena_base'] for a in re.findall(r'0x([0-9a-f]+)', frame)]
        assert offsets
        mapped = [locate(checked, offset) for offset in offsets]
        classes = {'scalar_excluded' if row['kind'] == 'scalar_leaf' else
                   'dead_definition' if offset//4 in dead else 'retained_word'
                   for offset, row in zip(offsets, mapped)}
        category = next(iter(classes)) if len(classes) == 1 else 'ambiguous_collapsed'
        sampled[category] += count
        if 'dead_definition' in classes:
            affected.append(dict(samples=count, category=category, offsets=offsets,
                function=mapped[0]['function'], pc=mapped[0]['pc'], label=mapped[0]['label']))
            if category == 'dead_definition':
                sampled_labels[mapped[0]['label']] += count
    assert sum(sampled.values()) == case['generated_samples']
    return dict(case=case['label'], total_words=len(machine), admitted_words=admitted,
        excluded_words=excluded, unknown_barrier_words=unknown, dead_words=len(dead),
        dead_by_label={k:v for k,v in static.items() if v}, dead_by_kind=dict(kinds),
        generated_samples=sum(sampled.values()), sample_partition=dict(sampled),
        dead_sample_labels=dict(sampled_labels), affected_samples=affected, spans=spans)


def main():
    frozen, cases = inputs()
    assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT).strip()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    raw = ROOT / '.work' / RUN
    raw.mkdir(exist_ok=False)
    records = []
    write(raw / 'records.json', records)
    write(raw / 'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
        controller_command=[sys.executable, *sys.orig_argv[1:]], expected_commands=2,
        original_project_guest_commands=0, source_builds=0, performance_measurement=False, cases=cases))
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        for label, folder, pattern, count in [('decoder', Path(words.__file__).parent, 'test_words.py', 9),
                                              ('boundaries', HERE, 'test_model.py', 7)]:
            require_space(ROOT, 8)
            command = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(folder), '-p', pattern, '-v']
            child, out, err = capture(command, cwd=ROOT, env=env, receipt_path=raw / 'active.json', receipt=dict(label=label))
            for stream, value in [('stdout', out), ('stderr', err)]:
                (raw / (label + '.' + stream)).write_text(value)
            records.append(dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
                stdout_sha256=sha(raw / (label + '.stdout')), stderr_sha256=sha(raw / (label + '.stderr'))))
            write(raw / 'records.json', records)
            assert child.returncode == 0 and f'Ran {count} tests' in err and err.rstrip().endswith('OK'), err
        summaries, outputs = [], {}
        for case in cases:
            result = analyze(case)
            path = raw / (case['label'] + '.json')
            write(path, result)
            outputs[str(path.relative_to(ROOT))] = sha(path)
            summaries.append({k:v for k,v in result.items() if k not in ['spans','affected_samples']})
            print(case['label'], 'dead words', result['dead_words'], 'sample partition', result['sample_partition'], flush=True)
            del result
            gc.collect()
        assert all(sha(ROOT / p) == h for p,h in frozen.items())
        output = ROOT / 'results' / RUN
        output.mkdir(exist_ok=False)
        write(output / 'summary.json', dict(status='passed', source_revision=revision, raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw / 'plan.json'), records_sha256=sha(raw / 'records.json'), outputs=outputs,
            commands=2, controls=16, cases=summaries, original_project_guest_commands=0, source_builds=0,
            performance_measurement=False, default_runtime_adoption=False))


def close():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        terminal = read(ROOT / '.work/experiments' / RUN / 'status.json')
        if terminal['returncode'] == 0:
            frozen, cases = inputs()
            raw = ROOT / '.work' / RUN
            assert frozen == read(raw / 'plan.json')['frozen']
            summary = read(ROOT / 'results' / RUN / 'summary.json')
            derived = []
            for case in cases:
                result = analyze(case)
                assert result == read(raw / (case['label'] + '.json'))
                derived.append({k:v for k,v in result.items() if k not in ['spans','affected_samples']})
                del result
                gc.collect()
            assert derived == summary['cases']
    focus.RUN = RUN
    focus.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--close']:
        close()
    else:
        assert len(sys.argv) == 1
        main()
