"""Independent byte, closure, input and exact-membership readback; no target imports."""
from pathlib import Path
import hashlib,json,os,re,stat,time
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
OUT=R/'results/runtime-installation-controls-07'
REPORT=O/'.work/runtime-installation-controls07-publication-independent-readback-01.json'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
def identity(p):return {k:getattr(p.lstat(),'st_'+k) for k in FIELDS}
def data(p):
    p=Path(p);assert p.is_absolute() and p.resolve(strict=True)==p
    before=identity(p);assert stat.S_ISREG(before['mode']) and before['size']<=8*2**20
    with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW),'rb') as f:
        assert {k:getattr(os.fstat(f.fileno()),'st_'+k) for k in FIELDS}==before
        b=f.read(8*2**20+1)
        assert {k:getattr(os.fstat(f.fileno()),'st_'+k) for k in FIELDS}==before
    assert identity(p)==before and len(b)==before['size'];return b

def main():
    assert not REPORT.exists();raw=data(OUT/'manifest.json');m=json.loads(raw)
    assert m['status']=='published-actual-controls07-passed' and m['controls']==25
    rows={x['path']:x for x in m['files']};assert len(rows)==len(m['files'])<=192
    copies={};expected={'manifest.json'};total=0
    for source,row in rows.items():
        rel=Path(row['relative']);assert not rel.is_absolute() and '..' not in rel.parts
        assert rel.as_posix() not in expected;expected.add(rel.as_posix())
        original=data(Path(source));copied=data(OUT/rel)
        assert original==copied and identity(Path(source))==row['identity']
        assert len(copied)==row['size'] and hashlib.sha256(copied).hexdigest()==row['sha256']
        copies[source]=copied;total+=len(copied)
    assert total<=16*2**20
    for row in m['generated_files']:
        b=data(OUT/row['relative']);assert len(b)==row['size'] and hashlib.sha256(b).hexdigest()==row['sha256'];expected.add(row['relative'])
    actual=set()
    for base,dirs,files in os.walk(OUT,followlinks=False):
        for name in dirs+files:
            p=Path(base)/name;assert not p.is_symlink()
            if p.is_file():actual.add(p.relative_to(OUT).as_posix())
    assert actual==expected
    for name,saved in m['closed_trees'].items():
        root=Path(name);current={'.':identity(root)}
        for base,dirs,files in os.walk(root,followlinks=False):
            for member in dirs+files:
                p=Path(base)/member;assert not p.is_symlink();current[str(p.relative_to(root))]=identity(p)
        assert current==saved
    def doc(p):return json.loads(copies[str(p)])
    def sha(p):return hashlib.sha256(copies[str(p)]).hexdigest()
    H=R/'experiments/runtime-installation-controls-07';W=R/'.work/runtime-installation-controls-07'
    E=R/'.work/runtime-installation-controls-verification-execution-07';P=R/'.work/runtime-installation-controls-preparation-execution-07'
    L=R/'.work/runtime-installation-controls-launcher-07';U=R/'.work/experiments/runtime-installation-controls-supervisor-07'
    inputs=doc(H/'inputs.json');audit_path=R/'.work/runtime-installation-controls-independent-verification-07.json';audit=doc(audit_path);execution=doc(E/'record.json')
    assert sha(audit_path)==m['audit_sha256']=='f644dc4252351654dcbfea4237ab3b42e7d1df7f94555f13d6c9f8b6998b845c'
    assert sha(E/'record.json')==m['audit_execution_sha256']=='5f574079215d9bfa437ebabb3b3afd94f75e23747ff98a32d55ef31bdf826f64'
    assert audit['status']=='verified' and audit['controls']==25 and execution['status']=='finished' and execution['returncode']==0
    assert execution['observation_errors']==[] and not any(k in execution for k in ['execution_error','publication_error'])
    assert execution['verified_output']['sha256']==sha(audit_path)
    assert sha(E/'source.py')==execution['source_sha256']==audit['verifier_sha256'];assert sha(E/'execution.py')==execution['execution_source_sha256']
    assert doc(E/'stdout')==audit and copies[str(E/'stderr')]==b''
    for name in ['stdout','stderr']:assert sha(E/name)==execution[name+'_sha256']
    receipt,result=doc(W/'receipt.json'),doc(W/'result.json')
    assert sha(W/'receipt.json')==audit['receipt_sha256'] and sha(W/'result.json')==audit['result_sha256']==receipt['result_sha256']
    assert receipt['status']==result['status']=='passed' and receipt['controls_passed']==result['tests_run']==25
    assert not any(result[k] for k in ['failures','errors','skipped','expected_failures','unexpected_successes','compiler_calls','child_processes'])
    assert sha(H/'inputs.json')==receipt['inputs_sha256']
    command=doc(W/'command/receipt.json');assert command['status']=='finished' and command['returncode']==0
    assert command['pid']==audit['test_pid']==receipt['commands'][0]['pid']
    assert sha(W/'command/receipt.json')==receipt['commands'][0]['sha256']
    rawstderr=copies[str(W/'command/stderr')].decode()
    names=sorted(f'{cls}.{method}' for method,cls in re.findall(r'^(test_\w+) \(([^)]+)\) \.\.\. ok$',rawstderr,re.M))
    assert names==audit['exact_names']==inputs['expected_names']==result['expected_names'] and len(names)==25
    assert re.search(r'\nRan 25 tests in [^\n]+\n\nOK\n$',rawstderr) and copies[str(W/'command/stdout')]==b''
    for name in ['stdout','stderr']:assert sha(W/'command'/name)==command[name+'_sha256']==audit['raw_sha256'][name]
    for path,status in [(L/'record.json','terminal-observed'),(U/'status.json','finished'),(P/'record.json','finished')]:
        d=doc(path);assert d['status']==status and d['returncode']==0
    launcher=doc(L/'record.json');outer=doc(U/'status.json');prep=doc(P/'record.json')
    assert sha(L/'record.json')==audit['launcher_sha256'] and sha(U/'status.json')==audit['outer_sha256']==launcher['outer_sha256']
    assert not launcher['actual_task_may_be_live'] and not launcher['wrapper_may_be_live'] and launcher['observation_errors']==[]
    assert outer['supervisor_pid']==audit['supervisor_pid']==receipt['parent_pid'] and outer['child_pid']==audit['helper_pid']==receipt['pid']
    assert prep['observation_errors']==[] and prep['finished_at']<=prep['canonical_released_at']<=receipt['started_at']
    assert prep['prepared_packet']==doc(P/'stdout') and prep['prepared_packet']['inputs_sha256']==sha(H/'inputs.json')
    assert len(inputs['files'])==m['input_files']==31 and sum(x['stamp'][3] for x in inputs['files'].values())==m['input_bytes']==1019352
    oldpath=R/'results/runtime-installation-controls-05/manifest.json';old={x['path']:x for x in doc(oldpath)['files']}
    reused={x['path']:x for x in m['referenced_binary_inputs']};assert len(reused)==3
    copied=0
    for name,row in inputs['files'].items():
        if name in reused:
            ref=reused[name];prior=old[name]
            assert ref['frozen_row']==row and ref['archive_manifest']==dict(path=str(oldpath),sha256=sha(oldpath))
            assert prior['relative']==ref['member'] and prior['sha256']==ref['sha256']==row['sha256'] and prior['bytes']==ref['bytes']==row['stamp'][3]
            assert [prior['identity'][k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]==row['stamp']
            assert name not in rows
        else:
            assert sha(name)==row['sha256'] and rows[name]['size']==row['stamp'][3]
            assert [rows[name]['identity'][k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]==row['stamp'];copied+=1
    assert copied==m['copied_input_files']==28
    assert len(m['predecessor_source_associations'])==7
    for association in m['predecessor_source_associations']:
        p=association['reference'];prior=old[p['path']]
        assert prior['sha256']==p['sha256'] and prior['bytes']==p['bytes'] and prior['relative']==association['member']
        assert association['archive_manifest']==dict(path=str(oldpath),sha256=sha(oldpath))
    report=dict(status='verified-exact-controls07-publication',manifest=dict(path=str(OUT/'manifest.json'),sha256=hashlib.sha256(raw).hexdigest()),copied_files=len(rows),copied_bytes=total,total_publication_files=len(actual),full_original_bytes_and_identities_unchanged=True,closed_trees=len(m['closed_trees']),controls=25,input_files=31,copied_input_files=28,referenced_binary_inputs=3,binary_payload_rereads=0,prior_source_archive_associations=7,exact_actual_raw_names=True,audit_sha256=sha(audit_path),audit_execution_sha256=sha(E/'record.json'),reader_sha256=hashlib.sha256(data(Path(__file__))).hexdigest(),pid=os.getpid(),finished_at=time.time(),scope='Publication/source/raw readback only; no control/producer/compiler/provider invocation')
    with REPORT.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    print(json.dumps(dict(report=str(REPORT),sha256=hashlib.sha256(data(REPORT)).hexdigest(),**report)))
if __name__=='__main__':main()
