"""Count pairable memory instructions in closed adopted captures; never execute guest code."""
from collections import Counter
from pathlib import Path
import argparse
import json
import os
import re
import struct
import subprocess
import sys
from decoder import pair

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from profile_vm_transitions import counts
from summarize_owned_sample import parse_tree, self_samples
from workflow_io import capture, require_space, write_json as write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'memory-pair-census-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        old_path = ROOT / 'results/memory-operation-parts-census-01/attribution.json'
        old = json.loads(old_path.read_text())
        assert old['status'] == 'passed' and old['guest_commands'] == 0
        closure_path = old_path.with_name('closure.json')
        closure = json.loads(closure_path.read_text())
        assert closure['status'] == 'passed' and closure['all_frozen_inputs_verified']
        bindings_path = old_path.with_name('source-bindings.json')
        assert sha(bindings_path) == closure['source_bindings_sha256']
        proof_path = ROOT / 'results/guarded-local-facts-profile-01/summary.json'
        proof = json.loads(proof_path.read_text())
        assert proof['status'] == 'passed' and proof['exact_per_pc_counts']
        frozen = dict(old['evidence'])
        paths = list(Path(__file__).parent.iterdir()) + [old_path, closure_path, bindings_path, proof_path]
        paths += [ROOT / 'scripts' / n for n in ['compare_saved_runtime.py', 'workflow_io.py',
            'profile_vm_transitions.py', 'summarize_owned_sample.py']]
        for p in paths:
            if p.is_file():
                key = str(p.relative_to(ROOT)); digest = sha(p)
                assert frozen.setdefault(key, digest) == digest, key
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen,
            source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            guest_commands=0, executable_code_publications=0, performance_measurement=False))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        assert not any(k.startswith('DYLD_') for k in env)
        commands = [
            ('assemble', ['/usr/bin/clang', '-target', 'arm64-apple-macos11', '-c', str(Path(__file__).with_name('control.s')), '-o', str(work / 'control.o')]),
            ('inspect', ['/usr/bin/otool', '-s', '__TEXT', '__text', str(work / 'control.o')]),
            ('decoder-tests', [sys.executable, '-B', '-m', 'unittest', 'test_decoder', '-v'])]
        records = []
        for label, command in commands:
            require_space(ROOT, 8)
            child, out, err = capture(command, cwd=Path(__file__).parent, env=env,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            records.append(dict(label=label, command=command, pid=child.pid,
                returncode=child.returncode, stdout=out, stderr=err))
            write(work / 'records.json', records)
            assert child.returncode == 0, (out + err)[-3000:]
            if label == 'inspect':
                words = [int(w, 16) for line in out.splitlines() if re.match(r'^[0-9a-f]{16}\s', line) for w in line.split()[1:]]
                assert len(words) == 12
                for i in range(0, 12, 3): assert pair(*words[i:i+2])['word'] == words[i+2]
            if label == 'decoder-tests': assert 'Ran 3 tests' in err and err.rstrip().endswith('OK')
        cases = []
        for index, label in enumerate(['block', 'exhaustive']):
            require_space(ROOT, 8)
            report_path = ROOT / '.work/memory-operation-parts-census-01' / (label + '.json')
            folder = ROOT / '.work' / ('adopted-runtime-sample-' + label + '-01') / '0'
            code_path = folder / 'jit-code/code.bin'; code = code_path.read_bytes()
            report = json.loads(report_path.read_text())
            mapping = json.loads((folder / 'jit-code/operations.json').read_text())
            assert report['status'] == 'passed' and report['complete_small_memory_partition']
            assert report['exact_full_function_reconstruction'] and report['observer_words_unchanged']
            assert report['guest_commands'] == report['executable_code_publications'] == 0
            assert report['code_sha256'] == mapping['code_sha256'] == sha(code_path)
            profile_path = ROOT / proof['raw'] / (str(index) + '-profile.json')
            comparison = proof['comparisons'][index]
            assert sha(profile_path) == comparison['profile_sha256']
            profile = json.loads(profile_path.read_text())
            accounting = counts(profile, comparison['statistics'])
            represented = set(); sites = []; by_pc = {}; static = Counter(); weighted = Counter()
            for f in report['functions']:
                fid = f['function']; assert fid not in represented; represented.add(fid)
                pf = profile['functions'][fid]; assert pf['name'] == f['name']
                selected = {s['pc']:(s['operation'], s['size']) for s in f['selected']}
                for s in f['memory_spans']:
                    assert selected[s['pc']] == (s['operation'], s['size'])
                    if s['size'] != 16 or s['part'] not in ['load_data', 'store_data']: continue
                    assert pf['jit_block_ends'][s['region_start']] == s['region_end']
                    hits = pf['jit_blocks'][s['region_start']]
                    offset = s['offset']
                    while offset + 8 <= s['end']:
                        decoded = pair(*struct.unpack_from('<II', code, offset))
                        if decoded is None: offset += 4; continue
                        assert decoded['kind'] + '_data' == s['part']
                        key = s['operation'] + '/' + s['part']
                        static[key] += 1; weighted[key] += hits
                        site = dict(function=fid, name=f['name'], pc=s['pc'],
                            offset=offset, operation=s['operation'], hits=hits, samples=0, **decoded)
                        for pc in [offset, offset + 4]:
                            assert pc not in by_pc; by_pc[pc] = len(sites)
                        sites.append(site); offset += 8
            omitted = [fid for fid, pf in enumerate(profile['functions']) if fid not in represented and any(pf['jit_blocks'])]
            assert not omitted
            samples = Counter(); ambiguous = []
            for root in parse_tree((folder / 'sample.txt').read_text()):
                for n, frame, _ in self_samples(root):
                    if '<unknown binary>' not in frame: continue
                    assert '...' not in frame
                    offsets = [int(a, 16) - mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)', frame)]
                    assert offsets and all(0 <= o < len(code) and o % 4 == 0 for o in offsets)
                    ids = {by_pc.get(o) for o in offsets}
                    if len(ids) != 1:
                        ambiguous.append(dict(samples=n, offsets=offsets)); samples['ambiguous'] += n
                    elif next(iter(ids)) is None: samples['other'] += n
                    else:
                        site = sites[next(iter(ids))]; site['samples'] += n
                        samples['eligible_' + site['kind']] += n
            previous = old['cases'][index]
            assert previous['case'] == label and sum(samples.values()) == previous['generated_samples']
            case = dict(case=label, functions=len(represented), pairs=len(sites),
                static_pairs_by_detail=dict(static), weighted_pair_executions=dict(weighted),
                potential_emitted_words_removed=sum(static.values()),
                samples=dict(samples), generated_samples=sum(samples.values()), ambiguous=ambiguous,
                omitted_executed_functions=omitted, logical_accounting=accounting,
                top_sampled_sites=sorted(sites, key=lambda s:(-s['samples'], -s['hits']))[:30])
            write(work / (label + '.json'), dict(case=case, sites=sites))
            cases.append(case)
            print(label, 'pairs', len(sites), 'samples', dict(samples), flush=True)
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results' / args.run_id; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', cases=cases, decoder_tests=3,
            assembler_controls=4, guest_commands=0, executable_code_publications=0,
            performance_measurement=False, raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'), records_sha256=sha(work/'records.json'),
            reports={label:sha(work/(label+'.json')) for label in ['block','exhaustive']},
            limitation='Affected samples cover both old instructions, not eliminated execution time. Weights and short sampled windows have different entropy provenance; no timing or runtime change is claimed.'))


if __name__ == '__main__': main()
