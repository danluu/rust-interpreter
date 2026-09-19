"""One finite native Ruff frontend screen; no application tests or adoption claim."""
from pathlib import Path
import argparse,fcntl,hashlib,json,os,re,shlex,stat,statistics,sys,time,tomllib
HERE=Path(__file__).absolute().parent
# All local executable source bytes are authenticated before importing common.
def bootstrap(sha):
    route=HERE.parents[1]/'.work/proc-macro-arena-ruff-screen-invocation-03.json'
    raw=route.read_bytes();assert len(raw)<=2**20 and hashlib.sha256(raw).hexdigest()==sha
    invocation=json.loads(raw);source=HERE/'source-manifest.json';payload=source.read_bytes()
    assert len(payload)<=2**20 and hashlib.sha256(payload).hexdigest()==invocation['source_manifest_sha256']
    manifest=json.loads(payload)
    assert set(manifest)=={'policy','files'} and manifest['policy']=='reviewed-Ruff-screen-source-v1'
    assert set(manifest['files'])=={'screen.py','common.py','rustc_capture.py','plan.json','registry-original.rs','registry-edited.rs'}
    for name,row in manifest['files'].items():
        p=HERE/name;assert p.resolve(strict=True)==p and p.is_file()
        b=p.read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
    sys.path.insert(0,str(HERE));import common
    assert common.file(route)['sha256']==sha
    return common,invocation,manifest


def relative(name):
    p=Path(name);c.require(not p.is_absolute() and name==str(p) and '..' not in p.parts,'safe relative source name');return p


def source_tree(plan,copy):
    inventory=c.read(plan['source_inventory']['path'],plan['source_inventory']['sha256'])
    rows=inventory;c.require(len(rows)==11119 and sum(x['bytes'] for x in rows.values())==89102713,'exact acquired source scope')
    base=Path(plan['source_root']);dest=c.WORK/'source';observed={};copied={}
    if copy:dest.mkdir()
    for name,row in sorted(rows.items()):
        p=base/relative(name);q=dest/name
        if row['kind']=='file':
            r=c.file(p);c.require(r['bytes']==row['bytes'] and r['sha256']==row['sha256'],'original Ruff source changed')
            c.require(row['mode'] in ['100644','100755'],'original logical Git mode retained in acquired inventory')
            observed[str(p)]=r
            if copy:
                q.parent.mkdir(parents=True,exist_ok=True)
                with q.open('xb') as f:f.write(p.read_bytes())
                os.chmod(q,stat.S_IMODE(r['identity']['mode']))
                c.require(c.file(p)==r,'source changed during copy')
            s=c.file(q);c.require(s['sha256']==row['sha256'] and s['bytes']==row['bytes'],'owned source copy differs');copied[str(q)]=s
        else:
            c.require(row['kind']=='symlink' and os.path.islink(p),'declared source symlink only')
            identity=c.stamp(p);target=os.readlink(p)
            c.require(target==row['target'] and c.digest(target.encode())==row['sha256'] and p.resolve(strict=True).is_relative_to(base),'bounded source alias')
            observed[str(p)]=dict(kind='symlink',identity=identity,target=target)
            if copy:q.parent.mkdir(parents=True,exist_ok=True);q.symlink_to(target)
            c.require(os.path.islink(q) and os.readlink(q)==target and q.resolve(strict=True).is_relative_to(dest),'owned source alias')
            copied[str(q)]=dict(kind='symlink',identity=c.stamp(q),target=target)
            c.require(c.stamp(p)==identity,'source alias changed')
    # Preserve the old marker as historical provenance, without importing its ownership authority.
    ref=plan['historical_source_marker'];p=Path(ref['path']);q=dest/p.name;r=c.file(p)
    c.require(r['sha256']==ref['sha256'],'historical source provenance marker')
    observed[str(p)]=r
    if copy:
        with q.open('xb') as f:f.write(p.read_bytes())
    copied[str(q)]=c.file(q);c.require(copied[str(q)]['sha256']==r['sha256'],'marker copy')
    found=set()
    for root,dirs,files in os.walk(dest,followlinks=False):
        for name in dirs+files:
            p=Path(root)/name
            if not p.is_dir() or p.is_symlink():found.add(str(p))
    c.require(found==set(copied),'complete fresh source membership; no .git or foreign files')
    return observed,copied


