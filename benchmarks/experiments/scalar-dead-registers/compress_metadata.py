"""Losslessly compress closed owned diagnostic metadata; do not retire payloads."""
import hashlib,json,os,stat,subprocess,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/heap-address-bias'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from compression_probe import metadata
NAME='closed-diagnostic-metadata-compression-02'
SELECTION='.work/scalar-dead-registers-metadata-compression-selection.json'
SELECTION_SHA='23598bda2746a587cb611824a1e25676c6f66b40ba46ad2a47ba3a45f614e7ae'

def no_open_file(path):
    r=subprocess.run(['lsof','-Fpn','--',str(path)],text=True,capture_output=True)
    assert r.returncode==1 and not r.stdout and not r.stderr,(path,r.stdout,r.stderr)

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        assert sha(ROOT/SELECTION)==SELECTION_SHA
        selection=json.loads((ROOT/SELECTION).read_text());assert len(selection)==117
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        helper='benchmarks/experiments/heap-address-bias/compression_probe.py'
        proofs={SELECTION:SELECTION_SHA,helper:sha(ROOT/helper)};sources={};completion=[]
        for name,item in selection.items():
            assert Path(name).name==name
            raw=ROOT/'.work'/name;result=ROOT/item['result'];plan=raw/'plan.json'
            assert result.parent.parent==ROOT/'results' and result.name=='summary.json'
            assert sha(result)==hashlib.sha256(subprocess.check_output(['git','show',revision+':'+item['result']])).hexdigest()
            summary=json.loads(result.read_text());assert summary['status'] in ['passed','completed']
            assert ROOT/summary['raw']==raw and json.loads(plan.read_text())['owner']==str(ROOT)
            if 'plan_sha256' in summary:assert sha(plan)==summary['plan_sha256']
            proofs[item['result']]=sha(result);proofs[str(plan.relative_to(ROOT))]=sha(plan)
            terminal=ROOT/'.work/experiments'/name/'status.json'
            if terminal.exists():
                t=json.loads(terminal.read_text())
                assert t['status']=='finished' and t['owner']==t['cwd']==str(ROOT)
                assert sha(terminal.with_name('command.log'))==t['log_sha256']
                proofs[str(terminal.relative_to(ROOT))]=sha(terminal)
            # Some completed cases have a shared outer controller rather than
            # an individual supervisor. Their committed passed case report and
            # owned immutable plan are retained; no live payload is selected.
            completion.append(dict(run=name,committed_report=item['result'],status=summary['status']))
            for key in item['files']:
                path=ROOT/key;assert path.parent==raw and path.suffix in ['.json','.jsonl']
                info=path.lstat();assert stat.S_ISREG(info.st_mode) and not path.is_symlink() and not info.st_mode&0o111
                if info.st_flags&32:continue
                assert info.st_size>=128*1024
                assert key not in sources;sources[key]=sha(path)
        assert sources
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        inventory=[]
        for relative,digest in sorted(sources.items()):
            source=ROOT/relative;before=metadata(source)
            assert stat.S_ISREG(before['mode']) and before['uid']==os.getuid() and before['links']==1
            assert not before['mode'] & 0o111 and sha(source)==digest
            no_open_file(source)
            inventory.append(dict(path=relative,sha256=digest,before=before))
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            script_sha256=sha(Path(__file__)),proofs=proofs,files=inventory,
            scope='Exact closed diagnostic JSON/JSONL named by the fixed selection manifest. A committed completed report and owned plan establish each scope; all readable hashes are recorded before compression. Preserve exact bytes and metadata. No source file, executable, bytecode, active output, compiler cache or private-workload cache is changed. This is storage maintenance, not historical performance requalification.',completed_scopes=completion))
        before_free=shutil.disk_usage(ROOT).free;rows=[]
        for item in inventory:
            require_space(ROOT,10);source=ROOT/item['path'];before=item['before'];digest=item['sha256']
            assert metadata(source)==before and sha(source)==digest;no_open_file(source)
            if before['flags'] & 32:
                rows.append(dict(path=item['path'],status='already compressed'));write(work/'records.json',rows);continue
            temp=source.with_name('.'+source.name+'.'+NAME);assert not temp.exists()
            command=['/usr/bin/ditto','--hfsCompression',str(source),str(temp)]
            child,out,err=capture(command,cwd=ROOT,env=os.environ.copy(),receipt_path=work/'active.json',receipt=dict(source=item['path'],temporary=str(temp.relative_to(ROOT))))
            row=dict(path=item['path'],command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err,source_sha256=digest)
            rows.append(row);write(work/'records.json',rows);assert child.returncode==0,err
            assert sha(temp)==digest;staged=metadata(temp)
            for field in ['size','mode','uid','gid','mtime_ns']:assert staged[field]==before[field],(source,field)
            assert staged['flags'] & 32 and staged['blocks']<before['blocks'],source
            assert metadata(source)==before and sha(source)==digest;no_open_file(source)
            # Replacing an unopened owned diagnostic file preserves its exact
            # readable bytes and timestamp. The receipt retains both identities.
            os.replace(temp,source)
            after=metadata(source);assert sha(source)==digest and after==staged
            row.update(status='compressed',before=before,after=after);write(work/'records.json',rows)
            print(len(rows),len(inventory),item['path'],before['blocks']*512,'->',after['blocks']*512,flush=True)
        assert all(sha(ROOT/p)==h for p,h in sources.items())
        assert all(sha(ROOT/p)==h for p,h in proofs.items())
        changed=[r for r in rows if r['status']=='compressed']
        result=dict(status='passed',files=len(rows),compressed_files=len(changed),all_original_sha256_unchanged=True,
            logical_bytes=sum(r['before']['size'] for r in changed),
            allocated_bytes_before=sum(r['before']['blocks']*512 for r in changed),
            allocated_bytes_after=sum(r['after']['blocks']*512 for r in changed),
            free_before=before_free,free_after=shutil.disk_usage(ROOT).free,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            performance_measurement=False)
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False);write(out/'summary.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
