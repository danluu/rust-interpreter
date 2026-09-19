#!/usr/bin/env python3
"""Prepare exact file retirement; read/hash current inputs, never remove/probe."""
import ast
import json
import os
from pathlib import Path
import sys
import time

import retire as r

CONSUMER=r.X/'experiments/hir-options-hash/compiler-build-continuation-03'
CONSUMER_HASHES={
    'continue.py':'f9e850f5545e08e5f60de3224f303886e94050ad729f5324b47ae496f5dee484',
    'prepare.py':'17c9845bfafb77c4838a37c0edfd912702e928f7c97cab9b1f0ab0e6ef7bc38d',
    'bounded_command_v2.py':'c4aa7dec6cd526e68b13adb0aea9309784acbe36ff279135f3813d26fdc71682',
    'support_producer.py':'6573f3d899f02314bd67b08db97bbf56665833e6f54d68afa9c9203032b10e54',
    'support_source.py':'f65cdf8c988c2bc16e51d088b07ccd152292d1dc853506591eca5ed51cd021b2',
    'producer_parsers.py':'4fc47abfcb8493efe32bbb58b62f0034a1ed3e32cb388b601b15cf11c065a7d4',
    'timing_context.py':'30780686391118c41c73a7765316ca339dc572e677d45b2cf88a41655c437f19',
}

def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')