def table_guard(rows,full=False):
    for name,row in rows.items():
        c.require(c.stamp(name)==row['identity'],'guarded input changed')
        if row.get('kind')=='symlink':c.require(os.readlink(name)==row['target'],'source symlink changed')
        elif full:c.require(c.file(name)==row,'guarded input bytes changed')


def target_tree(root):
    result={};n=0
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            p=Path(directory)/name;s=p.lstat();n+=1;c.require(n<=30000,'finite fresh Cargo cache')
            if stat.S_ISDIR(s.st_mode):continue
            c.require(stat.S_ISREG(s.st_mode),'Cargo target contains undeclared alias or special file')
            result[str(p)]=c.file(p)
    return result


def config_guard(plan):
    # Cargo consults the actual working directory ancestors and CARGO_HOME.
    roots=[c.WORK/'source',*(c.WORK/'source').parents];paths=[]
    for root in roots:paths.extend([root/'.cargo/config',root/'.cargo/config.toml'])
    paths.extend([Path(plan['environment']['CARGO_HOME'])/'config',Path(plan['environment']['CARGO_HOME'])/'config.toml'])
    result={}
    for p in dict.fromkeys(paths):
        if not os.path.lexists(p):result[str(p)]=None;continue
        row=c.file(p);c.require(row['bytes']<=2**20,'bounded Cargo config');d=tomllib.loads(p.read_text())
        c.require('include' not in d and not any(d.get(k) for k in ['env','source','paths','patch','profile','build']),'no hidden Cargo routing/env/source/profile/build override')
        c.require(not any(k in d.get('build',{}) for k in ['rustc','rustc-wrapper','rustc-workspace-wrapper','rustflags','target','incremental']),'no hidden compiler selection')
        for target,options in d.get('target',{}).items():
            c.require(target=='cfg(all(target_env="msvc", target_os = "windows"))' and options=={'rustflags':['-C','target-feature=+crt-static']},'only original inactive Windows flags allowed')
        result[str(p)]=row
    return result


def dep_paths(path,cwd):
    """Read the first make target rule, retaining escaped spaces and literal # paths."""
    row=c.file(path);c.require(row['bytes']<=8*2**20,'dep-info size');raw=Path(path).read_text();c.require(c.file(path)==row,'dep-info changed')
    lines=raw.replace('\\\n','').splitlines();line=next((x for x in lines if x and not x.startswith('#')),None)
    c.require(line is not None and ': ' in line,'actual make dependency rule')
    rhs=line.split(': ',1)[1];words=[];word='';escaped=False
    for ch in rhs:
        if escaped:word+=ch;escaped=False
        elif ch=='\\':escaped=True
        elif ch.isspace():
            if word:words.append(word);word=''
        else:word+=ch
    c.require(not escaped,'truncated dep-info escape')
    if word:words.append(word)
    paths={os.path.normpath(str(Path(cwd)/w)) if not Path(w).is_absolute() else os.path.normpath(w) for w in words}
    return row,raw,paths


def dependency_proof(route,overlay,arm):
    args=route['forwarded_arguments'];cwd=Path(route['cwd'])
    path=c.cargo_depinfo_path(args,cwd);row,text,paths=dep_paths(path,cwd)
    other='candidate' if arm=='stock' else 'stock'
    c.require('/.rustup/toolchains/' not in text and str(Path(overlay['overlay_work'])/other/'sysroot') not in text,'foreign Rust libraries in dep-info')
    c.require('libproc_macro-452900db9815e688.' not in text and 'librustc_literal_escaper-f4f532eb55f87a02.' not in text,'old client/literal fallback')
    selected={}
    if 'proc-macro' in c.crate_types(args):
        for name,value in overlay['overlay_data']['overlays-after.json']['entries'].items():
            if value['kind']=='file' and Path(name).is_relative_to(Path(overlay['overlay_work'])/arm/'sysroot'):
                c.require(name in paths,'host macro did not link each arm-owned client/literal flavor')
                selected[name]=c.file(name);c.require(selected[name]=={k:value[k] for k in ['bytes','sha256','identity']},'host macro client changed')
        c.require(len(selected)==4,'four selected host macro artifacts')
    return dict(depinfo=dict(path=str(path),**row),paths=sorted(paths),selected=selected)


