#!/usr/bin/env python3
"""Run one reviewed metadata or ordinary two-tool Cargo build stage.

No std/compiler rebuild, guest execution, tool publication or application proof
is implied. Build is separately invoked only after closed metadata readback.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time

HERE = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-exporter-after-installation07-01')


def bootstrap(digest):
    path = HERE/'sources.json'; data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise RuntimeError('reviewed exporter source manifest differs')
    sources = json.loads(data)['files']
    if sources.get(str(Path(__file__).resolve())) != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise RuntimeError('stage source differs')
    for name, expected in sources.items():
        p = Path(name)
        if p.resolve(strict=True) != p or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            raise RuntimeError('authenticated source changed: '+name)
    path = HERE/'common.py'
    if str(path) not in sources:
        raise RuntimeError('common source is unauthenticated')
    spec = importlib.util.spec_from_file_location('_exporter07_common', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module, sources


def imported(name):
    spec = importlib.util.spec_from_file_location('_exporter07_'+name,HERE/(name+'.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def loaded_libraries(c, raw, pid, allowed, driver):
    rows = []
    for line in raw.decode().splitlines():
        match = re.fullmatch(r'dyld\[(\d+)\]: <([0-9A-Fa-f-]{36})> (/.+)',line)
        c.require(match is not None and int(match[1]) == pid,'unrecognized actual dyld observation')
        path = match[3]
        if not path.startswith(('/usr/lib/','/System/Library/')):
            c.require(path in allowed,'unadmitted loaded non-system library: '+path)
        rows.append(dict(path=path,uuid=match[2]))
    c.require(driver in {r['path'] for r in rows},'actual driver was not loaded')
    return rows


class Stage:
    def __init__(self,c,mods,sources,args):
        self.c,self.mods,self.sources,self.args = c,mods,sources,args
        self.inputs = c.read(c.PACKET/'inputs.json',args.inputs_sha256)
        self.plan = c.read(c.PACKET/'plan.json',self.inputs['plan']['sha256'])
        c.require(self.inputs['files']==sources and self.plan['status']=='prepared-unexecuted'
            and self.plan['owner']==str(c.X) and self.plan['runtime_key']==c.KEY
            and self.plan['source_root']==str(c.PREFIX),'current exporter packet differs')
        c.require(c.file(Path(sys.executable).resolve(strict=True))==self.inputs['python'], 'Python executor differs')
        self.building=args.phase=='build'
        self.work=c.X/'.work/hir-options-hash-exporter-build-01' if self.building else c.WORK
        c.require(not os.path.lexists(self.work),'fresh exporter stage required')
        c.require(not os.path.lexists(c.TARGET),'fresh Cargo target required')
        self.work.mkdir();(self.work/'tmp').mkdir()
        self.record=dict(status='waiting',phase=args.phase,pid=os.getpid(),parent_pid=os.getppid(),
            started_at=time.time(),command=list(sys.argv),cwd=os.getcwd(),commands=[],
            inputs_sha256=args.inputs_sha256,sources_sha256=args.sources_sha256,
            plan_sha256=self.inputs['plan']['sha256'],runtime_key=c.KEY,
            exporter_builds=0,compiler_builds=0,VM_builds=0,guest_executions=0,
            application_qualified=False,performance_measurement=False,signals=0,retries=0)
        self.cache={};self.closed=[];self.save()

    def save(self):
        self.mods.owned.write(self.work/'receipt.json',self.record)

    def guard(self,full=False):
        self.c.file(self.c.PACKET/'inputs.json',self.args.inputs_sha256)
        self.c.file(self.c.PACKET/'plan.json',self.inputs['plan']['sha256'])
        self.c.guard(self.plan,self.mods,full=full,allow_target=self.building)

    def command(self,row):
        c=self.c;self.guard();self.mods.owned.disk(c.X,9)
        argv=row['command'];path=Path(argv[0]).resolve(strict=True)
        expected=self.plan['files'].get(str(path))
        if expected is None:
            c.require(self.building and path.parent==c.TARGET/'release','unadmitted command executor')
            expected=self.binaries[path.name]
        c.require(c.file(path)==expected,'command executor changed')
        out=self.work/'commands'/f'{len(self.record["commands"]):03d}'
        try:
            result=self.mods.owned.run(argv,cwd=row['cwd'],env=row['environment'],out=out,
                capacity_root=c.X,expected=tuple(row['expected']))
        finally:
            if (out/'receipt.json').exists():
                receipt=c.read(out/'receipt.json')
                self.record['commands'].append(dict(label=row['label'],path=str(out/'receipt.json'),
                    sha256=c.file(out/'receipt.json')['sha256'],pid=receipt.get('pid'),returncode=receipt.get('returncode')))
                self.save()
        result=c.read(out/'receipt.json')
        c.require(result['status']=='finished' and result['returncode'] in row['expected']
            and result['command']==argv and result['cwd']==row['cwd'] and result['environment']==row['environment'],
            'owned actual command did not close as declared')
        for stream in ('stdout','stderr'):c.file(out/stream,result[stream+'_sha256'])
        stdout,stderr=(out/'stdout').read_bytes(),(out/'stderr').read_bytes()
        if row.get('expected_stdout_sha256') is not None:
            c.require(not stderr and hashlib.sha256(stdout).hexdigest()==row['expected_stdout_sha256'],
                      'actual SDK query differs from selected verified output')
        self.guard()
        return dict(receipt=result,path=str(out/'receipt.json'),stdout=stdout,stderr=stderr)

    def closure(self,path):
        c=self.c
        def inspect(argv,*,text):
            c.require(text is True and argv[:3]==['/usr/bin/otool','-arch','arm64'],'unreviewed loader request')
            key=(str(Path(argv[-1]).resolve(strict=True)),argv[3])
            c.require(key in self.cache,'unrecorded loader input: '+str(key))
            outcome=self.cache[key]
            c.require(not outcome['stderr'],'loader diagnostics')
            return outcome['stdout'].decode()
        identity,state=self.mods.loaders.library_closure(Path(path),c.HOST,inspect=inspect)
        for row in identity['libraries']:
            c.require(self.plan['files'][row['resolved']]['sha256']==row['sha256'],'unadmitted loader dependency')
        return dict(identity=identity,state=state)

    def metadata(self):
        c=self.c;observed={}
        for row in self.plan['children']:
            result=self.command(row);observed[row['label']]=result
            if row['command'][:3]==['/usr/bin/otool','-arch','arm64']:
                self.cache[(str(Path(row['command'][-1]).resolve(strict=True)),row['command'][3])]=result
        closures={path:self.closure(path) for path in self.plan['loader_binaries']}
        roles={}
        for name in ('build','runtime'):
            binding=self.plan['binding'][name];path=binding['executable']['path']
            version=observed[name+'-version'];root=observed[name+'-sysroot']
            c.require(version['stdout'].decode()==binding['verbose_version'] and not root['stderr']
                and root['stdout'].decode()==binding['default_sysroot']+'\n','actual compiler role differs')
            allowed={path}|{r['resolved'] for r in closures[path]['identity']['libraries']}
            driver=[p for p in allowed if Path(p).name.startswith('librustc_driver-')]
            c.require(len(driver)==1,'ambiguous probed driver')
            roles[name]=dict(closure=closures[path],loaded=loaded_libraries(c,version['stderr'],
                version['receipt']['pid'],allowed,driver[0]),version_receipt=version['path'],sysroot_receipt=root['path'])
        cargo=observed['cargo-version'];version=cargo['stdout'].decode()
        c.require(not cargo['stderr'] and len([s for s in version.splitlines() if s.startswith('os: ')])==1
            and [s for s in version.splitlines() if not s.startswith('os: ')]
                ==[s for s in self.plan['historical_cargo_version'].splitlines() if not s.startswith('os: ')],
            'Cargo identity differs beyond selected OS line')
        metadata=observed['cargo-metadata'];c.require(not metadata['stderr'],'Cargo metadata stderr')
        expected=self.plan['historical_cargo_metadata']; original=c.read(expected['path'],expected['sha256'])
        dependencies=c.dependency_contract(json.loads(metadata['stdout']),original,c.PREFIX)
        c.write(self.work/'cargo-metadata.json',metadata['stdout'])
        serial_cache=[dict(path=p,flag=flag,receipt=v['path'],stdout_sha256=v['receipt']['stdout_sha256'])
                      for (p,flag),v in sorted(self.cache.items())]
        result=dict(status='metadata-passed-build-unexecuted',binding=self.plan['binding'],actual_roles=roles,
            closures=closures,dependencies=dependencies,loader_observations=serial_cache,
            plan_sha256=self.inputs['plan']['sha256'],actual_children=len(self.record['commands']),
            application_qualified=False,performance_measurement=False)
        self.guard(full=True)
        return c.write(self.work/'planned.json',result)

    def build(self):
        c=self.c
        c.require(self.args.metadata_receipt_sha256 is not None,'actual closed metadata pin required')
        receipt=c.read(c.WORK/'receipt.json',self.args.metadata_receipt_sha256)
        c.require(receipt['status']=='passed' and receipt['phase']=='metadata'
            and receipt['inputs_sha256']==self.args.inputs_sha256 and receipt['sources_sha256']==self.args.sources_sha256
            and len(receipt['commands'])==len(self.plan['children']),'complete actual metadata required')
        for saved,wanted in zip(receipt['commands'],self.plan['children'],strict=True):
            path=Path(saved['path']);actual=c.read(path,saved['sha256'])
            c.require(actual['status']=='finished' and actual['returncode']==0
                and actual['command']==wanted['command'] and actual['environment']==wanted['environment']
                and actual['cwd']==wanted['cwd'] and actual['supervisor_pid']==receipt['pid']
                and receipt['admitted_at']<=actual['started_at']<=actual['finished_at']<=receipt['finished_at'],
                'metadata command closure association differs')
            for stream in ('stdout','stderr'):c.file(path.parent/stream,actual[stream+'_sha256'])
        metadata=c.read(c.WORK/'planned.json',receipt['result']['sha256'])
        c.require(metadata['binding']==self.plan['binding'],'metadata role binding differs')
        for row in metadata['loader_observations']:
            path=Path(row['receipt']);raw=c.read(path)
            c.file(path.parent/'stdout',row['stdout_sha256'])
            self.cache[(row['path'],row['flag'])]=dict(stdout=(path.parent/'stdout').read_bytes(),stderr=b'')
        checks=imported('build_checks');parser=imported('cargo_output')
        future=self.plan['future_build']
        build=self.command(dict(label='cargo-build',command=future['command'],cwd=future['cwd'],
            environment=future['environment'],expected=[0]))
        checks.check_build_diagnostics(build['stderr'])
        parsed=parser.parse_cargo_output(build['stdout'],metadata['dependencies']['packages'])
        compiles=checks.cargo_compiles(build['stderr'],self.plan['binding'],c.PREFIX,set(self.plan['files']))
        names=['rust-interp-mir-export','rust-interp-rustc-wrapper']
        self.binaries={name:c.file(c.TARGET/'release'/name) for name in names}
        actual={r.get('executable') for r in parsed['messages'] if r.get('reason')=='compiler-artifact'
                and 'bin' in r.get('target',{}).get('kind',[]) and r.get('executable')}
        c.require(actual=={r['path'] for r in self.binaries.values()},'Cargo executable set differs')
        generated=[]
        for message in parsed['messages']:
            if message.get('reason')=='build-script-executed' and message.get('out_dir'):
                path=Path(message['out_dir'])/'compiler_roles.rs'
                if path.is_file():
                    c.require(path.is_relative_to(c.TARGET),'generated binding outside owned target')
                    generated.append(c.file(path))
        c.require(len(generated)==1,'exact generated role binding required')
        environment=self.plan['launch_environment']
        def command(label,argv,env=environment):
            return self.command(dict(label=label,command=argv,environment=env,cwd=str(c.X),expected=[0]))
        tool_closures={}
        for name in names:
            path=self.binaries[name]['path']
            for flag in ('-L','-l'):
                self.cache[(path,flag)]=command(name+flag,['/usr/bin/otool','-arch','arm64',flag,path])
            tool_closures[name]=self.closure(path)
        exporter=self.binaries[names[0]]['path'];wrapper=self.binaries[names[1]]['path']
        caps=command('exporter-capabilities',[exporter,'--rust-interp-capabilities'],environment|{'DYLD_PRINT_LIBRARIES':'1'})
        capabilities=json.loads(caps['stdout']);driver=self.plan['binding']['runtime_driver']['path']
        allowed={exporter}|{r['resolved'] for r in tool_closures[names[0]]['identity']['libraries']}
        loaded=loaded_libraries(c,caps['stderr'],caps['receipt']['pid'],allowed,driver)
        c.require(capabilities['schema_version']==1 and capabilities['bytecode_version']==5
            and capabilities['compiler_sysroot']==str(c.RUNTIME) and capabilities['compiler_roles']==self.plan['binding'],
            'built exporter capability/role binding differs')
        wrapper_result=command('wrapper-roles',[wrapper,'--rust-interp-compiler-roles'])
        c.require(not wrapper_result['stderr'],'wrapper role diagnostics')
        binary_map={name:row['sha256'] for name,row in self.binaries.items()}
        vm=self.plan['adopted_VM']['binary'];c.file(vm['path'],vm['sha256']);binary_map['rust-interp-vm']=vm['sha256']
        compiler=self.mods.runtime.load_runtime_compiler(c.R,c.KEY)
        self.mods.tools.bind_recorded_wrapper(capabilities,binary_map,compiler,wrapper_result['stdout'])
        evidence=c.write(self.work/'cargo-build-evidence.json',dict(parsed=parsed,compilers=compiles,generated=generated,
            cargo_receipt=build['path'],strip_failures=0,build_script_compiler_identity_probes=4))
        self.guard(full=True)
        for row in self.binaries.values():c.require(c.file(row['path'])==row,'built tool changed after qualification')
        self.record['exporter_builds']=1
        return c.write(self.work/'built-tools.json',dict(status='build-passed-frontend-unexecuted',binaries=binary_map,
            built_files=self.binaries,capabilities=capabilities,compiler_roles=self.plan['binding'],
            generated=generated,loader=loaded,tool_closures=tool_closures,evidence=evidence,
            VM=self.plan['adopted_VM'],runtime_owner=str(c.R),runtime_key=c.KEY,
            frontend_qualified=False,application_qualified=False,published=False))

    def execute(self):
        try:
            with self.mods.owned.workload_lock(self.c.LOCK,600):
                self.record.update(status='running',admitted_at=time.time(),entry_free_bytes=self.mods.owned.disk(self.c.X,16));self.save()
                self.guard(full=True)
                self.record['result']=self.build() if self.building else self.metadata()
                self.record.update(status='passed',finished_at=time.time(),free_bytes_after=self.mods.owned.disk(self.c.X,8));self.save()
        except BaseException as error:
            self.record.update(status='failed',error=repr(error),finished_at=time.time());self.save();raise


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--phase',choices=('metadata','build'),default='metadata')
    parser.add_argument('--inputs-sha256',required=True);parser.add_argument('--sources-sha256',required=True)
    parser.add_argument('--metadata-receipt-sha256')
    args=parser.parse_args();c,sources=bootstrap(args.sources_sha256)
    c.require(Path.cwd()==c.X and sys.dont_write_bytecode and not sys.flags.optimize,'fixed exporter Python -B/cwd required')
    mods=c.modules(sources)
    def no_signals(event,args):
        if event in ('os.kill','os.killpg'):raise RuntimeError('explicit process signals are forbidden')
    sys.addaudithook(no_signals)
    with c.aliases(mods.public):
        Stage(c,mods,sources,args).execute()


if __name__=='__main__':
    main()
