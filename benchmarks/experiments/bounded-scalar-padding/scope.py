"""Reuse closed typed reports; no compiler, guest or executable publication."""
from collections import Counter
from pathlib import Path
import re
import subprocess
import sys
from padding_model import alignment, widths, controls

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/scalar-entry-empty-work'))
import run as previous_scope

focus = previous_scope.focus
read, sha, write = previous_scope.read, previous_scope.sha, previous_scope.write
RUN = 'bounded-scalar-padding-scope-02'


def derive(case, path):
    previous = previous_scope.derive(case, path)
    typed = read(path)
    sites = {(r['caller'], r['pc']): r for r in typed['sites']}
    shapes = Counter()
    for row in sites.values():
        row['minimum_end_alignment'] = alignment(row['caller_frame_align'], row['caller_frame_size'])
        row['store_widths'] = widths(row['caller_frame_align'], row['caller_frame_size'], row['callee_frame_align'])
        shapes[str(row['store_widths'])] += 1
    protocol = read(ROOT / case['protocol'])
    fine = dict(rows=protocol['spans'], starts=[r['offset'] for r in protocol['spans']])
    folder = ROOT / case['folder']
    mapping = read(folder / 'jit-code/operations.json')
    code = (folder / 'jit-code/code.bin').read_bytes()
    length = len(code)
    checked = previous_scope.validate(mapping, read(folder / 'jit-code/map.json'), code,
                                     read(ROOT / case['profile']), read(folder / 'record.json')['identity']['pid'])
    counts, hot, ambiguous = Counter(), Counter(), []
    for root in previous_scope.parse_tree((folder / 'sample.txt').read_text()):
        for count, frame, _ in previous_scope.self_samples(root):
            if '<unknown binary>' not in frame:
                continue
            offsets = [int(a, 16) - mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)', frame)]
            if not offsets or not any(0 <= p < length for p in offsets):
                continue
            assert '...' not in frame and all(0 <= p < length for p in offsets)
            coarse = [previous_scope.locate(checked, p) for p in offsets]
            assert len({(r['function'], r['region_pc'], r['pc'], r['kind']) for r in coarse}) == 1
            if coarse[0]['kind'] != 'transition':
                continue
            rows = [previous_scope.locate(fine, p) for p in offsets]
            padding = [r is not None and r['kind'] == 'scalar_padding_clear' for r in rows]
            if not any(padding):
                continue
            if not all(padding) or len({(r['function'], r['pc']) for r in rows}) != 1:
                ambiguous.append(dict(count=count, frame=frame))
                continue
            key = rows[0]['function'], rows[0]['pc']
            row = sites[key]
            shape = str(row['store_widths'])
            counts[shape] += count
            hot[key] += count
    assert not ambiguous
    assert sum(counts.values()) == sum(previous['samples'].get(k, 0) for k in ['padding_unproved', 'padding_proven_empty'])
    return dict(name=case['name'], generated_samples=previous['generated_samples'],
                scalar_sites=len(sites), static_shapes=dict(shapes), padding_samples=sum(counts.values()),
                sampled_shapes=dict(counts), ambiguous=ambiguous,
                top_sites=[dict(**sites[key], samples=count) for key, count in hot.most_common()],
                performance_measurement=False)


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        previous_scope.acquire_lock(lock, 45)
        previous_scope.require_space(ROOT, 12)
        frozen = {}

        def bind(path, expected=None):
            digest = sha(path)
            assert expected is None or digest == expected, path
            frozen[str(path.relative_to(ROOT))] = digest
            return read(path) if path.suffix == '.json' else digest

        prior_result = ROOT / 'results/scalar-entry-empty-work-01'
        closed = bind(prior_result / 'closure.json')
        assert closed['status'] == 'closed' and closed['all_hashes_verified']
        summary = bind(prior_result / 'summary.json', closed['summary_sha256'])
        terminal = bind(prior_result / 'terminal.json', closed['terminal_sha256'])
        assert terminal['returncode'] == 0 and summary['status'] == 'passed'
        assert summary['commands'] == 6 and summary['tests_per_profile'] == 2
        prior = bind(ROOT / summary['raw'] / 'plan.json', summary['plan_sha256'])
        records = bind(ROOT / summary['raw'] / 'records.json', summary['records_sha256'])
        for record in records:
            for p, h in record['outputs'].items():
                bind(ROOT / p, h)
        for p, h in prior['frozen'].items():
            bind(ROOT / p, h)
        for p in [*HERE.glob('*.py'), *HERE.glob('*.md')]:
            bind(p)
        bind(Path(previous_scope.__file__))
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT).strip()
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        raw = ROOT / '.work' / RUN
        raw.mkdir(exist_ok=False)
        write(raw / 'records.json', [])
        cases = [dict(c, typed=summary['raw'] + '/' + str(c['index']) + '-scope.json') for c in prior['cases']]
        write(raw / 'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
              cases=cases, controller_command=[sys.executable, *sys.orig_argv[1:]], expected_commands=0,
              original_project_guest_commands=0, executable_code_publications=0, performance_measurement=False))
        checked = controls()
        write(raw / 'controls.json', checked)
        comparisons = []
        for case in cases:
            previous_scope.require_space(ROOT, 8)
            comparisons.append(derive(case, ROOT / case['typed']))
            write(raw / 'attribution.json', comparisons)
            print(case['name'], comparisons[-1]['sampled_shapes'], flush=True)
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results' / RUN
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', source_revision=revision,
              raw=str(raw.relative_to(ROOT)), plan_sha256=sha(raw / 'plan.json'),
              records_sha256=sha(raw / 'records.json'), commands=0, controls=checked, comparisons=comparisons,
              outputs={str((raw / p).relative_to(ROOT)): sha(raw / p) for p in ['controls.json', 'attribution.json']},
              original_project_guest_commands=0, executable_code_publications=0, performance_measurement=False))


def close():
    raw = ROOT / '.work' / RUN
    terminal = read(ROOT / '.work/experiments' / RUN / 'status.json')
    assert terminal['status'] == 'finished'
    if terminal['returncode'] == 0:
        summary, plan = read(ROOT / 'results' / RUN / 'summary.json'), read(raw / 'plan.json')
        assert summary['controls'] == controls()
        assert summary['comparisons'] == [derive(c, ROOT / c['typed']) for c in plan['cases']]
        assert summary['commands'] == 0
    focus.RUN = RUN
    focus.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--close']:
        close()
    else:
        assert len(sys.argv) == 1
        main()
