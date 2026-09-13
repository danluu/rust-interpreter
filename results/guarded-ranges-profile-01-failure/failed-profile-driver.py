#!/usr/bin/env python3
"""Replay the three current controls with the qualified guarded-range VM."""
import argparse
import json
import os
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from profile_vm_transitions import counts
from workflow_io import capture, require_space, write_json as write
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/operation-map'))
from maps import validate as validate_operation_map


def exact_profile_counts(profile, baseline):
    """The emitter changes host instructions, not VM operations or native regions."""
    assert len(profile['functions']) == len(baseline['functions'])
    keys = ['name', 'operations', 'interpreted', 'jit_blocks', 'jit_block_ends',
            'jit_tree_blocks', 'jit_tree_block_ends']
    for fid, (current, prior) in enumerate(zip(profile['functions'], baseline['functions'])):
        for key in keys:
            assert current[key] == prior[key], ('per-PC profile mismatch', fid, key)
    return True


def verify_range_checks(mapping, code):
    """Every speculative failure targets its unchanged-entry fallback."""
    assert len(code) == mapping['code_bytes']
    guards = reloads = 0
    for function in mapping['functions']:
        spans = function['spans']
        guarded = {}
        for row in spans:
            if row['kind'] != 'range_guard': continue
            guards += 1
            region = row['region_pc']
            assert region not in guarded
            guarded[region] = row
            fallback, = [s for s in spans if s['region_pc'] == region and s['kind'] == 'budget_fallback']
            budget, = [s for s in spans if s['region_pc'] == region and s['kind'] == 'budget']
            assert row['pc'] is None and row['offset'] < row['end'] == budget['offset']
            assert struct.unpack_from('<I',code,row['end']-4)[0] == 0x9e670170
            declines = 0
            for offset in range(row['offset'],row['end'],4):
                word, = struct.unpack_from('<I',code,offset)
                if word & 0xff000010 != 0x54000000: continue
                displacement = (word >> 5) & 0x7ffff
                if displacement & (1 << 18): displacement -= 1 << 19
                target = offset + displacement * 4
                if target == fallback['offset']: declines += 1
                else: assert offset < target < row['end'], 'guard branch escapes preflight/fallback'
            assert declines >= 3
        for row in spans:
            for offset in range(row['offset'],row['end'],4):
                word, = struct.unpack_from('<I',code,offset)
                if word & 0xffffffe0 != 0x9e660200: continue
                reloads += 1
                assert row['kind'] == 'operation' and row['pc'] is not None
                assert row['region_pc'] in guarded and guarded[row['region_pc']]['end'] <= offset
                assert word & 31 in [11,12], 'unexpected cached address destination'
    assert guards > 0 and reloads > 0
    return dict(guards=guards,cached_base_reloads=reloads,
        all_speculative_branches_and_region_cache_scopes_verified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    run_id = args.run_id
    assert re.fullmatch(r'guarded-ranges-profile-\d{2}', run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        build_path = args.build.resolve(strict=True)
        build = json.loads(build_path.read_text())
        assert build['status'] == 'passed'
        assert build['tests']['test-debug'] == build['tests']['test-release'] == dict(passed=478, ignored=1)
        vm = ROOT / '.work/interpreter-tools' / build['tool_key'] / 'rust-interp-vm'
        assert sha(vm) == build['binaries']['rust-interp-vm']
        proofs = [ROOT / 'results' / name / 'summary.json' for name in
            ['guarded-ranges-qualification-01', 'guarded-ranges-serial-01', 'guarded-ranges-cache-01']]
        for path in proofs:
            proof = json.loads(path.read_text()); assert proof['status'] == 'passed'
            digest = proof.get('vm_sha256') or proof.get('binaries', {}).get('candidate')
            assert digest == sha(vm) if digest else proof['tool_key'] == build['tool_key']
        reference_path = ROOT / 'results/current-runtime-boundaries-02/summary.json'
        reference = json.loads(reference_path.read_text())
        assert reference['status'] == 'passed' and reference['commands'] == 6
        assert reference['exact_logical_counts_memory_and_entropy']
        raw = ROOT / reference['raw']
        wide_path = ROOT / 'results/memory-operands-profile-01/summary.json'
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
            reference_path, raw / 'records.json', wide_path, wide_raw / 'records.json', entropy_path, library, *proofs,
            ROOT / 'benchmarks/experiments/operation-map/maps.py']
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
                '--jit-code-dump', str(dump_path), '--jit-operation-map',
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
            assert exact_profile_counts(current_profile, json.loads((wide_raw / f'{index}-profile.json').read_text()))
            assert stats['jit_entries'] == previous['candidate_jit_entries']
            assert attribution['interpreted_instructions'] == previous['candidate_interpreted']
            assert not any(r['kind'].startswith('resumable_indirect') for r in dump['ranges'])
            operation_map_path = dump_path / 'operations.json'
            operation_map = json.loads(operation_map_path.read_text())
            checked = validate_operation_map(operation_map, dump, (dump_path / 'code.bin').read_bytes(), current_profile, child.pid)
            assert operation_map['reconstructed_bytes_match']
            range_checks = verify_range_checks(operation_map, (dump_path / 'code.bin').read_bytes())
            del current_profile, checked, operation_map
            comparison = dict(index=index, name=item['name'], profile_sha256=sha(profile_path),range_checks=range_checks,
                baseline_interpreted=previous['candidate_interpreted'],
                candidate_interpreted=attribution['interpreted_instructions'],
                baseline_by_variant=previous['candidate_by_variant'], candidate_by_variant=attribution['by_rendered_variant'],
                baseline_jit_entries=previous['candidate_jit_entries'], candidate_jit_entries=stats['jit_entries'],
                baseline_jit_bytes=previous['candidate_jit_bytes'], candidate_jit_bytes=stats['jit_bytes'], statistics=stats,
                operation_map_sha256=sha(operation_map_path), code_map_sha256=sha(dump_path / 'map.json'), code_sha256=sha(dump_path / 'code.bin'))
            comparisons.append(comparison); row.update(selection=selection, statistics=stats, profile_sha256=sha(profile_path))
            write(work / 'records.json', records); write(work / 'comparisons.json', comparisons)
            assert all(sha(ROOT / p) == h for p,h in frozen.items())
            print(index, item['name'], 'PASS', comparison['baseline_interpreted'], '->', comparison['candidate_interpreted'], flush=True)
        assert comparisons[0]['candidate_jit_bytes'] < comparisons[0]['baseline_jit_bytes'], 'no primary generated code reduction'
        destination = ROOT / 'results' / run_id; destination.mkdir(exist_ok=False)
        result = dict(status='passed', commands=3, tool_key=build['tool_key'], vm_sha256=sha(vm),
            exact_logical_counts_memory_and_entropy=True, exact_per_pc_counts=True, exact_operation_map_reconstruction=True, comparisons=comparisons, performance_measurement=False,
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'))
        write(destination / 'summary.json', result)
        lines = ['# Guarded related-range mechanism check', '',
            'All three current original tests pass with the same per-PC logical instruction counts, peak memory and recorded entropy as the completed adopted memory-operand controls. No JIT compilation declines occurred.', '',
            '| Test | Baseline generated bytes | Candidate generated bytes | Baseline JIT entries | Candidate JIT entries |',
            '| --- | ---: | ---: | ---: | ---: |']
        for row in comparisons:
            lines.append(f"| {row['name']} | {row['baseline_jit_bytes']:,} | {row['candidate_jit_bytes']:,} | {row['baseline_jit_entries']:,} | {row['candidate_jit_entries']:,} |")
        lines += ['', 'Every interpreted count and native interval matches the adopted control at each PC. The primary artifact is smaller; static bytes and logical counts do not establish elapsed-time improvement. The declared changed-source screen remains required; all original tests and controls stay in its selection.']
        (destination / 'assessment.md').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