def capture_closure(arm):
    """Inspect raw native records even if a failed wrapper never wrote route.json."""
    base=c.OUT/'capture'/arm;rows=[]
    for directory in sorted(base.iterdir()):
        c.require(directory.is_dir() and not directory.is_symlink(),'owned capture directory')
        record=directory/'record.json'
        if not record.exists():rows.append(dict(path=str(record),native_closure_known=False,may_be_live=True));continue
        value=c.read(record)
        known=value['status']=='closed' and value.get('may_be_live') is False and type(value.get('returncode')) is int
        # A recorded Popen failure has no native child; it is still failed setup.
        absent=value['status']=='spawn-failed' and value.get('may_be_live') is False and 'pid' not in value
        rows.append(dict(path=str(record),sha256=c.file(record)['sha256'],native_closure_known=known or absent,
            may_be_live=not (known or absent),status=value['status'],pid=value.get('pid'),returncode=value.get('returncode')))
    c.require(len(rows)<=1024,'finite capture closure census')
    c.write(c.OUT/('native-closure-'+arm+'.json'),rows)
    return rows

def wrapper_attempts(arm,context_path):
    rows=[]
    for path in sorted((c.OUT/'wrapper-attempts').iterdir()):
        c.require(path.suffix=='.json' and path.is_file() and not path.is_symlink(),'complete wrapper attempt publication')
        record=c.read(path)
        c.require(record['status']=='returned-native-exit','wrapper refusal cannot become a swallowed capability=false result')
        if record['received_environment'].get('ARENA_SCREEN_CONTEXT')==str(context_path):
            call=c.OUT/'capture'/arm/record['id'];route=c.read(call/'route.json')
            c.require(route['attempt']==str(path) and route['wrapper_pid']==record['wrapper_pid'],'same recorded wrapper and native call')
            rows.append(dict(path=str(path),**c.file(path)))
    c.require(0<len(rows)<=1024,'every actual wrapper invocation is retained')
    return rows


