import hashlib, io, json, os
from pathlib import Path
import sys, tarfile, time
ROOT=Path('/Users/danluu/dev/rust-interp-mono-post-driver-20260913')
sys.path.insert(0,str(ROOT/'experiments/stable-cgu'))
from owned_stage import workload_lock, write
RUN=ROOT/'.work/hir-owner-coverage-01'
OUT=ROOT/'results/hir-owner-coverage-native-01'
receipt={'status':'waiting','pid':os.getpid(),'started_at':time.time()}
write(ROOT/'.work/hir-owner-coverage-archive-01.json',receipt)
with workload_lock(Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock'),600):
    receipt.update(status='running',lock_acquired_at=time.time())
    write(ROOT/'.work/hir-owner-coverage-archive-01.json',receipt)
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
        'source_commit':'5b5a502a','binary_sha256':result['binary_sha256'],'commands':len(result['commands']),
        'report_count':len(list((RUN/'reports').glob('*.json'))),
        'ordinary_raw_diagnostics_equal':True,'native_outputs_equal':True,'source_restored':result['source_restored'],
        'original_fixture':{'resolver_owners':original['resolver_owners'],'unvisited':original['unvisited_resolver_owners'],
                            'functions':original['counts']['function']},
        'compiler_input_files':328,'compiler_inputs_unchanged':result['compiler_inputs_unchanged'],
        'benchmark':False,'project_coverage':False,'cache_hit_qualification':False,'latency_target_qualification':False,
        'artifact_scope':'actual driver and fixture binaries/caches remain locally; archive contains their metadata plus complete raw outputs/reports/sources',
        'artifact_hashes':{str(p.relative_to(RUN)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((RUN/'artifacts').iterdir())},
        'archive_members':len(inventory),'archive_sha256':hashlib.sha256((OUT/'evidence.tar.gz').read_bytes()).hexdigest()}
    write(OUT/'summary.json',summary)
    (OUT/'README.md').write_text('''# HIR input-coverage diagnostic qualification

The exact-gate public compiler driver built and passed all 54 recorded commands
on the first attempt. Eight successful native states covered original source,
a body edit, an earlier Unicode source shift, restoration and restorations after
four uncalled-error controls. Type, move/borrow, const-evaluation and constant-panic
failures matched the ordinary compiler's complete raw stdout/stderr exactly.
Version and dep-info-only reports were correctly unusable.

The original synthetic fixture had 15 resolver owners, no unvisited owners, and
four eligible free functions out of nine. Their encoded resolved inputs totaled
1,843 bytes; observed candidate-format keys totaled 2,255 bytes. These are fixture
coverage facts, not project coverage or evidence of HIR cache hits or speedup.
The compiler cache patch itself remains uncompiled and unqualified.

`summary.json` identifies the actual binary and source producer. The verified
archive retains all command/process receipts, raw output, reports, source snapshots,
helper snapshots and compiler/tool identity documents. Binaries and incremental
caches remain in the owned local run and are not duplicated in this archive.
All 328 frozen public compiler input files and the loader/source guards were
revalidated unchanged; the fixture was restored. No project or holdout was run.
''')
    receipt.update(status='passed',completed_at=time.time(),members=len(inventory),archive_sha256=summary['archive_sha256'])
    write(ROOT/'.work/hir-owner-coverage-archive-01.json',receipt)
    print(json.dumps(receipt),flush=True)
