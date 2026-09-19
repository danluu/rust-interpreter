#!/usr/bin/env python3
"""Read-only preparation of the remaining-file successor, after real fixtures."""
import ast,json,os
from pathlib import Path
import time
import retire_remaining as r

OLD=r.HERE/'plan-01'
FAILED=r.OWNER/'.work/hir-options-hash-intermediate-retirement-01'
AUDIT=r.OWNER/'.work/hir-options-hash-intermediate-retirement-failure-verification-01.json'
CONTROL=r.OWNER/'.work/hir-options-hash-intermediate-retirement-controls-01'
CONTROL_AUDIT=r.OWNER/'.work/hir-options-hash-intermediate-retirement-controls-verification-01.json'

def write(path,value):
    with path.open('x') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
def ref(path):return dict(path=str(path),sha256=r.sha(path))

def main():
    assert Path.cwd()==r.OWNER and r.sys.dont_write_bytecode and not r.sys.flags.optimize
    assert not r.PACKET.exists() and not r.WORK.exists()
    assert r.sha(OLD/'inputs.json')=='4413647169a87a8a0e841ad5b79af7bbb9f813bdcbd6c44da1d036ab7afe8828'
    assert r.sha(AUDIT)=='b384210d5deb09e6c1b03cb10045215164cf4fb89907309ae59a8eefb887f84f'
    assert r.sha(CONTROL_AUDIT)=='40ecc5ef1e63e2de3480a5e76d18f58cf39498238fe3b87850ce2a426cb3a461'
    files={Path(name) for name in r.read(OLD/'inputs.json')['files']}
    for name,row in r.read(OLD/'inputs.json')['files'].items():assert r.file(Path(name))==row,name
    audit=r.read(AUDIT);terminal=r.read(FAILED/'receipt.json')
    assert audit['status']=='verified-partial-failure' and audit['removed_files']==1 and audit['remaining_selected_files']==4645
    assert terminal['status']=='failed' and terminal['deleted']==[] and terminal['error']=="RuntimeError('directory identity changed during unlink')"
    assert r.sha(FAILED/'receipt.json')==audit['terminal_sha256'] and not (FAILED/'deleted.jsonl').exists()
    old=r.read(OLD/'assessment.json');old_plan=r.read(OLD/'plan.json')
    missing=audit['missing_files'][0]['path'];relative=str(Path(missing).relative_to(r.ROOT))
    assert old['selected'][relative]==audit['missing_files'][0]['original']
    assert not Path(missing).exists() and not Path(missing).is_symlink()
    partial=Path(audit['complete_current_inventory']['path']);assert r.sha(partial)==audit['complete_current_inventory']['sha256']
    entries,allocated=r.inventory(r.ROOT);assert entries==r.read(partial)['entries']
    assert set(old['entries'])-set(entries)=={relative} and not set(entries)-set(old['entries'])
    changed={name for name in entries if entries[name]!=old['entries'][name]}
    assert changed==set(audit['changed_parent_directories'])=={str(Path(relative).parent)}
    for name in changed:
        before=old['entries'][name];after=entries[name];assert dict(before=before,after=after)==audit['changed_parent_directories'][name]
        assert before['kind']==after['kind']=='directory' and all(before['identity'][k]==after['identity'][k] for k in ['dev','ino','mode'])
    selected={name:row for name,row in old['selected'].items() if name!=relative}
    assert len(selected)==4645 and len({(row['identity']['dev'],row['identity']['ino']) for row in selected.values()})==4645
    for name,row in selected.items():assert entries[name]==dict(kind='file',identity=row['identity'],sha256=row['sha256']) and row['identity']['nlink']==1
    for name,rows in old['protected_roots'].items():assert r.inventory(Path(name))[0]==rows
    for name,row in old['protected_files'].items():assert r.file(Path(name))==row
    assert r.history()==old['history'] and r.identity(r.ROOT.parent)==old['outer_parent']
    for name in old['transition']['consumer']['absent_before_retirement']:
        path=Path(name);assert not path.exists() and not path.is_symlink()
    c=r.read(CONTROL/'receipt.json');cv=r.read(CONTROL_AUDIT)
    assert c['status']=='passed' and c['controls_passed']==cv['controls']==6 and cv['status']=='verified'
    assert r.sha(CONTROL/'receipt.json')==cv['receipt_sha256'] and r.sha(CONTROL/'result.json')==cv['result_sha256']
    control_freeze=r.read(r.HERE/'controls-01/inputs.json')
    for name,row in control_freeze['files'].items():
        path=Path(name);info=path.lstat();assert [info.st_dev,info.st_ino,info.st_mode,info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_nlink]==row['stamp'] and r.sha(path)==row['sha256'];files.add(path)
    prior=dict(terminal=ref(FAILED/'receipt.json'),audit=ref(AUDIT),inventory=ref(partial),removed_path=missing,original_record=old['selected'][relative],original_plan=ref(OLD/'plan.json'),original_freeze=ref(OLD/'inputs.json'),missing_ledger_truth='Failed01 unlinked exactly one file before its failed parent-nlink check and before old ledger publication; zero recorded deleted entries is not zero mutation.')
    transition=json.loads(json.dumps(old['transition']))
    transition.update(policy='explicit-compiler-intermediate-retirement-v2',prior_partial=prior,
        before='Exactly the independently audited prior one-file removal is already absent; remaining4645 retain original full bytes and identity.',
        after='This successor removes only remaining4645; combined with original partial one, original4646 selected paths are absent. Old snapshots remain historical, check stamp is unchanged but incomplete.',
        remaining_relative_paths=sorted(selected),combined_files=4646,successor_files=4645)
    assert missing not in transition['historical_snapshot']['retired_entries'] and missing not in transition['check_stamp']['retired_entries']
    assessment=old|dict(status='prepared-remaining-not-retired',entries=entries,selected=selected,allocated_bytes_observation=allocated,
        selected_allocated_bytes_observation=sum((r.ROOT/name).lstat().st_blocks*512 for name in selected),transition=transition,prior_partial=prior,prepared_at=time.time())
    starts=dict(old_plan['owned_start_times'])
    old_outer=r.OWNER/'.work/experiments/hir-options-hash-intermediate-retirement-supervisor-01'
    state=r.read(old_outer/'status.json');assert state['status']=='finished' and state['returncode']==1
    for key in ['supervisor_identity','child_identity']:
        parts=state[key].splitlines()[-1].split();starts[parts[0]]=parts[2:7]
    commands=json.loads(json.dumps(old_plan['commands']));commands[1]['argv'][2]=','.join(sorted(starts,key=int))
    plan=old_plan|dict(files=4645,commands=commands,owned_start_times=starts,platform=list(os.uname()),
        controls=dict(receipt=ref(CONTROL/'receipt.json'),audit=ref(CONTROL_AUDIT),freeze=ref(r.HERE/'controls-01/inputs.json')),
        mutation='Exactly remaining4645 single-link ordinary files; held nofollow directory/file FDs and dir_fd unlink, fsynced intent before unlink and completion before postconditions, stable parent dev/ino/mode plus exact membership. No directory removal or provider mutation.')
    # Preserve actual prior failure, fixtures and their complete raw evidence.
    for base in [FAILED,old_outer,CONTROL,r.OWNER/'.work/experiments/hir-options-hash-intermediate-retirement-controls-supervisor-01',r.HERE/'controls-01',OLD]:
        for path in base.rglob('*'):
            assert not path.is_symlink()
            if path.is_file():files.add(path)
    for name in ['hir-options-hash-intermediate-retirement-launch-01','hir-options-hash-intermediate-retirement-controls-launch-01']:
        for suffix in ['.actual.json','.stdout','.stderr']:files.add(r.OWNER/'.work'/(name+suffix))
    for name in ['verify_intermediate_retirement_failure_01.py','verify_intermediate_retirement_controls_01.py','launch_intermediate_retirement_01.py','launch_intermediate_retirement_controls_01.py']:
        files.add(r.OWNER/'.work'/name)
    files.update([AUDIT,partial,CONTROL_AUDIT,r.HERE/'fd_remove.py',r.HERE/'test_fd_remove.py',r.HERE/'retire_remaining.py',r.HERE/'prepare_remaining.py',r.HERE/'REMAINING.md'])
    r.PACKET.mkdir();write(r.PACKET/'assessment.json',assessment);write(r.PACKET/'plan.json',plan)
    files.update([r.PACKET/'assessment.json',r.PACKET/'plan.json'])
    frozen={}
    for path in sorted(files):
        frozen[str(path)]=r.file(path)
        if path.suffix=='.py':ast.parse(path.read_bytes())
    write(r.PACKET/'inputs.json',dict(files=frozen))
    command=['/opt/homebrew/bin/python3','-B',str(r.OWNER/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-intermediate-retirement-supervisor-02','--','/opt/homebrew/bin/python3','-B',str(r.HERE/'retire_remaining.py'),'--inputs-sha256',r.sha(r.PACKET/'inputs.json')]
    write(r.PACKET/'launch.json',dict(command=command,cwd=str(r.OWNER),environment=plan['environment'],review_required_before_execution=True))
    print(json.dumps(dict(status='prepared-unrun',files=len(frozen),bytes=sum(row['identity']['size'] for row in frozen.values()),selected=4645,entries=len(entries),launch_sha256=r.sha(r.PACKET/'launch.json'),freeze_sha256=r.sha(r.PACKET/'inputs.json'),plan_sha256=r.sha(r.PACKET/'plan.json')),indent=2))

if __name__=='__main__':main()
