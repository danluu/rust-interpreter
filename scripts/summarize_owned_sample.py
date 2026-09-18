#!/usr/bin/env python3
"""Report disjoint self samples, validating each fresh process and JIT mapping."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from vmmap_ranges import anonymous_executable_ranges

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def runtime_options(plan, commands):
    options = {k: plan.get(k, False) for k in
        ['jit_native_calls', 'jit_native_call_stubs', 'jit_persistent_registers', 'jit_resumable_calls', 'jit_scalar_calls']}
    require(all(type(v) is bool for v in options.values()), 'invalid runtime option type')
    require(not options['jit_native_call_stubs'] or options['jit_native_calls'], 'native stubs require native calls')
    require(not options['jit_resumable_calls'] or
            not (options['jit_native_calls'] or options['jit_native_call_stubs']), 'incompatible runtime options')
    require(not options['jit_scalar_calls'] or options['jit_resumable_calls'], 'scalar calls require resumable calls')
    for command in commands:
        for option, enabled in options.items():
            require(('--' + option.replace('_', '-') in command) == enabled,
                    'sampled runtime option differs from plan')
        require(type(plan.get('jit_operation_map', False)) is bool, 'invalid operation map option')
        require(('--jit-operation-map' in command) == plan.get('jit_operation_map', False),
                'sampled operation map option differs from plan')
    if plan.get('jit_operation_map', False):
        require(plan['dump_code'] and not options['jit_native_calls'] and not options['jit_native_call_stubs'],
                'incompatible operation map options')
        options['jit_operation_map'] = True
    return options


def parse_tree(sample):
    graph = sample.split('Call graph:', 1)[1].split('Total number in stack', 1)[0]
    roots, stack = [], []
    for line in graph.splitlines():
        match = re.match(r'^([ +!:|]*)([0-9]+) (.*)$', line)
        if not match:
            continue
        depth = len(match[1])
        node = dict(depth=depth, inclusive=int(match[2]), frame=match[3], children=[])
        while stack and stack[-1]['depth'] >= depth:
            stack.pop()
        if stack:
            stack[-1]['children'].append(node)
        else:
            require('Thread_' in node['frame'], 'unexpected call-graph root')
            roots.append(node)
        stack.append(node)
    require(roots, 'empty sample graph')
    return roots


def self_samples(node, ancestors=()):
    own = node['inclusive'] - sum(c['inclusive'] for c in node['children'])
    require(own >= 0, 'child samples exceed parent')
    if own:
        yield own, node['frame'], ancestors
    for child in node['children']:
        yield from self_samples(child, ancestors + (node['frame'],))


def summarize(folder):
    folder = folder.resolve()
    record = json.loads((folder / 'record.json').read_text())
    require(record['identity']['status'] == 'finished' and record['identity']['returncode'] == 0,
            'VM execution did not finish successfully')
    require(record['sample_returncode'] == 0 and record['mapped'], 'sample/mapping missing')
    require(not record['performance_measurement'], 'expected diagnostic record')
    require(all(sha(folder / p) == h for p, h in record['files'].items()), 'diagnostic file changed')
    sample = (folder / 'sample.txt').read_text()
    pid = re.search(r'^Analysis of sampling rust-interp-vm \(pid (\d+)\)', sample, re.M)
    require(pid and int(pid[1]) == record['identity']['pid'], 'sampled PID mismatch')
    ranges = anonymous_executable_ranges((folder / 'vmmap.stdout').read_text(), record['identity']['pid'])
    require(ranges, 'no generated-code mapping')
    roots = parse_tree(sample)
    total = sum(node['inclusive'] for node in roots)
    counts, frames, unknown = Counter(), Counter(), []
    for root in roots:
        for count, frame, ancestors in self_samples(root):
            # Only observed self PCs are assigned to generated code. Do not
            # extrapolate stack ancestors, caller offsets or old disassembly.
            if '<unknown binary>' in frame:
                addresses = [int(a, 16) for a in re.findall(r'0x([0-9a-f]+)', frame)]
                complete = '...' not in frame and addresses
                mapped = complete and all(any(lo <= a < hi for lo, hi in ranges) for a in addresses)
                category = 'generated_code' if mapped else 'unresolved_unknown_binary'
                if not mapped:
                    unknown.append(dict(count=count, frame=frame))
            elif any('rust_interp_bytecode' in f and any(name in f for name in
                     ['code_spans', 'operation_map', 'code_dump']) for f in (*ancestors, frame)):
                category = 'post_execution_diagnostic'
            elif 'rust_interp_bytecode' in frame and ('execute_impl' in frame or 'execute_observed' in frame):
                category = 'dispatcher_self'
            elif any(name in frame for name in
                     ['native_execution', 'native_continuation', 'run_regions', 'run_tree', 'run_resumable']):
                category = 'native_boundary_self'
            elif any('4heap' in f and 'rust_interp_bytecode' in f for f in (*ancestors, frame)):
                category = 'heap_inclusive'
            elif any('Memory13reserve_frame' in f for f in (*ancestors, frame)):
                category = 'frame_reservation_inclusive'
            elif any('Memory4copy' in f or 'copy_within' in f for f in (*ancestors, frame)):
                category = 'memory_copy_inclusive'
            elif any('3jit' in f and ('compile' in f or 'emit' in f or 'prepare' in f) for f in (*ancestors, frame)):
                category = 'jit_preparation_inclusive'
            else:
                category = 'other_host_self'
            counts[category] += count
            frames[frame.split('  (in ', 1)[0]] += count
    require(sum(counts.values()) == total, 'self counts do not partition graph')
    return dict(index=record['index'], pid=record['identity']['pid'], total_samples=total,
        disjoint_counts=dict(counts), self_symbols=dict(frames.most_common()), unresolved=unknown,
        generated_address_ranges=ranges, statistics=record['statistics'],
        evidence={str(p.relative_to(ROOT)): sha(p) for p in [folder / 'record.json', folder / 'sample.txt', folder / 'vmmap.stdout']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ('.', '..'), 'invalid run ID')
    work = ROOT / '.work' / args.run_id
    run = json.loads((work / 'summary.json').read_text())
    plan = json.loads((work / 'plan.json').read_text())
    require(run['source_unchanged'] and not run['performance_measurement'], 'incomplete diagnostic run')
    vm = ROOT / '.work/interpreter-tools' / run['tool_key'] / 'rust-interp-vm'
    require(sha(vm) == run['vm_sha256'], 'VM changed')
    require(sha(Path(plan['artifact'])) == run['artifact_sha256'], 'artifact changed')
    samples = [summarize(work / str(r['index'])) for r in run['records']]
    # Options describe the captured processes, not the current launcher.
    options = runtime_options(plan, [json.loads((work / str(record['index']) / 'record.json').read_text())
        ['identity']['command'] for record in run['records']])
    counts, frames = Counter(), Counter()
    for sample in samples:
        counts.update(sample['disjoint_counts'])
        frames.update(sample['self_symbols'])
    total = sum(counts.values())
    summary = dict(tool_key=run['tool_key'], vm_sha256=run['vm_sha256'],
        artifact_sha256=run['artifact_sha256'], total_samples=total,
        disjoint_counts=dict(counts), percentages={k: 100 * v / total for k, v in counts.items()},
        self_symbols=dict(frames.most_common()), samples=samples,
        performance_measurement=False, options=options,
        limitations='Partial, perturbed execution windows with original guest RNG. Self counts partition captured thread samples; grouped host PCs remain unresolved. Verified live arena addresses identify generated code, not individual guest operations. Shares do not predict speedup.',
        evidence={str(p.relative_to(ROOT)): sha(p) for p in [work / 'plan.json', work / 'summary.json', Path(__file__),
            Path(__file__).with_name('vmmap_ranges.py')]})
    out = ROOT / 'results' / args.run_id
    out.mkdir(exist_ok=False)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(dict(total_samples=total, percentages=summary['percentages'])))


if __name__ == '__main__':
    main()
