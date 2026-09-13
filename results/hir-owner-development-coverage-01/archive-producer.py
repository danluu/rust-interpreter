import hashlib,io,json,os,sys,tarfile,time
from collections import Counter
from pathlib import Path
ROOT=Path('/Users/danluu/dev/rust-interp-mono-post-driver-20260913')
sys.path.insert(0,str(ROOT/'.work/hir-owner-coverage-setup-01/helpers'))
from owned_stage import workload_lock,write
LOCK=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
OUT=ROOT/'results/hir-owner-development-coverage-01'
RAW=ROOT/'.work/hir-owner-development-coverage-01'
ASSESS=ROOT/'.work/hir-owner-development-assessment-01'
SETUP=ROOT/'.work/hir-owner-development-setup-03'
receipt_path=ROOT/'.work/hir-owner-development-archive-01.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
receipt=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),lock=str(LOCK),wait_seconds=600,compiler_commands=0)
write(receipt_path,receipt);print(json.dumps(receipt),flush=True)
try:
 with workload_lock(LOCK,600):
  receipt.update(status='running',lock_acquired_at=time.time());write(receipt_path,receipt)
  result=json.loads((ASSESS/'result.json').read_text());assert result['status']=='passed'
  assert sha(ASSESS/'coverage.json')==result['coverage_sha256']
  coverage=json.loads((ASSESS/'coverage.json').read_text());plan=json.loads((SETUP/'plan.json').read_text())
  assert sha(SETUP/'plan.json')==result['plan_sha256']
  OUT.mkdir(parents=True,exist_ok=False)
  sources={}
  def add(path,name):
   assert name not in sources,(path,name)
   sources[name]=Path(path)
  for attempt in ['01','02','03']:
   for path in sorted((ROOT/f'.work/hir-owner-development-setup-{attempt}').iterdir()):
    if path.is_file():add(path,f'setup-{attempt}/'+path.name)
  for path in sorted(RAW.iterdir()):
   if path.is_file():add(path,'run/'+path.name)
  for directory in ['reports','cargo-check']:
   for path in sorted((RAW/directory).iterdir()):
    if path.is_file():add(path,'run/'+directory+'/'+path.name)
  for path in sorted(ASSESS.iterdir()):
   if path.is_file():add(path,'assessment/'+path.name)
  for name,identity in plan['frozen_proofs'].items():
   path=RAW/'runner.py' if name==str(ROOT/'experiments/hir-owner-reuse/development/coverage.py') else Path(name)
   assert sha(path)==identity,name
   add(path,'frozen-inputs/'+str(Path(name).relative_to(ROOT)))
  for name in ['coverage.py','assess.py']:
   add(ROOT/'experiments/hir-owner-reuse/development'/name,'corrected-assessment-source/'+name)
  for name in ['summary.json','inventory.json','archive-receipt.json']:
   add(ROOT/'results/hir-owner-coverage-native-01'/name,'native-qualification/'+name)
  retirement=Path(json.loads((RAW/'result.json').read_text())['retirement_receipt'])
  assert sha(retirement)==json.loads((RAW/'result.json').read_text())['retirement_sha256']
  add(retirement,'retirement/summary.json')
  cargo_source=Path('/Users/danluu/dev/rust-interp-cargo-info-cache-20260913/.work/sources/cargo/src/compiler/mod.rs')
  add(cargo_source,'reference/cargo-compiler-mod.rs')
  inventory={}; source_inventory=json.loads((SETUP/'source-inventory.json').read_text())
  with tarfile.open(OUT/'evidence.tar.gz','w:gz',compresslevel=6) as archive:
   def member(name,raw,source,kind='file'):
    inventory[name]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),source=str(source),stored_kind=kind)
    info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o644;info.mtime=0
    archive.addfile(info,io.BytesIO(raw))
   for name,path in sorted(sources.items()):member(name,path.read_bytes(),path)
   for relative,expected in source_inventory.items():
    path=Path(plan['source'])/relative
    raw=os.fsencode(os.readlink(path)) if expected['kind']=='symlink' else path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected['sha256'],relative
    member('source/nushell/'+relative,raw,path,'git-symlink-link-text' if expected['kind']=='symlink' else 'file')
  with tarfile.open(OUT/'evidence.tar.gz','r:gz') as archive:
   members=archive.getmembers();assert len(members)==len(inventory)
   for item in members:
    assert item.isfile()
    raw=archive.extractfile(item).read();assert hashlib.sha256(raw).hexdigest()==inventory[item.name]['sha256']
  for name,path in sources.items():assert sha(path)==inventory[name]['sha256'],name
  write(OUT/'inventory.json',inventory)
  selected=[x for x in coverage['per_invocation'] if x['crate']=='nu_protocol']
  by_incremental={}
  for mode in [False,True]:
   rows=[x for x in coverage['per_invocation'] if x['incremental_session']==mode]
   by_incremental[str(mode).lower()]=dict(invocations=len(rows),resolver_owners=sum(x['resolver_owners'] for x in rows),
       free_functions=sum(x['free_functions'].get('owners',0) for x in rows),eligible=sum(x['eligible'] for x in rows))
  selected_reasons=[]
  for row in selected:
   r=json.loads((RAW/'reports'/row['report']).read_text())
   selected_reasons.append(dict(report=row['report'],role=row['role'],
       free_function_reasons=dict(Counter(x['reason'] for x in r['owners'] if x['kind']=='function'))))
  summary=dict(status='passed',scope='development native Cargo check --lib --tests, default features/profile',
      source_revision=plan['source_revision'],source_inventory_sha256=plan['source_inventory_sha256'],
      driver_sha256=plan['driver_sha256'],gate_sha256=json.loads((RAW/'reports'/selected[0]['report']).read_text())['gate_sha256'],
      compiler_commit=plan['compiler_commit'],plan_sha256=result['plan_sha256'],command=plan['command'],
      original_run_status='failed-report-classification-after-successful-Cargo',assessment_status='passed',
      source_setup_failures=['01: tracked regular-file symlink','02: tracked directory symlink'],
      reporting_correction=result['reporting_correction'],cargo_invocations=1,cargo_returncode=0,
      report_count=result['reports'],compiler_probes=len(coverage['compiler_probes']),groups=len(coverage['groups']),
      totals=coverage['totals'],by_incremental_session=by_incremental,selected_nu_protocol=selected,
      selected_free_function_first_rejections=selected_reasons,
      missing_owners=0,instrumentation_mismatches=0,source_unchanged=True,raw_diagnostics_retained=True,
      invocation_weighted=True,first_rejection_counts_are_not_widening_gains=True,
      benchmark=False,strict_14_test_workflow=False,cache_hits=False,output_capture_measured=False,
      compiler_cache_patch_compiled=False,holdout=False,latency_target_qualification=False,
      archive_members=len(inventory),archive_bytes=(OUT/'evidence.tar.gz').stat().st_size,
      archive_sha256=sha(OUT/'evidence.tar.gz'),excluded='compiler binaries, Cargo target/cache files, Git object database',
      native_qualification_archive=dict(path='results/hir-owner-coverage-native-01/evidence.tar.gz',sha256='a797bee45c584819bc00cb98fb1c30821b8caa6aee8edc510347e54f1d8aa2ee'))
  write(OUT/'summary.json',summary)
  (OUT/'README.md').write_text('''# Native development HIR input-gate coverage

The exact qualified diagnostic driver completed ordinary pinned Cargo `check
--locked --offline --jobs 2 --package nu-protocol --lib --tests` on an isolated
clone of Nushell 9d315796, retaining its default features, profile and Cargo config.
This was a development coverage diagnostic, not the strict 14-test workflow,
a performance measurement, a holdout, or a HIR cache-hit test.

Only one function passed the exact candidate input gate in each `nu-protocol`
configuration: 1/155 free functions and 1/12,488 all resolved owners in each of
two ordinary builds; 1/1,015 free functions and 1/17,877 owners in the test build.
The same source function accounts for all three accepted records (369 source
bytes each). Output capture remains unmeasured. This narrow subset does not
justify a full compiler cache build for Nushell performance.

All 742 raw reports are retained: 726 complete normal compiler invocations and
16 probes. There were no unexplained owner gaps or exact-gate/instrumentation
mismatches. Totals are invocation-weighted, not deduplicated. Of the 726 compiler
invocations, 689 had incremental disabled and were ineligible by construction.
The 37 incremental invocations contained 70,997 resolved owners and 3,941 free
functions, with three accepted records. Summary JSON separates those denominators.

The complete Cargo command succeeded. Its original supervisor result remains
failed because the initial report classifier expected `--test`; this project's
`harness=false` lib instead receives `--cfg test`. The corrected saved-only
assessment recognizes exact argv forms, validates every retained row/count,
and requires both selected normal and test configurations. No compilation was
repeated, result removed, or diagnostic substituted. Two earlier source-only
setup failures preserved ordinary Git symlink fixtures; the same clean clone
was reused and all 2,473 tracked source entries remained unchanged.

The archive contains complete raw outputs/reports and process receipts, both
failed setups, the successful source freeze, original and corrected assessment
source, native/compiler identity guards, frozen gate/helper inputs, source
inventory and all tracked Nushell source bytes. Symlinks are stored as inert Git
link-text files, with their real target/membership proof in source-inventory JSON.
No archive member creates a live symlink. Existing native qualification remains
linked by archive hash. Actual compiler/driver binaries and generated Cargo
caches remain local. No project names participate in the mechanism's gate.

First-rejection site counts show why the current gate rejects owners; they do
not predict gains from relaxing a guard or prove that later gates would pass.
''')
  receipt.update(status='passed',finished_at=time.time(),archive_members=len(inventory),archive_sha256=summary['archive_sha256'],archive_bytes=summary['archive_bytes'])
  write(receipt_path,receipt);print(json.dumps(receipt),flush=True)
except BaseException as error:
 receipt.update(status='failed',error=repr(error),finished_at=time.time());write(receipt_path,receipt);raise
