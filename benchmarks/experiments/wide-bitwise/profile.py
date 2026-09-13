#!/usr/bin/env python3
"""Replay the three current controls with the qualified wide-operation VM."""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from profile_vm_transitions import counts
from workflow_io import capture, require_space, write_json as write


def main():
    run_id = 'wide-bitwise-profile-01'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        build_path = ROOT / 'results/wide-bitwise-build-01/summary.json'
        build = json.loads(build_path.read_text())
        assert build['status'] == 'passed'
        assert build['tests']['test-debug'] == build['tests']['test-release'] == dict(passed=419, ignored=1)
        vm = ROOT / '.work/interpreter-tools' / build['tool_key'] / 'rust-interp-vm'
        assert sha(vm) == build['binaries']['rust-interp-vm']
        proofs = [ROOT / 'results' / name / 'summary.json' for name in
            ['wide-bitwise-qualification-01', 'wide-bitwise-serial-01', 'wide-bitwise-cache-01']]
        for path in proofs:
            proof = json.loads(path.read_text()); assert proof['status'] == 'passed'
            digest = proof.get('vm_sha256') or proof.get('binaries', {}).get('candidate')
            assert digest == sha(vm) if digest else proof['tool_key'] == build['tool_key']
        reference_path = ROOT / 'results/current-runtime-boundaries-02/summary.json'
        reference = json.loads(reference_path.read_text())
        assert reference['status'] == 'passed' and reference['commands'] == 6
        assert reference['exact_logical_counts_memory_and_entropy']
        raw = ROOT / reference['raw']
        assert sha(raw / 'records.json') == reference['records_sha256']
        rows = json.loads((raw / 'records.json').read_text())
        entropy_path = ROOT / 'results/fixed-frame-clear-entropy-check-01/summary.json'
        entropy = json.loads(entropy_path.read_text()); assert entropy['status'] == 'passed'
        library = ROOT / entropy['library']; assert sha(library) == entropy['library_sha256']
        paths = [Path(__file__), Path(__file__).with_name('PLAN.md'), build_path, vm,
            reference_path, raw / 'records.json', entropy_path, library, *proofs]
        paths += [ROOT / 'scripts' / name for name in ['workflow_io.py', 'compare_saved_runtime.py',
            'profile_vm_transitions.py', 'summarize_owned_sample.py', 'sample_owned_vm.py', 'interpreter.py']]
        for item in reference['profiles']:
            for key in ['artifact', 'catalog']:
                path = ROOT / item[key]; assert sha(path) == item[key + '_sha256']; paths.append(path)
            tape = raw / f"{item['index']}.tape"
            original, = [r for r in rows if r['index'] == item['index'] and r['mode'] == 'profile']
            assert sha(tape) == original['tape_sha256']; paths.append(tape)
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / run_id; work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, expected_commands=3,
            tool_key=build['tool_key'], reference=str(reference_path.relative_to(ROOT)), performance_measurement=False))
        env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library), RUST_INTERP_ENTROPY_MODE='replay', RUST_INTERP_VM_STATS='1')
        records, comparisons = [], []
        for item in reference['profiles']:
            require_space(ROOT, 8)
            index = item['index']; profile_path = work / f'{index}-profile.json'
            command = [str(vm), '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                '--profile', str(profile_path), '--profile-test', item['name'], '--suite-catalog', str(ROOT / item['catalog']),
                '--instruction-limit', str(item['limits']['instructions']), '--allocation-limit', str(item['limits']['allocations']),
                str(ROOT / item['artifact'])]
            child, out, err = capture(command, cwd=ROOT,
                env=dict(env, RUST_INTERP_ENTROPY_TAPE=str(raw / f'{index}.tape')),
                receipt_path=work / 'active.json', receipt=dict(index=index))
            row = dict(index=index, command=command, pid=child.pid, returncode=child.returncode, stdout=out, stderr=err)
            records.append(row); write(work / 'records.json', records)
            assert child.returncode == 0 and out == '0\n', err
            selection, = [json.loads(line.split(': ', 1)[1]) for line in err.splitlines()
                if line.startswith('rust-interp-profile-selection: ')]
            assert selection == item['selection']
            stats = {k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b', err)}
            assert all(stats[k] == item['statistics'][k] for k in
                ['instructions', 'peak_guest_memory', 'entropy_calls', 'entropy_bytes', 'jit_declined_functions'])
            assert stats['jit_declined_functions'] == 0 and profile_path.stat().st_size <= 256 * 1024**2
            attribution = counts(json.loads(profile_path.read_text()), stats)
            comparison = dict(index=index, name=item['name'], profile_sha256=sha(profile_path),
                baseline_interpreted=item['attribution']['interpreted_instructions'],
                candidate_interpreted=attribution['interpreted_instructions'],
                baseline_by_variant=item['attribution']['by_rendered_variant'], candidate_by_variant=attribution['by_rendered_variant'],
                baseline_jit_entries=item['statistics']['jit_entries'], candidate_jit_entries=stats['jit_entries'],
                baseline_jit_bytes=item['statistics']['jit_bytes'], candidate_jit_bytes=stats['jit_bytes'], statistics=stats)
            comparisons.append(comparison); row.update(selection=selection, statistics=stats, profile_sha256=sha(profile_path))
            write(work / 'records.json', records); write(work / 'comparisons.json', comparisons)
            assert all(sha(ROOT / p) == h for p,h in frozen.items())
            print(index, item['name'], 'PASS', comparison['baseline_interpreted'], '->', comparison['candidate_interpreted'], flush=True)
        destination = ROOT / 'results' / run_id; destination.mkdir(exist_ok=False)
        result = dict(status='passed', commands=3, tool_key=build['tool_key'], vm_sha256=sha(vm),
            exact_logical_counts_memory_and_entropy=True, comparisons=comparisons, performance_measurement=False,
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'))
        write(destination / 'summary.json', result)
        lines = ['# Wide-operation mechanism check', '',
            'All three current original tests pass with the same logical instruction counts, peak memory and recorded entropy as the completed controls. No JIT compilation declines occurred.', '',
            '| Test | Baseline interpreted operations | Candidate interpreted operations | Baseline JIT entries | Candidate JIT entries |',
            '| --- | ---: | ---: | ---: | ---: |']
        for row in comparisons:
            lines.append(f"| {row['name']} | {row['baseline_interpreted']:,} | {row['candidate_interpreted']:,} | {row['baseline_jit_entries']:,} | {row['candidate_jit_entries']:,} |")
        lines += ['', 'These are instrumented logical counts. They establish mechanism use, not elapsed-time improvement. The full changed-source comparison remains required; all original tests and controls stay in its selection.']
        (destination / 'assessment.md').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
