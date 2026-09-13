"""Identify exact existing clear/copy loops within the already attributed samples."""
from bisect import bisect_right
from collections import Counter
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from summarize_owned_sample import parse_tree, self_samples
from workflow_io import require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 8)
        proof_path = ROOT / 'results/native-protocol-census-01/attribution.json'
        proof = json.loads(proof_path.read_text()); assert proof['status'] == 'passed'
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), proof_path,
            ROOT / 'scripts/summarize_owned_sample.py', ROOT / 'scripts/compare_saved_runtime.py',
            ROOT / 'scripts/workflow_io.py']}
        output = []
        clear = [0xa9007d7f, 0xa9017d7f, 0xa9027d7f, 0xa9037d7f,
                 0x9101016b, 0xd1010129, 0xeb0a013f, 0x54ffff22]
        copy_tail = [0xeb0b019f, 0x54000109, 0x8b09016b, 0x8b09018c,
            0x385ffd6a, 0x381ffd8a, 0xf1000529, 0x54ffffa1, 0x14000005,
            0x3840156a, 0x3800158a, 0xf1000529, 0x54ffffa1, 0xd503201f]
        for case in proof['cases']:
            for p, h in case['evidence'].items(): assert sha(ROOT / p) == h; frozen[p] = h
            label = case['case']; folder = ROOT / '.work' / ('adopted-runtime-sample-' + label + '-01') / '0'
            mapping = json.loads((folder / 'jit-code/operations.json').read_text())
            spans = json.loads((ROOT / '.work/native-protocol-census-01' / (label + '.json')).read_text())['spans']
            starts = [s['offset'] for s in spans]
            raw = (folder / 'jit-code/code.bin').read_bytes()
            static, samples, sizes = Counter(), Counter(), Counter()
            ownership = {}
            for span in spans:
                if span['kind'] not in ['call_frame_clear', 'argument_copy', 'result_copy']: continue
                words = [int.from_bytes(raw[i:i+4], 'little') for i in range(span['offset'], span['end'], 4)]
                kinds = [span['kind'] + '/other'] * len(words)
                if span['kind'] == 'call_frame_clear':
                    hits = [i for i in range(len(words)-len(clear)+1) if words[i:i+len(clear)] == clear]
                    assert len(hits) <= 1
                    if hits:
                        i, = hits; kinds[i:i+len(clear)] = ['clear_64_byte_loop'] * len(clear)
                        static['clear_64_byte_loop'] += 1
                elif len(words) == 15 and words[0] & 0xffe0001f == 0xd2800009 and words[1:] == copy_tail:
                    size = (words[0] >> 5) & 65535; assert size > 128
                    for i in [5, 6, 7, 8, 10, 11, 12, 13]: kinds[i] = 'abi_byte_copy_loop/' + str(size)
                    static['abi_byte_copy_loop'] += 1
                for i, kind in enumerate(kinds): ownership[span['offset'] + i*4] = kind
            for root in parse_tree((folder / 'sample.txt').read_text()):
                for count, frame, _ in self_samples(root):
                    if '<unknown binary>' not in frame: continue
                    assert '...' not in frame
                    offsets = [int(a, 16) - mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)', frame)]
                    labels = {ownership.get(o) for o in offsets}
                    if labels == {None}: continue
                    assert None not in labels
                    if len(labels) != 1: samples['mixed_loop_parts'] += count; continue
                    kind, = labels
                    samples[kind] += count
            expected = sum(case['fine_samples'].get(k, 0) for k in
                ['Call/call_frame_clear', 'Call/argument_copy', 'Return/result_copy'])
            assert sum(samples.values()) == expected
            output.append(dict(case=label, target_samples=expected, generated_samples=case['generated_samples'],
                exact_loop_samples=dict(samples.most_common()), static_loop_sites=dict(static)))
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        path = ROOT / 'results/native-protocol-census-01/loop-parts.json'; assert not path.exists()
        write(path, dict(status='passed', cases=output, evidence=frozen, guest_commands=0,
            performance_measurement=False, limitation='Exact existing opcode-sequence matches. Unmatched instructions remain other; partial perturbed samples are not performance measurements.'))
        for case in output: print(json.dumps(case))


if __name__ == '__main__': main()
