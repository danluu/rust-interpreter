"""Finite controls07 publication; prior tool binaries remain archive references."""
from pathlib import Path
import hashlib,json,os,re,stat,time
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
OWNERS={'ROOT':ROOT,'O':O,'A':A,'X':X}
OUT=ROOT/'results/runtime-installation-controls-07'
H=ROOT/'experiments/runtime-installation-controls-07'
S=ROOT/'experiments/runtime-installation-after-preflight05-02'
W=ROOT/'.work/runtime-installation-controls-07'
P=ROOT/'.work/runtime-installation-controls-preparation-execution-07'
L=ROOT/'.work/runtime-installation-controls-launcher-07'
E=ROOT/'.work/runtime-installation-controls-verification-execution-07'
U=ROOT/'.work/experiments/runtime-installation-controls-supervisor-07'
D=ROOT/'results/runtime-installation06-test-development-01'
AUDIT=ROOT/'.work/runtime-installation-controls-independent-verification-07.json'
OLD=ROOT/'results/runtime-installation-controls-05/manifest.json'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
AUDIT_SHA='f644dc4252351654dcbfea4237ab3b42e7d1df7f94555f13d6c9f8b6998b845c'
EXEC_SHA='5f574079215d9bfa437ebabb3b3afd94f75e23747ff98a32d55ef31bdf826f64'
SYSTEM={'/bin/ps','/usr/sbin/lsof','/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14'}

def stamp(p):return {k:getattr(p.lstat(),'st_'+k) for k in FIELDS}
def read(p):
    p=Path(p);assert any(p.is_relative_to(root) for root in OWNERS.values())
    assert p.is_absolute() and p.resolve(strict=True)==p
    before=stamp(p);assert stat.S_ISREG(before['mode']) and before['size']<=8*2**20
    with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW),'rb') as f:
        assert {k:getattr(os.fstat(f.fileno()),'st_'+k) for k in FIELDS}==before
        b=f.read(8*2**20+1)
        assert {k:getattr(os.fstat(f.fileno()),'st_'+k) for k in FIELDS}==before
    assert stamp(p)==before and len(b)==before['size']
    return b,dict(size=len(b),sha256=hashlib.sha256(b).hexdigest(),identity=before)
def sha(p):return read(p)[1]['sha256']
def doc(p):return json.loads(read(p)[0])
def tree(root):
    rows={'.':stamp(root)}
    for parent,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            p=Path(parent)/name;s=stamp(p)
            assert stat.S_ISDIR(s['mode']) or stat.S_ISREG(s['mode'])
            rows[str(p.relative_to(root))]=s;assert len(rows)<=256
    return rows

