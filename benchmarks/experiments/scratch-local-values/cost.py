"""Refine saved scratch opportunities with original self-PCs; no guest execution."""
from bisect import bisect_right
from collections import Counter
from pathlib import Path
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from summarize_owned_sample import parse_tree, self_samples
from workflow_io import require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 8)
        output = ROOT / 'results/scratch-local-values-cost-01'
        output.mkdir(exist_ok=False)
        evidence = {str(Path(__file__).relative_to(ROOT)): sha(Path(__file__))}
        cases = []
        for index, label in enumerate(['block', 'exhaustive']):
            folder = ROOT / '.work' / ('adopted-runtime-sample-' + label + '-01') / '0'
            observed_path = ROOT / '.work/scratch-local-values-census-01' / (label + '.json')
            observed = json.loads(observed_path.read_text())
            proof_path = ROOT / 'results/scratch-local-values-census-01/attribution.json'
            proof = json.loads(proof_path.read_text())
            assert proof['status'] == 'passed'
            assert all(sha(ROOT/p) == h for p,h in proof['evidence'].items())
            old_path = ROOT / 'results' / ('adopted-runtime-sample-' + label + '-01') / 'operation-attribution.json'
            old = json.loads(old_path.read_text())
            assert old['status'] == 'passed' and old['unassigned_generated_samples'] == 0
            assert all(sha(ROOT/p) == h for p,h in old['evidence'].items())
            map_path = folder / 'jit-code/operations.json'; mapping = json.loads(map_path.read_text())
            code_path = folder / 'jit-code/code.bin'; code = code_path.read_bytes()
            assert observed['code_sha256'] == mapping['code_sha256'] == sha(code_path)
            profile_path = ROOT / '.work/guarded-local-facts-profile-01' / (str(index) + '-profile.json')
            profile = json.loads(profile_path.read_text())
            eligible = {(f['function'], h['pc']) for f in observed['functions'] for h in f['available_scratch_values']}
            rows = [dict(s, function=f['function']) for f in mapping['functions'] for s in f['spans'] if s['offset'] < s['end']]
            starts = [r['offset'] for r in rows]; assert starts == sorted(set(starts))
            def locate(offset):
                i = bisect_right(starts, offset)-1
                assert i >= 0 and rows[i]['offset'] <= offset < rows[i]['end'] and offset % 4 == 0
                return rows[i]
            weighted_all = weighted_eligible = eligible_words = 0
            word_histogram = Counter()
            for row in rows:
                if row['pc'] is None: continue
                words = (row['end']-row['offset'])//4
                hits = profile['functions'][row['function']]['jit_blocks'][row['region_pc']]
                weighted_all += words * hits
                if (row['function'],row['pc']) in eligible:
                    assert row['kind'] == 'operation'
                    word_histogram[words] += 1; eligible_words += words
                    weighted_eligible += words * hits
            affected = Counter(); generated = 0
            for root in parse_tree((folder/'sample.txt').read_text()):
                for count, frame, _ in self_samples(root):
                    if '<unknown binary>' not in frame: continue
                    assert '...' not in frame
                    offsets = [int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)]
                    assert offsets
                    spans = [locate(o) for o in offsets]
                    identities = {(s['function'],s['pc'],s['kind']) for s in spans}
                    assert len(identities) == 1
                    generated += count
                    s = spans[0]
                    if (s['function'],s['pc']) in eligible:
                        # These whole Load spans also include result publication,
                        # which a load substitution must retain.
                        affected[(s['function'],s['pc'])] += count
            assert generated == old['attributed_generated_samples']
            cases.append(dict(case=label,eligible_loads=len(eligible),static_eligible_whole_load_words=eligible_words,
                whole_load_word_histogram=dict(sorted(word_histogram.items())),
                weighted_all_mapped_operation_words=weighted_all,weighted_eligible_whole_load_words=weighted_eligible,
                generated_samples=generated,whole_eligible_load_samples=sum(affected.values()),
                top_sampled_sites=[dict(function=f,pc=pc,samples=n) for (f,pc),n in affected.most_common(15)]))
            for p in [observed_path,proof_path,old_path,map_path,code_path,profile_path,folder/'sample.txt']:
                evidence[str(p.relative_to(ROOT))] = sha(p)
        assert all(sha(ROOT/p) == h for p,h in evidence.items())
        write(output/'summary.json',dict(status='passed',cases=cases,evidence=evidence,guest_commands=0,
            source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            performance_measurement=False,limitation='Whole eligible Load spans include required result publication. Frequency-weighted static operation words include untaken paths and exclude non-operation spans; they are not retired instructions or a runtime bound. Samples are the two existing short perturbed windows. No speedup claim.'))
        for c in cases: print(json.dumps({k:v for k,v in c.items() if k != 'top_sampled_sites'}))


if __name__ == '__main__': main()
