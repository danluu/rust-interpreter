"""Retire only non-executable intermediates of nine completed own host checks."""
from pathlib import Path
import json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write,require_space
from workspace_check_evidence import workspace_check
from reclaim_workflow_objects import files,identity,no_open_files

NAME='closed-runtime-host-intermediates-retirement-01'
RUNS=['resumable-bulk-release-01','native-region-release-01','bounded-native-release-01',
      'persistent-release-01','resumable-boundary-release-01','allocation-trace-release-01',
      'resumable-release-01','resumable-copy-release-01','native-code-dump-release-01']

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        proofs={};targets=[];qualifications=[]
        for run in RUNS:
            target,bound,qualified=workspace_check(run,sha)
            assert target==ROOT/'.work/diagnostic-builds'/run
            assert qualified['kind']=='completed host workspace check'
            assert target!=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
            proofs.update(bound);targets.append(target)
            qualifications.append(dict(run=run,**qualified))
        rows=[];protected=dict(proofs);opened=[]
        for target in targets:
            opened.append(no_open_files(target))
            for path in files(target):
                key=str(path.relative_to(ROOT));before=identity(path)
                assert path.stat().st_uid==os.getuid()
                digest=sha(path);assert identity(path)==before
                # Installed executables and every externally bound output are
                # protected, including the copies in these completed targets.
                remove=path.suffix in ['.o','.rlib','.rmeta'] and not before['mode']&0o111 and key not in proofs
                if remove:rows.append(dict(path=key,**before,sha256=digest))
                else:protected[key]=digest
        assert rows and all(sha(ROOT/p)==h for p,h in protected.items())
        if '--inspect' in sys.argv:
            print(json.dumps(dict(files=len(rows),logical_bytes=sum(r['bytes'] for r in rows),protected_files=len(protected),targets=len(targets))));return
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'inventory.json',rows);write(work/'protected.json',protected)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            script_sha256=sha(Path(__file__)),qualifications=qualifications,open_checks=opened,
            targets=[str(p.relative_to(ROOT)) for p in targets],inventory_sha256=sha(work/'inventory.json'),
            protected_sha256=sha(work/'protected.json'),scope='Only exact non-executable .o/.rlib/.rmeta in nine completed owned host-check targets. No shared target, installed tool, bytecode, source snapshot, private cache or peer workspace.'))
        free_before=shutil.disk_usage(ROOT).free
        for target in targets:no_open_files(target)
        for row in rows:
            path=ROOT/row['path']
            assert identity(path)=={k:row[k] for k in ['device','inode','bytes','mode','mtime_ns']}
            assert sha(path)==row['sha256'];path.unlink()
        assert all(sha(ROOT/p)==h for p,h in protected.items())
        assert all(not (ROOT/r['path']).exists() for r in rows)
        result=ROOT/'results'/NAME;result.mkdir(exist_ok=False)
        summary=dict(status='passed',files_removed=len(rows),logical_bytes_removed=sum(r['bytes'] for r in rows),
            protected_files=len(protected),all_protected_hashes_unchanged=True,completed_host_checks=len(targets),
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),inventory_sha256=sha(work/'inventory.json'),
            protected_sha256=sha(work/'protected.json'),free_before=free_before,free_after=shutil.disk_usage(ROOT).free,
            performance_measurement=False)
        write(result/'summary.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
