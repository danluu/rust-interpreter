#!/usr/bin/env python3
"""Count exact checked_address sequences in same-process native samples."""
import argparse
from bisect import bisect_right
from collections import Counter
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from attribute_generated_sample import attribute
from summarize_owned_sample import parse_tree, require, self_samples, sha


def three(op, dst, left, right):
    return op | right << 16 | left << 5 | dst


def decode(words, start):
    """Recognize complete heap-aware static-size checks, including all exits.

    This is a source-bound diagnostic recognizer, not an AArch64 disassembler.
    Branch displacements must resolve to the same forward memory-fault tail.
    The materialized size may use MOVK, exactly as Assembler::imm emits it.
    """
    if words[start:start + 2] != [0xd280000e, 0xf2e8000e]:
        return None
    if start + 17 > len(words):
        return None
    address = (words[start + 2] >> 5) & 31
    if address not in (9, 10, 11, 12):
        return None
    expected = [three(0xeb000000, 31, address, 14),
                three(0xcb000000, 13, address, 14)]
    for dst, linear, heap in [(address, address, 13), (17, 2, 7),
                              (15, 3, 8), (14, 4, 31)]:
        expected.append(0x9a800000 | heap << 16 | 3 << 12 | linear << 5 | dst)
    if words[start + 2:start + 8] != expected:
        return None
    i = start + 8
    exits = []

    def guard(compare, condition):
        nonlocal i
        if i + 2 > len(words) or words[i] != compare:
            return False
        branch = words[i + 1]
        if branch & 0xff00001f != 0x54000000 | condition:
            return False
        displacement = (branch >> 5) & 0x7ffff
        if displacement & 0x40000:
            displacement -= 0x80000
        exits.append(i + 1 + displacement)
        i += 2
        return True

    if not guard(three(0xeb000000, 31, address, 31), 0):
        return None
    if not guard(three(0xeb000000, 31, address, 15), 8):
        return None
    if words[i] != three(0xcb000000, 15, 15, address):
        return None
    i += 1
    if words[i] & 0xffe0001f != 0xd280000d:
        return None
    size = (words[i] >> 5) & 0xffff
    i += 1
    shift = 0
    while i < len(words) and words[i] & 0xff80001f == 0xf280000d:
        next_shift = ((words[i] >> 21) & 3) * 16
        part = (words[i] >> 5) & 0xffff
        if next_shift <= shift or not part:
            return None
        shift = next_shift
        size |= part << shift
        i += 1
    if not size or not guard(three(0xeb000000, 31, 15, 13), 3):
        return None
    write = i < len(words) and words[i] == three(0xeb000000, 31, address, 14)
    if write and not guard(three(0xeb000000, 31, address, 14), 3):
        return None
    if i >= len(words) or words[i] != three(0x8b000000, address, 17, address):
        return None
    end = i + 1
    if len(set(exits)) != 1 or not end <= exits[0] < len(words):
        return None
    return dict(start=start, end=end, translation_end=start + 8,
                address=address, size=size, write=write, fault=exits[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ('.', '..'), 'invalid run ID')
    work = ROOT / '.work' / args.run_id
    plan = json.loads((work / 'plan.json').read_text())
    source = ROOT / 'crates/bytecode/src/jit.rs'
    require(sha(source) == plan['source_files'][str(source.relative_to(ROOT))], 'sampled emitter source differs')
    report_path = ROOT / 'results' / args.run_id / 'summary.json'
    report = json.loads(report_path.read_text())
    totals, functions, samples = Counter(), Counter(), []
    names = {}
    for sample in report['samples']:
        folder = work / str(sample['index'])
        attribute(folder, sample)  # Verify code, map, PID, arena, options and sampled PCs.
        dump = json.loads((folder / 'jit-code/map.json').read_text())
        words = [w[0] for w in struct.iter_unpack('<I', (folder / 'jit-code/code.bin').read_bytes())]
        ranges = dump['ranges']
        starts = [r['offset'] for r in ranges]
        classes, occurrences = {}, Counter()
        for i, word in enumerate(words):
            if word != 0xd280000e:
                continue
            seq = decode(words, i)
            if seq is None:
                continue
            row = ranges[bisect_right(starts, i * 4) - 1]
            require(seq['end'] * 4 <= row['end'] and seq['fault'] * 4 < row['end'], 'sequence crosses entry')
            names[row['function']] = row['name']
            occurrences['write' if seq['write'] else 'read'] += 1
            for at in range(i, seq['end']):
                require(at not in classes, 'overlapping recognized sequences')
                part = 'tag_translation' if at < seq['translation_end'] else 'bounds_and_address'
                classes[at] = (part, row['function'], row['kind'])
        local, ambiguous = Counter(), 0
        for root in parse_tree((folder / 'sample.txt').read_text()):
            for count, frame, _ in self_samples(root):
                if '<unknown binary>' not in frame:
                    continue
                identities = [classes.get((int(a, 16) - dump['arena_base']) // 4)
                              for a in re.findall(r'0x([0-9a-f]+)', frame)]
                if not identities or '...' in frame or len(set(identities)) != 1:
                    ambiguous += count
                elif identities[0] is not None:
                    part, fid, kind = identities[0]
                    local[part] += count
                    functions[(fid, kind)] += count
        totals.update(local)
        samples.append(dict(index=sample['index'], pid=sample['pid'], counts=dict(local),
                            exact_sequences=dict(occurrences), ambiguous_generated_samples=ambiguous))
    result = dict(status='passed', total_thread_samples=report['total_samples'],
                  checked_address_samples=sum(totals.values()), counts=dict(totals),
                  percentages={k: 100 * n / report['total_samples'] for k, n in totals.items()},
                  functions=[dict(function=f, name=names[f], entry_kind=k, samples=n)
                             for (f, k), n in functions.most_common()], samples=samples,
                  performance_measurement=False,
                  limitation='Partial perturbed windows; exact heap-aware static-size address sequences only. Shares do not predict speedup.',
                  evidence={str(p.relative_to(ROOT)): sha(p) for p in
                            [source, Path(__file__), report_path, work / 'plan.json']})
    with report_path.with_name('address-attribution.json').open('x') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps({k: result[k] for k in ['checked_address_samples', 'counts', 'percentages']}))


if __name__ == '__main__':
    main()
