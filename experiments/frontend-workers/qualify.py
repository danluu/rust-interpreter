#!/usr/bin/env python3
"""Prepared but unrun frontend-worker correctness history; no timing verdict."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock, lock_wait_seconds
from frontend_workers import COMPILER_COMMIT, require_capability
from interpreter import TOOLCHAIN, installed_tools, require_export_option
from std_mir import FLAGS, POLICY, stamp
from workflow_io import SourceEdit, capture, require_space, write_json

QUALIFICATION_POLICY = 'frontend-workers-qualification-v1'

ERRORS = {
    'type': ('fn unused() { let _: u32 = false; }\n', 'E0308'),
    'borrow': ('fn unused() { let x = vec![1]; let y = &x; drop(x); println!("{:?}", y); }\n', 'E0505'),
    'constant': ('const UNUSED: u32 = panic!("must be checked");\n', 'E0080'),
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compiler_environment(environment):
    exact = {'PATH', 'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'CARGO_BUILD_RUSTC',
             'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUSTC_BOOTSTRAP', 'RUSTUP_TOOLCHAIN',
             'CARGO_INCREMENTAL', 'CARGO_BUILD_TARGET', 'CARGO_TARGET_DIR', 'CARGO_HOME',
             'CARGO_BUILD_JOBS', 'CARGO_TERM_COLOR', 'CARGO_TERM_VERBOSE'}
    return {name: value for name, value in environment.items()
            if name in exact or name.startswith(('CARGO_PROFILE_', 'RUST_INTERP_'))
            or name.endswith('RUSTFLAGS')}


def prepared_std_unchanged(work, ready, host):
    artifacts = ready.get('artifacts')
    require(isinstance(artifacts, dict) and artifacts, 'prepared std MIR inventory is empty')
    library = work/'sysroot/lib/rustlib'/host/'lib'
    expected = set()
    for name, value in artifacts.items():
        path = work/name
        require(path.parent == library and path.suffix == '.rmeta' and not path.is_symlink(),
                'prepared std MIR inventory names an unexpected artifact')
        require(path.is_file() and stamp(path) == value['stamp'] and sha(path) == value['sha256'],
                'prepared std MIR artifact changed')
        expected.add(path.name)
    require(expected == {path.name for path in library.iterdir()}, 'prepared std MIR inventory is incomplete')
    for crate in ['core', 'alloc', 'std', 'test', 'proc_macro']:
        require(len(list(library.glob('lib'+crate+'-*.rmeta'))) == 1,
                'prepared std MIR lacks a unique '+crate)


def diagnostics(text):
    records = []
    for line in text.splitlines():
        if not line.startswith('{'):
            continue
        row = json.loads(line)
        if row.get('$message_type') == 'diagnostic':
            row.pop('rendered', None)
            records.append(row)
    require(records, 'missing structured rustc diagnostics')
    return sorted(json.dumps(row, sort_keys=True) for row in records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--lock-wait-seconds', type=lock_wait_seconds, default=600)
    args = parser.parse_args()
    require(args.lock.is_absolute() and args.lock.is_file()
            and args.lock.resolve(strict=True) == args.lock, 'qualification requires an existing explicit campaign lock')
    run = args.run_dir.resolve()
    require(not run.exists() and run.parent.is_dir(), 'run directory must be new in an existing parent')
    try:
        qualify(args,run)
    except BaseException as error:
        if run.is_dir():
            write_json(run/'failure.json',dict(status='failed',error=str(error),finished_at=time.time()))
        raise


def qualify(args,run):
    tools,key = installed_tools(args.tool_key)
    manifest = json.loads((tools/'ready.json').read_bytes())
    caps = json.loads((tools/'capabilities.json').read_bytes())
    require_export_option(tools,key,'frontend-workers-v1')
    require_export_option(tools,key,'function-cache-auto')
    require_capability(tools,caps,manifest)
    source_files = [ROOT/'Cargo.toml',ROOT/'Cargo.lock',ROOT/'rust-toolchain.toml',
                    *sorted((ROOT/'.cargo').rglob('*')),*sorted((ROOT/'scripts').glob('*.py')),
                    *sorted((ROOT/'crates').rglob('*')),
                    *sorted((Path(__file__).parent/'fixture').rglob('*'))]
    frozen = {str(path):sha(path) for path in source_files if path.is_file()}
    frozen[str(Path(__file__).resolve())] = sha(Path(__file__))
    run.mkdir()
    (run/'logs').mkdir()
    (run/'artifacts').mkdir()
    (run/'cache').mkdir()
    plan = dict(status='waiting', policy=QUALIFICATION_POLICY, owner=str(ROOT),
                supervisor_pid=os.getpid(), parent_pid=os.getppid(),
                argv=sys.argv, cwd=os.getcwd(), started_at=time.time(), tool_key=key,
                tools=manifest, capability=caps, frozen=frozen, lock=str(args.lock.resolve()),
                scope='correctness only; no performance conclusion', jobs=2)
    write_json(run/'plan.json',plan)
    environment = {k:v for k,v in os.environ.items() if not k.startswith('RUST_INTERP_')}
    environment.update(RUST_INTERP_LAUNCH_STATS='1',CARGO_TERM_COLOR='never',CARGO_TERM_VERBOSE='true')
    records = []

    def invoke(label, command, env=environment):
        require_space(run,8)
        inputs = [run/'fixture/shared/src/lib.rs',run/'fixture/src/lib.rs']
        if '-native-diagnostic-' in label:inputs.append(run/'diagnostic.rs')
        sources = {str(p.relative_to(run)):sha(p) for p in inputs if p.is_file()}
        child,stdout,stderr = capture(command,cwd=run,env=env,
            receipt_path=run/'logs'/f'{label}-process.json',
            receipt=dict(label=label,environment=compiler_environment(env),sources=sources))
        require(all(sha(run/name)==value for name,value in sources.items()),'qualification source changed during child')
        row = dict(label=label,command=command,returncode=child.returncode,stdout=stdout,stderr=stderr,sources=sources)
        write_json(run/'logs'/f'{label}.json',row)
        records.append(row)
        return row

    with args.lock.open('a') as lock:
        acquire_lock(lock,args.lock_wait_seconds)
        require(all(sha(Path(path)) == digest for path,digest in frozen.items()),'source changed before admission')
        compiler_path = invoke('compiler-path',['rustup','which','--toolchain',TOOLCHAIN,'rustc'])
        require(compiler_path['returncode']==0,'pinned compiler lookup failed')
        rustc = Path(compiler_path['stdout'].strip())
        version = invoke('compiler-version',[str(rustc),'-vV'])
        require(version['returncode']==0 and 'commit-hash: '+COMPILER_COMMIT in version['stdout'],
                'compiler is not the qualified stock pin')
        host = next(line[6:] for line in version['stdout'].splitlines() if line.startswith('host: '))
        require(host.startswith(('aarch64-','x86_64-')),'assembly control requires a qualified host architecture')
        source = rustc.parent.parent/'lib/rustlib/src/rust/library'
        identity = dict(policy=POLICY,compiler=version['stdout'],target=host,flags=FLAGS,
                        lock_sha256=sha(source/'Cargo.lock'))
        std_key = hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
        std_work = ROOT/'.work/std-mir'/std_key
        ready = json.loads((std_work/'ready.json').read_bytes())
        require(ready['owner']==str(ROOT) and ready['identity']==identity,'prepare matching std MIR separately first')
        prepared_std_unchanged(std_work,ready,host)
        # Requiring ready metadata avoids invoking the stock four-job preparation
        # path in this two-job qualification. The launcher policy itself is unchanged.
        plan.update(status='running',rustc=str(rustc),rustc_sha256=sha(rustc),std_key=std_key,
                    std_ready_sha256=sha(std_work/'ready.json'))
        write_json(run/'plan.json',plan)
        project = run/'fixture'
        shutil.copytree(Path(__file__).parent/'fixture',project)
        shared = project/'shared/src/lib.rs'
        library = project/'src/lib.rs'
        shared_original,library_original = shared.read_bytes(),library.read_bytes()
        workspace_paths = {}

        def launch(label, workers, *, expected=20, entry='answer', error=None):
            command = [sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(project/'Cargo.toml'),
                '--package','frontend-worker-fixture','--tool-key',key,'--std-mir','--jobs','2',
                '--function-cache','auto','--frontend-workers',str(workers),
                '--workspace-cache-root',str(run/'cache'),'--entry',entry]
            row = invoke(f'{label}-{workers}',command)
            if error:
                require(row['returncode']!=0 and error in row['stderr'] and not row['stdout'].strip(),
                        'failed compilation was accepted or guest output appeared')
                require('rust-interp-launch: ' not in row['stderr'],'failure reported successful launch')
                return None
            require(row['returncode']==0 and row['stdout'].strip()==str(expected),'wrong checked guest result')
            reports = [json.loads(line.removeprefix('rust-interp-launch: ')) for line in row['stderr'].splitlines()
                       if line.startswith('rust-interp-launch: ')]
            require(len(reports)==1,'missing unique launch receipt')
            report = reports[0]
            require(report['frontend_workers']['workers']==workers and report['tool_key']==key,
                    'worker/tool identity differs')
            path = Path(report['workspace_path'])
            require(path.is_relative_to(run/'cache'),'workspace escaped the owned cache')
            require(workspace_paths.setdefault(workers,path)==path,'workspace identity changed across edits')
            artifact = Path(report['artifact_path'])
            require(artifact.is_relative_to(path/'target') and sha(artifact)==report['artifact_sha256'],
                    'selected artifact digest or location differs')
            payload = artifact.read_bytes()
            (run/'artifacts'/f'{label}-{workers}.rbc').write_bytes(payload)
            return payload

        with SourceEdit(shared,shared_original) as shared_edit, SourceEdit(library,library_original) as library_edit:
            original = None
            for phase,value in [('cold',3),('edited',7),('restored',3)]:
                shared_edit.replace(f'pub fn value() -> u64 {{ {value} }}\n'.encode())
                pair = [launch(phase,count,expected=11+3*value) for count in [1,2]]
                require(pair[0]==pair[1],phase+' bytecode differs between worker counts')
                if phase=='cold':original=pair[0]
                elif phase=='edited':require(pair[0]!=original,'edit did not change bytecode')
                else:require(pair[0]==original,'restoration changed original bytecode')
            require(workspace_paths[1]!=workspace_paths[2],'worker modes share a Cargo cache')
            for label,(bad,code) in ERRORS.items():
                library_edit.replace(library_original+bad.encode())
                for count in [1,2]:launch(label,count,error=code)
                library_edit.replace(library_original)
                for count in [1,2]:require(launch(label+'-restored',count)==original,'post-error bytecode differs')
                diagnostic_source = run/'diagnostic.rs'
                diagnostic_source.write_text('pub fn good() -> u32 { 1 }\n'+bad)
                messages = []
                for count in [1,2]:
                    env = dict(environment,RUST_INTERP_FRONTEND_WORKERS=str(count))
                    row = invoke(f'{label}-native-diagnostic-{count}',[str(tools/'rust-interp-rustc-wrapper'),str(rustc),
                        '--crate-name','diagnostic','--crate-type','rlib','--emit=metadata','--error-format=json',
                        '-Cincremental='+str(run/f'diagnostic-{count}'),'-o',str(run/f'diagnostic-{count}.rmeta'),
                        str(diagnostic_source)],env)
                    require(row['returncode']!=0 and code in row['stderr'],'native diagnostic control was accepted')
                    messages.append(diagnostics(row['stderr']))
                require(messages[0]==messages[1],'structured diagnostics differ across worker counts')
            for count in [1,2]:launch('assembly-rejection',count,entry='assembly',error='unsupported terminator InlineAsm')
            for count in [1,2]:require(launch('assembly-restored',count)==original,'assembly selection affected restored bytecode')
        require(all(sha(Path(path))==digest for path,digest in frozen.items()),'qualification sources changed')
        installed_tools(key)
        require(sha(std_work/'ready.json')==plan['std_ready_sha256'],'std preparation identity changed')
        prepared_std_unchanged(std_work,ready,host)
        write_json(run/'result.json',dict(status='passed',policy=QUALIFICATION_POLICY,tool_key=key,commands=len(records),
            workspaces={str(k):str(v) for k,v in workspace_paths.items()},
            logs={str(p.relative_to(run)):sha(p) for p in sorted((run/'logs').glob('*.json'))},
            original_artifact_sha256=hashlib.sha256(original).hexdigest(),
            note='Correctness qualification only; timings are process receipts, not a performance comparison.'))


if __name__ == '__main__':
    main()
