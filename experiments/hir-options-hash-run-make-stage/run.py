#!/usr/bin/env python3
"""One D2 recipe compile and one unchanged E2 recipe execution; not timings."""
import argparse
import os
from pathlib import Path
import re
import sys
import time

import bounded_recipe as bounded
import history
import loader
import support as s


class Stage:
    def __init__(self,digest):
        assert sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==s.OWNER
        assert s.sha(s.HERE/'inputs.json')==digest
        self.freeze=s.read(s.HERE/'inputs.json');assert s.sha(s.HERE/'plan.json')==self.freeze['plan_sha256']
        self.plan=s.read(s.HERE/'plan.json');self.environment=dict(os.environ)
        assert str(Path(sys.executable).resolve(strict=True))==self.freeze['python']
        assert self.environment==self.freeze['environment']
        self.b=s.build_module();self.m=self.b.m;self.owned=bounded.owned
        s.absent(s.WORK);s.WORK.mkdir();(s.WORK/'commands').mkdir()
        self.record=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),commands=[],
                         performance_measurement=False,application_qualified=False,hash_driver_qualified=False)
        self.save()
    def save(self):self.owned.write(s.WORK/'receipt.json',self.record)
    def guard(self,full):
        assert dict(os.environ)==self.environment
        s.ancestor_guard(full)
        for name,row in self.freeze['files'].items():
            path=Path(name);assert path.resolve(strict=True)==path and s.stamp(path)==row['stamp'],name
            if full:assert s.sha(path)==row['sha256'],name
        build_freeze=s.read(s.BHERE/'inputs.json')
        for name,row in build_freeze['files'].items():
            path=Path(name);assert path.resolve(strict=True)==path and s.stamp(path)==row['stamp'],name
            if full:assert s.sha(path)==row['sha256'],name
        mfreeze=s.read(self.b.MHERE/'inputs.json')
        assert s.sha(self.b.MHERE/'inputs.json')==self.plan['metadata_inputs_sha256']
        self.m.guard(self.plan['metadata_plan'],mfreeze,full)
        for root,expected in self.plan['outputs'].items():
            if full:assert s.inventory(Path(root))==expected,root
            else:
                for name,row in expected.items():
                    path=Path(root)/name
                    if row['kind']=='file':assert path.resolve(strict=True)==path and s.stamp(path)==row['stamp']
                    elif row['kind']=='link':assert path.is_symlink() and s.stamp(path)==row['stamp'] and os.readlink(path)==row['target'] and str(path.resolve(strict=True))==row['resolved']
                    else:s.ordinary(path,True)
        for module in list(sys.modules.values()):
            name=getattr(module,'__file__',None)
            if name and name.startswith('/Users/danluu/dev/'):
                resolved=str(Path(name).resolve(strict=True))
                assert resolved in self.freeze['files'] or resolved in build_freeze['files'] or resolved in mfreeze['files'],name
        s.source_guard()
    def closure(self,path,cwd,dyld):
        return loader.closure(path,cwd=cwd,dyld=dyld,admitted=self.plan['admitted_provider_files'],macho=self.m.macho)
    def command(self,index):
        row=self.plan['children'][index];output=s.WORK/'commands'/f'{index:03}'
        self.guard(False)
        try:bounded.run(row['argv'],cwd=Path(row['cwd']),environment=row['environment'],output=output,canonical_fd=self.lockfd)
        finally:
            path=output/'receipt.json'
            if path.exists():self.record['commands'].append(dict(path=str(path),sha256=s.sha(path),pid=s.read(path).get('pid'),index=index));self.save()
        self.guard(False)
        raw=(output/'stdout').read_bytes();err=(output/'stderr').read_bytes()
        assert not re.search(rb'(?i)(?:failed to strip|stripping debuginfo.*failed|Library not loaded:|dyld\[\d+\]: Library)',raw+err),'native tooling/loader failure'
        return raw,err
    def run(self):
        try:
            with self.owned.workload_lock(self.owned.CANONICAL_LOCK,600) as fd:
                self.lockfd=fd;self.record.update(status='running',admitted_at=time.time(),free_bytes_before=self.owned.disk(s.OWNER,24));self.save()
                self.guard(True);s.completed_build()
                assert s.discover_support()==self.plan['support']
                assert s.directory_contract()==self.plan['directory_contract']
                s.absent(s.BASE);s.BASE.mkdir();s.OUT.mkdir();(s.BASE/'tmp').mkdir()
                for name,row in self.plan['fixture_copies'].items():
                    source=s.S/'tests/run-make/hir-body-cache-capture'/name
                    assert s.file(source)==row
                    with (s.OUT/name).open('xb') as stream:stream.write(source.read_bytes())
                    assert s.sha(s.OUT/name)==row['sha256']
                compile_env=self.plan['children'][0]['environment'];run_env=self.plan['children'][1]['environment']
                d2=self.closure(s.D2/'bin/rustc',s.S,compile_env['DYLD_LIBRARY_PATH'])
                e2=self.closure(s.E2/'bin/rustc',s.OUT,f'{s.OUT}:{s.E2}/lib:'+run_env['DYLD_LIBRARY_PATH'])
                s.write(s.WORK/'compiler-loader-closures.json',dict(D2=d2,E2=e2))
                self.command(0)
                recipe=s.BASE/'rmake';s.ordinary(recipe);assert os.access(recipe,os.X_OK)
                assert sorted(path.name for path in s.OUT.iterdir())==sorted(self.plan['fixture_copies'])
                generated=self.closure(recipe,s.OUT,run_env['DYLD_LIBRARY_PATH'])
                s.write(s.WORK/'recipe-loader-closure.json',generated)
                recipe_identity=s.file(recipe)
                raw,err=self.command(1);assert not raw,'unchanged recipe should write its verbose history to stderr'
                audit=history.audit(err,out=str(s.OUT),rustc=str(s.E2/'bin/rustc'),target=s.HOST,
                                    recipe_dyld=run_env['DYLD_LIBRARY_PATH'],e2=str(s.E2))
                s.write(s.WORK/'nested-history.json',audit)
                assert s.file(recipe)==recipe_identity
                assert self.closure(recipe,s.OUT,run_env['DYLD_LIBRARY_PATH'])==generated
                assert self.closure(s.E2/'bin/rustc',s.OUT,f'{s.OUT}:{s.E2}/lib:'+run_env['DYLD_LIBRARY_PATH'])==e2
                for name,row in self.plan['fixture_copies'].items():assert s.sha(s.OUT/name)==row['sha256']
                assert (s.OUT/'input.rs').read_bytes()==(s.OUT/'fixture.rs').read_bytes(),'final source restoration failed'
                s.write(s.WORK/'final-output-inventory.json',s.inventory(s.BASE))
                self.guard(True);s.completed_build()
                assert len(self.record['commands'])==2
                self.record.update(status='passed',recipe_compilations=1,recipe_executions=1,nested_commands=230,
                                   recipe_identity=recipe_identity,native_recipe_qualified=True,
                                   nested_history_sha256=s.sha(s.WORK/'nested-history.json'),final_outputs_sha256=s.sha(s.WORK/'final-output-inventory.json'),
                                   free_bytes_after=self.owned.disk(s.OWNER,9))
        except BaseException as error:self.record.update(status='failed',error=repr(error));raise
        finally:self.record['finished_at']=time.time();self.save()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True);args=parser.parse_args();Stage(args.inputs_sha256).run()
if __name__=='__main__':main()
