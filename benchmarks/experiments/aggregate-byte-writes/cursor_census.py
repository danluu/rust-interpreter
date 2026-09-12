#!/usr/bin/env python3
"""Split verified x19 memory samples by the pinned resumable cursor field."""
from collections import Counter
import argparse
import fcntl
import json
from pathlib import Path
import re
import struct

from build_relocation import ROOT, HERE, read, write, sha, require
import attribute_generated_sample as generated
from summarize_owned_sample import parse_tree, self_samples

FIELDS = ['remaining', 'profile_hits', 'memory_len', 'peak_linear', 'register_len',
          'frame_len', 'calls', 'returns', 'frames', 'registers', 'entries', 'profiles',
          'memory_end', 'register_end', 'frame_end', 'frame_limit', 'working_budget']
LAYOUT = {8 * i: name for i, name in enumerate(FIELDS)}
LAYOUT_SOURCES = ['crates/bytecode/src/native_continuation.rs', 'crates/bytecode/src/jit/resumable.rs']


def decode(word):
    kind = word & 0xffc003e0
    if kind not in [0xf9400260, 0xf9000260]:
        return None
    offset = ((word >> 10) & 4095) * 8
    if offset not in LAYOUT:
        return None
    return LAYOUT[offset], 'load' if kind == 0xf9400260 else 'store'


def agreed(words):
    decoded = [decode(word) for word in words]
    return decoded[0] if decoded and decoded[0] is not None and len(set(decoded)) == 1 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'aggregate-relocation-cursor-census-[0-9]{2}', args.run_id), 'unexpected census run ID')
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Fixed examples taken from the emitter's load64/store64 ABI, plus
        # sampler-group ambiguities. No generated round-trip encoder oracle.
        require(decode(0xf9400269) == ('remaining', 'load') and
                decode(0xf9000269) == ('remaining', 'store') and
                decode(0xf9402269) == ('frames', 'load'), 'known ABI words differ')
        rejected = [0xf9400009, 0xb9400269, 0xf9422269]
        require(all(decode(w) is None for w in rejected) and
                agreed([0xf9400269, 0xf940026a]) == ('remaining', 'load') and
                agreed([0xf9400269, 0xf9000269]) is None and
                agreed([0xf9400269, 0xf9402269]) is None and agreed([]) is None,
                'foreign access or ambiguous sampler group accepted')
        source_texts = [(ROOT/p).read_text() for p in LAYOUT_SOURCES]
        for offset, field in LAYOUT.items():
            text = source_texts[int(offset >= 64)]
            require(re.search(r'\b'+field.upper()+r'\s*==\s*'+str(offset)+r'\b', text),
                    'pinned compiled layout assertion missing: '+field)
        evidence = {p: sha(ROOT/p) for p in LAYOUT_SOURCES}
        cases = []
        for label in ['folded', 'token']:
            run = 'aggregate-relocation-'+label+'-sample-01'
            work, out = ROOT/'.work'/run, ROOT/'results'/run
            report, attribution, plan = read(out/'summary.json'), read(out/'generated-attribution.json'), read(work/'plan.json')
            provenance = read(out/'execution-provenance.json')
            require(provenance['status'] == 'verified' and provenance['profiled_executions'] == 3 and
                    all(sha(ROOT/p) == h for p, h in provenance['evidence'].items()) and
                    all(plan['source_files'][p] == evidence[p] for p in LAYOUT_SOURCES),
                    'profile/layout provenance changed')
            counts, kinds, ambiguous, samples = Counter(), {}, 0, []
            for index, sample in enumerate(report['samples']):
                folder = work/str(index)
                actual = generated.attribute(folder, sample)
                require(json.loads(json.dumps(actual)) == attribution['samples'][index], 'original attribution differs')
                code = (folder/'jit-code/code.bin').read_bytes()
                mapping = read(folder/'jit-code/map.json')
                old_classes, _ = generated.classify_words(code, resumable=True)
                per_sample, unresolved = Counter(), 0
                for root in parse_tree((folder/'sample.txt').read_text()):
                    for count, frame, _ in self_samples(root):
                        if '<unknown binary>' not in frame:
                            continue
                        addresses = [int(a, 16) for a in re.findall(r'0x([0-9a-f]+)', frame)]
                        if '...' in frame or not addresses:
                            continue  # Not part of the prior exact cursor category.
                        offsets = [address-mapping['arena_base'] for address in addresses]
                        require(all(0 <= off < len(code) and off % 4 == 0 for off in offsets), 'foreign code PC')
                        if any(old_classes[off//4] != 'cursor_load_store' for off in offsets):
                            continue
                        ranges = [next(r for r in mapping['ranges'] if r['offset'] <= off < r['end']) for off in offsets]
                        # Apply the original attribution's identity criterion.
                        if len({(r['kind'], r['function']) for r in ranges}) != 1:
                            continue
                        field = agreed([struct.unpack_from('<I', code, off)[0] for off in offsets])
                        if field is None:
                            unresolved += count
                            continue
                        key = field[0]+':'+field[1]
                        per_sample[key] += count
                        kinds.setdefault(ranges[0]['kind'], Counter())[key] += count
                require(sum(per_sample.values())+unresolved == actual['by_instruction_class'].get('cursor_load_store', 0),
                        'sample cursor counts do not reconcile')
                counts.update(per_sample)
                ambiguous += unresolved
                samples.append(dict(index=index, fields=dict(per_sample), ambiguous=unresolved))
            total = attribution['by_instruction_class']['cursor_load_store']
            require(sum(counts.values())+ambiguous == total, 'total cursor counts differ')
            cases.append(dict(label=label, thread_samples=report['total_samples'], cursor_samples=total,
                fields=dict(counts.most_common()), ambiguous=ambiguous, samples=samples,
                by_entry_kind={k: dict(v) for k, v in kinds.items()},
                percentage_of_thread_samples={k: 100*v/report['total_samples'] for k,v in counts.most_common()}))
            for name in ['summary.json', 'generated-attribution.json', 'execution-provenance.json']:
                p = out/name
                evidence[str(p.relative_to(ROOT))] = sha(p)
        for p in [Path(__file__), HERE/'CURSOR-CENSUS-NEXT.md', ROOT/'scripts/attribute_generated_sample.py']:
            evidence[str(p.relative_to(ROOT))] = sha(p)
        out = ROOT/'results'/args.run_id
        out.mkdir(exist_ok=False)
        write(out/'summary.json', dict(status='passed', cases=cases, evidence=evidence,
            decoder_examples=3, rejected_foreign_words=3, sampler_group_checks=4,
            new_guest_executions=0, performance_measurement=False))
        for case in cases:
            print(dict(label=case['label'], cursor_samples=case['cursor_samples'], ambiguous=case['ambiguous'],
                       fields=case['fields']))


if __name__ == '__main__':
    main()
