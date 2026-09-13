import hashlib, io, json, os
from pathlib import Path
import sys, tarfile, time
ROOT=Path('/Users/danluu/dev/rust-interp-mono-post-driver-20260913')
sys.path.insert(0,str(ROOT/'.work/hir-owner-coverage-setup-01/helpers'))
from owned_stage import workload_lock, write
RUN=ROOT/'.work/hir-body-coverage-native-01'
OUT=ROOT/'results/hir-body-coverage-native-01'
receipt={'status':'waiting','pid':os.getpid(),'started_at':time.time()}
write(ROOT/'.work/hir-body-coverage-archive-01.json',receipt)
with workload_lock(Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock'),600):
    receipt.update(status='running',lock_acquired_at=time.time())
    write(ROOT/'.work/hir-body-coverage-archive-01.json',receipt)
    OUT.mkdir(parents=True,exist_ok=False)
    paths=[RUN/name for name in ['result.json','commands.json','plan.json','compiler-inputs.json','compiler-libraries.json','driver.json']]
    for name in ['logs','reports','states','source','helpers']:
        paths.extend(p for p in sorted((RUN/name).rglob('*')) if p.is_file() and '__pycache__' not in p.parts)
    inventory={}
    with tarfile.open(OUT/'evidence.tar.gz','w:gz',compresslevel=6) as archive:
        for path in sorted(paths):
            raw=path.read_bytes(); name=str(path.relative_to(RUN))
            inventory[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
            info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o644;info.mtime=0
            archive.addfile(info,io.BytesIO(raw))
    with tarfile.open(OUT/'evidence.tar.gz','r:gz') as archive:
        for member in archive.getmembers():
            raw=archive.extractfile(member).read()
            assert hashlib.sha256(raw).hexdigest()==inventory[member.name]['sha256']
    write(OUT/'inventory.json',inventory)
    original=json.loads((RUN/'states/original-report.json').read_text())['report']
    result=json.loads((RUN/'result.json').read_text())
    summary={'status':result['status'],'scope':'public-driver and native fixture controls only',
        'source_commit':'501d992e','binary_sha256':result['binary_sha256'],'commands':len(result['commands']),
        'report_count':len(list((RUN/'reports').glob('*.json'))),
        'ordinary_raw_diagnostics_equal':True,'native_outputs_equal':True,'source_restored':result['source_restored'],
        'original_fixture':{'resolver_owners':original['resolver_owners'],'unvisited':original['unvisited_resolver_owners'],
                            'roles':original['counts']},
        'compiler_input_files':328,'compiler_inputs_unchanged':result['compiler_inputs_unchanged'],
        'benchmark':False,'project_coverage':False,'cache_effects_qualified':False,'hir_ids_observed':False,'cache_hit_qualification':False,'latency_target_qualification':False,
        'artifact_scope':'actual driver and fixture binaries/caches remain locally; archive contains their metadata plus complete raw outputs/reports/sources',
        'artifact_hashes':{str(p.relative_to(RUN)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((RUN/'artifacts').iterdir())},
        'archive_members':len(inventory),'archive_sha256':hashlib.sha256((OUT/'evidence.tar.gz').read_bytes()).hexdigest()}
    write(OUT/'summary.json',summary)
    (OUT/'README.md').write_text("""# Body-v2 diagnostic native qualification

The separate public-rustc body diagnostic passed all 66 commands on its first
attempt. Complete native compiler outputs and execution outputs matched the
ordinary pinned compiler across original/body edit/earlier Unicode shift/
restoration, external trait-resolution edit/restoration, and four uncalled
error histories (type, move/borrow, const evaluation, constant panic). Exact
wrapper-path version and wrong-compiler rejection, version and dep-info-only
controls also passed. The two non-analysis probes never qualified coverage.

The original synthetic fixture has36 resolver owners and zero unexplained gaps.
Its17 structurally accepted bodies comprise12/19 free functions,3/3 inherent
methods,1/3 trait methods(two required/no-body),and1/1 trait-impl methods.
The same external-method body changes its input digest when its imported trait
changes Left→Right, and restoration restores its original digest. Actual native
outputs validate both external method choices. Bare external direct calls without
current legacy-const metadata proof remain rejected; indirect external function
values and external trait candidates are represented by current DefPathHashes.

This qualifies the structural diagnostic only. No actual HIR S/E IDs, cache
capture/replay effects, HIR cache hits, timing gain, Nushell coverage or holdout
result is established here. V1 remains unchanged. All328 public compiler input
files, complete loader guards and frozen source inputs were revalidated unchanged.
The archive retains full outputs, reports, commands/process receipts, fixture
histories and compiler/tool/source identity. Native binaries/caches remain local,
with artifact hashes retained. Source producer501d992e and driver/gate hashes
are recorded; successful qualification does not turn the earlier unrun contract
into a cache implementation.
""")
    receipt.update(status='passed',completed_at=time.time(),members=len(inventory),archive_sha256=summary['archive_sha256'])
    write(ROOT/'.work/hir-body-coverage-archive-01.json',receipt)
    print(json.dumps(receipt),flush=True)
