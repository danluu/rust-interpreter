"""Resolve three owned samples against the exact retained VM disassembly."""
import fcntl, hashlib, json, re
from pathlib import Path
root = Path(__file__).resolve().parents[3]
lock = (root / '.work/benchmark.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assembly_path = root / '.work/retained-token-cpu-sample-04/retained-vm-disassembly.txt'
assembly = assembly_path.read_text().splitlines()
label = next(i for i, line in enumerate(assembly) if 'execute_observed' in line and line.endswith(':'))
base = int(assembly[label + 1].split('\t', 1)[0], 16)
instructions = {int(parts[0], 16): line for line in assembly
    if len(parts := line.split('\t', 1)) == 2 and re.fullmatch('[0-9a-f]{16}', parts[0])}
sites = {
    12388: ('frame_reservation_inclusive', 'Memory13reserve_frame'),
    12608: ('local_argument_copies', 'copy_within'),
    12676: ('general_argument_copies', 'Memory4copy'),
    13308: ('return_result_copies', 'Memory4copy'),
    11356: ('other_memory_copies', 'Memory4copy'),
    9136: ('other_memory_copies', 'Memory4copy'),
    8828: ('heap_management', 'Heap10deallocate'),
    11036: ('heap_management', 'Heap10reallocate'),
    9980: ('heap_management', 'Heap8allocate'),
    12968: ('jit_compilation', 'Jit16compile_function'),
    10772: ('switch_lookup', 'Iterator4find'),
    9568: ('memory_store', 'Memory5store'),
    1620: ('teardown', 'drop_glue'),
    10180: ('interpreted_arithmetic', '6binary'),
}
for offset, (_, symbol) in sites.items():
    line = instructions[base + offset - 4]
    assert '\tbl\t' in line and symbol in line, (offset, line)
work = root / '.work/retained-token-cpu-sample-04'
run = json.loads((work / 'summary.json').read_text())
plan = json.loads((work / 'plan.json').read_text())
assert run['tool_key'] == '57a54edd6b64db0e7a1a854dfb42ec0d519cde40366be977fe26d51bb1e16497'
assert run['vm_sha256'] == '98824128148f20854238d01e58b263d93da0c97b4788acd2e67a5e501fe0d369'
assert all(sha(root / p) == h for p,h in plan['source_files'].items())
vm = root / '.work/interpreter-tools' / run['tool_key'] / 'rust-interp-vm'
assert sha(vm) == run['vm_sha256']
assert sha(Path(plan['artifact'])) == run['artifact_sha256']
results = []
for index in range(3):
    folder = work / str(index)
    record = json.loads((folder / 'record.json').read_text())
    assert record['identity']['returncode'] == 0 and not record['performance_measurement']
    assert record['sample_returncode'] == 0 and record['mapped']
    assert all(sha(folder / p) == h for p,h in record['files'].items())
    sample = (folder / 'sample.txt').read_text()
    assert int(re.search(r'^Analysis of sampling rust-interp-vm \(pid (\d+)\)', sample, re.M)[1]) == record['identity']['pid']
    tree = sample.split('Call graph:',1)[1].split('Total number in stack',1)[0]
    total = int(re.search(r'^\s*(\d+) Thread_',tree,re.M)[1])
    rows = [(int(m[1]),m[2]) for line in tree.splitlines()
            if (m := re.match(r'^[ +!:|]{18}(\d+) (.*)$',line))]
    assert sum(n for n,_ in rows) == total
    ranges = [(int(a,16),int(b,16)) for a,b in re.findall(
        r'^VM_ALLOCATE\s+([0-9a-f]+)-([0-9a-f]+).*?rwx/rwx',(folder/'vmmap.stdout').read_text(),re.M)]
    assert ranges
    counts, unresolved = {}, []
    for n,name in rows:
        if '<unknown binary>' in name:
            address = int(re.search(r'\[0x([0-9a-f]+)\]',name)[1],16)
            assert any(a <= address < b for a,b in ranges)
            key = 'generated_code'
        elif 'Memory13reserve_frame' in name: key = 'frame_reservation_inclusive'
        elif 'Memory4copy' in name: key = 'other_memory_copies'
        elif 'Memory5store' in name: key = 'memory_store'
        elif '4heap' in name: key = 'heap_management'
        elif 'drop_glue' in name: key = 'teardown'
        elif 'execute_observed' in name:
            tail = name.split(' + ',1)[1].split(' [',1)[0].strip()
            if ',' in tail: key = 'dispatcher_self_unresolved'
            elif int(tail) in sites: key = sites[int(tail)][0]
            else: key = 'unresolved_host'; unresolved.append(dict(count=n,frame=name))
        else: key = 'unresolved_host'; unresolved.append(dict(count=n,frame=name))
        counts[key] = counts.get(key,0) + n
    assert sum(counts.values()) == total
    results.append(dict(index=index,total_samples=total,disjoint_counts=counts,unresolved=unresolved,
        percentages={k:100*n/total for k,n in counts.items()},generated_mapping_verified=True,
        generated_address_ranges=ranges,statistics=record['statistics'],performance_measurement=False,
        evidence={str(p.relative_to(root)):sha(p) for p in [folder/'record.json',folder/'sample.txt',folder/'vmmap.stdout']}))
counts = {}
for r in results:
    for k,n in r['disjoint_counts'].items():counts[k]=counts.get(k,0)+n
total = sum(r['total_samples'] for r in results)
assert total == sum(counts.values())
summary = dict(status='Three retained-VM CPU windows with verified live generated-code arenas',
    tool_key=run['tool_key'],vm_sha256=run['vm_sha256'],artifact_sha256=run['artifact_sha256'],
    total_samples=total,disjoint_counts=counts,percentages={k:100*n/total for k,n in counts.items()},
    samples=results,performance_measurement=False,host_sites={str(k):instructions[base+k-4] for k in sites},
    limitation='Partial execution windows with original RNG; sampling perturbs execution. Dispatcher self merges multiple PCs. Shares do not predict speedups or establish a before/after change.',
    evidence={str(p.relative_to(root)):sha(p) for p in [work/'summary.json',work/'plan.json',assembly_path,Path(__file__).resolve()]})
out=root/'results/retained-token-cpu-sample-04';out.mkdir()
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
text = "Three separate executions of the exact retained `57a54edd` VM passed the original\ntoken-phrase tests with their original RNG and assertions. Every sampled\ngenerated PC was checked against the live arena of that same owned process.\nHost call sites were checked against this binary's disassembly. All three\nexecutions completed with zero JIT declines. These are diagnostic windows,\nnot complete-command timings or before/after speedup measurements.\n\n| Disjoint category | Window 1 | Window 2 | Window 3 | Combined share |\n|---|---:|---:|---:|---:|\n"
for k,n in sorted(counts.items(),key=lambda item:-item[1]):
    values = ' | '.join(str(r['disjoint_counts'].get(k,0)) for r in results)
    text += f"| {k.replace('_',' ')} | {values} | {100*n/total:.1f}% |\n"
text += '\nNested memset and memcpy samples remain inside their parent category, so they\nare not counted twice. Frame reservation and argument/result copying remain\nsubstantial. Dispatcher self combines several instruction addresses; its share\ndoes not identify a single operation. Original RNG can vary work between runs.\n\nThe next candidate needs a typed count of calls and initialization requirements\nbefore implementation. In particular, examine whether callee argument stores\nimmediately overwrite a useful part of freshly zeroed frames. Preserve argument\nordering, overlapping slots, frame alignment, initialization semantics, memory\nlimits, fault ordering and original tests. A census is a screening step; any\nimplementation must improve real source-edit/build/test commands to advance.\n'
(out/'summary.md').write_text(text)
print(json.dumps(dict(total_samples=total,counts=counts,performance_measurement=False)))