def main():
    assert Path.cwd()==r.OWNER and sys.dont_write_bytecode and not sys.flags.optimize
    assert not r.PACKET.exists() and not r.WORK.exists()
    started=time.time();proposal=r.read(r.HERE/'proposal.json');files=set()
    for name,row in proposal['records'].items():
        path=Path(name);assert path.stat().st_size==row['bytes'] and r.sha(path)==row['sha256'];files.add(path)
    eligibility=r.read(r.OWNER/'.work/hir-options-hash-intermediate-eligibility-01.json')
    content=r.read(r.OWNER/'.work/hir-options-hash-intermediate-content-01.json')
    association=r.read(r.OWNER/'.work/hir-options-hash-intermediate-association-02.json')
    assert proposal['scope_root']==eligibility['root']==str(r.ROOT)
    assert set(content['candidates'])==set(eligibility['candidates'])==set(association['bindings']) and len(content['candidates'])==4646
    entries,allocated=r.inventory(r.ROOT)
    selected={}
    for name,row in content['candidates'].items():
        path=Path(name);relative=str(path.relative_to(r.ROOT));current=entries[relative]
        assert current==dict(kind='file',identity=row['identity'],sha256=row['sha256']) and current['identity']['nlink']==1,name
        assert association['bindings'][name] and all(0<=index<len(content['producer_commands']) for index in association['bindings'][name])
        assert path.name.endswith(('.rcgu.o','.rlib','.rmeta'))
        selected[relative]=dict(sha256=row['sha256'],identity=row['identity'],producer_commands=association['bindings'][name])
    assert len({(row['identity']['dev'],row['identity']['ino']) for row in selected.values()})==4646
    assert len(selected)==3954+391+301
    private=eligibility['stamps']['.librustc-stamp'];check=eligibility['stamps']['.check-librustc-stamp']
    assert len(private['paths'])==256 and not (set(private['paths'])&set(content['candidates']))
    stamps={};protected={}
    for row in [private,check]:
        path=Path(row['path']);assert r.sha(path)==row['sha256'];stamps[str(path)]=r.file(path)
        # The stamp spelling is the retained bootstrap target tag followed by
        # an absolute path, with NUL delimiters. Reconfirm complete membership.
        parts=path.read_bytes().split(b'\0');assert parts[-1]==b''
        paths=[word[1:].decode() for word in parts[:-1]]
        assert paths==row['paths']
    for name in private['paths']:
        path=Path(name);protected[name]=r.file(path)
    for name in ['rustc','rustdoc']:
        path=r.S/'build/bootstrap/debug'/name;protected[str(path)]=r.file(path)
    protected.update(stamps)
    provider_roots={}
    for name in ['stage0','ci-llvm','stage0-sysroot','stage1']:
        root=r.S/'build/aarch64-apple-darwin'/name;provider_roots[str(root)]=r.inventory(root)[0]
    assert all(not Path(name).is_relative_to(r.ROOT) for name in provider_roots)
    initial_path=r.X/'experiments/hir-options-hash/compiler-build-continuation-01/plan.json'
    initial=r.read(initial_path);assert r.sha(initial_path)==eligibility['original_snapshot_plan_sha256']
    initial_files=initial['continued_outputs'][str(r.S/'build')]
    transitions={}
    for name,row in content['candidates'].items():
        key=str(Path(name).relative_to(r.S/'build'))
        assert (key in initial_files)==row['prior_initial_snapshot']
        assert (name in check['paths'])==row['check_stamp_entry']
        if key in initial_files:transitions[name]=initial_files[key]
    check_retired=sorted(set(check['paths'])&set(content['candidates']))
    assert len(transitions)==1690 and len(check_retired)==143
    for row in eligibility['freeze_records']:
        path=Path(row['path']);assert r.sha(path)==row['sha256'];catalog=r.read(path)
        assert not (set(catalog['files'])&set(content['candidates']));files.add(path)
    consumer={}
    for name,digest in CONSUMER_HASHES.items():
        path=CONSUMER/name;assert r.sha(path)==digest,(name,r.sha(path));consumer[str(path)]=digest;files.add(path)
    # X explicitly holds preparation; future snapshot/terminal must not exist.
    consumer_absent=[CONSUMER/name for name in ['plan.json','inputs.json','launch.json']]
    consumer_absent.append(r.X/'.work/hir-options-hash-compiler-build-continuation-03')
    assert all(not p.exists() and not p.is_symlink() for p in consumer_absent)
    histories=r.history();starts={}
    for outer_name in ['hir-options-hash-compiler-build-supervisor-02','hir-options-hash-compiler-build-continuation-supervisor-01']:
        root=r.X/'.work/experiments'/outer_name;outer=r.read(root/'status.json')
        assert outer['status']=='finished' and outer['returncode']==1
        for name in ['supervisor_identity','child_identity']:
            words=outer[name].splitlines()[-1].split();starts[words[0]]=words[2:7]
        for path in root.iterdir():assert path.is_file() and not path.is_symlink();files.add(path)
    for proof in content['histories']:
        files.add(Path(proof['path']))
        for child in proof['children']:
            files.add(Path(child['path']))
            for row in child['streams'].values():files.add(Path(row['path']))
    for records in [content['source_references'],association['source']]:
        for name,row in records.items():
            path=Path(name);assert r.sha(path)==row['sha256'] and path.stat().st_size==row['bytes'];files.add(path)
    transition=dict(policy='explicit-compiler-intermediate-retirement-v1',before='All selected files present with retained complete hashes.',
        after='Only selected disposable intermediates absent. Old whole-tree snapshots remain historical observations. Original check stamp stays byte-identical but describes an incomplete cache.',
        historical_snapshot=dict(path=str(initial_path),sha256=r.sha(initial_path),retired_entries=transitions),
        check_stamp=dict(path=check['path'],sha256=check['sha256'],retired_entries=check_retired,complete_before=True,complete_after=False),
        private_stamp=dict(path=private['path'],sha256=private['sha256'],preserved_entries=private['paths']),
        no_byte_identical_rebuild_promise=True,reconstruction_references=proposal['records'],
        consumer=dict(files=consumer,role='Only registered D2 ToolBootstrap support test plus final two Git guards; no native/compiler/interface rebuild. Snapshot occurs after separately approved retirement.',absent_before_retirement=list(map(str,consumer_absent))))
    assessment=dict(status='prepared-not-retired',root=str(r.ROOT),started_at=started,finished_at=time.time(),
        entries=entries,selected=selected,outer_parent=r.identity(r.ROOT.parent),allocated_bytes_observation=allocated,
        selected_allocated_bytes_observation=eligibility['candidate_allocated_bytes'],protected_roots=provider_roots,
        protected_files=protected,stamp_files=stamps,history=histories,transition=transition)
    environment=dict(HOME='/Users/danluu',LANG='C',LC_ALL='C',PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
        PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHON_COLORS='0',__CF_USER_TEXT_ENCODING='0x1F5:0x0:0x0')
    assert os.getuid()==501
    executors={}
    for name in ['/opt/homebrew/bin/python3','/usr/sbin/lsof','/bin/ps']:
        path=Path(name);resolved=path.resolve(strict=True)
        executors[name]=dict(resolved=str(resolved),route_identity=r.identity(path),file=r.file(resolved));files.add(resolved)
    commands=[dict(label='open-handles-stage1-rustc',argv=['/usr/sbin/lsof','-nP','+D',str(r.ROOT)],expected=[1]),
        dict(label='completed-compiler-owners',argv=['/bin/ps','-p',','.join(sorted(starts,key=int)),'-o','pid=,ppid=,pgid=,lstart=,tty=,command='],expected=[0,1])]
    plan=dict(root=str(r.ROOT),owner=str(r.OWNER),files=4646,remove_directories=False,minimum_free_gib=9,wait_seconds=600,
        canonical_lock=str(r.owned.CANONICAL_LOCK),environment=environment,platform=list(os.uname()),
        python=str(Path('/opt/homebrew/bin/python3').resolve()),executors=executors,commands=commands,owned_start_times=starts,
        mutation='Exact single-link ordinary files only; held nofollow parent/root/file FDs and dir_fd unlink. No directory/permission/link/provider mutations.',
        capacity_limitation='st_blocks is an allocation observation, not an APFS extent reservation; only actual post-retirement free bytes decide future 24 GiB admission.',
        quiescence_limitation='Empty exact-target lsof and historical PID/start observations are point-in-time checks, not a reservation or process-control permission.')
    r.PACKET.mkdir();write(r.PACKET/'assessment.json',assessment);write(r.PACKET/'plan.json',plan)
    files.update([r.PACKET/'assessment.json',r.PACKET/'plan.json',r.HERE/'proposal.json',r.HERE/'PROPOSAL.md',
        r.HERE/'retire.py',r.HERE/'prepare.py',r.HERE/'RETIREMENT.md',r.OWNER/'experiments/stable-cgu/owned_stage.py',r.OWNER/'scripts/supervise_experiment.py'])
    frozen={}
    for path in sorted(files):
        frozen[str(path)]=r.file(path)
        if path.suffix=='.py':ast.parse(path.read_bytes())
    write(r.PACKET/'inputs.json',dict(files=frozen))
    command=['/opt/homebrew/bin/python3','-B',str(r.OWNER/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-intermediate-retirement-supervisor-01','--',
        '/opt/homebrew/bin/python3','-B',str(r.HERE/'retire.py'),'--inputs-sha256',r.sha(r.PACKET/'inputs.json')]
    write(r.PACKET/'launch.json',dict(command=command,cwd=str(r.OWNER),environment=environment,review_required_before_execution=True))
    print(json.dumps(dict(packet=str(r.PACKET),frozen_files=len(frozen),frozen_bytes=sum(v['identity']['size'] for v in frozen.values()),
        selected_files=len(selected),target_entries=len(entries),protected_files=len(protected),protected_tree_entries=sum(map(len,provider_roots.values())),
        launch_sha256=r.sha(r.PACKET/'launch.json'),freeze_sha256=r.sha(r.PACKET/'inputs.json'),plan_sha256=r.sha(r.PACKET/'plan.json')),indent=2))

if __name__=='__main__':main()
