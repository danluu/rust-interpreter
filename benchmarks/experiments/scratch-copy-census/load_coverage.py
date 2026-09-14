"""Quantify existing Load observations in the same closed Copy census."""
import json
from pathlib import Path
import re
import subprocess
import sys
from attribute import ROOT, locate, read
from compare_saved_runtime import acquire_lock, sha
from summarize_owned_sample import parse_tree, self_samples
from workflow_io import require_space, write_json as write

NAME = 'scratch-load-copy-coverage-01'


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        proof_path = ROOT / 'results/scratch-copy-census-01/summary.json'
        closure_path = proof_path.with_name('closure.json')
        proof, closure = read(proof_path), read(closure_path)
        assert proof['status'] == 'passed' and closure['status'] == 'closed' and closure['all_hashes_verified']
        assert sha(proof_path) == closure['summary_sha256']
        binding_path = ROOT / closure['bindings']
        assert sha(binding_path) == closure['bindings_sha256']
        bindings = read(binding_path)
        paths = [proof_path, closure_path, binding_path, Path(__file__), Path(__file__).with_name('attribute.py')]
        paths += [ROOT / 'scripts' / n for n in ['compare_saved_runtime.py', 'summarize_owned_sample.py', 'workflow_io.py']]
        for p, h in bindings['artifacts'].items():
            assert sha(ROOT / p) == h
            paths.append(ROOT / p)
        inputs = []
        for label in ['block', 'exhaustive']:
            typed = ROOT / '.work/scratch-copy-census-01' / (label + '.json')
            folder = ROOT / '.work' / ('scalar-runtime-sample-' + label + '-01') / '0'
            inputs.append((label, typed, folder / 'jit-code/operations.json', folder / 'sample.txt'))
            paths += list(inputs[-1][1:])
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        work = ROOT / '.work' / NAME
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
            guest_commands=0, rust_builds=0, performance_measurement=False, initial_gib=12, minimum_child_gib=8))
        output = []
        for label, typed_path, map_path, sample_path in inputs:
            require_space(ROOT, 8)
            typed, mapping = read(typed_path), read(map_path)
            assert typed['scratch_copy_observed'] and typed['code_sha256'] == mapping['code_sha256']
            rows = [dict(s, function=f['function']) for f in typed['functions'] for s in f['memory_spans']]
            starts = [r['offset'] for r in rows]
            assert starts == sorted(set(starts))
            coarse = [dict(s, function=f['function']) for f in mapping['functions'] for s in f['spans'] if s['offset'] < s['end']]
            coarse_starts = [r['offset'] for r in coarse]
            selected = {(f['function'], s['pc']): (s['operation'], s['size']) for f in typed['functions'] for s in f['selected']}
            eligible = {}
            for f in typed['functions']:
                for field, operation in [('available_load_values', 'Load'), ('available_copy_values', 'Copy')]:
                    for hit in f[field]:
                        key = (f['function'], hit['pc'])
                        assert key not in eligible and selected[key] == (operation, 8)
                        eligible[key] = operation
            counts = {op: dict(sites=sum(v == op for v in eligible.values()), whole_samples=0,
                              load_samples=0, ambiguous_samples=0) for op in ['Load', 'Copy']}
            generated = 0
            for root in parse_tree(sample_path.read_text()):
                for n, frame, _ in self_samples(root):
                    if '<unknown binary>' not in frame:
                        continue
                    assert '...' not in frame
                    offsets = [int(a, 16) - mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)', frame)]
                    assert offsets
                    owners = [locate(coarse, coarse_starts, o) for o in offsets]
                    identities = {(r['function'], r['pc'], r['kind']) for r in owners}
                    assert len(identities) == 1
                    fid, pc, kind = next(iter(identities))
                    generated += n
                    if kind != 'operation' or (fid, pc) not in eligible:
                        continue
                    parts = [locate(rows, starts, o) for o in offsets]
                    assert all((r['function'], r['pc']) == (fid, pc) for r in parts)
                    counter = counts[eligible[fid, pc]]
                    counter['whole_samples'] += n
                    kinds = {r['part'] for r in parts}
                    if kinds == {'load_data'}:
                        counter['load_samples'] += n
                    elif len(kinds) > 1:
                        counter['ambiguous_samples'] += n
            previous, = [c for c in proof['cases'] if c['case'] == label]
            assert generated == previous['generated_samples']
            for field, old in [('sites', 'eligible_copy_sites'), ('whole_samples', 'eligible_copy_whole_samples'), ('load_samples', 'eligible_copy_load_samples')]:
                assert counts['Copy'][field] == previous[old]
            output.append(dict(case=label, generated_samples=generated, operations=counts,
                combined_load_samples=sum(v['load_samples'] for v in counts.values())))
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        out = ROOT / 'results' / NAME
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', cases=output, frozen_inputs=len(frozen),
            all_frozen_inputs_verified=True, source_revision=revision, raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            guest_commands=0, rust_builds=0, executable_code_publications=0, performance_measurement=False,
            limitation='Same partial windows; Copy queried after address handling, legacy Load observations before address handling. Load coverage is an upper estimate until an implementation queries after address formation. These shares do not predict whole-command speedup.'))
        print(json.dumps(output), flush=True)


if __name__ == '__main__':
    main()
