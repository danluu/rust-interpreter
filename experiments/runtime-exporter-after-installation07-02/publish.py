#!/usr/bin/env python3
"""Publish the ordinary three-tool runtime composition after closed frontend34."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

HERE=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-exporter-after-installation07-02')
OPTIONS=('stable-cgu-partitioning','compiler-argv-record-v1','function-cache-auto',
         'inline-leaves','trap-unsupported-calls','run-try-callbacks','host-proc-macro-opt-v1',
         'entry-catalog','list-tests')
NAMES=('rust-interp-mir-export','rust-interp-rustc-wrapper','rust-interp-vm')


def bootstrap(args):
    path=HERE/'publication-sources.json';payload=path.read_bytes()
    if hashlib.sha256(payload).hexdigest()!=args.publication_sources_sha256:
        raise RuntimeError('publication source selection differs')
    inventory=json.loads(payload)
    if (set(inventory)!={'policy','frontend_sources','files'}
            or inventory['policy']!='runtime-exporter07-publication-sources-v1'
            or type(inventory['files']) is not dict or len(inventory['files'])!=25):
        raise RuntimeError('publication source manifest schema differs')
    files=inventory['files'];front=HERE/'frontend-sources.json'
    data=front.read_bytes()
    if hashlib.sha256(data).hexdigest()!=args.frontend_sources_sha256:
        raise RuntimeError('frontend source selection differs')
    selected=json.loads(data)['files']
    R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
    extra={str(HERE/n) for n in ('publish.py','validate_published.py')}
    extra|={str(R/'scripts'/n) for n in ('interpreter.py','workspace_cache.py')}
    if (set(files)!=set(selected)|extra|{str(front)}
            or files.get(str(front))!=args.frontend_sources_sha256
            or inventory['frontend_sources']!=dict(path=str(front),sha256=args.frontend_sources_sha256)
            or any(files.get(n)!=h for n,h in selected.items())):
        raise RuntimeError('publication/ordinary reader source closure differs')
    for name,digest in files.items():
        p=Path(name)
        if (p.resolve(strict=True)!=p or p.is_symlink() or not p.is_file()
                or hashlib.sha256(p.read_bytes()).hexdigest()!=digest):
            raise RuntimeError('authenticated publication source changed: '+name)
    if Path(__file__).resolve()!=HERE/'publish.py':raise RuntimeError('fixed publisher source path required')
    spec=importlib.util.spec_from_file_location('_exporter07_publisher_frontend',HERE/'frontend.py')
    frontend=importlib.util.module_from_spec(spec);spec.loader.exec_module(frontend)
    c,metadata,Build,sources,build_sources,frontend_sources,recipes,validation,telemetry=frontend.bootstrap(args)
    Frontend=frontend.frontend_class(metadata,Build,recipes,validation,telemetry)
    return c,metadata,Frontend,sources,build_sources,frontend_sources,files,recipes,telemetry


def publisher_class(metadata,Frontend,recipes,telemetry):
    class Publisher(Frontend):
        def __init__(self,c,mods,sources,build_sources,frontend_sources,publication_sources,args):
            self.c,self.mods,self.sources,self.args=c,mods,sources,args
            self.build_sources,self.frontend_sources,self.publication_sources=build_sources,frontend_sources,publication_sources
            self.inputs=c.read(c.PACKET/'inputs.json',args.inputs_sha256)
            self.plan=c.read(c.PACKET/'plan.json',self.inputs['plan']['sha256'])
            c.require(self.inputs['files']==sources and self.plan['status']=='prepared-unexecuted'
                and self.plan['owner']==str(c.X) and self.plan['runtime_key']==c.KEY
                and self.plan['source_root']==str(c.PREFIX),'current exporter packet differs')
            c.require(c.file(Path(sys.executable).resolve(strict=True))==self.inputs['python'],'Python executor differs')
            self.building=True
            self.work=c.X/'.work/hir-options-hash-exporter-publication-02'
            self.front_work=c.X/'.work/hir-options-hash-exporter-frontend-02'
            self.build_work=c.X/'.work/hir-options-hash-exporter-build-02'
            c.require(not os.path.lexists(self.work),'fresh publication work required')
            self.work.mkdir();(self.work/'tmp').mkdir()
            self.protected={};self.cache={};self.binaries={};self.closed=[];self.closures=[];self.published={}
            self.record=dict(status='waiting',phase='publication',pid=os.getpid(),parent_pid=os.getppid(),
                started_at=time.time(),command=list(sys.argv),cwd=os.getcwd(),commands=[],
                inputs_sha256=args.inputs_sha256,sources_sha256=args.sources_sha256,
                build_sources_sha256=args.build_sources_sha256,frontend_sources_sha256=args.frontend_sources_sha256,
                publication_sources_sha256=args.publication_sources_sha256,
                metadata_receipt_sha256=args.metadata_receipt_sha256,build_receipt_sha256=args.build_receipt_sha256,
                built_tools_sha256=args.built_tools_sha256,frontend_receipt_sha256=args.frontend_receipt_sha256,
                plan_sha256=self.inputs['plan']['sha256'],runtime_key=c.KEY,
                exporter_builds=0,compiler_builds=0,VM_builds=0,guest_executions=0,
                frontend_qualified=False,application_qualified=False,performance_measurement=False,
                publication=False,signals=0,retries=0,capacity=dict(entry_gib=16,stop_gib=9,floor_gib=8),
                canonical_lock=str(c.LOCK),wait_seconds=600)
            self.schedule=[];self.save()

        def guard(self,full=False):
            super().guard(full=full)
            self.c.file(HERE/'publication-sources.json',self.args.publication_sources_sha256)
            for name,digest in self.publication_sources.items():self.c.file(name,digest)
            for name,row in self.published.items():
                self.c.require(self.c.file(name)==row,'published output changed')

        @contextmanager
        def tool_lock(self):
            path=self.c.R/'.work/interpreter-tools.lock'
            self.c.require(path.parent.resolve(strict=True)==path.parent and path.parent.is_dir()
                and not path.is_symlink() and (not path.exists() or path.is_file()),'ordinary tool lock required')
            with path.open('a+') as lock:
                before=os.fstat(lock.fileno());deadline=time.monotonic()+600
                while True:
                    try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);break
                    except BlockingIOError:
                        self.c.require(time.monotonic()<deadline,'runtime tool publication lock timed out')
                        time.sleep(.25)
                after=path.stat()
                self.c.require((before.st_dev,before.st_ino)==(after.st_dev,after.st_ino),'tool lock replaced')
                yield

        def frontend_proof(self):
            c=self.c;path=self.front_work/'receipt.json'
            self.protect(path,self.args.frontend_receipt_sha256);terminal=c.read(path,self.args.frontend_receipt_sha256)
            for field in ('inputs_sha256','sources_sha256','build_sources_sha256','frontend_sources_sha256',
                          'metadata_receipt_sha256','build_receipt_sha256','built_tools_sha256'):
                c.require(terminal[field]==getattr(self.args,field),'frontend prerequisite/source pin differs: '+field)
            c.require(terminal['status']=='passed' and terminal['phase']=='frontend'
                and terminal['runtime_key']==c.KEY and terminal['plan_sha256']==self.inputs['plan']['sha256']
                and terminal['cwd']==str(c.X) and terminal['frontend_qualified'] is True
                and terminal['source_restored'] is True and terminal['source_unchanged'] is True
                and terminal['application_qualified'] is False and terminal['published'] is False
                and terminal['performance_measurement'] is False
                and terminal['exporter_builds']==terminal['compiler_builds']==terminal['VM_builds']==0
                and terminal['guest_executions']==terminal['signals']==terminal['retries']==0 and 'error' not in terminal
                and 0<terminal['started_at']<=terminal['admitted_at']<=terminal['finished_at']<=self.record['started_at'],
                'successful full current frontend closure required')
            recipe=recipes.context(c,self.front_work,self.plan['launch_environment'])
            linker=[s for s in self.plan['binding']['build_rustflags'] if s.startswith('-Clinker=')]
            c.require(len(linker)==1,'qualified frontend linker missing')
            sdk=dict(clang=linker[0].split('=',1)[1],path=self.plan['launch_environment']['SDKROOT'])
            rows=recipe.application_commands(sdk)
            context=SimpleNamespace(c=c,work=self.front_work,plan=self.plan,recipe=recipe,rows=rows,sdk=sdk)
            schedule=Frontend.make_schedule(context)
            refs={}
            for field,name in (('run_plan','run-plan.json'),('result','frontend-results.json'),('tool_closures','tool-closures.json')):
                ref=terminal[field];p=self.front_work/name
                c.require(ref['path']==str(p) and self.protect(p,ref['sha256'])==ref,'frontend output reference differs')
                refs[field]=ref
            declared=c.read(refs['run_plan']['path'],refs['run_plan']['sha256'])
            c.require(declared==dict(children=schedule,application_commands=rows,diagnostic_pairs=9,
                direct_frontend_controls=18,fresh_loader_commands=6,sdk_commands=10,
                capacity=terminal['capacity'],binding=self.plan['binding'],source_checkpoint=c.CHECKPOINT),
                'full frontend recipe declaration differs')
            c.require(len(terminal['commands'])==len(schedule)==34,'full34 frontend commands required')
            previous=terminal['admitted_at'];observed={}
            for index,(saved,wanted) in enumerate(zip(terminal['commands'],schedule,strict=True)):
                p=self.front_work/'commands'/f'{index:03d}'/'receipt.json'
                c.require(saved['path']==str(p) and saved['label']==wanted['label'],'frontend command path/order differs')
                self.protect(p,saved['sha256']);child=c.read(p,saved['sha256'])
                c.require(child['status']=='finished' and child['returncode']==saved['returncode']
                    and child['returncode'] in wanted['expected'] and child['pid']==saved['pid']
                    and child['command']==wanted['command'] and child['environment']==wanted['environment']
                    and child['cwd']==wanted['cwd'] and child['supervisor_pid']==terminal['pid']
                    and child['parent_pid']==terminal['parent_pid']
                    and previous<=child['started_at']<=child['finished_at']<=terminal['finished_at'],
                    'frontend child closed association differs')
                previous=child['finished_at'];observed[wanted['label']]=p
                for stream in ('stdout','stderr'):self.protect(p.parent/stream,child[stream+'_sha256'])
            result=c.read(refs['result']['path'],refs['result']['sha256'])
            c.require(result['raw_compiler_diagnostic_parity'] is True and result['whole_stderr_parity'] is False
                and result['telemetry_losslessly_retained'] is True and result['bytecode_parity'] is True
                and result['source_restored'] is True and result['guest_executions']==0
                and len(result['children'])==18 and len(result['comparison_pairs'])==9,
                'full frontend diagnostic/bytecode result differs')
            for row,item in zip(rows,result['children'],strict=True):
                p=observed[row['name']]
                c.require(item['name']==row['name'] and item['receipt']==str(p)
                    and item['receipt_sha256']==self.protected[str(p)]['sha256'],'frontend result/receipt association differs')
                for field in ('source','compiler_argv','artifact'):
                    ref=item[field]
                    if ref is not None:
                        c.require(self.protect(ref['path'],ref['sha256'])==ref,'frontend retained output changed')
                c.require(item['compiler_argv']==recipe.argv_record(row,self.front_work/'outputs'/(row['name']+'-argv')),
                          'frontend final compiler argv differs')
                raw=(p.parent/'stderr').read_bytes()
                if row['error']!='wrong-role':
                    split=telemetry.split_stderr(raw,allow_telemetry=row['profile'] in ('basic','test') and row['error'] is None)
                    c.require(split==item['stderr_separation'],'frontend lossless raw separation differs')
            for n in ('basic.rs','test_export.rs'):
                c.require((self.front_work/'fixture'/n).read_bytes()==(c.PREFIX/'tests/fixtures/borrowck-cache'/n).read_bytes(),
                          'frontend fixture not restored')
            closures=c.read(refs['tool_closures']['path'],refs['tool_closures']['sha256'])
            c.require([v['name'] for v in closures]==list(NAMES),'complete composed tool closures required')
            for item in closures:
                c.require(self.protect(item['binary']['path'],item['binary']['sha256'])==item['binary'],
                          'frontend closure binary changed')
                self.closures.append(dict(identity=item['identity'],state=item['state']))
            self.front_refs=dict(receipt=self.protected[str(path)],**refs)
            self.record['frontend']=self.front_refs;self.save()

        def compose(self):
            c=self.c
            sources={r['path']:r['sha256'] for r in self.plan['source_materialization'].values()}
            c.require(len(sources)==238,'full exporter source identity required')
            readers={name:digest for name,digest in self.publication_sources.items()
                     if Path(name).is_relative_to(c.R/'scripts')}
            composition=dict(kind=self.mods.tools.POLICY,compiler_key=c.KEY,compiler_sysroot=str(c.RUNTIME),
                binaries=self.built['binaries'],compiler_roles=self.plan['binding'],
                source=dict(owner=str(c.X),root=str(c.PREFIX),checkpoint=c.CHECKPOINT,files=sources,
                    metadata=self.record['metadata']['receipt']),
                actual_build=dict(receipt=self.record['build']['receipt'],tools=self.record['build']['result'],
                    evidence=self.built['evidence'],recipe=self.plan['future_build'],strip_failures=0),
                adopted_VM=self.plan['adopted_VM'],direct_frontend=self.front_refs,
                ordinary_launcher=dict(owner=str(c.R),source_files=readers),
                guest_execution_qualified=False,benchmark=False)
            self.key=self.mods.tools.digest(composition);self.directory=c.R/'.work/interpreter-tools'/self.key
            self.composition=composition
            c.require(set(OPTIONS)<=set(self.built['capabilities']['export_options']),'ordinary application options missing')
            return composition

        def command(self,row):
            c=self.c;self.guard();self.mods.owned.disk(c.X,9)
            c.require(len(self.record['commands'])<len(self.schedule)
                and row==self.schedule[len(self.record['commands'])],'unreviewed publication command')
            path=Path(row['command'][0]).resolve(strict=True)
            expected=self.published.get(str(path),self.plan['files'].get(str(path)))
            c.require(expected is not None and c.file(path)==expected,'publication executor changed')
            out=self.work/'commands'/f'{len(self.record["commands"]):03d}'
            try:
                self.mods.owned.run(row['command'],cwd=row['cwd'],env=row['environment'],out=out,
                    capacity_root=c.X,expected=tuple(row['expected']))
            finally:
                if (out/'receipt.json').exists():
                    child=c.read(out/'receipt.json');self.record['commands'].append(dict(label=row['label'],
                        path=str(out/'receipt.json'),sha256=c.file(out/'receipt.json')['sha256'],
                        pid=child.get('pid'),returncode=child.get('returncode')));self.save()
            child=c.read(out/'receipt.json')
            c.require(child['status']=='finished' and child['returncode']==0 and child['command']==row['command']
                and child['environment']==row['environment'] and child['cwd']==row['cwd'],'publication child did not close')
            self.protect(out/'receipt.json')
            for stream in ('stdout','stderr'):self.protect(out/stream,child[stream+'_sha256'])
            self.guard()
            return dict(path=str(out/'receipt.json'),receipt=child,stdout=(out/'stdout').read_bytes(),stderr=(out/'stderr').read_bytes())

        def publish(self):
            c=self.c;namespace=self.directory.parent
            c.require(c.R.resolve(strict=True)==c.R and namespace.parent.resolve(strict=True)==namespace.parent,
                      'ordinary installed runtime owner required')
            if not os.path.lexists(namespace):namespace.mkdir()
            c.require(namespace.is_dir() and not namespace.is_symlink() and namespace.resolve(strict=True)==namespace,
                      'ordinary tool namespace required')
            c.require(not os.path.lexists(self.directory),'fresh key-owned publication required')
            original={n:(self.plan['adopted_VM']['binary']['path'] if n=='rust-interp-vm' else self.binaries[n]['path']) for n in NAMES}
            before={n:c.file(p,self.built['binaries'][n]) for n,p in original.items()}
            c.require(sum(v['bytes'] for v in before.values())<=512*2**20
                and all(v['bytes']<=256*2**20 for v in before.values()),'finite ordinary three-tool copy budget exceeded')
            self.mods.owned.disk(c.R,9);self.directory.mkdir();copied={}
            for n,source in original.items():
                destination=self.directory/n
                with Path(source).open('rb') as inp,destination.open('xb') as out:
                    while block:=inp.read(1024*1024):
                        self.mods.owned.disk(c.R,9);out.write(block)
                    out.flush();os.fsync(out.fileno())
                destination.chmod(0o555);after=c.file(destination,before[n]['sha256'])
                c.require(after['identity'][6]==1 and after['identity'][:2]!=before[n]['identity'][:2]
                    and c.file(source)==before[n],'publication copy aliases/changes original')
                self.published[str(destination)]=after;copied[n]=dict(source=before[n],destination=after)
            env=self.plan['launch_environment']|{'TMPDIR':str(self.work/'tmp')+'/'}
            self.schedule=[dict(label='published-exporter',command=[str(self.directory/NAMES[0]),'--rust-interp-capabilities'],
                cwd=str(c.X),environment=env|{'DYLD_PRINT_LIBRARIES':'1'},expected=[0]),
                dict(label='published-wrapper',command=[str(self.directory/NAMES[1]),'--rust-interp-compiler-roles'],
                cwd=str(c.X),environment=env,expected=[0]),
                dict(label='ordinary-installed-reader',command=[c.PYTHON,'-B',str(HERE/'validate_published.py'),
                    '--publication-sources-sha256',self.args.publication_sources_sha256,'--tool-key',self.key,
                    '--runtime-compiler-key',c.KEY],cwd=str(c.R),environment=env,expected=[0])]
            c.write(self.work/'publication-plan.json',dict(composition=self.composition,tool_key=self.key,
                directory=str(self.directory),children=self.schedule,required_export_options=list(OPTIONS)))
            exporter=self.command(self.schedule[0]);caps=json.loads(exporter['stdout'])
            c.require(caps=={k:v for k,v in self.built['capabilities'].items() if k!='runtime_wrapper'},
                      'published exporter capabilities differ')
            allowed={str(self.directory/NAMES[0])}|{r['resolved'] for r in self.closures[0]['identity']['libraries']}
            loaded=metadata.loaded_libraries(c,exporter['stderr'],exporter['receipt']['pid'],allowed,
                                            self.plan['binding']['runtime_driver']['path'])
            wrapper=self.command(self.schedule[1]);c.require(not wrapper['stderr'],'published wrapper diagnostics')
            compiler=self.mods.runtime.load_runtime_compiler(c.R,c.KEY)
            self.mods.tools.bind_recorded_wrapper(caps,self.built['binaries'],compiler,wrapper['stdout'])
            caps.update(tool_key=self.key,exporter_sha256=self.built['binaries'][NAMES[0]])
            c.require(set(OPTIONS)<=set(caps['export_options']),'ordinary published options missing')
            for n,value in (('compiler.json',self.composition),('capabilities.json',caps),('ready.json',self.built['binaries'])):
                raw=c.encoded(value);c.require(len(raw)<=8*2**20,'bounded publication metadata exceeded')
                p=self.directory/n;c.write(p,raw);p.chmod(0o444);self.published[str(p)]=c.file(p)
            self.directory.chmod(0o555)
            validation=self.command(self.schedule[2])
            c.require(not validation['stderr'] and json.loads(validation['stdout'])==dict(status='passed',
                tool_key=self.key,runtime_key=c.KEY,directory=str(self.directory)), 'ordinary installed tool validation failed')
            c.require(set(c.tree(self.directory))==set(NAMES)|{'compiler.json','capabilities.json','ready.json'},
                      'published complete membership differs')
            self.mods.tools.validate_tool_runtime(self.directory,self.key,compiler)
            return c.write(self.work/'published-tools.json',dict(tool_key=self.key,directory=str(self.directory),
                composition=self.composition,copied=copied,capabilities=caps,loaded_images=loaded,
                actual_exporter_probe=exporter['path'],actual_wrapper_probe=wrapper['path'],
                installed_validation=validation['path'],guest_execution=False,benchmark=False))

        def execute(self):
            try:
                with self.mods.owned.workload_lock(self.c.LOCK,600):
                    self.record.update(status='running',admitted_at=time.time(),entry_free_bytes=self.mods.owned.disk(self.c.X,16));self.save()
                    self.guard(full=True);self.check_build();self.frontend_proof();self.compose()
                    with self.tool_lock():
                        self.guard(full=True);result=self.publish();self.guard(full=True)
                    self.c.require(len(self.record['commands'])==3,'three actual publication probes required')
                    self.record.update(status='passed',finished_at=time.time(),frontend_qualified=True,
                        publication=True,tool_key=self.key,published_directory=str(self.directory),
                        result=result,published_tools_sha256=result['sha256'],free_bytes_after=self.mods.owned.disk(self.c.R,8));self.save()
            except BaseException as error:
                self.record.update(status='failed',error=repr(error),finished_at=time.time());self.save();raise
    return Publisher


def main():
    parser=argparse.ArgumentParser(__doc__)
    for name in ('inputs-sha256','sources-sha256','build-sources-sha256','frontend-sources-sha256',
                 'publication-sources-sha256','metadata-receipt-sha256','build-receipt-sha256',
                 'built-tools-sha256','frontend-receipt-sha256'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    c,metadata,Frontend,sources,build_sources,frontend_sources,files,recipes,telemetry=bootstrap(args)
    c.require(Path.cwd()==c.X and sys.dont_write_bytecode and not sys.flags.optimize,'fixed publisher Python -B/cwd required')
    mods=c.modules(sources)
    def no_signals(event,arguments):
        if event in ('os.kill','os.killpg'):raise RuntimeError('explicit process signals forbidden')
    sys.addaudithook(no_signals)
    with c.aliases(mods.public):
        publisher_class(metadata,Frontend,recipes,telemetry)(c,mods,sources,build_sources,frontend_sources,files,args).execute()


if __name__=='__main__':main()
