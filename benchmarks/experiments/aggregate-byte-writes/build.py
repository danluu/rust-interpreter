#!/usr/bin/env python3
"""Build an isolated byte-write observer while retaining all current VM/wrapper bytes."""
import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from interpreter import installed_tools
from tool_source_index import index
from verify_repeated_workflow import require

PARENT = '0e94d6d82b4b734e281e5b8c95a55866e5c7b0a8be53be2dafadd410708467ee'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())
def write(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n'); temp.replace(path)
def environment():
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or name in [
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
            'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']:
            env.pop(name)
    env['CARGO_TERM_COLOR'] = 'never'
    return env
def replace(path, old, new):
    text = path.read_text(); require(text.count(old) == 1, 'injection anchor changed: ' + old[:100])
    path.write_text(text.replace(old, new))


def inject(source):
    frame = source / 'crates/mir-export/src/lower/scalar_frame.rs'
    replace(frame, 'fn plan(shapes: &[(usize, usize)], mut eligible: Vec<bool>, mut events: Vec<Vec<Event>>, successors: &[Vec<usize>]) -> Option<(Vec<Slot>, usize)> {',
        '''fn plan(shapes: &[(usize, usize)], eligible: Vec<bool>, events: Vec<Vec<Event>>, successors: &[Vec<usize>]) -> Option<(Vec<Slot>, usize)> {
    plan_with_eligibility(shapes, eligible, events, successors, None)
}
fn plan_with_eligibility(shapes: &[(usize, usize)], mut eligible: Vec<bool>, mut events: Vec<Vec<Event>>, successors: &[Vec<usize>], eligibility: Option<&mut Vec<bool>>) -> Option<(Vec<Slot>, usize)> {''')
    replace(frame, '    Some((slots, end))', '    if let Some(out) = eligibility { *out = eligible; }\n    Some((slots, end))')
    with frame.open('a') as out: out.write('\n#[path="byte_writes.rs"]\npub(super) mod byte_writes;\n')
    shutil.copy2(HERE / 'observe.rs', frame.with_name('byte_writes.rs'))
    shutil.copy2(HERE / 'tests.rs', frame.with_name('byte_writes_tests.rs'))
    bytecode = source / 'crates/bytecode/src/lib.rs'
    with bytecode.open('a') as out:
        out.write('\n/// Diagnostic snapshot only; share the retained exhaustive operand visitor.\npub fn diagnostic_visit_registers(op: &Op, read: impl FnMut(Reg), write: impl FnMut(Reg)) { registers::visit_registers(op, read, write); }\n')
    lower = source / 'crates/mir-export/src/lower.rs'
    replace(lower, '    trace_function: Option<usize>,',
        '    trace_function: Option<usize>,\n    byte_writes: Vec<scalar_frame::byte_writes::Observation>,')
    replace(lower, '        trace_function: None,', '        trace_function: None,\n        byte_writes: vec![],')
    replace(lower, '    caller_location: Option<Slot>,',
        '    caller_location: Option<Slot>,\n    byte_local_extent: usize,\n    byte_spans: Vec<Vec<Option<(usize, usize)>>>,')
    replace(lower, '            caller_location: None,', '''            caller_location: None,
            byte_local_extent: 0,
            byte_spans: if body.local_decls.len() <= 4096 && body.basic_blocks.iter().map(|b| b.statements.len()+1).sum::<usize>() <= 32768 {
                body.basic_blocks.iter().map(|b| vec![None; b.statements.len()+1]).collect()
            } else { vec![] },''')
    replace(lower, '        scalar_frame::pack(&mut this)?;',
        '        scalar_frame::pack(&mut this)?;\n        this.byte_local_extent = this.frame_size;')
    replace(lower, '            for statement in &block.statements {',
        '            for (statement_index, statement) in block.statements.iter().enumerate() {\n                let emitted_start = self.code.len();')
    replace(lower, '            }\n            match &block.terminator().kind {',
        '                scalar_frame::byte_writes::remember(&mut self, bb.as_usize(), statement_index, emitted_start);\n            }\n            let emitted_start = self.code.len();\n            match &block.terminator().kind {')
    replace(lower, '        }\n        for &index in &self.fixups {',
        '            scalar_frame::byte_writes::remember(&mut self, bb.as_usize(), block.statements.len(), emitted_start);\n        }\n        for &index in &self.fixups {')
    replace(lower, '        scalar_promote::apply(&mut self)?;',
        '        let observed = scalar_frame::byte_writes::capture(&self);\n        self.exporter.byte_writes.push(observed);\n        scalar_promote::apply(&mut self)?;')
    replace(lower, '    scalar_frame::report();',
        '    scalar_frame::byte_writes::report(exporter.byte_writes, &program);\n    scalar_frame::report();')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id, 'invalid run ID')
    work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
    status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
    write(work / 'status.json', status)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            parent = index('aa2f6ea'); require(parent['tool_key'] == PARENT, 'parent source key differs')
            installed, _ = installed_tools(PARENT)
            require(all(sha(ROOT / p) == h for p,h in parent['files'].items()), 'production compiler changed')
            fs = os.statvfs(ROOT); free = fs.f_bavail * fs.f_frsize
            require(free >= 20 * 1024**3, 'insufficient build/export headroom')
            paths = [HERE / n for n in ['build.py', 'observe.rs', 'tests.rs']]
            paths += [ROOT / 'benchmarks/experiments/aggregate-reuse-census/BYTE-WRITES-NEXT.md']
            frozen = {**parent['files'], **{str(p.relative_to(ROOT)):sha(p) for p in paths}}
            source = work / 'tool-source'; source.mkdir()
            data = subprocess.check_output(['git','archive',parent['commit'],'Cargo.toml','Cargo.lock','rust-toolchain.toml','crates','scripts/interpreter.py'],cwd=ROOT)
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                for member in archive:
                    path=Path(member.name); require(not path.is_absolute() and '..' not in path.parts,'invalid archive path')
                    if member.isfile():
                        out=source/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(archive.extractfile(member).read())
                    else: require(member.isdir(),'unexpected archive entry')
            inject(source)
            inputs=[source/'Cargo.toml',source/'Cargo.lock']
            for crate in ['bytecode','mir-export']:
                inputs += sorted((source/'crates'/crate).rglob('*.rs'))
                inputs.append(source/'crates'/crate/'Cargo.toml')
            digest=hashlib.sha256()
            for path in inputs: digest.update(str(path.relative_to(source)).encode()+b'\0'+path.read_bytes())
            key=digest.hexdigest(); copied={str(p.relative_to(source)):sha(p) for p in inputs}
            write(work/'provenance.json',dict(parent_source_commit=parent['commit'],parent_tool_key=PARENT,
                source=str(source.relative_to(ROOT)),copied_inputs=copied,root_frozen=frozen,tool_key=key,
                observed_free_bytes=free,diagnostic_only=True,vm_and_wrapper_copied_from_parent=True))
            def verify():
                require(all(sha(ROOT/p)==h for p,h in frozen.items()),'root input changed')
                require(all(sha(source/p)==h for p,h in copied.items()),'diagnostic input changed')
                require(all(sha(installed/p)==h for p,h in parent['binaries'].items()),'parent binaries changed')
            target=ROOT/'.work/diagnostic-builds'/args.run_id
            records=[];env=environment()
            for action in ['test','build']:
                verify()
                command=['cargo','+nightly-2026-09-08',action,'--release','--locked','--offline','--jobs','2',
                    '--manifest-path',str(source/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-mir-export']
                with (work/(action+'.log')).open('x') as log:
                    child=subprocess.Popen(command,cwd=source,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                    status.update(status='running',child_pid=child.pid,command=command,child_cwd=str(source),child_started_at=time.time())
                    write(work/'status.json',status);code=child.wait()
                records.append(dict(command=command,pid=child.pid,returncode=code,log_sha256=sha(work/(action+'.log'))))
                write(work/'commands.json',records);require(code==0,'diagnostic '+action+' failed')
            tests=(work/'test.log').read_text()
            names=re.findall(r'^test (\S*byte_writes::tests::\S+) \.\.\. ok$',tests,re.M)
            require(len(names)==9 and len(set(names))==9,'missing observer tests')
            counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed;',tests)
            require(counts and all(f=='0' for _,f in counts),'exporter tests incomplete')
            verify()
            destination=ROOT/'.work/interpreter-tools'/key
            binaries=dict(parent['binaries']);binaries['rust-interp-mir-export']=sha(target/'release/rust-interp-mir-export')
            with (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
                fcntl.flock(publication,fcntl.LOCK_EX);destination.mkdir(exist_ok=False)
                for name in binaries:
                    shutil.copy2(target/'release'/name if name=='rust-interp-mir-export' else installed/name,destination/name)
                capability=json.loads(subprocess.check_output([str(destination/'rust-interp-mir-export'),'--rust-interp-capabilities'],env=env,text=True))
                capability.update(tool_key=key,exporter_sha256=binaries['rust-interp-mir-export'])
                write(destination/'capabilities.json',capability)
                write(destination/'source.json',dict(tool_key=key,parent_tool_key=PARENT,source=str(source.relative_to(ROOT)),
                    files=copied,provenance_sha256=sha(work/'provenance.json'),diagnostic_only=True))
                require(all(sha(destination/n)==h for n,h in binaries.items()),'published binary differs')
                write(destination/'ready.json',binaries)
            result=dict(status='passed',tool_key=key,parent_tool_key=PARENT,binaries=binaries,observer_tests=names,
                exporter_test_count=sum(int(n) for n,_ in counts),source=str(source.relative_to(ROOT)),
                provenance=str((work/'provenance.json').relative_to(ROOT)),provenance_sha256=sha(work/'provenance.json'),
                production_change=False,performance_measurement=False,commands=records)
            write(work/'summary.json',result)
            out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',finished_at=time.time(),returncode=0);write(work/'status.json',status)
            print(json.dumps(dict(tool_key=key,observer_tests=len(names),exporter_tests=result['exporter_test_count'])))
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise


if __name__=='__main__':main()
