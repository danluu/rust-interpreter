#!/usr/bin/env python3
"""Replay the three current controls with the qualified guarded-indirect VM."""
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


def logical_counts(function):
    """Expand native intervals without multiplying the work by interval length."""
    n = len(function['operations'])
    delta = [0] * (n + 1)
    for hits, ends in [('jit_blocks', 'jit_block_ends'), ('jit_tree_blocks', 'jit_tree_block_ends')]:
        assert len(function[hits]) == len(function[ends]) == n
        for pc, count in enumerate(function[hits]):
            if count:
                end = function[ends][pc]
                assert type(count) is int and count > 0 and pc < end <= n
                delta[pc] += count
                delta[end] -= count
    result, live = [], 0
    assert len(function['interpreted']) == n
    for pc in range(n):
        live += delta[pc]
        result.append(function['interpreted'][pc] + live)
    assert live + delta[n] == 0
    return result


def indirect_counts(profile, baseline, dump):
    assert len(profile['functions']) == len(baseline['functions'])
    published = {(r['function'], r['pc']) for r in dump['ranges']
                 if r['kind'] == 'resumable_indirect_call'}
    sites = []
    for fid, (current, prior) in enumerate(zip(profile['functions'], baseline['functions'])):
        assert current['name'] == prior['name'] and current['operations'] == prior['operations']
        logical = logical_counts(current)
        assert logical == logical_counts(prior), ('per-PC logical mismatch', fid)
        for pc, op in enumerate(current['operations']):
            if not op.startswith('CallIndirect {'):
                continue
            native = current['jit_blocks'][pc]
            assert current['jit_tree_blocks'][pc] == 0
            if native:
                assert current['jit_block_ends'][pc] == pc + 1 and (fid, pc) in published
            assert current['interpreted'][pc] + native == logical[pc]
            if logical[pc] or (fid, pc) in published:
                sites.append(dict(function=fid, name=current['name'], pc=pc,
                    logical_calls=logical[pc], native_calls=native, vm_calls=current['interpreted'][pc],
                    published=(fid, pc) in published))
    assert published <= {(s['function'], s['pc']) for s in sites}
    return dict(published_thunks=len(published),
        native_calls=sum(s['native_calls'] for s in sites),
        vm_calls=sum(s['vm_calls'] for s in sites),
        thunk_code_bytes=sum(r['end']-r['offset'] for r in dump['ranges']
                             if r['kind'] == 'resumable_indirect_call'),
        sites=sorted(sites, key=lambda s: -s['logical_calls'])[:40],
        scope='VM calls combine first use, target mismatches, unready callees and other declines; these counters do not distinguish their reasons.')


