"""Attribute existing call protocol samples without building or executing guests."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write
from summarize_owned_sample import parse_tree, self_samples
from profile_vm_transitions import counts
from analyze import call_index, attribute, summarize


def read(path, limit=256 * 1024**2):
    assert path.stat().st_size <= limit
    return json.loads(path.read_text())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-id', required=True)
    args = p.parse_args()
    assert re.fullmatch(r'native-call-cost-census-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        closure_path = ROOT / 'results/native-continuation-census-01/closure.json'
        closure = read(closure_path)
        assert closure['status'] == 'passed' and closure['all_frozen_inputs_verified']
        assert closure['guest_commands'] == closure['executable_code_publications'] == 0
        expected = dict(closure['frozen'])
        for name, digest in closure['evidence'].items():
            assert name not in expected or expected[name] == digest
            expected[name] = digest
        profile_proof_path = ROOT / 'results/guarded-local-facts-profile-01/summary.json'
        protocol_proof_path = ROOT / 'results/native-protocol-census-01/attribution.json'
        prior_cost_path = ROOT / 'results/native-continuation-census-01/attribution.json'
        for path in [profile_proof_path, protocol_proof_path, prior_cost_path]:
            assert sha(path) == expected[str(path.relative_to(ROOT))]
        profiles, protocol, prior_cost = map(read, [profile_proof_path, protocol_proof_path, prior_cost_path])
        assert profiles['status'] == protocol['status'] == prior_cost['status'] == 'passed'
        assert profiles['exact_per_pc_counts'] and profiles['exact_operation_map_reconstruction']
        paths = [closure_path, profile_proof_path, protocol_proof_path, prior_cost_path]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py', '.md']]
        paths += [ROOT / 'scripts' / name for name in ['compare_saved_runtime.py', 'workflow_io.py',
            'summarize_owned_sample.py', 'profile_vm_transitions.py', 'sample_owned_vm.py', 'interpreter.py']]
        inputs = []
        for index, label in enumerate(['block', 'exhaustive']):
            folder = ROOT / '.work' / ('adopted-runtime-sample-' + label + '-01') / '0'
            inputs.append(dict(index=index, label=label, folder=folder,
                profile=ROOT / profiles['raw'] / (str(index) + '-profile.json'),
                typed=ROOT / '.work/native-continuation-census-01' / (label + '.json'),
                fine=ROOT / '.work/native-protocol-census-01' / (label + '.json'),
                mapping=folder / 'jit-code/operations.json', code=folder / 'jit-code/code.bin',
                sample=folder / 'sample.txt'))
            for field in ['profile', 'typed', 'fine', 'mapping', 'code', 'sample']:
                path = inputs[-1][field]
                assert sha(path) == expected[str(path.relative_to(ROOT))], str(path)
                paths.append(path)
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        bindings = []
        import hashlib
        for name, digest in frozen.items():
            if name.startswith(('scripts/', 'benchmarks/', 'results/')):
                spec = revision + ':' + name
                assert hashlib.sha256(subprocess.check_output(['git', 'show', spec], cwd=ROOT)).hexdigest() == digest
                bindings.append(dict(path=name, sha256=digest, git_source=spec))
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
            expected_controls=2, analysis_cases=2, guest_commands=0, rust_builds=0,
            performance_measurement=False, initial_gib=12, minimum_child_gib=8))
        require_space(ROOT, 8)
        child, out, err = capture([sys.executable, '-m', 'unittest', 'test_analyze', '-v'],
            cwd=Path(__file__).parent, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work / 'active.json', receipt=dict(stage='join controls'))
        records = [dict(label='controls', pid=child.pid, returncode=child.returncode, stdout=out, stderr=err)]
        write(work / 'records.json', records)
        assert child.returncode == 0 and 'Ran 2 tests' in err and err.rstrip().endswith('OK'), err
        cases = []
        for item in inputs:
            require_space(ROOT, 8)
            index, label = item['index'], item['label']
            profile, typed, fine, mapping = [read(item[k]) for k in ['profile', 'typed', 'fine', 'mapping']]
            comparison = profiles['comparisons'][index]
            assert sha(item['profile']) == comparison['profile_sha256']
            assert typed['exact_baseline_reconstruction'] and fine['exact_full_function_reconstruction']
            assert fine['complete_partition'] and fine['exact_transition_reconstruction']
            assert sha(item['code']) == typed['code_sha256'] == fine['code_sha256'] == mapping['code_sha256']
            assert mapping['complete'] and mapping['reconstructed_bytes_match'] and not mapping['profiled']
            accounting = counts(profile, comparison['statistics'])
            calls = call_index(typed, profile)
            assert sum(c['hits'] for c in calls.values()) == comparison['statistics']['jit_resumable_calls']
            samples = [frame for root in parse_tree(item['sample'].read_text()) for frame in self_samples(root)]
            a, b, parts, generated = attribute(calls, mapping, fine, samples)
            previous = protocol['cases'][index]
            assert previous['case'] == label and parts == Counter(previous['fine_samples'])
            assert generated == previous['generated_samples']
            assert sum(parts.values()) == previous['transition_samples']
            rows = summarize(profile, calls, mapping, a, b)
            assert sum(r['native_incoming_calls'] for r in rows) == comparison['statistics']['jit_resumable_calls']
            assert sum(r['call_samples'] for r in rows) == previous['coarse_counts']['Call']
            assert sum(r['return_samples'] for r in rows) == previous['coarse_counts']['Return']
            assert prior_cost['cases'][index]['native_calls'] == comparison['statistics']['jit_resumable_calls']
            result_path = work / (label + '.json')
            write(result_path, dict(status='passed', case=label, callees=rows, logical_accounting=accounting,
                fine_samples=dict(parts), generated_samples=generated, guest_commands=0,
                limitation='Saved sampled windows and whole-test counts have different entropy and scopes. Rendered labels are not a safety proof.'))
            cases.append(dict(case=label, callees=len(rows), native_calls=comparison['statistics']['jit_resumable_calls'],
                generated_samples=generated, call_samples=previous['coarse_counts']['Call'], return_samples=previous['coarse_counts']['Return'],
                report_sha256=sha(result_path), top_callees=[{k: r[k] for k in ['function', 'name', 'native_incoming_calls',
                    'frame_size', 'registers', 'bytecode_operations', 'call_samples', 'return_samples', 'call_parts', 'return_parts']}
                    for r in rows[:12]]))
            print(label, 'PASS', len(rows), 'callee groups,', sum(parts.values()), 'transition samples', flush=True)
        assert all(sha(ROOT / name) == digest for name, digest in frozen.items())
        destination = ROOT / 'results' / args.run_id
        destination.mkdir(exist_ok=False)
        write(destination / 'source-bindings.json', dict(source_revision=revision, files=bindings))
        write(destination / 'summary.json', dict(status='passed', controls=2, commands=1, analysis_cases=2, cases=cases,
            unique_frozen_inputs=len(frozen), all_frozen_inputs_verified=True, git_bindings=len(bindings),
            source_bindings_sha256=sha(destination / 'source-bindings.json'), raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'),
            guest_commands=0, rust_builds=0, executable_code_publications=0, performance_measurement=False))


if __name__ == '__main__': main()
