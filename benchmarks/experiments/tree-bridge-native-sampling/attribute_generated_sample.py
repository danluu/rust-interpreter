#!/usr/bin/env python3
"""Attribute sampled generated PCs using code dumped by that same process."""
import argparse
from bisect import bisect_right
from collections import Counter
import json
from pathlib import Path
import re
import struct

from summarize_owned_sample import ROOT, require, sha, parse_tree, self_samples

# Exact sequences from Assembler::zero_range and the large ABI memmove loops.
# Match complete sequences, including their local branch displacements.
ZERO_RANGE = (0xcb0b0189, 0xd280020a, 0xeb0a013f, 0x54000063, 0xa8817d7f,
              0x17fffffb, 0xeb0c017f, 0x54000060, 0x3800157f, 0x17fffffd)
# Assembler::zero_range_at_least's 64-byte loop, including the entry setup.
# Require its complete exact tail too; classify that tail with ZERO_RANGE so
# the categories remain disjoint and historical small-loop reports unchanged.
ZERO_BULK_PREFIX = (0xcb0b0189, 0xd280080a, 0xa9007d7f, 0xa9017d7f,
                    0xa9027d7f, 0xa9037d7f, 0x9101016b, 0xd1010129,
                    0xeb0a013f, 0x54ffff22)
ZERO_BULK = ZERO_BULK_PREFIX + ZERO_RANGE
COPY_BACKWARD = (0x385ffd6a, 0x381ffd8a, 0xf1000529, 0x54ffffa1)
COPY_FORWARD = (0x3840156a, 0x3800158a, 0xf1000529, 0x54ffffa1)


def classify_words(data, resumable=False, bulk_zero=False):
    require(len(data) % 4 == 0, 'unaligned AArch64 code bytes')
    words = [w[0] for w in struct.iter_unpack('<I', data)]
    classes = []
    for w in words:
        # These instructions use x0 as the current u128 register-array base
        # throughout the emitter's internal ABI. Large computed offsets are
        # deliberately left unclassified here.
        direct = w & 0xffc003e0
        if direct == 0xf9400000:
            kind = 'direct_register_array_load'
        elif direct == 0xf9000000:
            kind = 'direct_register_array_store'
        elif direct in (0xf9400260, 0xf9000260):
            kind = 'cursor_load_store'
        elif resumable and direct in (0xf9400280, 0xf9000280, 0x39400280, 0x39000280):
            # x20 holds the current guest Frame only in the resumable ABI.
            kind = 'frame_descriptor_load_store'
        else:
            kind = 'other_generated'
        classes.append(kind)
    sequences = Counter()
    for i, w in enumerate(words):
        if (resumable or bulk_zero) and w == ZERO_BULK[0] and tuple(words[i:i + len(ZERO_BULK)]) == ZERO_BULK:
            classes[i:i + len(ZERO_BULK_PREFIX)] = ['native_zero_bulk'] * len(ZERO_BULK_PREFIX)
            sequences['native_zero_bulk'] += 1
        for pattern, kind in [(ZERO_RANGE, 'native_zero_range'),
                              (COPY_BACKWARD, 'native_abi_byte_copy'),
                              (COPY_FORWARD, 'native_abi_byte_copy')]:
            if w == pattern[0] and tuple(words[i:i + len(pattern)]) == pattern:
                classes[i:i + len(pattern)] = [kind] * len(pattern)
                sequences[kind] += 1
    return classes, dict(sequences)


def classify_ranges(code,ranges,resumable):
    classes=[];sequences=Counter();end=0
    for row in ranges:
        require(row['offset']==end and row['end']>end and row['end']%4==0 and row['end']<=len(code), 'invalid class partition')
        tree=row['kind']=='native_tree'
        local,found=classify_words(code[end:row['end']],resumable=resumable and not tree,bulk_zero=resumable)
        # x20 is a return destination in trees, not a Frame descriptor. Keep
        # ordinary classifications local to their actual ABI and entry range.
        if tree and resumable:
            for i,(word,) in enumerate(struct.iter_unpack('<I',code[end:row['end']])):
                if word & 0xffc003ff == 0xd10002d6 and 1 <= (word>>10)&0xfff <= 1024:
                    local[i]='tree_register_budget_debit'
        if resumable:
            fields={0:'remaining',8:'profile',16:'live_memory',24:'peak_memory',
                32:'register_length',40:'frame_length',48:'call_count',56:'return_count',
                64:'frames_pointer',72:'register_pointer',80:'entry_table',88:'profile_table',
                96:'memory_bound',104:'register_bound',112:'depth_bound',120:'working_bound',
                184:'tree_profile_table',224:'tree_frames_pointer',232:'tree_register_pointer',
                240:'tree_depth',248:'tree_fault_depth',256:'tree_fault_register_end',
                264:'tree_instruction_count',272:'tree_call_count',280:'tree_entry_count'}
            for i,(word,) in enumerate(struct.iter_unpack('<I',code[end:row['end']])):
                if local[i]=='cursor_load_store':
                    local[i]='cursor_load_store:'+fields.get(((word>>10)&0xfff)*8,'other_field')
        classes.extend(local);sequences.update(found);end=row['end']
    require(end==len(code), 'incomplete class partition')
    return classes,dict(sequences)