def cargo_setup(plan,invocation,arm,fd,manifest):
    target=c.WORK/'target'/arm;target.mkdir(parents=True)
    temporary=c.WORK/'tmp'/arm;temporary.mkdir(parents=True)
    capture=c.OUT/'capture'/arm;capture.mkdir(parents=True)
    context=dict(arm=arm,compiler=plan['compiler'],compiler_row=c.file(plan['compiler']),
        sysroot=str(Path(plan['overlay_work'])/arm/'sysroot'),common_sha256=manifest['files']['common.py']['sha256'],
        wrapper_sha256=manifest['files']['rustc_capture.py']['sha256'],probe_sources=plan['probe_sources'],absolute_deadline_monotonic=DEADLINE)
    cp=c.WORK/'contexts'/(arm+'.json');c.write(cp,context)
    env=dict(plan['environment'],RUSTC=str(HERE/'rustc_capture.py'),RUSTC_WRAPPER='',RUSTC_WORKSPACE_WRAPPER='',
        TMPDIR=str(temporary),ARENA_SCREEN_CONTEXT=str(cp),ARENA_SCREEN_CONTEXT_SHA=c.file(cp)['sha256'],ARENA_SCREEN_LOCK_FD=str(fd))
    args=[plan['cargo'],*[str(target) if v=='<fresh-arm-target>' else v for v in plan['cargo_arguments']]]
    c.overlay_guard(invocation,False)
    try:record=c.run(args,c.WORK/'source',env,c.OUT/('cargo-'+arm),fd=fd,seconds=900,cpu=900,until=DEADLINE)
    except BaseException:
        # Cargo may be live or may have closed after a wrapper failed. Either
        # way retain all visible native state, then abort without restoration.
        capture_closure(arm);raise
    closure=capture_closure(arm)
    c.require(all(x['native_closure_known'] and not x['may_be_live'] for x in closure),'native child closure unknown; no restoration or continuation')
    attempts=wrapper_attempts(arm,cp);c.require(len(attempts)==len(closure),'no unrecorded swallowed wrapper attempts')
    c.require(record['returncode']==0,'Cargo setup failed; no screen')
    routes=[];selected=[];macros=[];inputs={};probes=[]
    for directory in sorted(capture.iterdir()):
        route=c.read(directory/'route.json');child=c.read(directory/'record.json',route['record']['sha256'])
        c.require(child['status']=='closed' and not child['may_be_live'],'all Cargo rustc calls close')
        classification=route['classification'];c.require(child['returncode'] in classification.get('expected_exit_set',[0]),'actual crate/query/probe exit policy')
        c.require(child['parent_pid']==route['wrapper_pid'] and child['command']==route['forwarded_arguments'] and child['environment']==route['forwarded_environment'],'actual wrapper/compiler association')
        c.require(c.option(child['command'],'--sysroot')==context['sysroot'],'every actual host/probe call uses arm sysroot')
        if route['is_compile']:
            proof=dependency_proof(route,invocation,arm);route['dependency_proof']=proof
            c.write(directory/'dependency-proof.json',proof)
            for name in proof['paths']:
                p=Path(name)
                # SDK and rust-src paths may be aliases; bind resolved bytes plus exact declared route.
                q=p.resolve(strict=True);r=c.file(q);r=dict(r,declared_path=name,resolved=str(q))
                if name in inputs:c.require(inputs[name]==r,'dependency changed during setup')
                inputs[name]=r
            if proof['selected']:macros.append(dict(crate=c.option(child['command'],'--crate-name'),route=str(directory/'route.json'),proof=proof))
            if c.option(child['command'],'--crate-name')=='ruff_linter' and '--test' in child['command']:selected.append(route)
        elif classification['kind'].endswith('-probe'):
            source_sha=child['stdin']['sha256'] if classification['probe_source']=='captured stdin' else classification['source_row']['sha256']
            probes.append(dict(kind=classification['kind'],cwd=route['cwd'],source_sha256=source_sha,returncode=child['returncode'],
                out_dir=route['forwarded_environment']['OUT_DIR'],route=str(directory/'route.json'),record=str(directory/'record.json')))
        routes.append(route)
    c.require(0<len(routes)<=1024 and len(selected)==1 and macros,'fresh setup must actually build macro dylibs and one real library-test frontend')
    top=selected[0];c.require(c.option(top['forwarded_arguments'],'--emit')=='dep-info,metadata','genuine test metadata compile')
    source_args=[x for x in top['forwarded_arguments'] if x.endswith('.rs')]
    c.require(len(source_args)==1 and (Path(top['cwd'])/source_args[0]).resolve()==c.WORK/'source/crates/ruff_linter/src/lib.rs','exact top-level real Ruff source')
    c.require(top['forwarded_environment'].get('CARGO_INCREMENTAL')=='0','nonincremental preparation')
    # Raw Cargo events prove the selected top-level target, independently of the wrapper spelling.
    events=[json.loads(x) for x in (c.OUT/('cargo-'+arm)/'stdout').read_text().splitlines() if x.strip()]
    c.require(events and events[-1]=={'reason':'build-finished','success':True},'actual Cargo completion')
    c.require(any(x.get('reason')=='compiler-artifact' and x['target']['name']=='ruff_linter' and x['profile']['test'] is True for x in events),'Cargo test-target event')
    result=dict(record=record,top=top,macros=macros,routes=routes,inputs=inputs,probes=probes,compiler_calls=len(routes))
    c.write(c.OUT/('setup-'+arm+'.json'),dict(record=record,top=top,macros=macros,probes=probes,compiler_calls=len(routes),attempts=attempts,
        route_records=[dict(path=str(Path(r['call_directory'])/'route.json'),**c.file(Path(r['call_directory'])/'route.json')) for r in routes]))
    return result


def normalize(value):
    text=json.dumps(value,sort_keys=True)
    for arm in ['stock','candidate']:
        text=text.replace(str(c.WORK/'target'/arm),'<target>').replace(str(c.WORK/'tmp'/arm),'<tmp>')
        text=text.replace(str(Path(plan['overlay_work'])/arm/'sysroot'),'<sysroot>')
    return text


