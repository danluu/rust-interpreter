"""Bounded read-only inventory; no compression or change to existing evidence."""
import hashlib,json,stat,subprocess,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
RUN='closed-compact-switch-evidence-inventory-01'
RUNS=['session-runtime-composition-parser-incremental-01', 'session-runtime-composition-screen-token-01', 'session-runtime-composition-edit-token-01', 'session-runtime-composition-edit-folded-01', 'compact-native-switch-screen-token-01', 'compact-native-switch-edit-token-01', 'compact-native-switch-edit-folded-01']
SUFFIXES={'.json','.rbc','.stdout','.stderr','.txt'}
FORBIDDEN={'native','native_lines','check','target','source','sources','.git','build','deps','incremental'}
def read(p):
    assert p.stat().st_size<=64*1024**2
    return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        frozen={}
        def bind(p,expected=None):
            h=sha(p)
            if expected is not None:assert h==expected,p
            frozen[str(p.relative_to(ROOT))]=h;return read(p) if p.suffix=='.json' else h
        proof=ROOT/'results/closed-evidence-compression-probe-02';c=bind(proof/'closure.json')
        assert c['status']=='closed' and c['all_hashes_verified']
        compatibility=bind(proof/'summary.json',c['summary_sha256']);bind(proof/'terminal.json',c['terminal_sha256'])
        assert compatibility['status']=='passed' and compatibility['existing_files_modified']==0
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);rows=[];runs=[]
        for name in RUNS:
            result=ROOT/'results'/name;c=bind(result/'closure.json')
            if 'evidence_path' in c:
                assert c['status']=='passed' and c['retained_artifacts_verified']>0
                manifest=c['evidence_path'];evidence=bind(ROOT/manifest,c['evidence_sha256'])
                s=bind(result/'summary.json',evidence[str((result/'summary.json').relative_to(ROOT))])
                t=bind(result/'terminal.json',evidence[str((result/'terminal.json').relative_to(ROOT))])
            else:
                assert c['status']=='closed' and c['all_hashes_verified']
                manifest=c['evidence'];evidence=bind(ROOT/manifest,c['evidence_sha256'])
                s=bind(result/'summary.json',c['summary_sha256']);t=bind(result/'terminal.json',c['terminal_sha256'])
            assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
            assert not s.get('private',False)
            stage=ROOT/s['raw'];assert stage==ROOT/'.work'/name and stage.resolve(strict=True)==stage
            assert len(evidence)<=50000
            count=len(rows)
            for path,expected in evidence.items():
                p=ROOT/path
                if not p.is_relative_to(stage) or p.suffix not in SUFFIXES:continue
                if set(p.relative_to(stage).parts)&FORBIDDEN:continue
                st=p.lstat()
                if not stat.S_ISREG(st.st_mode) or st.st_mode&0o111 or st.st_nlink!=1 or st.st_size<256*1024:continue
                if p.resolve(strict=True)!=p or st.st_flags&stat.UF_COMPRESSED:continue
                assert isinstance(expected,str) and len(expected)==64
                with p.open('rb') as f:sample=f.read(65536)
                after=p.lstat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
                rows.append(dict(run=name,path=path,expected_plaintext_sha256=expected,size=st.st_size,allocated_bytes=st.st_blocks*512,
                    device=st.st_dev,inode=st.st_ino,mtime_ns=st.st_mtime_ns,mode=st.st_mode,flags=st.st_flags,
                    sample_bytes=len(sample),sample_zlib_bytes=len(zlib.compress(sample)),sample_ratio=len(zlib.compress(sample))/len(sample)))
            runs.append(dict(run=name,eligible_files=len(rows)-count,evidence_manifest=manifest,evidence_sha256=c['evidence_sha256']))
            print(name,len(rows)-count,'eligible files',flush=True)
        rows.sort(key=lambda r:r['allocated_bytes'],reverse=True)
        write(raw/'inventory.json',rows);write(raw/'runs.json',runs)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,runs=RUNS,
            controller_command=[sys.executable,*sys.orig_argv[1:]],minimum_initial_gib=12,existing_files_modified=0,
            full_payload_hashes_rechecked=False,sample_bytes_per_file=65536,original_project_guest_commands=0,performance_measurement=False))
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),runs=len(runs),eligible_files=len(rows),
            allocated_bytes=sum(r['allocated_bytes'] for r in rows),logical_bytes=sum(r['size'] for r in rows),
            top_allocated_bytes=[r['allocated_bytes'] for r in rows[:10]],sample_only=True,full_payload_hashes_rechecked=False,
            existing_files_modified=0,real_evidence_compression_admitted=False,performance_measurement=False,
            **{n+'_sha256':sha(raw/(n+'.json')) for n in ['plan','inventory','runs']}))
        print('Read-only inventory',len(rows),'files;',sum(r['allocated_bytes'] for r in rows),'allocated bytes')
if __name__=='__main__':main()
