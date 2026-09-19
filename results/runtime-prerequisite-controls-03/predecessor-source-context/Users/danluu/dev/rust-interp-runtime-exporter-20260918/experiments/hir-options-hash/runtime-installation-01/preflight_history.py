"""Pure actual two-probe source-preflight reader for later installation discovery."""
import json
from pathlib import Path


def require(ok,message):
    if not ok:raise RuntimeError(message)


def validate(q,recipe,*,packet,work,candidate,audit_reference,read_json,read_bytes,sha):
    packet,work=Path(packet),Path(work)
    plan=read_json(packet/'plan.json');freeze=read_json(packet/'inputs.json')
    terminal=read_json(work/'receipt.json');result=read_json(work/'source-probe/result.json')
    audit=read_json(audit_reference['path'])
    require(sha(audit_reference['path'])==audit_reference['sha256'] and audit['status']=='verified'
        and audit['receipt_sha256']==sha(work/'receipt.json'),'actual independent source-preflight audit required')
    require(terminal['status']=='passed' and terminal['phase']==plan['phase']=='preflight'
        and terminal['inputs_sha256']==sha(packet/'inputs.json')
        and terminal['plan_sha256']==freeze['plan_sha256']==sha(packet/'plan.json')
        and terminal['source_preflight_sha256']==sha(work/'source-probe/result.json'),'actual source-preflight terminal binding differs')
    require(read_json(plan['specification']['path'])==candidate and sha(plan['specification']['path'])==plan['specification']['sha256'],
        'actual source-preflight candidate differs')
    outer=read_json(Path(plan['supervisor_work'])/'status.json')
    launch=read_json(packet/'launch.json')
    require(outer['status']=='finished' and outer['returncode']==0 and outer['child_pid']==terminal['pid']
        and outer['supervisor_pid']==terminal['parent_pid'] and outer['command']==launch['command'][6:]
        and outer['cwd']==plan['owner'] and outer['log_sha256']==sha(Path(plan['supervisor_work'])/'command.log')
        and outer['child_started_at']<=terminal['started_at']<=terminal['admitted_at']<=terminal['finished_at']<=outer['finished_at'],
        'actual source-preflight supervisor/lock release differs')
    desired=recipe.preflight_commands(q,candidate,Path(plan['owner']),work/'source-probe',plan['environment'])
    require(plan['children']==desired and len(terminal['children'])==len(result['commands'])==2,
        'two exact actual source-preflight commands required')
    require(result['status']=='passed' and result['policy']==q.PREFLIGHT and result['full_current_guard_passed'] is True
        and result['candidate_sha256']==q.runtime.digest(candidate) and result['candidate_is_not_installation'] is True
        and result['capability_added'] is False and result['exact_source_paths_observed'] is True,
        'source-preflight result scope differs')
    identity=q.runtime.identity_for(candidate)
    component=next(c for c in candidate['components'] if c['role']=='runtime')
    checkout=Path(identity['provenance']['source_checkout']);sysroot=Path(component['root'])
    files={name[len(q.std.SOURCE):]:digest for name,digest in identity['files'].items() if name.startswith(q.std.SOURCE)}
    source=work/'source-probe/source.rs'
    require(read_bytes(source)==q.PROBE,'actual probe source differs')
    def payload(relative):
        require(relative in files and q.runtime.relative(relative)==relative,'unadmitted diagnostic source')
        path=checkout/'library'/relative
        require(sha(path)==files[relative],'current diagnostic source byte differs')
        retained=result['retained_sources'][relative]
        require(Path(retained['path'])==work/'source-probe/sources'/relative and retained['sha256']==files[relative]
            and sha(retained['path'])==files[relative] and read_bytes(retained['path'])==read_bytes(path),'retained diagnostic source differs')
        return read_bytes(path)
    previous=terminal['admitted_at'];missing=[]
    for index,(wanted,ref,proof) in enumerate(zip(desired,terminal['children'],result['commands'],strict=True)):
        path=Path(wanted['output'])/'receipt.json';child=read_json(path)
        require(ref['path']==proof['path']==str(path) and ref['sha256']==proof['sha256']==sha(path)
            and ref['pid']==child['pid'] and ref['returncode']==child['returncode']==1,'actual source-probe references differ')
        require(child['status']=='finished' and child['command']==wanted['argv'] and child['cwd']==wanted['cwd']
            and child['environment']==wanted['environment'] and child['expected']==[1]
            and child['supervisor_pid']==terminal['pid'] and child['parent_pid']==terminal['parent_pid']
            and previous<=child['started_at']<=child['finished_at']<=terminal['finished_at'],'source-probe actual ownership differs')
        previous=child['finished_at']
        obs=child['identity'];parts=obs['ps'].split()
        require(obs['ps_returncode']==0 and list(map(int,parts[:3]))==[child['pid'],terminal['pid'],child['pid']]
            and len(parts)>9 and parts[8]=='??' and obs['ps'].endswith(' '.join(wanted['argv'])),'source-probe PS identity differs')
        if obs['cwd_returncode']==0:require('n'+wanted['cwd']+'\n' in obs['cwd'],'source-probe cwd differs')
        else:
            require(obs['cwd_returncode']==1 and obs['cwd']=='','source-probe cwd error differs')
            missing.append(dict(index=index,pid=child['pid'],requested_cwd=wanted['cwd'],limitation='Fast-child contemporaneous cwd observation unavailable.'))
        for stream in ['stdout','stderr']:require(sha(path.parent/stream)==child[stream+'_sha256'],'source-probe raw digest differs')
        require(not read_bytes(path.parent/'stdout'),'unexpected source-preflight stdout')
        diagnostics=[json.loads(line) for line in read_bytes(path.parent/'stderr').splitlines() if line.strip()]
        observed=q.validate_observation(diagnostics,application=source,
            local_roots=(sysroot/'lib/rustlib/src/rust/library',checkout/'library'),
            virtual_root=Path('/rustc')/result['source_commit']/'library',files=files,payload_for=payload,virtual=index==1)
        require(observed==proof['observed'],'actual diagnostic observation differs')
    return dict(result=result,reference=dict(path=str(work/'source-probe/result.json'),sha256=sha(work/'source-probe/result.json')),
        audit=dict(audit_reference),receipt_sha256=sha(work/'receipt.json'),unavailable_contemporaneous_cwd=missing)
