"""Finite controls08 publication; prior tool binaries remain archive references."""
from pathlib import Path
import hashlib,json,os,re,stat,time
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
OWNERS={'ROOT':ROOT,'O':O,'A':A,'X':X,'R':R}
OUT=ROOT/'results/runtime-installation-controls-08'
H=ROOT/'experiments/runtime-installation-controls-08'
S=ROOT/'experiments/runtime-installation-after-preflight05-03'
W=ROOT/'.work/runtime-installation-controls-08'
P=ROOT/'.work/runtime-installation-controls-preparation-execution-08'
L=ROOT/'.work/runtime-installation-controls-launcher-08'
E=ROOT/'.work/runtime-installation-controls-verification-execution-08'
U=ROOT/'.work/experiments/runtime-installation-controls-supervisor-08'
DERIVATION=A/'.work/runtime-installation-controls08-source-derivation-01'
BINDING=A/'.work/runtime-installation-controls08-actual-packet-binding-01'
AUDIT=ROOT/'.work/runtime-installation-controls-independent-verification-08.json'
OLD=ROOT/'results/runtime-installation-controls-05/manifest.json'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
AUDIT_SHA='a9c87c2f554f0abeaf877923c24636fce390b0f00cdf25d5117a6f902c4afa7d'
EXEC_SHA='06f7db8da2385245e29fd4f8f1b0b947b4d44e3313bc83f3c77eb6163618192f'
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
    assert audit['status']=='verified' and audit['controls']==48
    assert execution['status']=='finished' and execution['returncode']==0 and execution['observation_errors']==[]
    assert not any(k in execution for k in ['execution_error','publication_error'])
    assert execution['verified_output']==dict(path=str(AUDIT),sha256=AUDIT_SHA,receipt_sha256=audit['receipt_sha256'])
    assert sha(E/'source.py')==execution['source_sha256']==audit['verifier_sha256']
    assert sha(E/'execution.py')==execution['execution_source_sha256']
    for name in ['stdout','stderr']:assert sha(E/name)==execution[name+'_sha256']
    assert read(E/'stderr')[0]==b''
    inputs,receipt,result=doc(H/'inputs.json'),doc(W/'receipt.json'),doc(W/'result.json')
    assert receipt['status']==result['status']=='passed' and receipt['controls_passed']==result['tests_run']==48
    assert sha(W/'receipt.json')==audit['receipt_sha256'] and sha(W/'result.json')==audit['result_sha256']==receipt['result_sha256']
    assert inputs['expected_names']==result['expected_names']==sorted(audit['exact_names'])
    assert len(inputs['files'])==48 and sum(row['stamp'][3] for row in inputs['files'].values())==1952550
    for name in ['stdout','stderr']:assert sha(W/'command'/name)==audit['raw_sha256'][name]
    raw=read(W/'command/stderr')[0].decode()
    matches=re.findall(r'^(test_\w+) \(([^)]+)\) \.\.\. ok$',raw,re.M)
    assert all(full.rsplit('.',1)[-1]==method for method,full in matches)
    names=[full for method,full in matches]
    assert sorted(names)==inputs['expected_names'] and len(names)==48 and re.search(r'\nRan 48 tests in [^\n]+\n\nOK\n$',raw)
    assert read(W/'command/stdout')[0]==b''
    terminal,launcher=doc(U/'status.json'),doc(L/'record.json')
    assert terminal['status']=='finished' and terminal['returncode']==0 and sha(U/'status.json')==audit['outer_sha256']
    assert launcher['status']=='terminal-observed' and launcher['returncode']==launcher['launcher_returncode']==0
    assert launcher['observation_errors']==[] and not launcher['actual_task_may_be_live'] and not launcher['wrapper_may_be_live']
    assert sha(L/'record.json')==audit['launcher_sha256'] and launcher['outer_sha256']==audit['outer_sha256']
    prep=doc(P/'record.json')
    assert sha(P/'record.json')=='28e757e6eaf0397446aea4358f1170d86caa28d20717584dd7cb41798b5a103d'
    assert prep['status']=='finished' and prep['returncode']==0 and prep['observation_errors']==[]
    assert prep['finished_at']<=prep['canonical_released_at']<=receipt['started_at']
    assert prep['prepared_packet']==doc(P/'stdout')==dict(status='prepared-unrun',controls=48,files=48,bytes=1952550,
        inputs_sha256=sha(H/'inputs.json'),launch_sha256=sha(H/'launch.json'))
    # Source03's concurrent production packet is outside this finite selection.
    roots=[H,W,P,L,E,U,DERIVATION,BINDING,
        A/'.work/runtime-installation07-binder05-before-actual-controls08-01',
        ROOT/'.work/runtime-installation07-before-source-cap520-01']
    trees={str(p):tree(p) for p in roots}
    paths={root/name for root in roots for name,row in trees[str(root)].items() if stat.S_ISREG(row['mode'])}
    old=doc(OLD);old_rows={row['path']:row for row in old['files']};reused=[]
    for name,row in inputs['files'].items():
        if name in SYSTEM:
            prior=old_rows[name];expected=[prior['identity'][k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]
            assert prior['sha256']==row['sha256'] and prior['bytes']==row['stamp'][3] and expected==row['stamp']
            reused.append(dict(path=name,frozen_row=row,archive_manifest=dict(path=str(OLD),sha256=sha(OLD)),member=prior['relative'],bytes=prior['bytes'],sha256=prior['sha256'],verification='exact prior published manifest association; no live binary payload reread'))
        else:
            p=Path(name);data,current=read(p)
            assert current['sha256']==row['sha256'] and [current['identity'][k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]==row['stamp']
            paths.add(p)
    assert {r['path'] for r in reused}==SYSTEM
    source_names=['entry.py','controller.py','audit_owner.py','routes.json','prepare.py','prepare_once.py','launch.py','imports.py','test_installation.py','test_imports.py']
    paths.update(S/name for name in source_names)
    paths.update(S/(name+'.from-02.diff') for name in source_names)
    native=ROOT/'experiments/runtime-native-loader-probes-01'
    paths.update(native/name for name in ['runtime_compiler.py.diff','producer_recipe.py.diff','audit_recipe.py.diff','derivation.json'])
    scripts=['prepare_runtime_installation_controls_08_once.py','launch_runtime_installation_controls_08_bounded.py','verify_runtime_installation_controls_08.py','execute_runtime_installation_controls_audit_08.py']
    paths.update(ROOT/'.work'/name for name in scripts)
    # Original manifests are selected subsets, without implied membership for
    # later notes. Both ordinary30 passes are retained honestly.
    development_subsets=[]
    for name in ['runtime-installation07-test-development-01','runtime-installation07-test-development-02','runtime-native-loader-development-01']:
        d=ROOT/'results'/name;m=doc(d/'manifest.json');assert len(m)==9 and 'manifest.json' not in m
        for n,row in m.items():
            assert Path(n).name==n and set(row)=={'bytes','sha256'}
            b,current=read(d/n);assert current['size']==row['bytes'] and current['sha256']==row['sha256'];paths.add(d/n)
        paths.add(d/'manifest.json')
        development_subsets.append(dict(directory=str(d),manifest_sha256=sha(d/'manifest.json'),selected_original_files=sorted([*m,'manifest.json']),full_later_directory_membership_claimed=False))
    paths.update(A/'.work'/name for name in [
        'runtime-installation07-source-integration-handoff-01.json',
        'runtime-installation07-preimport-census-01.json',
        'runtime-installation07-native-policy-budget-01.json',
        'runtime-installation-controls08-actual-qualification-handoff-01.json',
        'derive_runtime_installation_controls_08.py','read_bind_runtime_installation_controls_08.py',
        'runtime-native-loader-probes-source-handoff-01.json'])
    paths.update(O/'.work'/name for name in [
        'runtime-installation07-source-development-independent-review-01.json',
        'runtime-native-loader-successor-independent-review-01.json',
        'runtime-native-loader-identity-schema-review-01.json'])
    paths.update(ROOT/'.work'/name for name in [
        'runtime-installation-controls08-prelaunch-root-review-01.json',
        'bind_runtime_installation07_preparation_05.py',
        'bind_runtime_installation07_preparation_05.from-04.diff',
        'runtime-installation07-startup-qualified-source-manifest-01.json',
        'runtime-installation07-preparation-invocation-01.json',
        'runtime-installation07-preparation-source-binding-review-01.json'])
    paths.update([AUDIT,OLD,ROOT/'results/runtime-installation-controls-07/manifest.json',Path(__file__)])
    prior_manifest=ROOT/'results/runtime-installation-controls-07/manifest.json'
    previous={row['path']:row for row in doc(prior_manifest)['files']}
    handoff=doc(DERIVATION/'handoff.json');predecessors=[]
    for current,value in handoff['sources'].items():
        p=value['predecessor'];oldrow=previous[p]
        assert oldrow['sha256']==value['predecessor_sha256']
        predecessors.append(dict(path=p,sha256=oldrow['sha256'],bytes=oldrow['size'],archive_manifest=dict(path=str(prior_manifest),sha256=sha(prior_manifest)),member=oldrow['relative']))
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
    text='''Controls08 passed all48 pure controls: installation route/resource/prerequisite25, native-loader18, and factory5 (including source-admission520 boundary subtests). Test86865, helper86863, supervisor86860 and independent audit parent94399/child95114 closed successfully. Audit a9c87c2f554f0abeaf877923c24636fce390b0f00cdf25d5117a6f902c4afa7d verifies the exact48-input packet, raw names and complete execution closure.

This finite capsule retains all current48 input references:45 source/metadata files copied and three exact tool-binary associations to published controls05. It also retains preparation, test/raw, supervisor, launcher and independent-audit closures; unbound and bound source forms with diffs; both passing ordinary30 development runs and original passing18; source/cap history, metadata budgets, binding reviews and closed binder05 outputs. The seven harness predecessors refer to exact controls07 published members. No binary/provider payload is reread or duplicated by this publication.

Development manifests cover their original nine payloads plus manifest; later notes outside those subsets are not implicitly claimed. Historical source-only wording remains unchanged. Both ordinary30 runs passed: run02 added the approved520-row helper and boundary subtests. Actual48 is a separate controlled qualification. Historical07/25 remains associated with source02. Reviewed source03 entry.py line40 contains one harmless trailing space; these frozen bytes are retained unchanged.

Scope is pure control qualification, with10/9/8 GiB control admission and existing finite fixture/output bounds. No compiler, provider, application or performance workload ran in these controls. The concurrent production preparation07 and any future installation are outside this capsule and are not claimed qualified. Copied source bytes and seven-field identities, finite closed-tree membership and full output readback are checked. Root owns subsequent Git publication; disk completeness is not a Git-index or HEAD claim.
'''
    with (OUT/'STATUS.md').open('xb') as f:f.write(text.encode());f.flush();os.fsync(f.fileno())
    status=read(OUT/'STATUS.md')[1]
    manifest=dict(status='published-actual-controls08-passed',controls=48,audit_sha256=AUDIT_SHA,audit_execution_sha256=EXEC_SHA,input_files=48,input_bytes=1952550,copied_input_files=45,referenced_binary_inputs=reused,predecessor_source_associations=predecessors,development_subsets=development_subsets,files=copies,closed_trees=trees,originals_unchanged=True,generated_files=[dict(relative='STATUS.md',size=status['size'],sha256=status['sha256'])],source_only_history_preserved=True,development_is_frozen_qualification=False,compiler_calls=0,provider_reads=0,production_calls=0,binary_bytes_copied=0,performance_measurement=False,publisher_pid=os.getpid(),finished_at=time.time())
    b=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode();assert len(b)<=4*2**20
    with (OUT/'manifest.json').open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
    assert read(OUT/'manifest.json')[0]==b
    expected={row['relative'] for row in copies}|{'STATUS.md','manifest.json'}
    assert {str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()}==expected
    print(json.dumps(dict(files=len(saved),bytes=sum(row['size'] for data,row in saved.values()),manifest_sha256=hashlib.sha256(b).hexdigest(),referenced_binary_files=len(reused),status='published')))
if __name__=='__main__':main()
