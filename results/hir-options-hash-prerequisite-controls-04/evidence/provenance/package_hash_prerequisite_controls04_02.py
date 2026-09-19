"""Retain closed actual63 qualification; no imports of candidate or workload calls."""
import ast, hashlib, json, os, re, stat, time
from pathlib import Path
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
SOURCE=ROOT/'experiments/hir-options-hash-driver-stage'
CONTROL=ROOT/'experiments/hir-options-hash-prerequisite-controls-04'
W=ROOT/'.work/hir-options-hash-prerequisite-controls-04'
OUTER=ROOT/'.work/experiments/hir-options-hash-prerequisite-controls-supervisor-04'
LAUNCH=ROOT/'.work/hir-options-hash-prerequisite-controls-launch-execution-04'
AUDIT_RUN=ROOT/'.work/hir-options-hash-prerequisite-controls-verification-execution-04'
PREP=ROOT/'.work/hir-options-hash-prerequisite-controls-preparation-execution-04'
RESULT=ROOT/'results/hir-options-hash-prerequisite-controls-04'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
copies={};destinations={};total=0

def identity(path):
    s=Path(path).lstat();return {key:getattr(s,'st_'+key) for key in FIELDS}

def raw(path):
    path=Path(path);before=identity(path)
    assert path.resolve(strict=True)==path and stat.S_ISREG(before['mode']) and before['size']<=4*2**20
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
        assert {key:getattr(os.fstat(stream.fileno()),'st_'+key) for key in FIELDS}==before
        data=stream.read(4*2**20+1)
        assert len(data)==before['size'] and {key:getattr(os.fstat(stream.fileno()),'st_'+key) for key in FIELDS}==before
    assert identity(path)==before
    return data,before

def sha(path):return hashlib.sha256(raw(path)[0]).hexdigest()

def read(path):return json.loads(raw(path)[0])

def write(path,data):
    global total
    path=Path(path);assert path.is_relative_to(ROOT) and path not in destinations 
    total+=len(data);assert total<=16*2**20 and len(data)<=4*2**20
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        assert str(path) in prior['files'] and raw(path)[0]==data
    else:
        with path.open('xb') as stream:assert stream.write(data)==len(data);stream.flush();os.fsync(stream.fileno())
    assert raw(path)[0]==data
    destinations[path]=dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))

def js(path,value):write(path,(json.dumps(value,sort_keys=True,indent=2)+'\n').encode())

def copy(source,destination):
    source=Path(source);data,before=raw(source);write(destination,data)
    assert identity(source)==before
    copies[str(destination.relative_to(ROOT))]=dict(original_path=str(source),original_identity=before,
        sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))

def tree(source,destination):
    source=Path(source);entries=[]
    for parent,dirs,names in os.walk(source,followlinks=False):
        for name in dirs:
            p=Path(parent)/name;assert p.is_dir() and not p.is_symlink()
        for name in names:
            p=Path(parent)/name;entries.append(str(p.relative_to(source)))
    for name in sorted(entries):copy(source/name,destination/name)
    assert sorted(entries)==sorted(str(p.relative_to(source)) for p in source.rglob('*') if p.is_file())


