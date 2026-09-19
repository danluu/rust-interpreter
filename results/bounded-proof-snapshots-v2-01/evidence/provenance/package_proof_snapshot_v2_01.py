"""Copy closed v2 helper qualification with stable identities; no Git/workloads."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
SOURCE=A/'experiments/bounded-proof-snapshots-v2'
CONTROL=A/'experiments/bounded-proof-snapshot-controls-v2-01'
W=A/'.work/bounded-proof-snapshot-controls-v2-01'
OUTER=A/'.work/experiments/bounded-proof-snapshot-controls-v2-supervisor-01'
LAUNCH=A/'.work/proof-snapshot-controls-v2-launch-execution-01'
AUDIT_RUN=A/'.work/proof-snapshot-controls-v2-verification-execution-01'
RESULT=ROOT/'results/bounded-proof-snapshots-v2-01'
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
    path=Path(path);assert path.is_relative_to(ROOT) and path not in destinations and not path.exists()
    total+=len(data);assert total<=16*2**20 and len(data)<=4*2**20
    path.parent.mkdir(parents=True,exist_ok=True)
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

assert not RESULT.exists()
for destination in [ROOT/'experiments/bounded-proof-snapshots-v2',ROOT/'experiments/bounded-proof-snapshot-controls-v2-01']:
    assert not destination.exists()
f=read(CONTROL/'inputs.json');proposal=read(CONTROL/'launch.json');terminal=read(W/'receipt.json')
child=read(W/'command/receipt.json');result=read(W/'result.json');outer=read(OUTER/'status.json')
launcher=read(LAUNCH/'record.json');audit_path=A/'.work/proof-snapshot-controls-v2-independent-verification-01.json'
audit=read(audit_path);execution=read(AUDIT_RUN/'record.json')
assert sha(CONTROL/'inputs.json')=='0880defb3dfe6e37491856badd700748b868dbf255331fe3429bdb5e2438048c'
assert sha(CONTROL/'launch.json')=='8c3b162a55ee17468d4f722d2c9d9d970babc3ba09c4c4f53ad7078a081258f1'
assert sha(audit_path)=='a918d190b5b5810bce877408a5a13235ead329e5e56f2fd952e7912be6278c8d'
assert audit['status']=='verified' and audit['controls']==22
assert audit['receipt_sha256']==sha(W/'receipt.json')== '8c0d932964c40d394168f178c46b3e91eb665e44fe0d9918affc87393cca066b'
assert terminal['status']=='passed' and terminal['controls_passed']==22
assert terminal['inputs_sha256']==sha(CONTROL/'inputs.json')
assert terminal['result_sha256']==audit['result_sha256']==sha(W/'result.json')
assert result['status']=='passed' and result['tests_run']==22
assert all(result[key]==0 for key in ['failures','errors','skipped','expected_failures','unexpected_successes','child_processes','compiler_calls'])
assert terminal['commands']==[dict(path=str(W/'command/receipt.json'),pid=child['pid'],sha256=sha(W/'command/receipt.json'))]
assert child['status']=='finished' and child['returncode']==0 and child['command']==f['command']
assert child['cwd']==str(SOURCE) and child['environment']==f['environment']
assert child['supervisor_pid']==terminal['pid'] and child['parent_pid']==terminal['parent_pid']==outer['supervisor_pid']
assert child['identity']['ps_returncode']==0
ps=child['identity']['ps'].split();assert list(map(int,ps[:3]))==[child['pid'],terminal['pid'],child['pid']]
assert child['identity']['cwd_returncode']==0 and child['identity']['cwd']=='p'+str(child['pid'])+'\nfcwd\nn'+str(SOURCE)+'\n'
assert outer['status']=='finished' and outer['returncode']==0 and outer['child_pid']==terminal['pid']
assert outer['command']==proposal['command'][6:] and outer['cwd']==str(A)
assert outer['plan_sha256']==sha(OUTER/'plan.json') and outer['log_sha256']==sha(OUTER/'command.log')
assert outer['child_started_at']<=terminal['started_at']<=terminal['admitted_at']<=child['started_at']<=child['finished_at']<=terminal['finished_at']<=outer['finished_at']
assert launcher['status']=='terminal-observed' and launcher['returncode']==0 and launcher['launcher_returncode']==0
assert launcher['launch_sha256']==sha(CONTROL/'launch.json') and launcher['command']==proposal['command']
assert launcher['outer_sha256']==sha(OUTER/'status.json') and launcher['controller_pid']==terminal['pid']
assert launcher['supervisor_pid']==outer['supervisor_pid'] and launcher['terminal_observed_at']>=outer['finished_at']
assert sha(Path(launcher['launcher_source_path']))==launcher['launcher_source_sha256']=='33220be13feea7d316c2eb523b48f85afa878fb4d502abf1e847eaf54ff22cd2'
assert execution['status']=='finished' and execution['returncode']==0
assert execution['source_sha256']==audit['verifier_sha256']==sha(A/'.work/verify_proof_snapshot_controls_v2_01.py')
for stream in ['stdout','stderr']:
    assert sha(W/'command'/stream)==child[stream+'_sha256']==audit['raw_sha256'][stream]
    assert sha(LAUNCH/stream)==launcher[stream+'_sha256']
    assert sha(AUDIT_RUN/stream)==execution[stream+'_sha256']
names=[]
for name in ['test_proof_snapshots.py','test_reference_reuse.py']:
    for cls in ast.parse(raw(SOURCE/name)[0]).body:
        if isinstance(cls,ast.ClassDef):names.extend(Path(name).stem+'.'+cls.name+'.'+m.name for m in cls.body if isinstance(m,ast.FunctionDef) and m.name.startswith('test_'))
stderr=raw(W/'command/stderr')[0].decode();observed=re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$',stderr,re.M)
assert len(names)==22 and sorted(names)==sorted(observed)==f['expected_names']==result['expected_names']==sorted(audit['exact_names'])
assert not raw(W/'command/stdout')[0] and re.search(r'^Ran 22 tests in [0-9.]+s\n\nOK\n$',stderr,re.M)
assert len(f['files'])==14 and sum(row['stamp'][3] for row in f['files'].values())==864036
for name,row in f['files'].items():
    data,s=raw(Path(name));assert hashlib.sha256(data).hexdigest()==row['sha256']
    assert [s[key] for key in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]==row['stamp']
for name,resolved in f['routes'].items():assert str(Path(name).resolve(strict=True))==resolved
assert not list((W/'tmp').iterdir())

tree(SOURCE,ROOT/'experiments/bounded-proof-snapshots-v2')
tree(CONTROL,ROOT/'experiments/bounded-proof-snapshot-controls-v2-01')
tree(SOURCE,RESULT/'evidence/source')
tree(CONTROL,RESULT/'evidence/proposal')
for index,name in enumerate(sorted(f['files'])):copy(name,RESULT/'evidence/frozen-inputs'/(str(index).zfill(3)+'-'+Path(name).name))
for source,name in [(W,'work'),(OUTER,'outer'),(LAUNCH,'launcher'),(AUDIT_RUN,'audit-execution')]:tree(source,RESULT/'evidence'/name)
for path in [audit_path,A/'.work/launch_proof_snapshot_controls_v2_01.py',A/'.work/launch_proof_snapshot_controls_v2_01.diff',
    A/'.work/verify_proof_snapshot_controls_v2_01.py',A/'.work/verify_proof_snapshot_controls_v2_01.diff',
    A/'.work/hash-evidence-reservation-analysis-01.json',ROOT/'.work/root-snapshot-v2-controls-packet-review-01.json',Path(__file__).resolve()]:
    copy(path,RESULT/'evidence/provenance'/path.name)
js(RESULT/'evidence/preparation-observation.json',dict(status='peer-reported-tool-observation',
    original_owner=str(A),command=['/opt/homebrew/bin/python3','-B','experiments/bounded-proof-snapshot-controls-v2-01/prepare.py'],
    cwd=str(A),tool_session_id=29357,reported_returncode=0,reporter='/root/runtime_installation',
    limitation='The preparer was run once with an explicitly waited tool session. No standalone preparation execution record or raw streams were saved; none are reconstructed here.',
    proposal_inputs_sha256=sha(CONTROL/'inputs.json'),proposal_launch_sha256=sha(CONTROL/'launch.json')))
js(RESULT/'evidence/helper-source-review.json',dict(status='source-reviewed',reviewer='/root/workspace_capacity',
    helper_sha256=sha(SOURCE/'proof_snapshots.py'),review_scope='Full reference reuse helper source; no imports or test execution by this reviewer.',
    findings=['Exact logical SHA/size, full compressed and logical EOF, ordinary single-link physical blobs and accounted roots.',
              'No repeated physical credit; all aliases remain logical inputs; only new blobs are written.',
              'Caller must bind closed predecessor receipts, projections, manifests and audits before admitting reuse.']))
summary=dict(status='passed-pure-helper-controls',original_source=str(SOURCE),original_controls_source=str(CONTROL),
    original_work=str(W),original_outer=str(OUTER),controls=22,original_test_controls=7,reference_reuse_controls=15,
    helper_sha256=sha(SOURCE/'proof_snapshots.py'),inputs_sha256=sha(CONTROL/'inputs.json'),launch_sha256=sha(CONTROL/'launch.json'),
    receipt_sha256=sha(W/'receipt.json'),result_sha256=sha(W/'result.json'),independent_audit_sha256=sha(audit_path),
    frozen_input_files=14,frozen_input_bytes=864036,exact_test_names=sorted(names),
    supervisor_pid=outer['supervisor_pid'],helper_pid=terminal['pid'],test_pid=child['pid'],canonical_released_at=outer['finished_at'],
    compiler_calls=0,provider_probes=0,process_signals=0,fixtures_remaining=0,
    source_copy_policy='Exact original bytes; copied controls retain original A paths and do not authorize a ROOT rerun.',
    publication_copy_policy='Seven identity fields before/after full source read, exact destination byte readback; atime excluded.',
    limitations=[launcher['wrapper_identity_limitation'],'Preparation has a tool observation only; no saved raw preparation record.',
                 'This qualifies the reusable helper and synthetic controls, not a native fixture, hash driver, application or performance result.'])
js(RESULT/'summary.json',summary)
write(RESULT/'README.md',b'# Bounded proof snapshots v2\n\nThe reusable lossless snapshot helper passed seven original controls and fifteen reference-reuse controls in the original A worktree. The retained evidence includes all fourteen frozen input files, exact test output, source, launch, supervisor, dispatcher and independent audit. No compiler or provider workload ran.\n\nReuse preserves every logical input and verifies each retained gzip blob through compressed SHA and full logical EOF. Callers must separately bind a closed audited predecessor and an already-counted evidence root; reuse only reduces new physical writes. Total logical and compressed limits remain enforced.\n\nPublished source copies are byte-identical to the A originals. Historical controls contain their original paths and are not a ROOT execution recipe. Preparation was observed through one waited tool session; no preparation raw record exists. See summary.json and evidence/preparation-observation.json for exact scope and limitations.\n')
js(RESULT/'manifest.json',dict(status='complete-source-and-closed-evidence-copy',copied_files=copies,
    generated_files={str(path.relative_to(ROOT)):row for path,row in destinations.items() if str(path.relative_to(ROOT)) not in copies},
    original_inputs_sha256=sha(CONTROL/'inputs.json'),original_receipt_sha256=sha(W/'receipt.json')))
for path,row in destinations.items():assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
paths=sorted(str(path.relative_to(ROOT)) for path in destinations)
publication=dict(status='ready-for-exact-root-review-no-git-changes',files={name:destinations[ROOT/name] for name in paths},
    file_count=len(paths),bytes=sum(row['bytes'] for row in destinations.values()),summary_sha256=sha(RESULT/'summary.json'),
    manifest_sha256=sha(RESULT/'manifest.json'),independent_actual_readback=True,original_inputs_unchanged=True,
    source_sha256=sha(Path(__file__).resolve()),finished_at=time.time())
manifest=ROOT/'.work/proof-snapshot-v2-publication-01.json';assert not manifest.exists()
manifest.write_text(json.dumps(publication,sort_keys=True,indent=2)+'\n')
pathlist=ROOT/'.work/proof-snapshot-v2-publication-paths-01.txt';assert not pathlist.exists();pathlist.write_text('\n'.join(paths)+'\n')
print(json.dumps(dict(manifest=str(manifest),sha256=sha(manifest),pathlist=str(pathlist),pathlist_sha256=sha(pathlist),files=len(paths),bytes=publication['bytes']),indent=2))
