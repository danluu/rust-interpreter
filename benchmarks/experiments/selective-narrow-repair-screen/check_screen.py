"""Freeze protocol controls and reuse the exact complete Python build checks."""
import argparse,json,os,re,sys
from pathlib import Path
import screen
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
def read(p):return json.loads(p.read_text())
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True);args=parser.parse_args()
    assert re.fullmatch(r'selective-narrow-repair-screen-protocol-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        build_path=ROOT/'results/selective-narrow-repair-build-01/summary.json';build=read(build_path)
        assert build['status']=='passed' and build['python']==dict(discovered=449,passed=427,skipped=22)
        build_closed=build_path.with_name('closure.json');closed=read(build_closed)
        assert closed['status']=='closed' and closed['all_hashes_verified'] and closed['summary_sha256']==sha(build_path)
        raw=ROOT/build['raw'];plan=read(raw/'plan.json');records=read(raw/'records.json')
        assert sha(raw/'plan.json')==build['plan_sha256'] and sha(raw/'records.json')==build['records_sha256']
        record,=[r for r in records if r['label']=='python'];assert record['returncode']==0
        paths=[build_path,build_closed,raw/'plan.json',raw/'records.json']
        for stream in ['stdout','stderr']:
            p=raw/('python.'+stream);assert sha(p)==record[stream+'_sha256'];paths.append(p)
        source_paths=list((ROOT/'scripts').glob('*.py'))+list((ROOT/'tests').glob('*.py'))
        assert all(sha(p)==plan['frozen'][str(p.relative_to(ROOT))] for p in source_paths)
        paths+=source_paths+list(Path(__file__).parent.glob('*.py'))+list(Path(__file__).parent.glob('*.md'))
        controls=[ROOT/'results'/n/'summary.json' for n in ['scratch-memory-values-build-02',
            'scratch-scalar-main-qualification-01','scratch-memory-values-qualification-01',
            'scratch-memory-values-full-01','scratch-memory-values-parser-01']]
        assert screen.validate_baseline(*map(read,controls));paths+=controls
        hashes={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False);write(work/'inputs.json',hashes)
        child,out,err=capture([sys.executable,'-m','unittest','test_screen','test_native_observation','-v'],
            cwd=Path(__file__).parent,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work/'active.json',receipt=dict(stage='selective full-width interpreter repair screen protocol'))
        (work/'stdout').write_text(out);(work/'stderr').write_text(err)
        write(work/'record.json',dict(pid=child.pid,returncode=child.returncode,stdout_sha256=sha(work/'stdout'),stderr_sha256=sha(work/'stderr')))
        assert child.returncode==0 and 'Ran 16 tests' in err and err.rstrip().endswith('OK'),err
        assert all(sha(ROOT/p)==h for p,h in hashes.items())
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',tests=13,observation_controls=3,launcher_tests=449,launcher_skipped=22,
            commands=1,launcher_commands_reused=1,raw=str(work.relative_to(ROOT)),inputs_sha256=sha(work/'inputs.json'),
            stdout_sha256=sha(work/'stdout'),stderr_sha256=sha(work/'stderr'),record_sha256=sha(work/'record.json'),
            reused_launcher_summary=str(build_path.relative_to(ROOT)),guest_commands=0,performance_measurement=False))
        print('PASS 13 protocol / 3 observation controls; reused exact 449 Python tests (22 skips)',flush=True)
if __name__=='__main__':main()
