"""Weight unambiguous inventories by typed direct-call counts."""
from pathlib import Path
from collections import defaultdict
import hashlib
import json

root = Path(__file__).resolve().parents[3]
work = root / '.work/mir-frame-census-collection-01'
data = json.loads((work / 'summary.json').read_text())
counts = json.loads((root / '.work/frame-initialization-census-01/summary.json').read_text())
out = root / 'results/mir-frame-census-01'
out.mkdir(exist_ok=True)
assert not list(out.iterdir()), 'never overwrite a published report'
results = []
for case in data['cases']:
    label = 'folded' if case['label'] == 'folded-literal-trie' else 'token-phrase'
    groups = defaultdict(list)
    for row in case['inventories']: groups[row['name']].append(row)
    ambiguous = {n for n, rows in groups.items() if any(r != rows[0] for r in rows)}
    callees = next(r for r in counts['cases'] if r['label'] == label)['census']['callees']
    rows = []
    totals = dict(frame=0, unused=0, unnamed=0, after_decl=0, inline=0, unattributed=0)
    for callee in callees:
        calls = callee['proven_local']['calls'] + callee['unknown_sources']['calls']
        totals['frame'] += calls * max(1, callee['frame_size'])
        name = callee['name']
        if name not in groups or name in ambiguous:
            totals['unattributed'] += calls * max(1, callee['frame_size'])
            continue
        inventory = groups[name][0]
        end = max(inventory['declared_range_end'], sum(inventory['caller_location']) if inventory['caller_location'] else 0)
        row = dict(id=callee['id'], name=name, calls=calls, frame=callee['frame_size'],
            unused=inventory['semantically_unreferenced_mir_bytes'],
            unnamed=inventory['non_abi_mir_bytes_without_named_local_address'],
            after_decl=inventory['frame_size_before_bytecode_inlining'] - end,
            inline=callee['frame_size'] - inventory['frame_size_before_bytecode_inlining'])
        assert row['after_decl'] >= 0 and row['inline'] >= 0
        for key in ['unused', 'unnamed', 'after_decl', 'inline']:
            totals[key] += calls * row[key]
        rows.append(row)
    # Name collisions are not silently coalesced. In these saved profiles none
    # of the ambiguous shims have an observed direct call.
    assert totals['unattributed'] == 0
    results.append(dict(label=label, inventories=len(case['inventories']), distinct_names=len(groups),
        ambiguous_display_names=len(ambiguous), ambiguous_names=sorted(ambiguous),
        weighted_bytes=totals, percentages={k:100*n/totals['frame'] for k,n in totals.items() if k != 'frame'},
        top_callees=sorted(rows, key=lambda r:-r['calls']*r['frame'])[:12],
        artifact_sha256=case['artifact_sha256'], original_tests_pass=True, artifact_identical_to_retained=True))
report = dict(status='Qualified diagnostic; unused MIR allocation has limited weighted scope',
    tool_key=data['tool_key'], retained_tool_key=data['retained_tool_key'], binaries=data['binaries'],
    exporter_tests=11, cases=results, production_change=False, performance_measurement=False,
    source_unchanged=True, preserved_report_failure='.work/mir-frame-census-report-failure-01.json',
    evidence={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
        root / '.work/mir-frame-census-build-01/summary.json', root / '.work/mir-frame-census-build-01/provenance.json',
        work / 'summary.json', root / '.work/mir-frame-census-report-failure-01.json', Path(__file__).resolve()]})
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
text = '''The isolated exporter inventory preserves both freshly exported folded/token
bytecode artifacts exactly, with original tests passing. Its VM binary is
identical to retained 57a5, and all 11 exporter tests pass. The observer changes
no slots or bytecode. These instrumented compilations are not timing evidence.

After weighting by recorded direct calls, semantically unreferenced MIR local
ranges account for only 1.46% of folded frame bytes and 1.78% of token frame
bytes. This does not justify a frame-layout rewrite as the next speed experiment.

| Recorded direct-call frame bytes | Folded | Token |
|---|---:|---:|
'''
for key, label in [('frame', 'Total frame bytes, excluding alignment padding'),
    ('unused', 'MIR ranges without a semantic use'), ('unnamed', 'Non-ABI ranges without a named local address'),
    ('after_decl', 'Bytes after declared locals and caller-location storage'), ('inline', 'Additional inline-bank extent')]:
    values = []
    for result in results:
        total = result['weighted_bytes']
        values.append(f"{total[key]:,}" + (f" ({100*total[key]/total['frame']:.2f}%)" if key != 'frame' else ''))
    text += f"| {label} | {' | '.join(values)} |\n"
text += '''
Unreferenced and unnamed ranges overlap and must not be added. Neither proves
that omission or relocation preserves pointer behavior. Later temporary storage
and alignment contribute to the post-declaration extent. Existing scalar
coloring and inline-bank reuse already apply. Indirect targets, entry/TLS frames
and alignment padding are excluded from these weighted counts.

The first report attempt rejected duplicate display names: distinct compiler
shims can share the rendered function name while having different frames.
There is one such name in folded and eleven in token. The corrected report
keeps those inventories separate and excludes ambiguous matches. None of those
shims has an observed direct call in these profiles, so every weighted callee
has an unambiguous inventory. The failed uniqueness assertion is preserved.

Keep the current frame layout. The remaining call-transition costs warrant a
larger experiment, preceded by a typed census of fully native leaf callees and
their rejection reasons. Benchmark reproducibility and repeated per-edit
controls should also be improved before the next performance decision.
'''
(out / 'summary.md').write_text(text)
print(json.dumps([dict(label=r['label'], weighted_bytes=r['weighted_bytes'], ambiguous_names=r['ambiguous_display_names']) for r in results]))