def main():
    run_id = 'guarded-indirect-profile-01'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        build_path = ROOT / 'results/guarded-indirect-build-01/summary.json'
        build = json.loads(build_path.read_text())
        assert build['status'] == 'passed'
        assert build['tests']['test-debug'] == build['tests']['test-release'] == dict(passed=424, ignored=1)
        vm = ROOT / '.work/interpreter-tools' / build['tool_key'] / 'rust-interp-vm'
        assert sha(vm) == build['binaries']['rust-interp-vm']
        proofs = [ROOT / 'results' / name / 'summary.json' for name in
            ['guarded-indirect-qualification-01', 'guarded-indirect-serial-01', 'guarded-indirect-cache-01']]
        for path in proofs:
            proof = json.loads(path.read_text()); assert proof['status'] == 'passed'
            digest = proof.get('vm_sha256') or proof.get('binaries', {}).get('candidate')
            assert digest == sha(vm) if digest else proof['tool_key'] == build['tool_key']
        reference_path = ROOT / 'results/current-runtime-boundaries-02/summary.json'
        reference = json.loads(reference_path.read_text())
        assert reference['status'] == 'passed' and reference['commands'] == 6
        assert reference['exact_logical_counts_memory_and_entropy']
        raw = ROOT / reference['raw']
        wide_path = ROOT / 'results/wide-bitwise-profile-01/summary.json'
        wide = json.loads(wide_path.read_text())
        assert wide['status'] == 'passed' and wide['exact_logical_counts_memory_and_entropy']
        wide_raw = ROOT / wide['raw']
        assert sha(wide_raw / 'records.json') == wide['records_sha256']
        assert sha(raw / 'records.json') == reference['records_sha256']
        rows = json.loads((raw / 'records.json').read_text())
        entropy_path = ROOT / 'results/fixed-frame-clear-entropy-check-01/summary.json'
        entropy = json.loads(entropy_path.read_text()); assert entropy['status'] == 'passed'
        library = ROOT / entropy['library']; assert sha(library) == entropy['library_sha256']
        paths = [Path(__file__), Path(__file__).with_name('PLAN.md'), build_path, vm,
            reference_path, raw / 'records.json', wide_path, wide_raw / 'records.json', entropy_path, library, *proofs]
        paths += [ROOT / 'scripts' / name for name in ['workflow_io.py', 'compare_saved_runtime.py',
            'profile_vm_transitions.py', 'summarize_owned_sample.py', 'sample_owned_vm.py', 'interpreter.py']]
        for item in reference['profiles']:
            previous, = [c for c in wide['comparisons'] if c['index'] == item['index']]
            prior_profile = wide_raw / f"{item['index']}-profile.json"
            assert sha(prior_profile) == previous['profile_sha256']; paths.append(prior_profile)
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
            dump_path = work / f'{index}-code'
            command = [str(vm), '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                '--jit-code-dump', str(dump_path),
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
            current_profile = json.loads(profile_path.read_text())
            attribution = counts(current_profile, stats)
            previous, = [c for c in wide['comparisons'] if c['index'] == index]
            dump = json.loads((dump_path / 'map.json').read_text())
            assert dump['pid'] == child.pid and dump['profiled'] and dump['resumable_calls']
            assert dump['code_bytes'] == stats['jit_bytes'] == (dump_path / 'code.bin').stat().st_size
            cursor = 0
            for r in dump['ranges']:
                assert r['offset'] == cursor and r['end'] > cursor and r['end'] % 4 == 0
                cursor = r['end']
            assert cursor == dump['code_bytes']
            indirect = indirect_counts(current_profile, json.loads((wide_raw / f'{index}-profile.json').read_text()), dump)
            del current_profile
            comparison = dict(index=index, name=item['name'], profile_sha256=sha(profile_path),
                baseline_interpreted=previous['candidate_interpreted'],
                candidate_interpreted=attribution['interpreted_instructions'],
                baseline_by_variant=previous['candidate_by_variant'], candidate_by_variant=attribution['by_rendered_variant'],
                baseline_jit_entries=previous['candidate_jit_entries'], candidate_jit_entries=stats['jit_entries'],
                baseline_jit_bytes=previous['candidate_jit_bytes'], candidate_jit_bytes=stats['jit_bytes'], statistics=stats,
                indirect=indirect, code_map_sha256=sha(dump_path / 'map.json'), code_sha256=sha(dump_path / 'code.bin'))
            comparisons.append(comparison); row.update(selection=selection, statistics=stats, profile_sha256=sha(profile_path))
            write(work / 'records.json', records); write(work / 'comparisons.json', comparisons)
            assert all(sha(ROOT / p) == h for p,h in frozen.items())
            print(index, item['name'], 'PASS', comparison['baseline_interpreted'], '->', comparison['candidate_interpreted'], flush=True)
        destination = ROOT / 'results' / run_id; destination.mkdir(exist_ok=False)
        result = dict(status='passed', commands=3, tool_key=build['tool_key'], vm_sha256=sha(vm),
            exact_logical_counts_memory_and_entropy=True, exact_per_pc_counts=True, comparisons=comparisons, performance_measurement=False,
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'))
        write(destination / 'summary.json', result)
        lines = ['# Guarded indirect-call mechanism check', '',
            'All three current original tests pass with the same per-PC logical instruction counts, peak memory and recorded entropy as the completed wide-operation controls. No JIT compilation declines occurred.', '',
            '| Test | Baseline interpreted operations | Candidate interpreted operations | Baseline JIT entries | Candidate JIT entries |',
            '| --- | ---: | ---: | ---: | ---: |']
        for row in comparisons:
            lines.append(f"| {row['name']} | {row['baseline_interpreted']:,} | {row['candidate_interpreted']:,} | {row['baseline_jit_entries']:,} | {row['candidate_jit_entries']:,} |")
        lines += ['', 'These are instrumented logical counts. They establish mechanism use, not elapsed-time improvement. The full changed-source comparison remains required; all original tests and controls stay in its selection.']
        (destination / 'assessment.md').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
