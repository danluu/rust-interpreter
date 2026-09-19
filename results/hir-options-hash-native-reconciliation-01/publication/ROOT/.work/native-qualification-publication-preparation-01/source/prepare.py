"""Read-only exact publication freeze; source proposal, not an archive launch."""
import ast
import json
import os
from pathlib import Path
import sys

import history
import retain as r


def main():
    r.require(Path.cwd()==r.A and sys.dont_write_bytecode and not sys.flags.optimize,'explicit publication owner/Python')
    r.require(all(not p.exists() and not p.is_symlink() for p in [r.WORK,r.OUT,r.SOURCE_BUNDLE,r.HERE/'inputs.json',r.HERE/'launch.json']),
        'fresh publication proposal required')
    r.require(r.sha(history.SCOPE)==history.SCOPE_SHA,'exact approved payload selection required')
    scope=r.read(history.SCOPE)
    r.require(scope['owner']==str(r.A) and scope['proposed_archive_bounds']==r.BOUNDS
        and scope['exact_file_count']==866 and scope['logical_bytes']==265977385
        and scope['physical_unique_bytes']==215262439,'reviewed bounded publication scope differs')
    files={};sources=set();routes={};directories={}
    def add(path,expected=None,archive=True):
        path=Path(path);before=r.stamp(path)
        row=dict(stamp=before,bytes=before[3],sha256=r.sha(path))
        r.check(path,row)
        if expected:
            r.require(row['bytes']==expected['size'] and row['sha256']==expected['sha256']
                and before==[expected['identity'][key] for key in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']],
                'scope file changed before freeze')
        r.require(str(path) not in files or files[str(path)]==row,'selected input changed')
        files[str(path)]=row
        if archive:sources.add(str(path))
        r.require(len(files)<r.BOUNDS['members'],'finite publication inputs')
        return path
    for name,row in scope['files'].items():add(name,row)
    for name,expected in scope['directories'].items():
        actual={str(p.relative_to(name)):'directory' if p.is_dir() else 'file' for p in Path(name).rglob('*')}
        r.require(actual==expected and not any(p.is_symlink() for p in Path(name).rglob('*')),'closed scope membership changed')
        directories[name]=dict(members=r.members(name),excluded_future_outputs=[])
    add(history.SCOPE)
    for path in sorted(r.HERE.iterdir()):
        add(path)
        if path.suffix=='.py':ast.parse(path.read_bytes(),filename=str(path))
    for path in [r.OWNED,r.A/'scripts/supervise_experiment.py']:add(path)
    python=Path(sys.executable).resolve(strict=True);add(python,archive=False)
    for name in ['/opt/homebrew/bin/python3','/bin/ps','/usr/sbin/lsof']:
        path=Path(name).resolve(strict=True);add(path,archive=False);routes[name]=str(path)
    prior=[]
    for item in scope['prior_archives']:
        path=Path(item['path']);before=r.stamp(path)
        r.require(path.resolve(strict=True)==path and before[3]<=192*r.MIB
            and r.sha(path)==item['sha256'] and r.stamp(path)==before,'prior retained B308 reference changed')
        prior.append(dict(item,stamp=before,bytes=before[3]))
    observed=history.validate_all()
    logical=sum(files[name]['bytes'] for name in sources)
    physical=sum(size for _,size in {(files[name]['sha256'],files[name]['bytes']) for name in sources})
    r.require(logical<r.BOUNDS['logical_bytes']-4*r.MIB and physical<r.BOUNDS['physical_bytes']-4*r.MIB,
        'bounded complete standalone archive required')
    environment=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',
        PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR='/tmp')
    freeze=dict(status='prepared-unrun',owner=str(r.A),files=files,routes=routes,directories=directories,
        python=str(python),environment=environment,archive_sources=sorted(sources),bounds=r.BOUNDS,history=observed,
        source_copies=scope['source_copies'],prior_archives=prior,
        absent_paths=[str(history.A/('.work/hir-options-hash-native-controls-'+n)/'native-controls.json') for n in ['01','02','03']],
        input_bytes=sum(row['bytes'] for row in files.values()),archive_logical_bytes_before_freeze=logical,
        archive_physical_bytes_before_freeze=physical,scope=dict(path=str(history.SCOPE),sha256=history.SCOPE_SHA),
        payload_exclusions=dict(executor_payload_references=scope['executor_payload_references'],
            live_provider_payloads_excluded=True,older_unqualified_stock_payloads_excluded=True,
            four_qualified_output_payloads=scope['qualified_output_payloads'],
            explanation=scope['excluded_live_payloads']),
        capacity=dict(entry_gib=9,stop_gib=9,floor_gib=8,reservation_bytes=r.BOUNDS['expanded_bytes']),
        canonical_lock='/Users/danluu/dev/rust-interp/.work/benchmark.lock',wait_seconds=600,workload_children=0)
    r.guard(freeze,history)
    def write(path,value):
        data=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
        r.require(len(data)<=2*r.MIB,'bounded publication proposal metadata')
        with path.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        r.require(path.read_bytes()==data,'proposal full readback differs')
    write(r.HERE/'inputs.json',freeze)
    launch=dict(status='prepared-unrun-awaiting-review',owner=str(r.A),environment=environment,
        command=[str(python),'-B',str(r.A/'scripts/supervise_experiment.py'),'--run-id','native-qualification-publication-supervisor-01',
            '--',str(python),'-B',str(r.HERE/'retain.py'),'--inputs-sha256',r.sha(r.HERE/'inputs.json')],
        inputs_sha256=r.sha(r.HERE/'inputs.json'),helper_sha256=r.sha(r.HERE/'retain.py'),expected_workload_children=0,
        bounds=r.BOUNDS,capacity=freeze['capacity'])
    write(r.HERE/'launch.json',launch)
    print(json.dumps(dict(status='prepared-unrun',launch_sha256=r.sha(r.HERE/'launch.json'),inputs_sha256=launch['inputs_sha256'],
        archive_members=len(sources)+1,logical_bytes=logical,physical_bytes=physical,source_copies=58)))


if __name__=='__main__':main()
