"""Close the six completed primitive/nested/wiring runs with bound source blobs."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write

RUNS=[f'tree-bridge-{stage}-{number:02}' for stage in ['primitives','nested','wiring'] for number in [1,2]]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True);args=parser.parse_args()
    assert args.run_id=='tree-bridge-focused-closure-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        objects={};trees={};evidence={};runs=[]
        for run in RUNS:
            raw=ROOT/'.work'/run;outer=ROOT/'.work/experiments'/run;result=ROOT/'results'/run
            terminal=json.loads((result/'terminal.json').read_text());summary=json.loads((result/'summary.json').read_text())
            assert terminal==json.loads((outer/'status.json').read_text())
            assert terminal['status']=='finished' and terminal['owner']==str(ROOT) and terminal['cwd']==str(ROOT)
            assert terminal['returncode']==(0 if run.endswith('02') else 1)
            assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
            assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
            plan=json.loads((raw/'plan.json').read_text());revision=plan['source_revision']
            if revision not in trees:
                data=subprocess.check_output(['git','ls-tree','-r','-z',revision],cwd=ROOT)
                trees[revision]={entry.split(b'\t',1)[1].decode():entry.split(b'\t',1)[0].split()[2].decode()
                    for entry in data.split(b'\0') if entry}
            bindings={}
            for path,digest in plan['frozen'].items():
                blob=trees[revision][path]
                if blob not in objects:objects[blob]=subprocess.check_output(['git','cat-file','blob',blob],cwd=ROOT)
                import hashlib
                assert hashlib.sha256(objects[blob]).hexdigest()==digest,(run,path)
                bindings[path]=dict(sha256=digest,git_blob=blob)
            for directory in [raw,outer,result]:
                for path in directory.iterdir():
                    if path.is_file():
                        assert not path.is_symlink()
                        evidence[str(path.relative_to(ROOT))]=sha(path)
            runs.append(dict(run=run,source_revision=revision,status=summary['status'],bindings=bindings))
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False)
        manifest=dict(runs=runs,evidence=evidence,source_objects=len(objects),controller_sha256=sha(Path(__file__)),
            note='Every frozen source matches its recorded Git revision; archives contain the exact source blobs and all six terminal command receipts.')
        write(out/'manifest.json',manifest)
        archive=out/'evidence.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            for path,digest in evidence.items():
                assert sha(ROOT/path)==digest
                tar.add(ROOT/path,arcname=path,recursive=False)
            for blob,body in objects.items():
                info=tarfile.TarInfo('sources/'+blob);info.size=len(body);info.mode=0o600
                tar.addfile(info,io.BytesIO(body))
            tar.add(out/'manifest.json',arcname='manifest.json',recursive=False)
        with tarfile.open(archive,'r:gz') as tar:
            for path,digest in evidence.items():
                assert hashlib.sha256(tar.extractfile(path).read()).hexdigest()==digest
            for blob,body in objects.items():assert tar.extractfile('sources/'+blob).read()==body
        write(out/'summary.json',dict(status='passed',runs=len(runs),source_objects=len(objects),
            source_bindings=sum(len(run['bindings']) for run in runs),evidence_files=len(evidence),
            manifest_sha256=sha(out/'manifest.json'),archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,
            guest_commands=0,performance_measurement=False))
        print('PASS',len(runs),'runs;',len(objects),'source blobs;',archive.stat().st_size,'archive bytes',flush=True)

if __name__=='__main__':main()