prior=read(ROOT/'.work/hash-prerequisite-controls04-publication-attempt-01.json')
assert set(prior['files'])=={str(p) for p in RESULT.rglob('*') if p.is_file()}
for p,row in prior['files'].items():assert sha(p)==row['sha256'] and Path(p).stat().st_size==row['bytes']
f=read(CONTROL/'inputs.json');launch=read(CONTROL/'launch.json')
audit_path=ROOT/'.work/hir-options-hash-prerequisite-controls-independent-verification-04.json'
audit=read(audit_path);receipt=read(W/'receipt.json');result=read(W/'result.json')
child=read(W/'command/receipt.json');outer=read(OUTER/'status.json');launcher=read(LAUNCH/'record.json')
assert sha(audit_path)=='3a13fc479808c1a6433811a237bf4d1d1319f5c5b67b527c878d5ca185f05d99'
assert sha(CONTROL/'inputs.json')==receipt['inputs_sha256']=='898bae9f553909b0dae1549dc41c393595f616fb5fb27ad3d4654b18772bb426'
assert sha(CONTROL/'launch.json')==launcher['launch_sha256']=='d06d85acb4815605f549999a62cf32617cd001faec37a136daea086a90044d31'
assert sha(W/'receipt.json')==audit['receipt_sha256']=='752ba52ffd1033185c8d8ef10bd420178d233f3b779bedf2d2fb4f264545e6ef'
assert sha(W/'result.json')==receipt['result_sha256']==audit['result_sha256']
assert audit['status']=='verified' and audit['controls']==receipt['controls_passed']==result['tests_run']==63
assert receipt['status']==result['status']=='passed'
assert all(result[k]==0 for k in ['errors','failures','skipped','expected_failures','unexpected_successes','child_processes','compiler_calls'])
assert len(f['files'])==18 and sum(x['stamp'][3] for x in f['files'].values())==1059721
for name,row in f['files'].items():
    data,s=raw(name);assert hashlib.sha256(data).hexdigest()==row['sha256']
    assert [s[k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]==row['stamp']
for name,route in f['routes'].items():assert str(Path(name).resolve(strict=True))==route
names=[]
for name in ['test_prerequisites.py','test_native_wrapper.py','test_snapshot_bindings.py']:
    for cls in ast.parse(raw(SOURCE/name)[0]).body:
        if isinstance(cls,ast.ClassDef):names.extend(Path(name).stem+'.'+cls.name+'.'+m.name for m in cls.body if isinstance(m,ast.FunctionDef) and m.name.startswith('test_'))
stderr=raw(W/'command/stderr')[0].decode()
observed=re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$',stderr,re.M)
assert sorted(names)==sorted(observed)==sorted(audit['exact_names'])==f['expected_names']==result['expected_names'] and len(names)==63
assert not raw(W/'command/stdout')[0] and re.search(r'^Ran 63 tests in [0-9.]+s\n\nOK\n$',stderr,re.M)
assert receipt['commands']==[dict(path=str(W/'command/receipt.json'),pid=child['pid'],sha256=sha(W/'command/receipt.json'))]
assert child['status']=='finished' and child['returncode']==0 and child['command']==f['command']
assert child['environment']==f['environment'] and child['cwd']==str(SOURCE)
assert child['supervisor_pid']==receipt['pid'] and child['parent_pid']==receipt['parent_pid']==outer['supervisor_pid']
ps=child['identity']['ps'].split();assert list(map(int,ps[:3]))==[child['pid'],receipt['pid'],child['pid']]
assert child['identity']['cwd']=='p'+str(child['pid'])+'\nfcwd\nn'+str(SOURCE)+'\n'
assert outer['status']=='finished' and outer['returncode']==0 and outer['child_pid']==receipt['pid']
assert outer['command']==launch['command'][6:] and outer['cwd']==str(ROOT)
assert outer['plan_sha256']==sha(OUTER/'plan.json') and outer['log_sha256']==sha(OUTER/'command.log')
assert outer['child_started_at']<=receipt['started_at']<=receipt['admitted_at']<=child['started_at']<=child['finished_at']<=receipt['finished_at']<=outer['finished_at']
assert launcher['status']=='terminal-observed' and launcher['returncode']==launcher['launcher_returncode']==0
assert launcher['outer_sha256']==sha(OUTER/'status.json') and launcher['controller_pid']==receipt['pid'] and launcher['supervisor_pid']==outer['supervisor_pid']
assert launcher['command']==launch['command'] and launcher['terminal_observed_at']>=outer['finished_at']
assert sha(launcher['launcher_source_path'])==launcher['launcher_source_sha256']=='e86774ed3625f35fd3cb105017082ed7562185168f62657b0c70268d336ed41d'
for folder in [LAUNCH,AUDIT_RUN,PREP]:
    record=read(folder/'record.json');assert record['returncode']==0
    for stream in ['stdout','stderr']:assert sha(folder/stream)==record[stream+'_sha256']
assert read(AUDIT_RUN/'record.json')['source_sha256']==audit['verifier_sha256']=='26348c6978f1f6436035ea8d6e388c12afc84949cb336b54dc177eef8189f571'
for stream in ['stdout','stderr']:assert sha(W/'command'/stream)==child[stream+'_sha256']==audit['raw_sha256'][stream]
assert not list((W/'tmp').iterdir())
# Candidate controller/prepare/verifier are source-reviewed; they were not exercised by these pure controls.
for name,digest in {'stage.py':'8daf98086fd3eabb3e2a403f0f19995140956edf52178345a3fd11493d999b2d','prepare.py':'679bcccbddfadbda1e0ebb891f73f7bb19aad2e72e5655ddeaae1b5798082948','verify.py':'99635ff121f2225bed43b4056da095594312b6004c348728a857afffbca0dca5'}.items():assert sha(SOURCE/name)==digest
for index,name in enumerate(sorted(f['files'])):copy(name,RESULT/'evidence/frozen-inputs'/(str(index).zfill(3)+'-'+Path(name).name))
for source,name in [(CONTROL,'proposal'),(W,'work'),(OUTER,'outer'),(LAUNCH,'launcher'),(AUDIT_RUN,'audit-execution'),(PREP,'preparation-execution')]:tree(source,RESULT/'evidence'/name)
for name in ['stage.py','prepare.py','verify.py']:copy(SOURCE/name,RESULT/'evidence/source-reviewed'/name)
provenance=[ROOT/'.work/package_hash_prerequisite_controls04_01.py',ROOT/'.work/hash-prerequisite-controls04-publication-attempt-01.json',audit_path,ROOT/'.work/launch_hash_prerequisite_controls_04_bounded.py',ROOT/'.work/verify_hash_prerequisite_controls_04.py',
 ROOT/'.work/root-hash-reconciliation-snapshot-controls-source-review-01.json',ROOT/'.work/root-hash-prerequisite-controls04-harness-source-review-01.json',ROOT/'.work/root-hash-prerequisite-controls04-packet-review-01.json',
 O/'.work/hash-prerequisite-controls04-harness.diff',O/'.work/hash-prerequisite-controls04-launch-audit.diff',O/'.work/hash-native-reconciliation-prerequisites-source-review-02.json',
 ROOT/'.work/hash-snapshot-v2-integration-source-02.diff',ROOT/'.work/hash-v2-independent-verifier-source-review-01.json',ROOT/'.work/hash-v2-independent-verifier-source-review-02.json',Path(__file__).resolve()]
for path in provenance:copy(path,RESULT/'evidence/provenance'/path.name)
summary=dict(status='passed-pure-prerequisite-controls',controls=63,original_history_controls=9,original_wrapper_controls=12,reconciliation_controls=17,snapshot_binding_controls=25,
 original_source=str(SOURCE),original_control_source=str(CONTROL),original_work=str(W),receipt_sha256=sha(W/'receipt.json'),independent_audit_sha256=sha(audit_path),
 inputs_sha256=sha(CONTROL/'inputs.json'),launch_sha256=sha(CONTROL/'launch.json'),exact_names=sorted(names),frozen_files=18,frozen_bytes=1059721,
 compiler_calls=0,provider_probes=0,process_signals=0,supervisor_pid=outer['supervisor_pid'],helper_pid=receipt['pid'],test_pid=child['pid'],
 limitations=[launcher['wrapper_identity_limitation'],'Stage, preparation and independent workload verifier received source review only; actual hash stage and application timing remain unrun.'],
 publication_copy_policy='Full original bytes and seven stable identity fields; destination readback; atime excluded. Historical absolute paths retain actual execution owners.')
js(RESULT/'summary.json',summary)
write(RESULT/'README.md',b'# Hash prerequisite and snapshot bindings\n\nAll 63 pure controls passed once: nine original command-history checks, twelve original wrapper checks, seventeen saved-native reconciliation checks and twenty-five snapshot association checks. An independent audit verified the exact test names, all eighteen frozen inputs, raw output, actual child identity, dispatcher and supervisor completion.\n\nThe source keeps a failed native controller distinct from the later read-only qualification. Snapshot reuse retains every logical input and binds previously retained bytes to their original audited owner and counted evidence root. No compiler or provider workload ran.\n\nAll frozen source/tool bytes and raw preparation, execution and audit records are retained. The enclosing hash controller, preparer and verifier have source review only; these controls establish no actual hash-driver qualification, installed runtime, application speedup or sub-0.5-second result. Original absolute paths are historical evidence, not a portable rerun recipe.\n')
js(RESULT/'manifest.json',dict(copied_files=copies,generated_files={str(p.relative_to(ROOT)):r for p,r in destinations.items() if str(p.relative_to(ROOT)) not in copies},original_audit_sha256=sha(audit_path)))
paths=sorted(str(p.relative_to(ROOT)) for p in destinations)
for p,row in destinations.items():assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
manifest=ROOT/'.work/hash-prerequisite-controls04-publication-01.json';assert not manifest.exists()
manifest.write_text(json.dumps(dict(status='verified-closed-evidence-copy',files={p:destinations[ROOT/p] for p in paths},file_count=len(paths),bytes=total,finished_at=time.time()),sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(manifest=str(manifest),sha256=sha(manifest),files=len(paths),bytes=total),indent=2))
