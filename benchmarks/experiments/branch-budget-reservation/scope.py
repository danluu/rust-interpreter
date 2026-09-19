"""Join the abstract budget model to immutable native code and profile evidence."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from model import Region, plan

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'benchmarks/experiments/adopted-hot-loop-census-v2'))
sys.path.insert(0, str(ROOT/'benchmarks/experiments/scratch-memory-values'))
from graph import successors
from summarize_owned_sample import parse_tree, self_samples
from native_observation import logical_counts
from workflow_io import require_space


def read(path):
    assert path.stat().st_size <= 256*1024**2
    return json.loads(path.read_text())


def budget_words(words, cost):
    return (len(words) == 4 and 1 <= cost <= 1024
        and words[0] == (0xd280000a | (cost << 5))
        and words[1] == 0xeb0a02df
        and words[2] & 0xff00001f == 0x54000003
        and words[3] == 0xcb0a02d6)


def case(index, label):
    require_space(ROOT, 8)
    folder = ROOT/'.work'/('adopted-current-sample-'+label+'-02')/'0'
    native = read(folder/'jit-code/map.json')
    mapping = read(folder/'jit-code/operations.json')
    code = (folder/'jit-code/code.bin').read_bytes()
    assert native['profiled'] is False and hashlib.sha256(code).hexdigest() == mapping['code_sha256']
    assert mapping['complete'] and mapping['reconstructed_bytes_match']
    profile = read(ROOT/'.work/compact-switch-current-host-01/adopted'/f'{index}-profile.json')
    _, totals = logical_counts(profile)
    loop_details = read(ROOT/'.work/adopted-hot-loop-census-02'/(label+'-details.json'))
    by_label = Counter()
    for site in loop_details['sites']:
        by_label[site['label']] += site['samples']
    spans = defaultdict(dict)
    for function in mapping['functions']:
        for span in function['spans']:
            if span['kind'] not in ['budget', 'range_guard']:
                continue
            key = (function['function'], span['region_pc'])
            assert span['kind'] not in spans[key]
            spans[key][span['kind']] = span
    functions = defaultdict(dict)
    metadata = {}
    for region in native['ranges']:
        if region['kind'] != 'resumable_region':
            continue
        fid, pc, end = region['function'], region['pc'], region['pc_end']
        f = profile['functions'][fid]
        assert 0 <= pc < end <= len(f['operations']) and end-pc <= 1024
        targets, _ = successors(f['operations'][end-1], end-1, len(f['operations']))
        s = spans[fid,pc]['budget']
        words = struct.unpack('<'+str((s['end']-s['offset'])//4)+'I', code[s['offset']:s['end']])
        assert budget_words(words, end-pc), (fid,pc,words)
        guarded = 'range_guard' in spans[fid,pc]
        if guarded:
            g = spans[fid,pc]['range_guard']
            assert g['end'] > g['offset']
        assert pc not in functions[fid]
        functions[fid][pc] = Region(end-pc, targets, guarded)
        hits = f['jit_blocks'][pc]
        assert type(hits) is int and hits >= 0
        assert hits == 0 or f['jit_block_ends'][pc] == end
        metadata[fid,pc] = (end, s, hits)
    predecessors=defaultdict(set)
    ordinary_end={}
    for (fid,pc),(end,_,_) in metadata.items():ordinary_end[fid,end-1]=pc
    for fid,nodes in functions.items():
        ops=profile['functions'][fid]['operations']
        for pc,op in enumerate(ops):
            targets,_=successors(op,pc,len(ops))
            for target in targets:
                if target in nodes:
                    predecessors[fid,target].add(ordinary_end.get((fid,pc),-1))
        if 0 in nodes:predecessors[fid,0].add(-1)
    rows, cmp_words, eligible_words, region_words, word_kinds = [], {}, {}, {}, {}
    counts = Counter()
    for fid, nodes in sorted(functions.items()):
        p = plan(nodes)
        counts['functions'] += 1
        for pc, node in sorted(nodes.items()):
            end, span, hits = metadata[fid,pc]
            fast = p['fast'][pc]
            incoming=predecessors[fid,pc]
            all_certified=bool(incoming) and all(source in p['fast'] and pc in p['fast'][source] for source in incoming)
            pending=p['credit'][pc]-node.cost
            refund_targets=[t for t in node.successors if pending-(p['credit'][t] if t in fast else 0)>0]
            row = dict(all_normal_predecessors_certified=all_certified,normal_predecessors=sorted(incoming),refund_successors=refund_targets,function=fid, pc=pc, end=end, cost=node.cost, guarded=node.guarded,
                successors=list(node.successors), credit=p['credit'][pc], fast_successors=list(fast),
                incoming_fast=pc in p['incoming'], extra_immediate=pc in p['extra_immediate'],
                budget_offset=span['offset'], logical_native_visits=hits,
                potential_budget_samples=0, budget_span_samples=0)
            rows.append(row)
            counts['regions'] += 1
            counts['logical_refund_edge_upper_bound'] += hits*bool(refund_targets)
            counts['logical_refund_edge_lower_bound'] += hits*bool(node.successors and set(refund_targets)==set(node.successors))
            counts['regions_with_pending_suffix'] += p['credit'][pc] > node.cost
            counts['range_guarded_regions'] += node.guarded
            counts['fast_edges'] += len(fast)
            counts['potential_fast_target_regions'] += row['incoming_fast']
            counts['logical_native_region_visits'] += hits
            counts['logical_extra_immediate_if_all_entries_checked'] += hits*row['extra_immediate']
            # These are flow bounds on normal completed region visits. They do
            # not identify edges in the separate partial native sample window.
            counts['logical_fast_edge_lower_bound'] += hits*bool(node.successors and set(fast)==set(node.successors))
            counts['logical_fast_edge_upper_bound'] += hits*bool(fast)
            counts['logical_fast_destination_upper_bound'] += hits*row['incoming_fast']
            for offset in range(span['offset'], span['end'], 4):
                assert offset not in region_words
                region_words[offset] = row
                word_kinds[offset] = ['materialize','compare','branch','debit'][(offset-span['offset'])//4]
                if row['incoming_fast']:
                    eligible_words[offset] = row
            for offset in [span['offset']+4, span['offset']+8]:
                cmp_words[offset] = row
    lower = counts['logical_fast_edge_lower_bound']
    upper = min(counts['logical_fast_edge_upper_bound'], counts['logical_fast_destination_upper_bound'])
    assert lower <= upper
    counts['logical_fast_edge_upper_bound'] = upper
    extra = counts['logical_extra_immediate_if_all_entries_checked']
    counts['nominal_budget_word_change_lower_bound'] = 2*counts['logical_refund_edge_lower_bound']-4*upper
    counts['nominal_budget_word_change_upper_bound'] = 2*counts['logical_refund_edge_upper_bound']-4*lower
    generated = budget_samples = cmp_samples = potential = ambiguous = 0
    partitions=Counter();potential_partitions=Counter();entry_partition=Counter()
    for root in parse_tree((folder/'sample.txt').read_text()):
        for n, frame, _ in self_samples(root):
            if '<unknown binary>' not in frame:
                continue
            assert '...' not in frame
            offsets = [int(a,16)-native['arena_base'] for a in re.findall(r'0x([0-9a-f]+)', frame)]
            assert offsets and all(0 <= o < len(code) and o%4==0 for o in offsets)
            generated += n
            if all(o in region_words for o in offsets):
                owners = {(region_words[o]['function'],region_words[o]['pc']) for o in offsets}
                assert len(owners)==1
                kinds={word_kinds[o] for o in offsets}
                partitions[next(iter(kinds)) if len(kinds)==1 else 'ambiguous'] += n
                budget_samples += n
                region_words[offsets[0]]['budget_span_samples'] += n
            if all(o in cmp_words for o in offsets):
                cmp_samples += n
            if all(o in eligible_words for o in offsets):
                kinds={word_kinds[o] for o in offsets}
                potential_partitions[next(iter(kinds)) if len(kinds)==1 else 'ambiguous'] += n
                entry_partition['all_normal_predecessors_certified' if eligible_words[offsets[0]]['all_normal_predecessors_certified'] else 'mixed_predecessors'] += n
                potential += n
                eligible_words[offsets[0]]['potential_budget_samples'] += n
            elif any(o in eligible_words for o in offsets):
                ambiguous += n
    assert generated == sum(by_label.values())
    assert potential <= budget_samples <= by_label['budget']
    assert cmp_samples <= budget_samples
    assert sum(partitions.values())==budget_samples and sum(potential_partitions.values())==potential
    assert sum(row['potential_budget_samples'] for row in rows)==potential
    summary = dict(case=label,generated_samples=generated,all_budget_samples=by_label['budget'],
        ordinary_budget_samples=budget_samples,ordinary_cmp_branch_samples=cmp_samples,
        potential_budget_samples=potential,ambiguous_potential_samples=ambiguous,
        potential_entry_classification=dict(entry_partition),instruction_samples=dict(partitions),potential_instruction_samples=dict(potential_partitions),
        potential_percent=100*potential/generated,counts=dict(counts),whole_test_fixed_entropy_logical=totals,
        top_sites=sorted((r for r in rows if r['potential_budget_samples']),
            key=lambda r:(-r['potential_budget_samples'],r['function'],r['pc']))[:20])
    return summary, rows
