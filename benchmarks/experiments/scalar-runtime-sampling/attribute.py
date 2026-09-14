"""Join unprofiled current-runtime self PCs to verified schema-2 code spans."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/scalar-private-transfers'))
from compare_saved_runtime import sha
from native_observation import validate
from summarize_owned_sample import parse_tree, self_samples

LEGACY = ROOT / 'benchmarks/experiments/operation-map'
sys.path.insert(0, str(LEGACY))
spec = importlib.util.spec_from_file_location('legacy_operation_attribute', LEGACY / 'attribute.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
assign, detail = legacy.assign, legacy.detail


def read(path):
    assert path.stat().st_size <= 256 * 1024**2
    return json.loads(path.read_text())


def attribute(run_id, profile_path, expected_vm):
    folder = ROOT / '.work' / run_id / '0'
    result = ROOT / 'results' / run_id
    summary_path = result / 'summary.json'
    summary = read(summary_path)
    assert summary['vm_sha256'] == expected_vm and len(summary['samples']) == 1
    for key in ['jit_persistent_registers', 'jit_resumable_calls', 'jit_scalar_calls', 'jit_operation_map']:
        assert summary['options'][key] is True
    record = read(folder / 'record.json')
    assert record['identity']['status'] == 'finished' and record['identity']['returncode'] == 0
    assert all(sha(folder / p) == h for p, h in record['files'].items())
    command = record['identity']['command']
    assert '--profile' not in command and '--profile-test' not in command
    assert '--select-test' in command and '--jit-scalar-calls' in command
    native_path = folder / 'jit-code/map.json'
    operations_path = folder / 'jit-code/operations.json'
    code_path = folder / 'jit-code/code.bin'
    native, operations, profile = map(read, [native_path, operations_path, profile_path])
    assert native['profiled'] is False and native['pid'] == summary['samples'][0]['pid']
    assert native['code_bytes'] == record['statistics']['jit_bytes']
    base = native['arena_base']
    assert any(lo == base and base + native['code_bytes'] <= hi
               for lo, hi in summary['samples'][0]['generated_address_ranges'])
    checked = validate(operations, native, code_path.read_bytes(), profile, record['identity']['pid'])
    assert checked['static_words'].get('scalar_leaf', 0) > 0
    frames = [frame for root in parse_tree((folder / 'sample.txt').read_text()) for frame in self_samples(root)]
    labels, sites, unresolved = assign(checked, base, frames)
    unknown = sum(summary['disjoint_counts'].get(k, 0)
                  for k in ['generated_code', 'unresolved_unknown_binary'])
    assert sum(labels.values()) + sum(r['count'] for r in unresolved) == unknown
    assert sum(labels.values()) > 0
    detailed, static, functions = Counter(), Counter(), Counter()
    for row in checked['rows']:
        static[detail(row, profile)] += (row['end'] - row['offset']) // 4
    top = []
    for (fid, region, pc, kind, label), count in sites.most_common():
        detailed[detail(dict(function=fid, pc=pc, label=label), profile)] += count
        functions[fid, kind] += count
        if len(top) < 40:
            top.append(dict(function=fid, name=profile['functions'][fid]['name'],
                region_pc=region, pc=pc, kind=kind, label=label, samples=count,
                operation=profile['functions'][fid]['operations'][pc] if pc is not None else None))
    paths = [summary_path, profile_path, folder / 'record.json', folder / 'sample.txt',
             native_path, operations_path, code_path, Path(__file__), LEGACY / 'attribute.py',
             LEGACY / 'maps.py', ROOT / 'benchmarks/experiments/scalar-private-transfers/native_observation.py']
    report = dict(status='passed', tool_key=summary['tool_key'], vm_sha256=expected_vm,
        captured_thread_samples=summary['total_samples'], attributed_generated_samples=sum(labels.values()),
        unassigned_generated_samples=sum(r['count'] for r in unresolved), unresolved=unresolved,
        by_label=dict(labels.most_common()), by_detail=dict(detailed.most_common()),
        static_words=dict(static), top_sites=top,
        top_functions=[dict(function=fid, name=profile['functions'][fid]['name'], kind=kind, samples=n)
                       for (fid, kind), n in functions.most_common(25)],
        disjoint_counts=summary['disjoint_counts'],
        known_post_execution_samples=summary['disjoint_counts'].get('post_execution_diagnostic', 0),
        reconstructed_same_process_code=True, profile_used_for_static_identity_only=True,
        performance_measurement=False, evidence={str(p.relative_to(ROOT)): sha(p) for p in paths},
        limitation='One partial perturbed normal-entropy window. Static profile identity only; no dynamic count comparison. Scalar spans identify whole bodies, not individual operations. Generated self PCs only; host samples can include preparation/reconstruction/I/O. No speedup inference.')
    target = result / 'operation-attribution.json'
    with target.open('x') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    return dict(report=str(target.relative_to(ROOT)), report_sha256=sha(target),
        attributed_generated_samples=report['attributed_generated_samples'],
        unassigned_generated_samples=report['unassigned_generated_samples'],
        by_label=report['by_label'], disjoint_counts=report['disjoint_counts'])