def setup_parity(setups):
    # Compare actual vectors as a multiset, allowing Cargo scheduling order only.
    def rows(setup):
        result=[]
        for route in setup['routes']:
            if not route['is_compile']:continue
            result.append(normalize(route['forwarded_arguments']))
        return sorted(result)
    left,right=rows(setups['stock']),rows(setups['candidate'])
    c.require(left==right,'setup flags/dependency identities differ beyond arm routes')
    c.require(normalize(setups['stock']['top']['forwarded_arguments'])==normalize(setups['candidate']['top']['forwarded_arguments']),'matched actual top-level profile/cfg')
    # The stale Cargo jobserver descriptors are transport, recorded verbatim and
    # replaced explicitly with owned jobs=1 pipes for replay; no other map edit.
    normalized=[]
    for arm in ['stock','candidate']:
        env,_=replay_environment(setups[arm]['top']['forwarded_environment'],1000001,1000002)
        normalized.append(normalize(env))
    c.require(normalized[0]==normalized[1],'captured top-level environments differ beyond recorded arm routes/jobserver transport')
    def probe_values(setup):
        return sorted(normalize({k:x[k] for k in ['kind','cwd','source_sha256','returncode','out_dir']}) for x in setup['probes'])
    c.require(probe_values(setups['stock'])==probe_values(setups['candidate']),'actual build-script probe sources and outcomes differ')


def inputs_guard(rows,full=False):
    for name,row in rows.items():
        p=Path(name);c.require(str(p.resolve(strict=True))==row['resolved'] and c.stamp(row['resolved'])==row['identity'],'actual compiler dependency changed')
        if full:c.require(c.file(row['resolved'])=={k:row[k] for k in ['bytes','sha256','identity']},'actual registry/generated/compiler dependency bytes changed')


def retain_input_table(label,rows):
    """Fixed-size evidence parts; all actual rows retained before any timing."""
    directory=c.OUT/label;directory.mkdir();names=sorted(rows);parts=[]
    for start in range(0,len(names),1000):
        subset={name:rows[name] for name in names[start:start+1000]};path=directory/f'part-{start//1000:03d}.json'
        c.write(path,subset);parts.append(dict(path=str(path),rows=len(subset),**c.file(path)))
    c.require(sum(p['rows'] for p in parts)==len(rows),'complete retained input table')
    index=dict(rows=len(rows),canonical_sha256=c.digest(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()),parts=parts)
    c.write(directory/'index.json',index);return dict(path=str(directory/'index.json'),**c.file(directory/'index.json'))


def edited_state(plan,copied,state):
    name=str(c.WORK/'source'/plan['source_edit']['relative']);row=copied[name]
    c.require(c.file(name)==row,'only owned expected source may be edited')
    desired=(HERE/('registry-'+state+'.rs')).read_bytes();ref=plan['source_edit'][state]
    c.require(c.digest(desired)==ref['sha256'],'exact declared edit/restoration')
    marker=plan['source_edit']['test_marker'].encode();c.require(c.digest(desired.split(marker,1)[1])==plan['source_edit']['tests_sha256'],'test bodies unchanged')
    tmp=Path(name+'.arena-screen-new');c.require(not os.path.lexists(tmp),'fresh edit staging')
    with tmp.open('xb') as f:f.write(desired);f.flush();os.fsync(f.fileno())
    os.chmod(tmp,stat.S_IMODE(row['identity']['mode']));os.replace(tmp,name)
    copied[name]=c.file(name);c.require(copied[name]['sha256']==ref['sha256'],'actual source state')
    return dict(path=name,state=state,at=time.time(),row=copied[name])


def replay_environment(original,read_fd,write_fd):
    result=dict(original);substitutions={}
    pair,present=c.jobserver_pair(original)
    c.require(pair is not None and 'CARGO_MAKEFLAGS' in present,'one coherent captured Cargo jobserver transport')
    for name in ['CARGO_MAKEFLAGS','MAKEFLAGS','MFLAGS']:
        if name not in original:continue
        value=original[name];matches=list(re.finditer(r'--jobserver-(auth|fds)=([0-9]+),([0-9]+)',value))
        kinds=[m.group(1) for m in matches];pairs={m.group(2,3) for m in matches}
        c.require(len(matches)<=2 and len(kinds)==len(set(kinds)) and len(pairs)<=1 and
            value.count('--jobserver-')==len(matches),'unrecognized Cargo jobserver transport')
        if matches:
            result[name]=re.sub(r'--jobserver-(auth|fds)=([0-9]+),([0-9]+)',lambda m:'--jobserver-'+m.group(1)+'='+str(read_fd)+','+str(write_fd),value)
            substitutions[name]=dict(before=value,after=result[name])
    c.require('CARGO_MAKEFLAGS' in substitutions,'captured jobs=1 jobserver expected')
    return result,substitutions


