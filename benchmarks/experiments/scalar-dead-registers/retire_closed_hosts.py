"""Retire exact completed runtime host intermediates; preserve all other bytes."""
from pathlib import Path
import json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write,require_space
from reclaim_workflow_objects import files,identity,no_open_files
NAME='closed-runtime-host-intermediates-retirement-04'
TARGETS={'native-memory-words-annotated-01': [['.work/native-memory-words-01/active-command.json', '.work/native-memory-words-01/active-command.json']], 'scalar-frame-cost-01': [['.work/scalar-frame-cost-01/active-command.json', '.work/scalar-frame-cost-01/active-command.json']], 'packed-native-cache-reproduction-01': [['.work/packed-native-cache-reproduction-01/active-command.json', '.work/packed-native-cache-reproduction-01/active-command.json']], 'scalar-packed-cache-01': [['.work/scalar-packed-cache-build-01/active-command.json', '.work/scalar-packed-cache-build-01/active-command.json']], 'allocation-budget-c-boundaries-01': [['.work/allocation-budget-c-boundaries-01/active-command.json', '.work/allocation-budget-c-boundaries-01/active-command.json']], 'scalar-promotion-entry-01': [['.work/scalar-promotion-entry-build-01/active-command.json', '.work/scalar-promotion-entry-build-01/active-command.json']], 'scalar-frame-01': [['.work/scalar-frame-probe-01/active-command.json', '.work/scalar-frame-probe-01/active-command.json']], 'native-call-oracle-baseline-01': [['.work/native-call-fresh-baseline-01/active-command.json', '.work/native-call-fresh-baseline-01/active-command.json']], 'native-call-error-baseline-02': [['.work/native-call-error-baseline-02/active-command.json', '.work/native-call-error-baseline-02/active-command.json']], 'cast-width-observation-01': [['.work/cast-width-observation-01/active-command.json', '.work/cast-width-observation-01/active-command.json']], 'virtual-register-compaction-artifacts-01': [['.work/virtual-register-compaction-artifacts-01/active-command.json', '.work/virtual-register-compaction-artifacts-01/active-command.json']], 'local-memory-forwarding-reproduction-01': [['.work/local-memory-forwarding-reproduction-01/active-command.json', '.work/local-memory-forwarding-reproduction-01/active-command.json']], 'call-boundary-observation-01': [['.work/call-boundary-observation-01/active-command.json', '.work/call-boundary-observation-01/active-command.json']], 'allocation-budget-c-boundaries-02': [['.work/allocation-budget-c-boundaries-02/active-command.json', '.work/allocation-budget-c-boundaries-02/active-command.json']], 'scalar-frame-integration-01': [['.work/scalar-frame-dense-integration-01/active-command.json', '.work/scalar-frame-dense-integration-01/active-command.json']], 'scalar-packed-cache-reproduction-01': [['.work/scalar-packed-cache-reproduction-01/active-command.json', '.work/scalar-packed-cache-reproduction-01/active-command.json']], 'scalar-promotion-weighted-01': [['.work/scalar-promotion-weighted-01/active-command.json', '.work/scalar-promotion-weighted-01/active-command.json']], 'scalar-promotion-register-zero-01': [['.work/scalar-promotion-register-zero-01/active-command.json', '.work/scalar-promotion-register-zero-01/active-command.json']], 'native-register-tool-pair-01': [['.work/native-register-tool-pair-01/active-command.json', '.work/native-register-tool-pair-01/active-command.json']]}

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        protected={};targets=[];qualifications=[];raws=set()
        def bind(path):
            assert path.resolve(strict=True)==path and path.is_file(),path
            protected[str(path.relative_to(ROOT))]=sha(path)
            return json.loads(path.read_text()) if path.suffix=='.json' else None
        for name,refs in TARGETS.items():
            assert Path(name).name==name
            target=ROOT/'.work/diagnostic-builds'/name
            assert target.resolve(strict=True)==target and target.is_dir()
            assert target!=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
            commands=[];checks=[]
            for record_name,terminal_name in refs:
                record=ROOT/record_name;terminal=ROOT/terminal_name
                assert record.parent==terminal.parent and record.parent.parent==ROOT/'.work'
                rows=bind(record);status=bind(terminal)
                if isinstance(rows,dict):rows=[rows]
                assert status['status']=='finished' and type(status['returncode'])==int
                cwd=Path(status['cwd']);assert cwd.is_relative_to(ROOT) and cwd.is_dir()
                assert not cwd.is_relative_to(ROOT/'.work/publication-main')
                pids=[status[k] for k in ['pid','parent_pid','child_pid','supervisor_pid'] if k in status]
                assert pids
                check=subprocess.run(['ps','-p',','.join(map(str,pids)),'-o','pid,ppid,lstart,tty,command'],text=True,capture_output=True)
                assert check.returncode in [0,1] and not check.stderr
                assert not any(record.parent.name in line for line in check.stdout.splitlines()[1:])
                checks.append(dict(terminal=terminal_name,returncode=status['returncode'],process_inspection=check.stdout))
                matched=[]
                for row in rows:
                    if not isinstance(row,dict):continue
                    cmd=row.get('command',[])
                    if '--target-dir' not in cmd:continue
                    actual=Path(cmd[cmd.index('--target-dir')+1])
                    if not actual.is_absolute():actual=ROOT/actual
                    if actual!=target:continue
                    assert type(row.get('returncode'))==int
                    assert any(Path(part).name=='cargo' for part in cmd[:2]),cmd
                    # Older direct Cargo captures selected Cargo.toml in their
                    # recorded cwd. Require that exact file; do not guess by
                    # searching parent directories or changing any source.
                    manifest=Path(cmd[cmd.index('--manifest-path')+1]) if '--manifest-path' in cmd else cwd/'Cargo.toml'
                    if not manifest.is_absolute():manifest=cwd/manifest
                    assert manifest.is_relative_to(ROOT) and manifest.is_file(),manifest
                    assert not manifest.is_relative_to(ROOT/'.work/publication-main')
                    bind(manifest);matched.append(row)
                assert matched,(target,record)
                commands+=matched;raws.add(record.parent)
            targets.append(target)
            qualifications.append(dict(target=str(target.relative_to(ROOT)),completed_host_commands=len(commands),
                recorded_exit_codes=[r['returncode'] for r in commands],checks=checks))
        # Source copies, raw outputs and all target executables are retained.
        # This does not reinterpret a failed historical test as a passing one.
        for raw in sorted(raws):
            for p in files(raw):bind(p)
        inventory=[];open_checks=[]
        for target in targets:
            open_checks.append(no_open_files(target))
            for p in files(target):
                key=str(p.relative_to(ROOT));before=identity(p);assert p.stat().st_uid==os.getuid()
                digest=sha(p);assert identity(p)==before
                relative=p.relative_to(target)
                eligible=(relative.parts[0] in ['debug','release'] and p.suffix in ['.o','.rlib','.rmeta']
                    and not before['mode']&0o111 and key not in protected)
                if eligible:inventory.append(dict(path=key,**before,sha256=digest))
                else:protected[key]=digest
        assert inventory and all(sha(ROOT/p)==h for p,h in protected.items())
        if '--inspect' in sys.argv:
            print(json.dumps(dict(targets=len(targets),files=len(inventory),logical_bytes=sum(r['bytes'] for r in inventory),
                protected_files=len(protected),raw_histories=len(raws))));return
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'inventory.json',inventory);write(work/'protected.json',protected)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            script_sha256=sha(Path(__file__)),qualifications=qualifications,open_checks=open_checks,
            inventory_sha256=sha(work/'inventory.json'),protected_sha256=sha(work/'protected.json'),
            scope='Only non-executable .o/.rlib/.rmeta in 19 exact completed runtime host targets. All captured host commands have terminal exit codes; failures remain failures. Preserve raw histories/source copies and every other target file. No shared target, installed tool, guest bytecode, private-workload cache or peer worktree.'))
        before=shutil.disk_usage(ROOT).free
        for target in targets:no_open_files(target)
        for row in inventory:
            p=ROOT/row['path'];assert identity(p)=={k:row[k] for k in ['device','inode','bytes','mode','mtime_ns']}
            assert sha(p)==row['sha256'];p.unlink()
        assert all(sha(ROOT/p)==h for p,h in protected.items())
        assert all(not (ROOT/r['path']).exists() for r in inventory)
        result=ROOT/'results'/NAME;result.mkdir(exist_ok=False)
        summary=dict(status='passed',targets=len(targets),raw_histories=len(raws),files_removed=len(inventory),
            logical_bytes_removed=sum(r['bytes'] for r in inventory),protected_files=len(protected),all_protected_hashes_unchanged=True,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),inventory_sha256=sha(work/'inventory.json'),
            protected_sha256=sha(work/'protected.json'),free_before=before,free_after=shutil.disk_usage(ROOT).free,performance_measurement=False)
        write(result/'summary.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