def dump_options(dump, command):
    for field, flag in [('native_call_stubs', '--jit-native-call-stubs'),
                        ('persistent_registers', '--jit-persistent-registers'),
                        ('resumable_calls', '--jit-resumable-calls')]:
        require(type(dump.get(field, False)) is bool, 'invalid dumped runtime option type')
        require(dump.get(field, False) == (flag in command), 'dumped runtime option differs from command')
    resumable = dump.get('resumable_calls', False)
    require(not resumable or not any(f in command for f in ['--jit-native-calls', '--jit-native-call-stubs']),
            'incompatible dumped runtime options')
    bridge = '--jit-tree-bridge' in command
    require(not bridge or resumable, 'tree bridge requires resumable calls')
    require(not bridge or '--jit-operation-map' not in command, 'bridge operation maps are unsupported')
    allowed = ({'resumable_region', 'resumable_call', 'resumable_return'} if resumable else
               {'ordinary_region'} | ({'call_stub'} if '--jit-native-call-stubs' in command else set()) |
               ({'native_tree'} if '--jit-native-calls' in command else set()))
    if bridge: allowed |= {'native_tree'}
    require(all(r['kind'] in allowed for r in dump['ranges']), 'dumped range kind differs from runtime options')
    return resumable


def attribute(folder, sample_summary):
    record = json.loads((folder / 'record.json').read_text())
    for path, digest in record['files'].items():
        require(sha(folder / path) == digest, 'diagnostic evidence changed')
    dump_path = folder / 'jit-code/map.json'
    dump = json.loads(dump_path.read_text())
    require(dump['schema_version'] == 1 and dump['architecture'] == 'aarch64' and dump['byte_order'] == 'little', 'unsupported code dump')
    require(dump['pid'] == record['identity']['pid'] == sample_summary['pid'], 'code/sample PID mismatch')
    code_path = folder / 'jit-code/code.bin'
    code = code_path.read_bytes()
    require(len(code) == dump['code_bytes'] == record['statistics']['jit_bytes'], 'dump length mismatch')
    require(not dump['profiled'], 'instruction-profile instrumentation enabled')
    command = record['identity']['command']
    resumable = dump_options(dump, command)
    ranges = dump['ranges']
    end = 0
    for row in ranges:
        require(row['offset'] == end and row['end'] > end and row['end'] % 4 == 0, 'nonpartitioning code ranges')
        end = row['end']
    require(end == len(code), 'range/code length mismatch')
    base = dump['arena_base']
    require(any(lo == base and base + len(code) <= hi for lo, hi in sample_summary['generated_address_ranges']), 'dump is not inside sampled process arena')
    classes, sequences = classify_ranges(code,ranges,resumable)
    offsets = [r['offset'] for r in ranges]
    by_kind, by_class, by_function = Counter(), Counter(), Counter()
    by_kind_class = {}
    unresolved = []
    for root in parse_tree((folder / 'sample.txt').read_text()):
        for count, frame, _ in self_samples(root):
            if '<unknown binary>' not in frame:
                continue
            addresses = [int(a, 16) for a in re.findall(r'0x([0-9a-f]+)', frame)]
            if '...' in frame or not addresses:
                unresolved.append(dict(count=count, frame=frame)); continue
            identities = []
            for address in addresses:
                offset = address - base
                require(0 <= offset < len(code) and offset % 4 == 0, 'sample PC outside dumped published code')
                row = ranges[bisect_right(offsets, offset) - 1]
                identities.append((row['kind'], classes[offset // 4], row['function']))
            if len(set(identities)) != 1:
                unresolved.append(dict(count=count, frame=frame)); continue
            kind, word_class, function = identities[0]
            by_kind[kind] += count
            by_class[word_class] += count
            by_function[(kind, function)] += count
            by_kind_class.setdefault(kind, Counter())[word_class] += count
    total = sum(by_kind.values())
    require(total + sum(r['count'] for r in unresolved) == sample_summary['disjoint_counts'].get('generated_code', 0) + sample_summary['disjoint_counts'].get('unresolved_unknown_binary', 0), 'generated counts do not reconcile')
    result = dict(index=record['index'], pid=dump['pid'], generated_samples=total,
        by_entry_kind=dict(by_kind), by_instruction_class=dict(by_class),
        by_function=[dict(kind=k, function=f, samples=n) for (k, f), n in by_function.most_common()],
        exact_sequence_occurrences=sequences, unresolved=unresolved,
        code_sha256=sha(code_path), map_sha256=sha(dump_path))
    if resumable:
        result['by_entry_instruction_class'] = {k: dict(v) for k, v in by_kind_class.items()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ('.', '..'), 'invalid run ID')
    work = ROOT / '.work' / args.run_id
    plan = json.loads((work / 'plan.json').read_text())
    require(plan['dump_code'], 'no code capture requested')
    report_path = ROOT / 'results' / args.run_id / 'summary.json'
    report = json.loads(report_path.read_text())
    samples = [attribute(work / str(s['index']), s) for s in report['samples']]
    kinds, classes = Counter(), Counter()
    for s in samples:
        kinds.update(s['by_entry_kind']); classes.update(s['by_instruction_class'])
    total = report['total_samples']
    result = dict(tool_key=report['tool_key'], vm_sha256=report['vm_sha256'], samples=samples,
        total_thread_samples=total, attributed_generated_samples=sum(kinds.values()),
        by_entry_kind=dict(kinds), by_instruction_class=dict(classes),
        percentage_of_thread_samples={k: 100 * n / total for k, n in classes.items()},
        performance_measurement=False,
        limitation='Partial perturbed windows. Exact emitted sequences and direct register/cursor accesses only; all other instructions remain grouped. Entry kinds include wrappers and failure tails. This is not an opcode cost model or speedup prediction.',
        evidence={str(p.relative_to(ROOT)): sha(p) for p in [report_path, Path(__file__)]})
    path = report_path.with_name('generated-attribution.json')
    with path.open('x') as output:
        json.dump(result, output, indent=2); output.write('\n')
    print(json.dumps(dict(kinds=dict(kinds), classes=dict(classes), percentages=result['percentage_of_thread_samples'])))


if __name__ == '__main__':
    main()
