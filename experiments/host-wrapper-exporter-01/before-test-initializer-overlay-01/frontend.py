#!/usr/bin/env python3
"""Run the full18 ordinary frontend cases after exact closed metadata/build.

No tool publication, guest execution, compiler/VM rebuild, or application timing.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

HERE = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/host-wrapper-exporter-01')
FRONTEND_NAMES = ('frontend.py','frontend_recipe.py','frontend_results.py','frontend_telemetry.py')


def bootstrap(args):
    manifest=HERE/'frontend-sources.json'; data=manifest.read_bytes()
    if hashlib.sha256(data).hexdigest()!=args.frontend_sources_sha256:
        raise RuntimeError('frontend source selection differs')
    inventory=json.loads(data); selected=inventory['files']
    build_manifest=HERE/'build-sources.json'; build_data=build_manifest.read_bytes()
    if hashlib.sha256(build_data).hexdigest()!=args.build_sources_sha256:
        raise RuntimeError('build source selection differs')
    build_sources=json.loads(build_data)['files']
    expected=set(build_sources)|{str(build_manifest)}|{str(HERE/n) for n in FRONTEND_NAMES}
    if (set(selected)!=expected or selected.get(str(build_manifest))!=args.build_sources_sha256
            or any(selected.get(n)!=h for n,h in build_sources.items())):
        raise RuntimeError('frontend source/import closure differs')
    for name,digest in selected.items():
        path=Path(name)
        if (path.resolve(strict=True)!=path or path.is_symlink() or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest()!=digest):
            raise RuntimeError('authenticated frontend source changed: '+name)
    if Path(__file__).resolve()!=HERE/'frontend.py':
        raise RuntimeError('fixed frontend source path required')
    def load(name):
        private='_exporter07_frontend_'+name
        if private in sys.modules:raise RuntimeError('unexpected existing frontend module')
        spec=importlib.util.spec_from_file_location(private,HERE/(name+'.py'))
        module=importlib.util.module_from_spec(spec);sys.modules[private]=module;spec.loader.exec_module(module)
        return module
    build=load('build')
    c,metadata,checks,cargo,sources,build_sources=build.bootstrap(args.sources_sha256,args.build_sources_sha256)
    return (c,metadata,build.build_class(metadata,checks,cargo),sources,build_sources,selected,
            load('frontend_recipe'),load('frontend_results'),load('frontend_telemetry'))


def frontend_class(metadata, Build, recipes, validation, telemetry):
    class Frontend(Build):
        def __init__(self,c,mods,sources,build_sources,frontend_sources,args):
            # Retain the inherited proof-reader/guard/recorded-command methods;
            # do not construct a build Stage or create its completed work path.
            self.c,self.mods,self.sources,self.args=c,mods,sources,args
            self.build_sources,self.frontend_sources=build_sources,frontend_sources
            self.inputs=c.read(c.PACKET/'inputs.json',args.inputs_sha256)
            self.plan=c.read(c.PACKET/'plan.json',self.inputs['plan']['sha256'])
            c.require(self.inputs['files']==sources and self.plan['status']=='prepared-unexecuted'
                and self.plan['owner']==str(c.X) and self.plan['runtime_key']==c.KEY
                and self.plan['source_root']==str(c.PREFIX),'current exporter packet differs')
            c.require(c.file(Path(sys.executable).resolve(strict=True))==self.inputs['python'], 'Python executor differs')
            self.building=True
            self.work=c.X/'.work/host-wrapper-exporter-frontend-01'
            self.build_work=c.X/'.work/host-wrapper-exporter-build-01'
            c.require(not os.path.lexists(self.work),'fresh frontend work required')
            self.work.mkdir();(self.work/'tmp').mkdir()
            self.protected={};self.cache={};self.binaries={};self.closed=[];self.closures=[]
            self.record=dict(status='waiting',phase='frontend',pid=os.getpid(),parent_pid=os.getppid(),
                started_at=time.time(),command=list(sys.argv),cwd=os.getcwd(),commands=[],
                inputs_sha256=args.inputs_sha256,sources_sha256=args.sources_sha256,
                build_sources_sha256=args.build_sources_sha256,frontend_sources_sha256=args.frontend_sources_sha256,
                metadata_receipt_sha256=args.metadata_receipt_sha256,build_receipt_sha256=args.build_receipt_sha256,
                built_tools_sha256=args.built_tools_sha256,plan_sha256=self.inputs['plan']['sha256'],
                runtime_key=c.KEY,exporter_builds=0,compiler_builds=0,VM_builds=0,guest_executions=0,
                frontend_qualified=False,application_qualified=False,performance_measurement=False,
                published=False,signals=0,retries=0,capacity=dict(entry_gib=16,stop_gib=9,floor_gib=8),
                canonical_lock=str(c.LOCK),wait_seconds=600)
            self.recipe=recipes.context(c,self.work,self.plan['launch_environment'])
            flags=[s for s in self.plan['binding']['build_rustflags'] if s.startswith('-Clinker=')]
            c.require(len(flags)==1,'one qualified clang required')
            self.sdk=dict(clang=flags[0].split('=',1)[1],path=self.plan['launch_environment']['SDKROOT'])
            self.rows=self.recipe.application_commands(self.sdk)
            self.schedule=[];self.save()

        def guard(self,full=False):
            super().guard(full=full)
            self.c.file(HERE/'frontend-sources.json',self.args.frontend_sources_sha256)
            for path,digest in self.frontend_sources.items():self.c.file(path,digest)
            for closure in self.closures:
                self.c.require(self.mods.loaders.library_state(closure['identity'])==closure['state'],
                               'frontend tool library resolution changed')

        def command(self,row):
            self.c.require(len(self.record['commands'])<len(self.schedule)
                and row==self.schedule[len(self.record['commands'])],'unreviewed frontend command/order')
            outcome=metadata.Stage.command(self,row)
            self.protect(outcome['path'])
            for stream in ('stdout','stderr'):
                self.protect(Path(outcome['path']).parent/stream,outcome['receipt'][stream+'_sha256'])
            return outcome

        def check_build(self):
            c=self.c
            self.metadata_receipts()
            path=self.build_work/'receipt.json';self.protect(path,self.args.build_receipt_sha256)
            receipt=c.read(path,self.args.build_receipt_sha256)
            schedule=Build.child_schedule(SimpleNamespace(c=c,plan=self.plan,work=self.build_work))
            c.require(receipt['status']=='passed' and receipt['phase']=='build'
                and receipt['inputs_sha256']==self.args.inputs_sha256
                and receipt['sources_sha256']==self.args.sources_sha256
                and receipt['build_sources_sha256']==self.args.build_sources_sha256
                and receipt['metadata_receipt_sha256']==self.args.metadata_receipt_sha256
                and receipt['plan_sha256']==self.inputs['plan']['sha256']
                and receipt['runtime_key']==c.KEY and receipt['cwd']==str(c.X)
                and receipt['exporter_builds']==1 and receipt['compiler_builds']==receipt['VM_builds']==0
                and receipt['signals']==receipt['retries']==0 and 'error' not in receipt
                and receipt['frontend_qualified'] is False and receipt['published'] is False
                and 0<receipt['started_at']<=receipt['admitted_at']<=receipt['finished_at']<=self.record['started_at']
                and len(receipt['commands'])==len(schedule)==7,'complete successful actual build required')
            previous=receipt['admitted_at'];observed={}
            for index,(saved,wanted) in enumerate(zip(receipt['commands'],schedule,strict=True)):
                path=self.build_work/'commands'/f'{index:03d}'/'receipt.json'
                c.require(saved['path']==str(path) and saved['label']==wanted['label'],'build child path/label differs')
                self.protect(path,saved['sha256']);child=c.read(path,saved['sha256'])
                c.require(child['status']=='finished' and child['returncode']==saved['returncode']==0
                    and child['pid']==saved['pid'] and child['command']==wanted['command']
                    and child['environment']==wanted['environment'] and child['cwd']==wanted['cwd']
                    and child['supervisor_pid']==receipt['pid'] and child['parent_pid']==receipt['parent_pid']
                    and previous<=child['started_at']<=child['finished_at']<=receipt['finished_at'],
                    'build child actual closure differs')
                previous=child['finished_at'];observed[wanted['label']]=path
                for stream in ('stdout','stderr'):self.protect(path.parent/stream,child[stream+'_sha256'])
            result_path=self.build_work/'built-tools.json';reference=receipt['result']
            c.require(reference['path']==str(result_path) and reference['sha256']==self.args.built_tools_sha256
                and self.protect(result_path,self.args.built_tools_sha256)==reference,'actual build result ref differs')
            self.built=c.read(result_path,self.args.built_tools_sha256)
            c.require(self.built['status']=='build-passed-frontend-unexecuted'
                and self.built['compiler_roles']==self.plan['binding']
                and self.built['runtime_key']==c.KEY and self.built['runtime_owner']==str(c.R)
                and self.built['VM']==self.plan['adopted_VM']
                and self.built['frontend_qualified'] is False and self.built['application_qualified'] is False
                and self.built['published'] is False and self.built['performance_measurement'] is False,
                'built tool/current runtime composition differs')
            c.require(set(self.built['built_files'])=={'rust-interp-mir-export','rust-interp-rustc-wrapper'},
                      'exact two built tools required')
            for name,row in self.built['built_files'].items():
                c.require(row['path']==str(c.TARGET/'release'/name)
                    and self.protect(row['path'],row['sha256'])==row
                    and self.built['binaries'][name]==row['sha256'],'built binary identity differs')
                self.binaries[name]=row
            vm=self.plan['adopted_VM']['binary'];self.protect(vm['path'],vm['sha256'])
            c.require(self.built['binaries']['rust-interp-vm']==vm['sha256'],'adopted VM differs')
            for row in self.built['generated']+[self.built['evidence']]:
                c.require(self.protect(row['path'],row['sha256'])==row,'build role/evidence output changed')
            caps=json.loads((observed['exporter-capabilities'].parent/'stdout').read_bytes())
            compiler=self.mods.runtime.load_runtime_compiler(c.R,c.KEY)
            self.mods.tools.bind_recorded_wrapper(caps,self.built['binaries'],compiler,
                (observed['wrapper-roles'].parent/'stdout').read_bytes())
            c.require(caps==self.built['capabilities'],'built recorded capability/wrapper association differs')
            self.record['build']=dict(receipt=self.protected[str(self.build_work/'receipt.json')],result=reference)
            self.save()

        def make_schedule(self):
            c=self.c;env=self.plan['launch_environment']|{'TMPDIR':str(self.work/'tmp')+'/'}
            sdk=[row for row in self.plan['children'] if row['label'].startswith('sdk-')
                 and not row['label'].startswith('sdk-after-')]
            c.require(len(sdk)==5,'full fixed SDK query set required')
            rows=[dict(row,environment=env,label='before-'+row['label']) for row in sdk]
            for name in ('rust-interp-mir-export','rust-interp-rustc-wrapper','rust-interp-vm'):
                binary=self.plan['adopted_VM']['binary']['path'] if name=='rust-interp-vm' else str(c.TARGET/'release'/name)
                for flag in ('-L','-l'):
                    rows.append(dict(label=name+flag,command=['/usr/bin/otool','-arch','arm64',flag,binary],
                        cwd=str(c.X),environment=env,expected=[0]))
            rows.extend(dict(label=row['name'],command=row['argv'],cwd=str(self.work/'fixture'),
                environment=self.recipe.application_environment(row,self.sdk),expected=[1,2] if row['error'] else [0])
                for row in self.rows)
            rows.extend(dict(row,environment=env,label='after-'+row['label']) for row in sdk)
            c.require(len(self.rows)==18 and len(rows)==34,'exact full frontend schedule differs')
            return rows

        def tool_closures(self):
            c=self.c;driver=self.plan['binding']['runtime_driver']['path']
            admitted={driver,str(c.RUNTIME/'lib/libLLVM.dylib')}
            observations=[]
            for name in ('rust-interp-mir-export','rust-interp-rustc-wrapper','rust-interp-vm'):
                binary=self.plan['adopted_VM']['binary']['path'] if name=='rust-interp-vm' else str(c.TARGET/'release'/name)
                fresh={}
                for flag in ('-L','-l'):
                    out=self.command(self.schedule[len(self.record['commands'])]);fresh[flag]=out['path']
                    c.require(not out['stderr'],'fresh tool loader diagnostics')
                    self.cache[(binary,flag)]=out
                closure=self.closure(binary)
                actual={r['resolved'] for r in closure['identity']['libraries']}
                c.require((driver in actual and actual<=admitted) if name=='rust-interp-mir-export' else not actual,
                          'unexpected non-system composed tool library')
                if name!='rust-interp-vm':
                    c.require(closure==self.built['tool_closures'][name],'built tool closure changed')
                self.closures.append(closure)
                observations.append(dict(name=name,binary=c.file(binary),**closure,fresh_inspections=fresh))
            row=c.write(self.work/'tool-closures.json',observations);self.protect(row['path'],row['sha256'])
            return row

        def applications(self):
            c=self.c;fixture=self.work/'fixture';output=self.work/'outputs'
            fixture.mkdir();output.mkdir()
            original={n:(c.PREFIX/'tests/fixtures/borrowck-cache'/n).read_bytes() for n in ('basic.rs','test_export.rs')}
            for n,data in original.items():c.write(fixture/n,data)
            states={'original':original['basic.rs']}|{n:original['basic.rs']+extra for n,_,extra in self.recipe.errors}
            outcomes=[]
            try:
                for row in self.rows:
                    raw=states[row['state']];(fixture/'basic.rs').write_bytes(raw)
                    c.require((fixture/'test_export.rs').read_bytes()==original['test_export.rs'],'test fixture changed')
                    retained=c.write(self.work/(row['name']+'.source.rs'),
                        original['test_export.rs'] if row['name'].startswith('test-') else raw)
                    self.protect(retained['path'],retained['sha256'])
                    (output/(row['name']+'-argv')).mkdir()
                    outcomes.append(self.command(self.schedule[len(self.record['commands'])]))
                    c.require((fixture/'basic.rs').read_bytes()==raw
                        and (fixture/'test_export.rs').read_bytes()==original['test_export.rs'],
                        'frontend compiler changed fixture inputs')
                    for name in c.tree(output):self.protect(output/name)
            finally:
                for n,data in original.items():(fixture/n).write_bytes(data)
                for n,data in original.items():c.require((fixture/n).read_bytes()==data,'fixture restoration failed')
            result=validation.validate(c,telemetry,self.recipe,self.work,self.plan,self.rows,outcomes)
            self.protect(result['path'],result['sha256'])
            return result

        def run(self):
            self.guard(full=True);self.check_build();self.schedule=self.make_schedule()
            declaration=self.c.write(self.work/'run-plan.json',dict(children=self.schedule,application_commands=self.rows,
                diagnostic_pairs=9,direct_frontend_controls=18,fresh_loader_commands=6,sdk_commands=10,
                capacity=self.record['capacity'],binding=self.plan['binding'],source_checkpoint=self.c.CHECKPOINT))
            self.protect(declaration['path'],declaration['sha256'])
            for _ in range(5):self.command(self.schedule[len(self.record['commands'])])
            closures=self.tool_closures();result=self.applications()
            for _ in range(5):self.command(self.schedule[len(self.record['commands'])])
            self.guard(full=True)
            self.c.require(len(self.record['commands'])==34,'complete frontend history required')
            return dict(result=result,tool_closures=closures,run_plan=declaration)

        def execute(self):
            try:
                with self.mods.owned.workload_lock(self.c.LOCK,600):
                    self.record.update(status='running',admitted_at=time.time(),entry_free_bytes=self.mods.owned.disk(self.c.X,16));self.save()
                    self.record.update(self.run())
                    self.record.update(status='passed',finished_at=time.time(),frontend_qualified=True,
                        source_restored=True,source_unchanged=True,free_bytes_after=self.mods.owned.disk(self.c.X,8));self.save()
            except BaseException as error:
                self.record.update(status='failed',error=repr(error),finished_at=time.time());self.save();raise
    return Frontend


def main():
    parser=argparse.ArgumentParser(__doc__)
    for name in ('inputs-sha256','sources-sha256','build-sources-sha256','frontend-sources-sha256',
                 'metadata-receipt-sha256','build-receipt-sha256','built-tools-sha256'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    c,metadata,Build,sources,build_sources,selected,recipes,validation,telemetry=bootstrap(args)
    c.require(Path.cwd()==c.X and sys.dont_write_bytecode and not sys.flags.optimize,'fixed frontend Python -B/cwd required')
    mods=c.modules(sources)
    def no_signals(event,arguments):
        if event in ('os.kill','os.killpg'):raise RuntimeError('explicit process signals are forbidden')
    sys.addaudithook(no_signals)
    with c.aliases(mods.public):
        frontend_class(metadata,Build,recipes,validation,telemetry)(c,mods,sources,build_sources,selected,args).execute()


if __name__=='__main__':
    main()
