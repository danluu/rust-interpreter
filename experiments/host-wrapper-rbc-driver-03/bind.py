"""Bind saved qualified metadata and a future actual tool publication; no probes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    for name in ('sources-sha256','tool-key','publication-receipt-sha256','published-tools-sha256','publication-execution-sha256'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args();raw=(HERE/'sources.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=args.sources_sha256:raise RuntimeError('source selection differs')
    sources=json.loads(raw)['files']
    if not {str(Path(__file__).resolve()),str(HERE/'support.py')} <= set(sources):
        raise RuntimeError('caller/support authentication missing')
    for name,digest in sources.items():
        p=Path(name)
        if p.resolve(strict=True)!=p or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:
            raise RuntimeError('source changed before import: '+name)
    spec=importlib.util.spec_from_file_location('_rbc_bind_support',HERE/'support.py')
    s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
    s.require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==s.R,'fixed -B/R cwd')
    s.require(set(sources)=={str(p) for p in s.source_paths()},'exact source closure')
    s.require(all(s.valid_key(v) for v in vars(args).values()),'exact actual digests/key required')
    s.require(not (HERE/'binding.json').exists(),'fresh binding only')
    evidence=dict(s.KNOWN_SAVED_PINS)
    values={p:s.read(p,h) for p,h in evidence.items()}
    runtime=s.R/'.work/runtime-compilers'/s.RUNTIME_KEY
    std=s.R/'.work/std-mir'/s.STD_KEY
    ready=values[str(runtime/'ready.json')];standard=values[str(std/'ready.json')]
    s.require(ready['key']==s.RUNTIME_KEY and ready['status']=='installed'
        and standard['key']==s.STD_KEY and standard['identity']['compiler_key']==s.RUNTIME_KEY,'qualified runtime/std differs')
    pubwork=s.X/'.work/host-wrapper-exporter-publication-01'
    terminal=s.read(pubwork/'receipt.json',args.publication_receipt_sha256)
    result=s.read(pubwork/'published-tools.json',args.published_tools_sha256)
    s.require(terminal['phase']=='publication' and terminal['status']=='passed' and terminal['publication'] is True
        and terminal['tool_key']==args.tool_key and terminal['runtime_key']==s.RUNTIME_KEY
        and len(terminal['commands'])==4 and terminal['result']['sha256']==args.published_tools_sha256
        and terminal['result']['path']==str(pubwork/'published-tools.json'),'actual new publisher success required')
    parent_path=s.ROOT/'.work/host-wrapper-exporter-publication-execution-01/record.json'
    parent=s.read(parent_path,args.publication_execution_sha256)
    outer_path=s.X/'.work/experiments/host-wrapper-exporter-publication-supervisor-01/status.json'
    outer=s.read(outer_path,parent['outer_status_sha256'])
    s.require(parent['status']=='finished' and parent['returncode']==parent['controller_returncode']==0
        and parent['supervisor_may_be_live'] is False and parent['controller_may_be_live'] is False
        and outer['status']=='finished' and outer['returncode']==0
        and outer['supervisor_pid']==parent['pid']==terminal['parent_pid']
        and outer['supervisor_parent_pid']==parent['parent_pid'] and outer['child_pid']==terminal['pid'],
        'actual normal parent/outer/publication closure required')
    evidence[str(parent_path)]=args.publication_execution_sha256
    evidence[str(outer_path)]=parent['outer_status_sha256']
    s.require(parent['started_at']<=outer['started_at']<=terminal['started_at']
        <=terminal['finished_at']<=outer['finished_at']<=parent['finished_at'],
        'publication owner chronology differs')
    outer_plan=s.read(outer_path.parent/'plan.json',parent['outer_plan_sha256'])
    s.require(outer['plan_sha256']==parent['outer_plan_sha256'] and outer_plan['owner']==str(s.X)
        and outer_plan['command']==outer['command'] and parent['cwd']==outer['cwd']==str(s.X),
        'publication saved outer plan differs')
    for p,h in [(parent_path.parent/'stdout',parent['stdout_sha256']),
                (parent_path.parent/'stderr',parent['stderr_sha256']),
                (outer_path.parent/'plan.json',parent['outer_plan_sha256']),
                (outer_path.parent/'command.log',outer['log_sha256']),
                (HERE/'sources.json',args.sources_sha256)]:
        ref=s.file(p,h);evidence[str(p)]=ref['sha256']
    directory=s.R/'.work/interpreter-tools'/args.tool_key
    s.require(result['tool_key']==args.tool_key and result['directory']==str(directory)
        and result['composition']['host_codegen_policy']=='host-codegen-opt-v1'
        and result['host_codegen_application_qualified'] is False,'new policy publication differs')
    evidence[str(pubwork/'receipt.json')]=args.publication_receipt_sha256
    evidence[str(pubwork/'published-tools.json')]=args.published_tools_sha256
    previous=terminal['admitted_at']
    for index,saved in enumerate(terminal['commands']):
        p=pubwork/'commands'/f'{index:03d}'/'receipt.json';r=s.read(p,saved['sha256'])
        s.require(saved['path']==str(p) and r['status']=='finished' and r['returncode']==saved['returncode']==0
            and r['pid']==saved['pid'] and r['supervisor_pid']==terminal['pid']
            and previous<=r['started_at']<=r['finished_at']<=terminal['finished_at'],'publication child closure differs')
        previous=r['finished_at'];evidence[str(p)]=saved['sha256']
        for stream in ('stdout','stderr'):
            ref=s.file(p.parent/stream,r[stream+'_sha256']);evidence[ref['path']]=ref['sha256']
    installed={}
    for name in ('ready.json','compiler.json','capabilities.json'):
        p=directory/name;ref=s.file(p);evidence[str(p)]=ref['sha256'];installed[name]=s.read(p,ref['sha256'])
    s.require(installed['ready.json']==result['composition']['binaries']
        and installed['compiler.json']==result['composition'] and installed['capabilities.json']==result['capabilities'],'physical publication metadata differs')
    s.require(set(installed['ready.json'])=={'rust-interp-mir-export','rust-interp-rustc-wrapper','rust-interp-vm'},'exact three tool binaries')
    payloads={str(directory/n):h for n,h in installed['ready.json'].items()}
    def add(root,files):
        for name,digest in files.items():
            p=root/name
            s.require(not Path(name).is_absolute() and '..' not in Path(name).parts and s.valid_key(digest),'saved relative file inventory differs')
            old=payloads.setdefault(str(p),digest);s.require(old==digest,'conflicting saved file identity')
    add(runtime/'sysroot',ready['identity']['files'])
    add(std/'sysroot',standard['sysroot_files']);add(std/'library',standard['identity']['source_files']);add(std/'evidence',standard['evidence_files'])
    cargo=standard['identity']['cargo'];s.require(not cargo['libraries']['libraries'],'this pinned Cargo has only system-cache libraries')
    payloads[cargo['executable']]=cargo['sha256']
    for p in (std/'owner.json',runtime/'qualification.json',runtime/'admission.json'):
        ref=s.file(p);evidence[str(p)]=ref['sha256']
    launch=values[str(s.ROOT/'experiments/runtime-std-after-installation07-01/launch.json')]
    environment=dict(launch['environment']);environment['TMPDIR']=str(s.WORK/'tmp')+'/'
    s.require(not any(k.startswith(('LD_','DYLD_','CARGO_PROFILE_','RUST_INTERP_')) for k in environment),'qualified clean environment required')
    output=dict(policy='host-wrapper-rbc-binding-v1',sources=sources,evidence=evidence,payloads=payloads,
        source_manifest=dict(path=str(HERE/'sources.json'),sha256=args.sources_sha256),tool_key=args.tool_key,
        runtime_key=s.RUNTIME_KEY,std_key=s.STD_KEY,std_sysroot=str(std/'sysroot'),cargo=cargo['executable'],
        environment=environment,tests=list(s.TESTS),status='bound-unrun',benchmark=False,
        limits=dict(canonical_wait_seconds=600,suite_observed_seconds=600,child_observed_seconds=30,
                    owned_bytes=2**30,owned_entries=65536,entry_gib=16,stop_gib=9,floor_gib=8))
    s.write(HERE/'binding.json',output)
    print(json.dumps(dict(status='bound-unrun',binding=s.file(HERE/'binding.json'),sources=len(sources),
                         declared_payloads=len(payloads),payloads_read=0,processes=0),sort_keys=True))


if __name__=='__main__':main()
