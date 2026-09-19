#!/usr/bin/env python3
"""Six offline metadata controls using preserved, admitted stage0 providers."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import time

import bounded_controls as bounded
import controls

HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[2]
BHERE=OWNER/'experiments/hir-options-hash/compiler-build-01'
FAILED=OWNER/'.work/hir-options-hash-compiler-build-01'
FIXTURE=bounded.NAMESPACE
WORK=bounded.EVIDENCE
sys.path.insert(0,str(BHERE))
spec=importlib.util.spec_from_file_location('workspace_control_original_build',BHERE/'build.py')
b=importlib.util.module_from_spec(spec);sys.modules[spec.name]=b;spec.loader.exec_module(b)
m=b.m
owned=bounded.owned
D2=b.S/'build'/m.HOST/'stage0'

def read(path):return m.read(path)
def sha(path):return m.sha(path)
def write(path,value):owned.write(path,value)

def failed_history():
    terminal=read(FAILED/'receipt.json');plan=read(BHERE/'plan.json')
    assert terminal['status']=='failed' and terminal['compiler_stages_completed']==0
    assert terminal['error']=="AssertionError('unexpected compiler-stage return code')"
    assert len(terminal['commands'])==3 and len(plan['children'])==25
    previous=terminal['admitted_at']
    for index,(reference,expected) in enumerate(zip(terminal['commands'],plan['children'][:3],strict=True)):
        directory=FAILED/'commands'/f'{index:03}';path=directory/'receipt.json';child=read(path)
        assert reference['path']==str(path) and reference['sha256']==sha(path)
        assert reference['command']==child['command']==expected['argv']
        assert child['cwd']==str(b.S) and child['environment']==expected['environment']
        assert reference['pid']==child['pid'] and child['supervisor_pid']==terminal['pid']
        assert previous<=child['started_at']<=child['finished_at']<=terminal['finished_at'];previous=child['finished_at']
        assert child['returncode']==(1 if index==2 else 0)
        assert child['status']==('failed' if index==2 else 'finished')
        for stream in ['stdout','stderr']:assert sha(directory/stream)==child[stream+'_sha256']
    raw=(FAILED/'commands/002/stderr').read_text()
    assert "current package believes it's in a workspace when it's not" in raw
    assert 'current:   '+str(b.S/'src/bootstrap/Cargo.toml') in raw
    assert 'workspace: '+str(OWNER/'Cargo.toml') in raw
    assert not (FAILED/'compiled.json').exists()
    return terminal,plan

def providers(build_plan):
    # Archive-bound executable/library bytes are separate from new extraction
    # bookkeeping (stamps/manifests). No old binary may substitute for D2.
    seeded={}
    for seed in build_plan['metadata_plan']['seeds'].values():
        if not seed['active'] or seed.get('output_root')!='stage0':continue
        for name,row in seed['members'].items():
            path=D2/name
            if row['kind']=='file':
                assert path.resolve(strict=True)==path and stat.S_ISREG(path.lstat().st_mode)
                assert sha(path)==row['sha256'];seeded[str(path)]=dict(kind='file',**m.file(path))
            else:
                assert path.is_symlink() and os.readlink(path)==row['target']
                seeded[str(path)]=dict(kind='link',target=row['target'],stamp=m.stamp(path))
    assert len(seeded)==85
    closures={}
    for name,binary in [('stage0-cargo','cargo'),('stage0-rustc','rustc')]:
        requests=[];closure=m.planned_closure(D2/'bin'/binary,requests,build_plan['environment'])
        assert closure['identity']==build_plan['new_closure_identities'][name]
        assert str(D2/'bin'/binary) in seeded
        for library in closure['identity']['libraries']:
            path=library['resolved'];assert path in seeded and seeded[path]['sha256']==library['sha256']
        closures[name]=dict(**closure,static_parser_requests=requests,
            qualification='Pure current-byte Mach-O decoding equals admitted old closure after the exact owned-path remap; no new otool or dynamic-loader probe executed.')
    return dict(seed_files=seeded,all_stage0_files=b.output_files(D2),closures=closures)

class Stage:
    def __init__(self,digest):
        assert sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==OWNER
        assert sha(HERE/'inputs.json')==digest
        self.freeze=read(HERE/'inputs.json');assert sha(HERE/'plan.json')==self.freeze['plan_sha256']
        self.plan=read(HERE/'plan.json');self.environment=dict(os.environ)
        assert str(Path(sys.executable).resolve(strict=True))==self.freeze['python']
        expected=self.freeze['environment'];extra=set(self.environment)-set(expected)
        assert all(self.environment.get(k)==v for k,v in expected.items()) and extra<={'__CF_USER_TEXT_ENCODING'}
        if extra:
            cf=self.environment['__CF_USER_TEXT_ENCODING'].split(':')
            assert len(cf)==3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})',v) for v in cf)
            assert int(cf[0],16 if cf[0].lower().startswith('0x') else 10)==os.getuid()==501
        assert not WORK.exists() and not WORK.is_symlink();WORK.mkdir();(WORK/'commands').mkdir()
        self.record=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),commands=[],compiler_builds=0)
        self.save()
    def save(self):write(WORK/'receipt.json',self.record)
    def guard(self,full):
        assert dict(os.environ)==self.environment
        assert sha(b.MHERE/'inputs.json')==self.plan['metadata_inputs_sha256']
        original=read(b.MHERE/'inputs.json')
        m.guard(self.plan['metadata_plan'],original,full)
        for name,row in self.freeze['files'].items():
            path=Path(name);assert path.resolve(strict=True)==path and m.stamp(path)==row['stamp'],path
            if full:assert sha(path)==row['sha256'],path
        for name,row in self.plan['providers']['all_stage0_files'].items():
            path=D2/name
            if row['kind']=='file':
                assert path.resolve(strict=True)==path and m.stamp(path)==row['stamp']
                if full:assert sha(path)==row['sha256']
            else:assert path.is_symlink() and m.stamp(path)==row['stamp'] and os.readlink(path)==row['target'] and str(path.resolve(strict=True))==row['resolved']
        for closure in self.plan['providers']['closures'].values():assert m.loaders.library_state(closure['identity'])==closure['state']
        for module in list(sys.modules.values()):
            path=getattr(module,'__file__',None)
            if path and path.startswith('/Users/danluu/dev/'):
                assert str(Path(path).resolve(strict=True)) in self.freeze['files'] or str(Path(path).resolve(strict=True)) in original['files'],path
    def invoke(self,label,argv,cwd,env,expected):
        row=self.plan['children'][len(self.record['commands'])]
        assert row==dict(label=label,argv=argv,cwd=str(cwd),environment=env,expected_returncode=expected)
        self.guard(False);output=WORK/'commands'/f'{len(self.record["commands"]):03}'
        try:bounded.run(argv,cwd=cwd,environment=env,output=output,canonical_fd=self.lockfd,expected=(expected,))
        finally:
            path=output/'receipt.json'
            if path.exists():self.record['commands'].append(dict(label=label,path=str(path),sha256=sha(path),pid=read(path).get('pid')));self.save()
        self.guard(False)
        return (output/'stdout').read_bytes(),(output/'stderr').read_bytes()
    def run(self):
        try:
            with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
                self.lockfd=fd;self.record.update(status='running',admitted_at=time.time(),free_bytes_before=owned.disk(OWNER,16));self.save()
                self.guard(True);failed_history();assert not FIXTURE.exists() and not FIXTURE.is_symlink()
                result=controls.exercise(cargo=D2/'bin/cargo',rustc=D2/'bin/rustc',work=FIXTURE,environment=self.plan['environment'],invoke=self.invoke)
                assert len(self.record['commands'])==result['metadata_commands']==6 and result['compiler_builds']==0
                self.guard(True)
                assert providers(read(BHERE/'plan.json'))==self.plan['providers']
                write(WORK/'controls.json',result)
                self.record.update(status='passed',controls_passed=6,controls_sha256=sha(WORK/'controls.json'),free_bytes_after=owned.disk(OWNER,9))
        except BaseException as error:self.record.update(status='failed',error=repr(error));raise
        finally:self.record['finished_at']=time.time();self.save()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True);args=parser.parse_args();Stage(args.inputs_sha256).run()
if __name__=='__main__':main()