def replay(plan,invocation,setup,arm,label,fd,copied,original,dependencies,timed):
    c.exact_table(SOURCE_CURRENT,False);table_guard(original);table_guard(copied);inputs_guard(dependencies);c.overlay_guard(invocation)
    c.budget();c.disk();c.require(time.monotonic()<DEADLINE,'finite overall screen deadline')
    output=c.WORK/'replays'/label;output.mkdir(parents=True)
    argv=c.change_option(setup['top']['forwarded_arguments'],'--out-dir',str(output))
    read_fd,write_fd=os.pipe();os.set_inheritable(read_fd,True);os.set_inheritable(write_fd,True)
    environment,substitutions=replay_environment(setup['top']['forwarded_environment'],read_fd,write_fd)
    transport=c.jobserver_observation(environment)
    try:
        record=c.run(argv,setup['top']['cwd'],environment,c.OUT/'replays'/label,fd=fd,seconds=180,cpu=180,until=DEADLINE)
    finally:os.close(read_fd);os.close(write_fd)
    c.require(record['returncode']==0,'edited/restored actual frontend failed')
    route=dict(setup['top'],forwarded_arguments=argv,forwarded_environment=environment)
    proof=dependency_proof(route,invocation,arm)
    c.require(c.WORK.as_posix()+'/source/'+plan['source_edit']['relative'] in proof['paths'],'replay dependency proof includes actually edited production file')
    # Rustc emits success artifact events alongside JSON diagnostics; keep both raw.
    diagnostics=[]
    for raw in (c.OUT/'replays'/label/'stderr').read_text().splitlines():
        item=json.loads(raw);kind=item.get('$message_type')
        c.require(kind in ['diagnostic','artifact'],'unexpected rustc message kind')
        if kind=='diagnostic':
            c.require(item.get('level') not in ['error','failure-note'],'unexpected compiler failure diagnostic')
            diagnostics.append(item)
    c.require(record['stdout']['bytes']==0,'unexpected compiler stdout')
    table_guard(original);table_guard(copied);inputs_guard(dependencies);c.overlay_guard(invocation)
    verified=dict(arm=arm,label=label,timed=timed,record=dict(path=str(c.OUT/'replays'/label/'record.json'),**c.file(c.OUT/'replays'/label/'record.json')),
        wall_seconds=record['elapsed_seconds'],cpu_user_seconds=record['cpu_user_seconds'],cpu_system_seconds=record['cpu_system_seconds'],
        jobserver_substitution=substitutions,jobserver_transport=transport,dependency_proof=proof,diagnostics=diagnostics)
    path=c.OUT/'replays'/label/'verification.json';c.write(path,verified)
    return dict(arm=arm,label=label,timed=timed,verification=dict(path=str(path),**c.file(path)),
        wall_seconds=record['elapsed_seconds'],cpu_user_seconds=record['cpu_user_seconds'],cpu_system_seconds=record['cpu_system_seconds'],
        normalized_diagnostics_sha256=c.digest(normalize(diagnostics).encode()))


def prerequisites(plan,invocation):
    c.require(invocation['policy']=='reviewed-passed-overlay-for-Ruff-screen-v1' and invocation['actual_success'] is True,'actual overlay qualification required')
    data={name:c.read(ref['path'],ref['sha256']) for name,ref in invocation['overlay_proofs'].items()}
    c.require(set(data)=={'result.json','execution.json','overlays-after.json','runtime-after.json'},'finite overlay proof names')
    for name,ref in invocation['overlay_proofs'].items():c.require(ref['path']==str(Path(plan['overlay_results'])/name),'exact prior overlay proof route')
    result=data['result.json'];execution=data['execution.json'];proof=invocation['overlay_independent_readback'];audit=c.read(proof['path'],proof['sha256'])
    c.require(result['status']=='passed' and result['default_discovery_qualified'] is True and result['execution_sha256']==invocation['overlay_proofs']['execution.json']['sha256'],'closed overlay success')
    c.require(execution['status']=='passed' and execution['children']==20 and execution['canonical_released_at']>=execution['finished_at'],'closed overlay ownership')
    c.require(audit['status']=='verified' and audit['command_count']==20 and audit['stable_caller_pairs']==9 and audit['default_discovery_qualified'] is True,'independent actual semantic proof')
    c.require(audit['result']==invocation['overlay_proofs']['result.json'] and audit['execution']==invocation['overlay_proofs']['execution.json'],'independent same actual closure')
    c.require(proof==plan['overlay_independent_readback'] and invocation['overlay_proofs']['result.json']['sha256']==plan['overlay_result_sha256'],'exact reviewed actual prerequisite')
    for previous in [plan['earlier_failed_predecessor'],plan['failed_predecessor']]:
        failure=c.read(previous['independent_readback']['path'],previous['independent_readback']['sha256'])
        failed=c.read(previous['execution']['path'],previous['execution']['sha256'])
        c.require(failure['status']==previous['readback_status'] and failure['crate_compilations']==previous['crate_compilations'] and failure['timed_calls']==failure['source_edits']==0,'actual failed predecessor scope')
        c.require(failure['execution']['sha256']==previous['execution']['sha256'] and failed['status']=='failed' and failed['samples']==failed['edits']==[],'same preserved failed execution')
    invocation=dict(invocation,overlay_data=data,overlay_work=plan['overlay_work'],runtime_root=str(Path(plan['compiler']).parent.parent))
    c.require(c.file(plan['cargo'])==invocation['cargo'],'exact installed Cargo bytes and current identity')
    c.overlay_guard(invocation,True);return invocation


