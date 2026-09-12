"""Exact historical public workflow snapshots, never scheduled timing inputs."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from reclaim_workflow_objects import corpus_member,no_open_files
from verify_repeated_workflow import verify

RUNS=['resumable-copy-original-e2e-01','resumable-e2e-01',
      'resumable-bulk-e2e-01','resumable-bulk-e2e-02','persistent-e2e-01',
      'native-region-e2e-01','bounded-native-e2e-01']


def inputs():
    values=[];proofs=[Path(__file__),ROOT/'scripts/verify_repeated_workflow.py',
                      ROOT/'scripts/reclaim_workflow_objects.py'];origins={};roots=[]
    for parent in RUNS:
        run=parent+'-token-phrase';work=ROOT/'.work/runs'/run
        report_path=ROOT/'results'/run/'summary.json';report=json.loads(report_path.read_text())
        corpus_path=ROOT/'results'/parent/'summary.json';corpus=json.loads(corpus_path.read_text())
        corpus_member(corpus,parent,run,report_path,report)
        assert report['project']=='fre' and report['raw']==str(work.relative_to(ROOT))
        assert work.resolve(strict=True)==work
        verification=report_path.with_name('verification.json')
        assert verify(report)==json.loads(verification.read_text())
        active=work/'active-command.json';a=json.loads(active.read_text())
        assert a['status']=='finished'
        records=work/'records.json';rows=json.loads(records.read_text())
        artifacts=[artifact for row in rows for artifact in row.get('artifacts',[])]
        assert len(artifacts)==42 and len({a['path'] for a in artifacts})==42
        no_open_files(work)
        for artifact in artifacts:
            path=ROOT/artifact['path']
            assert path.is_relative_to(work/'artifacts') and path.suffix=='.rbc'
            assert path.resolve(strict=True)==path and path.stat().st_size==artifact['bytes']
            assert sha(path)==artifact['sha256']
            values.append((path,artifact['sha256'],parent))
            origins[artifact['path']]='historical complete-command artifact digest'
        proofs += [report_path,corpus_path,verification,active,records,work/'source-transitions.json']
        proofs += [p for p in [work/'check-records.json',work/'case.json'] if p.exists()]
        roots.append(str(work))
    process=subprocess.run(['ps','-axo','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
    assert process.returncode==0 and not process.stderr
    assert not any(any(root in line for root in roots) for line in process.stdout.splitlines()[1:])
    return values,proofs,origins
