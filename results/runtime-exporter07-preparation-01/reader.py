"""Independent byte, identity and membership readback of the finite capsule."""
import hashlib
import json
import os
from pathlib import Path
import resource
import stat
import subprocess
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
OUT = ROOT/'results/runtime-exporter07-preparation-01'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def identity(p):
    s = p.lstat()
    return {key:getattr(s, 'st_'+key) for key in ('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')}


def read(p):
    p = Path(p); before = identity(p)
    require(p.resolve(strict=True) == p and stat.S_ISREG(before['mode'])
            and before['nlink'] == 1 and before['size'] <= 8*2**20, 'bounded ordinary file')
    b = p.read_bytes()
    require(identity(p) == before and len(b) == before['size'], 'read changed file')
    return b, dict(identity=before, sha256=hashlib.sha256(b).hexdigest(), size=len(b))


def tree(root):
    root = Path(root); rows = {'.':identity(root)}
    require(root.resolve(strict=True) == root and stat.S_ISDIR(rows['.']['mode']), 'ordinary tree root')
    for parent, ds, fs in os.walk(root, followlinks=False):
        for name in ds+fs:
            p=Path(parent)/name; value=identity(p)
            require(stat.S_ISDIR(value['mode']) or stat.S_ISREG(value['mode']), 'ordinary tree entry')
            rows[str(p.relative_to(root))]=value
    return rows


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (60,60))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8*2**20,8*2**20))
    started=time.time(); manifest_bytes, manifest_ref=read(OUT/'manifest.json')
    require(manifest_ref['sha256']=='2ab39de1fa2327d23075940a083daac3a6ca5b9a7558236e15a6f088ad3f8fba','exact manifest')
    manifest=json.loads(manifest_bytes); scope_bytes,scope_ref=read(OUT/'scope.json');scope=json.loads(scope_bytes)
    require(scope_ref['sha256']=='8d984a11dce4dcb73f3a94513c999717e32c49ce35e6d6d08895d3f201a35162','exact scope')
    require(manifest['payload_files']==len(manifest['files'])==26
            and manifest['payload_bytes']==sum(r['source']['size'] for r in manifest['files'])==1008830,
            'payload census')
    observations=[]
    for item in manifest['files']:
        original=Path(item['original']); destination=OUT/item['relative']
        ob,orow=read(original); db,drow=read(destination)
        require(orow==item['source'] and drow==item['destination'] and ob==db,'copy source or destination differs')
        require(orow['identity']['ino']!=drow['identity']['ino'],'copy must have independent inode')
        wanted=scope['files'][str(original)]
        require(item['relative']==wanted['destination']
                and orow=={k:wanted[k] for k in ('identity','sha256','size')},'scope association')
        observations.append(dict(original=str(original),relative=item['relative'],sha256=orow['sha256'],bytes=orow['size']))
    require(manifest['root_references']==scope['references'] and len(scope['references'])==32,'reference scope')
    for name,row in scope['references'].items():require(read(name)[1]==row,'referenced source/packet changed')
    for root,rows in manifest['source_trees'].items():require(tree(root)==rows,'original closed tree changed')
    for name,row in manifest['metadata_files'].items():require(read(OUT/name)[1]==row,'publication metadata changed')
    for proof in scope['external_source_resolution']:
        if 'commit' in proof:
            result=subprocess.run(['git','show',proof['commit']+':'+proof['path']],cwd=ROOT,capture_output=True)
            require(result.returncode==0 and hashlib.sha256(result.stdout).hexdigest()==proof['sha256'],
                    'external dependency differs from retained HEAD blob')
        else:
            pm=proof['publication_manifest']; data,entry=read(pm['path'])
            require(entry['sha256']==pm['sha256'] and read(proof['published_path'])[1]['sha256']==proof['sha256'],
                    'published external dependency differs')
            old=json.loads(data)
            require(any(v['original']==proof['original'] and v['source']['sha256']==proof['sha256']
                        for v in old['files']),'prior source manifest association')
    wanted={v['relative'] for v in manifest['files']}|{'scope.json','publisher.py','STATUS.md','manifest.json'}
    current=tree(OUT)
    require({n for n,r in current.items() if stat.S_ISREG(r['mode'])}==wanted,'exact30 initial publication files')
    require({n for n,r in current.items() if stat.S_ISDIR(r['mode'])}
            =={'.'}|{str(p) for n in wanted for p in Path(n).parents},'exact publication directories')
    reader_bytes,reader_ref=read(Path(__file__).resolve())
    with (OUT/'reader.py').open('xb') as stream:stream.write(reader_bytes)
    require(read(OUT/'reader.py')[0]==reader_bytes,'retained reader differs')
    result=dict(status='verified-exporter07-preparation-publication',pid=os.getpid(),parent_pid=os.getppid(),
        started_at=started,finished_at=time.time(),manifest=manifest_ref,scope=scope_ref,reader=reader_ref,
        payload_files=26,payload_bytes=1008830,references=32,external_source_payload_duplicates=0,
        all_original_and_copy_bytes_stamps_equal=True,all_five_closed_trees_unchanged=True,
        observations=observations,reference_rows=scope['references'],capture_status=scope['capture_status'],
        provider_payload_reads=False,provider_tree_walks=False,target_imports=False,workload_execution=False,
        git_reads_only=True,compiler_calls=0,publication_expected_files=32)
    with (OUT/'readback.json').open('x') as stream:json.dump(result,stream,sort_keys=True,indent=2);stream.write('\n')
    final=tree(OUT); expected=wanted|{'reader.py','readback.json'}
    require({n for n,r in final.items() if stat.S_ISREG(r['mode'])}==expected,'exact32 final publication files')
    require(sum(r['size'] for r in final.values() if stat.S_ISREG(r['mode']))<=2*2**20,'publication byte cap')
    staged=sorted(str((OUT/name).relative_to(ROOT)) for name in expected)
    all_stage=sorted(set(staged)|set(scope['root_stage_paths']))
    stage=dict(status='exact-exporter07-preparation-stage-list',publication=staged,
               root_source_and_packet=scope['root_stage_paths'],all_paths=all_stage,
               publication_files=32,publication_bytes=sum(r['size'] for r in final.values() if stat.S_ISREG(r['mode'])),
               manifest_sha256=manifest_ref['sha256'],readback_sha256=read(OUT/'readback.json')[1]['sha256'])
    stage_path=O/'.work/runtime-exporter07-preparation-publication-staged-paths-01.json'
    with stage_path.open('x') as stream:json.dump(stage,stream,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps(dict(readback=read(OUT/'readback.json')[1],stage_paths=read(stage_path)[1],
        publication_files=32,publication_bytes=stage['publication_bytes'],stage_count=len(all_stage),pid=os.getpid()),sort_keys=True))


if __name__=='__main__':main()