def main():
    assert Path.cwd()==ROOT and not os.path.lexists(OUT)
    assert sha(AUDIT)==AUDIT_SHA and sha(E/'record.json')==EXEC_SHA
    audit,execution=doc(AUDIT),doc(E/'record.json')
    assert audit['status']=='verified' and audit['controls']==25
    assert execution['status']=='finished' and execution['returncode']==0 and execution['observation_errors']==[]
    assert not any(k in execution for k in ['execution_error','publication_error'])
    assert execution['verified_output']==dict(path=str(AUDIT),sha256=AUDIT_SHA,receipt_sha256=audit['receipt_sha256'])
    assert sha(E/'source.py')==execution['source_sha256']==audit['verifier_sha256']
    assert sha(E/'execution.py')==execution['execution_source_sha256']
    for name in ['stdout','stderr']:assert sha(E/name)==execution[name+'_sha256']
    assert read(E/'stderr')[0]==b''
    inputs,receipt,result=doc(H/'inputs.json'),doc(W/'receipt.json'),doc(W/'result.json')
    assert receipt['status']==result['status']=='passed' and receipt['controls_passed']==result['tests_run']==25
    assert sha(W/'receipt.json')==audit['receipt_sha256'] and sha(W/'result.json')==audit['result_sha256']==receipt['result_sha256']
    assert inputs['expected_names']==result['expected_names']==audit['exact_names']
    assert len(inputs['files'])==31 and sum(row['stamp'][3] for row in inputs['files'].values())==1019352
    for name in ['stdout','stderr']:assert sha(W/'command'/name)==audit['raw_sha256'][name]
    raw=read(W/'command/stderr')[0].decode()
    matches=re.findall(r'^(test_\w+) \(([^)]+)\) \.\.\. ok$',raw,re.M)
    assert all(full.rsplit('.',1)[-1]==method for method,full in matches)
    names=[full for method,full in matches]
    assert sorted(names)==inputs['expected_names'] and len(names)==25 and re.search(r'\nRan 25 tests in [^\n]+\n\nOK\n$',raw)
    assert read(W/'command/stdout')[0]==b''
    terminal,launcher=doc(U/'status.json'),doc(L/'record.json')
    assert terminal['status']=='finished' and terminal['returncode']==0 and sha(U/'status.json')==audit['outer_sha256']
    assert launcher['status']=='terminal-observed' and launcher['returncode']==launcher['launcher_returncode']==0
    assert launcher['observation_errors']==[] and not launcher['actual_task_may_be_live'] and not launcher['wrapper_may_be_live']
    assert sha(L/'record.json')==audit['launcher_sha256'] and launcher['outer_sha256']==audit['outer_sha256']
    prep=doc(P/'record.json')
    assert sha(P/'record.json')=='c2677570a8fceaa67b4964715ce008bc658c3c827a96b06cd1da670f2d2e84d5'
    assert prep['status']=='finished' and prep['returncode']==0 and prep['observation_errors']==[]
    assert prep['finished_at']<=prep['canonical_released_at']<=receipt['started_at']
    assert prep['prepared_packet']==doc(P/'stdout')==dict(status='prepared-unrun',controls=25,files=31,bytes=1019352,
        inputs_sha256=sha(H/'inputs.json'),launch_sha256=sha(H/'launch.json'))
    roots=[H,W,P,L,E,U,D,O/'.work/runtime-installation-controls07-publication-before-name-parser-01'];trees={str(p):tree(p) for p in roots}
    paths={root/name for root in roots for name,row in trees[str(root)].items() if stat.S_ISREG(row['mode'])}
    old=doc(OLD);old_rows={row['path']:row for row in old['files']}
    reused=[]
    for name,row in inputs['files'].items():
        if name in SYSTEM:
            prior=old_rows[name];expected=[prior['identity'][k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]
            assert prior['sha256']==row['sha256'] and prior['bytes']==row['stamp'][3] and expected==row['stamp']
            reused.append(dict(path=name,frozen_row=row,archive_manifest=dict(path=str(OLD),sha256=sha(OLD)),member=prior['relative'],bytes=prior['bytes'],sha256=prior['sha256'],verification='exact prior published manifest association; no live provider or binary payload reread'))
        else:
            p=Path(name);data,current=read(p)
            assert current['sha256']==row['sha256'] and [current['identity'][k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]==row['stamp']
            paths.add(p)
    assert {r['path'] for r in reused}==SYSTEM
    source_names=['entry.py','controller.py','audit_owner.py','routes.json','prepare.py','prepare_once.py','launch.py','test_installation.py']
    paths.update(S/name for name in source_names+['README.md'])
    paths.update(S/(name+'.from-05.diff') for name in source_names)
    scripts=['prepare_runtime_installation_controls_07_once.py','launch_runtime_installation_controls_07_bounded.py','verify_runtime_installation_controls_07.py','execute_runtime_installation_controls_audit_07.py']
    paths.update(ROOT/'.work'/name for name in scripts)
    for name in scripts[1:]:
        stem=name[:-3];paths.update([ROOT/'.work'/(stem+'.unbound-01.py'),ROOT/'.work'/(stem+'.packet-binding-01.diff')])
    for name in ['run.py','prepare.py','child.py']+scripts:
        paths.add(ROOT/'.work'/('runtime-installation-controls07-'+name+'.from-passed05.diff'))
    paths.update(A/'.work'/name for name in ['runtime-installation-controls07-source-handoff-01.json','runtime-installation-controls07-prepared-readback-01.json','runtime-installation-controls07-actual-packet-binding-01.json','readback_installation_controls07_packet_01.py','runtime-installation16-successor-plan-01.json','runtime-installation16-successor-source-handoff-01.json','runtime-installation16-successor-source-handoff-02.json','runtime-installation06-binder04-source-handoff-01.json','runtime-installation06-binder04-independent-readback-01.json'])
    paths.update(ROOT/'.work'/name for name in ['bind_runtime_installation06_preparation_04.py','bind_runtime_installation06_preparation_04.from-03.diff','runtime-installation06-preparation-source-binding-review-01.json','runtime-installation06-preparation-invocation-01.json','runtime-installation06-startup-qualified-source-manifest-01.json'])
    paths.update([AUDIT,OLD,ROOT/'results/runtime-installation-controls-05/root-readback.json',ROOT/'results/runtime10-preflight-saved-audit-01/manifest.json',Path(__file__),O/'.work/verify_runtime_installation_controls07_publication_01.py',O/'.work/runtime-installation06-binder04-preimport-independent-source-slice-01.json'])
    handoff=doc(A/'.work/runtime-installation-controls07-source-handoff-01.json')
    predecessors=[]
    for value in handoff['sources']:
        prior=value['predecessor'];archived=old_rows[prior['path']]
        assert archived['sha256']==prior['sha256'] and archived['bytes']==prior['bytes']
        predecessors.append(dict(reference=prior,archive_manifest=dict(path=str(OLD),sha256=sha(OLD)),member=archived['relative']))
    saved={str(p):read(p) for p in sorted(paths)}
    assert len(saved)<=192 and sum(row['size'] for data,row in saved.values())<=16*2**20
    OUT.mkdir();copies=[]
    for name,(data,row) in saved.items():
        p=Path(name);label,base=next((label,base) for label,base in OWNERS.items() if p.is_relative_to(base))
        rel=Path('payloads')/label/p.relative_to(base);dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        assert read(dest)[0]==data and read(p)==(data,row)
        copies.append(dict(path=name,relative=str(rel),**row))
    assert {str(p):tree(p) for p in roots}==trees
    text='''Controls07 passed all 25 pure installation route, phase, prerequisite, and prefix-budget controls. The test process50745, helper49297, supervisor49294, and independent audit parent55057/child55848 closed successfully. Actual audit f644dc4252351654dcbfea4237ab3b42e7d1df7f94555f13d6c9f8b6998b845c authenticates the complete31-input packet and raw test names.

This capsule includes the actual preparation, launch, command, supervisor and independent-audit closures; executed and unbound source forms; binding and predecessor diffs; the direct25 development provenance; and the later binder04 association. Source-only handoffs and unbound files retain their original historical wording. They are not claims that those historical snapshots had already run.

All31 frozen input rows are retained. The28 source/evidence inputs are copied; three tool binaries use explicit byte-identical member associations in the already published controls05 capsule. No live provider binaries were reread or duplicated. The seven prior harness source versions likewise have explicit controls05 archive associations. The complete direct-development directory includes its original13-file selection and later root readback separately.

Scope is pure control qualification only. Control admission10GiB differs from the separately reviewed production16GiB policy. No compiler, provider, production installation, application, or performance workload was run by this publication. Active production preparation evidence is outside this capsule. Original bytes, seven-field file identities, and selected closed-tree membership were preserved.
'''
    with (OUT/'STATUS.md').open('xb') as f:f.write(text.encode());f.flush();os.fsync(f.fileno())
    status=read(OUT/'STATUS.md')[1]
    manifest=dict(status='published-actual-controls07-passed',controls=25,audit_sha256=AUDIT_SHA,audit_execution_sha256=EXEC_SHA,input_files=31,input_bytes=1019352,copied_input_files=28,referenced_binary_inputs=reused,predecessor_source_associations=predecessors,files=copies,closed_trees=trees,originals_unchanged=True,generated_files=[dict(relative='STATUS.md',size=status['size'],sha256=status['sha256'])],source_only_history_preserved=True,development_is_frozen_qualification=False,compiler_calls=0,provider_reads=0,production_calls=0,binary_bytes_copied=0,performance_measurement=False,publisher_pid=os.getpid(),finished_at=time.time())
    b=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode();assert len(b)<=4*2**20
    with (OUT/'manifest.json').open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
    assert read(OUT/'manifest.json')[0]==b
    print(json.dumps(dict(files=len(saved),bytes=sum(row['size'] for data,row in saved.values()),manifest_sha256=hashlib.sha256(b).hexdigest(),referenced_binary_files=len(reused),status='published')))
if __name__=='__main__':main()