def main(args):
    global c,plan,DEADLINE,SOURCE_CURRENT
    c,invocation,manifest=bootstrap(args.invocation_sha256);plan=c.read(HERE/'plan.json',manifest['files']['plan.json']['sha256'])
    c.require(HERE==c.SOURCE and Path.cwd()==c.ROOT,'exact source and launch cwd')
    c.require(not os.path.lexists(c.WORK) and not os.path.lexists(c.OUT),'fresh owned work/results')
    c.require(plan['actual_result'] is None and len(plan['schedule'])==36,'fixed unrun screen')
    SOURCE_CURRENT={str(HERE/name):c.file(HERE/name) for name in [*manifest['files'],'source-manifest.json']}
    for ref in [*plan['probe_source_references'],*plan['probe_sources'].values()]:
        row=c.file(ref['path']);c.require(row['sha256']==ref['sha256'] and row['bytes']==ref['bytes'],'source-read probe implementation unchanged')
        SOURCE_CURRENT[ref['path']]=row
    c.disk(True);c.OUT.mkdir();c.WORK.mkdir();(c.WORK/'contexts').mkdir();(c.OUT/'wrapper-attempts').mkdir()
    c.write(c.OUT/'ownership.json',dict(owner='/root',purpose=plan['policy'],source_copy=c.WORK.as_posix()+'/source',historical_marker_is_not_current_ownership_authority=True))
    summary=dict(status='waiting',parent_pid=os.getpid(),started_at=time.time(),invocation_sha256=args.invocation_sha256,plan_sha256=manifest['files']['plan.json']['sha256'],samples=[],warmups=[],restorations=[],edits=[],signals=[],retries=0,benchmark_scope='native nonincremental frontend screening only',application_tests_run=False,full_workflow_qualified=False)
    c.write(c.OUT/'execution.json',summary);lock=None;DEADLINE=time.monotonic()+5400
    try:
        c.require(c.LOCK.resolve(strict=True)==c.LOCK and stat.S_ISREG(c.LOCK.lstat().st_mode),'ordinary canonical lock')
        lock=c.LOCK.open('r+');until=time.monotonic()+600
        while True:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:c.require(time.monotonic()<until,'canonical admission timed out');time.sleep(.25)
        fd=lock.fileno();os.set_inheritable(fd,True);c.inherited_lock(fd);c.disk(True)
        summary.update(status='running',admitted_at=time.time());c.write(c.OUT/'execution.json',summary)
        invocation=prerequisites(plan,invocation)
        original,copied=source_tree(plan,True)
        retained_tables=dict(original_source=retain_input_table('original-source-current',original),copied_source=retain_input_table('copied-source-initial',copied))
        configuration=config_guard(plan);c.write(c.OUT/'cargo-configurations.json',configuration)
        setups={}
        for arm in plan['setup_order']:setups[arm]=cargo_setup(plan,invocation,arm,fd,manifest);table_guard(original);table_guard(copied)
        setup_parity(setups)
        cache={arm:target_tree(c.WORK/'target'/arm) for arm in ['stock','candidate']}
        for arm,rows in cache.items():retained_tables['cache_'+arm]=retain_input_table('cache-'+arm+'-before',rows)
        # Source rows include registry.rs; its two exact states are separately guarded.
        mutable=str(c.WORK/'source'/plan['source_edit']['relative']);dependencies={}
        for setup in setups.values():
            for name,row in setup['inputs'].items():
                if name==mutable:continue
                if name in dependencies:c.require(dependencies[name]==row,'same declared dependency changed across arms')
                dependencies[name]=row
        retained_tables['actual_compiler_inputs']=retain_input_table('actual-compiler-inputs',dependencies)
        summary['retained_input_tables']=retained_tables
        c.write(c.OUT/'execution.json',summary);c.budget()
        for block in range(6):
            samples=[s for s in plan['schedule'] if s['block']==block];first=[s['arm'] for s in samples if s['kind']=='ab'][:2]
            summary['edits'].append(edited_state(plan,copied,'edited'))
            for arm in first:summary['warmups'].append(replay(plan,invocation,setups[arm],arm,f'b{block}-warm-{arm}',fd,copied,original,dependencies,False))
            for sample in samples:
                arm=sample['arm'];value=replay(plan,invocation,setups[arm],arm,f"sample-{sample['index']:02d}-{arm}",fd,copied,original,dependencies,True)
                summary['samples'].append(dict(sample,**value));c.write(c.OUT/'execution.json',summary)
            summary['edits'].append(edited_state(plan,copied,'original'))
            for arm in reversed(first):summary['restorations'].append(replay(plan,invocation,setups[arm],arm,f'b{block}-restored-{arm}',fd,copied,original,dependencies,False))
            for arm,rows in cache.items():c.exact_table(rows,False)
        c.require(len(summary['samples'])==36 and len(summary['warmups'])==12 and len(summary['restorations'])==12,'exact finite sample/setup/restoration counts')
        pairs=[]
        for index in range(18):
            pair=[x for x in summary['samples'] if x['pair']==index];c.require(len(pair)==2 and [x['position'] for x in pair]==[0,1],'fixed pair order')
            c.require(pair[0]['normalized_diagnostics_sha256']==pair[1]['normalized_diagnostics_sha256'],'paired diagnostics changed')
            if pair[0]['kind']=='aa':ratio=pair[1]['wall_seconds']/pair[0]['wall_seconds']
            else:ratio=next(x['wall_seconds'] for x in pair if x['arm']=='candidate')/next(x['wall_seconds'] for x in pair if x['arm']=='stock')
            pairs.append(dict(pair=index,kind=pair[0]['kind'],ratio=ratio))
        ab=[x['ratio'] for x in pairs if x['kind']=='ab'];aa=[x['ratio'] for x in pairs if x['kind']=='aa']
        median=statistics.median(ab);noise=max(abs(x-1) for x in aa)
        decision='screen-gain-exceeds-AA-noise' if 1-median>noise else 'park-allocator-performance-path'
        for arm,rows in cache.items():c.require(target_tree(c.WORK/'target'/arm)==rows,'fresh cache membership/bytes changed during replay')
        table_guard(original,True);table_guard(copied,True);source_tree(plan,False);inputs_guard(dependencies,True)
        c.require(config_guard(plan)==configuration,'Cargo configuration changed');c.overlay_guard(invocation,True)
        c.require(c.file(plan['cargo'])==invocation['cargo'],'Cargo changed');c.exact_table(SOURCE_CURRENT,True)
        summary.update(status='passed',finished_at=time.time(),pairs=pairs,median_candidate_stock_ratio=median,max_absolute_AA_variation=noise,decision=decision,unchanged_retry_allowed=False,owned=c.budget(),free_bytes_after=c.disk())
    except BaseException as error:
        # No restoration here: a failed observer can leave an actual child holding the lock.
        summary.update(status='failed',error=repr(error),observation_finished_at=time.time(),failure_does_not_authorize_restoration=True)
        raise
    finally:
        if lock is not None:lock.close();summary['parent_lock_closed_at']=time.time()
        c.write(c.OUT/'execution.json',summary)
    c.write(c.OUT/'result.json',dict(status='passed',execution=c.file(c.OUT/'execution.json'),timed_calls=36,pairs=pairs,median_candidate_stock_ratio=median,max_absolute_AA_variation=noise,decision=decision,full_workflow_qualified=False,application_tests_run=False,sub_half_second_claim=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--invocation-sha256',required=True);main(p.parse_args())
