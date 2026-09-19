"""Preserve exactly274 saved-cache executables; no deletion or process probes."""
import fcntl
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
OUT = ROOT/'results/runtime-exporter07-closed-cache-executable-preservation-01'
PLAN = ROOT/'experiments/runtime-exporter07-closed-cache-retirement-01/plan.json'
PLAN_SHA = '8720f4814a6ab357e751163e37720689e2e5ebf764e820ab2ec053d15faf3d10'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
FIELDS = ('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
DEADLINE = None


def require(ok, message):
    if not ok: raise RuntimeError(message)


def identity(path):
    s = path if isinstance(path, os.stat_result) else Path(path).lstat()
    return {k:getattr(s,'st_'+k) for k in FIELDS}


def encoded(value): return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()


def write(path, value):
    data = encoded(value); require(len(data) <= 4*2**20, 'bounded metadata output')
    with path.open('xb') as out: out.write(data); out.flush(); os.fsync(out.fileno())
    require(path.read_bytes() == data, 'metadata readback differs')


def capacity():
    if DEADLINE is not None: require(time.monotonic() < DEADLINE, 'bounded preservation deadline')
    s = os.statvfs(ROOT); free = s.f_bavail*s.f_frsize
    require(free >= 9*2**30, 'nine GiB stop threshold')
    return free


def ref(path, limit=16*2**20):
    path = Path(path); before = identity(path)
    require(path.resolve(strict=True) == path and stat.S_ISREG(before['mode']) and before['size'] <= limit, 'ordinary bounded file')
    h = hashlib.sha256(); size = 0
    with path.open('rb') as stream:
        while block := stream.read(2**20): capacity(); h.update(block); size += len(block)
    require(identity(path) == before and size == before['size'], 'current reference changed')
    return dict(path=str(path),sha256=h.hexdigest(),bytes=size,identity=before)


def main():
    global DEADLINE
    require(Path.cwd() == ROOT and not os.path.lexists(OUT), 'fresh owned publication/cwd required')
    source = ref(Path(__file__).resolve()); plan_ref = ref(PLAN)
    require(plan_ref['sha256'] == PLAN_SHA, 'held1456 plan differs')
    plan = json.loads(PLAN.read_bytes()); selected = []; inventories = []
    for i, scope in enumerate(plan['scopes']):
        r = ref(scope['inventory']['path']); require(r['sha256'] == scope['inventory']['sha256'], 'inventory pin differs')
        inventories.append(r); payload = gzip.decompress(Path(r['path']).read_bytes())
        require(len(payload) == scope['inventory']['expanded_bytes'] and hashlib.sha256(payload).hexdigest() == scope['inventory']['expanded_sha256'], 'saved inventory full EOF differs')
        rows = json.loads(payload)['rows']
        for name in scope['retained_files']:
            row = rows[name]
            if not row['identity']['mode'] & 0o111 or Path(name).suffix != '': continue
            require(row['kind'] == 'file' and name not in scope['selected_files'], 'must be separate retained executable')
            selected.append(dict(root=scope['root'],relative=name,path=str(Path(scope['root'])/name),member=f'root-{i:02d}/'+name,**row))
    require(len(selected) == 274 and sum(r['identity']['size'] for r in selected) == 352273936, 'exact274 scope differs')
    require(len({r['path'] for r in selected}) == len({r['member'] for r in selected}) == 274, 'duplicate member')
    OUT.mkdir(mode=0o700); record = dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),source=source,plan=plan_ref,deletions=0,compiler_calls=0,process_probes=0)
    write(OUT/'started.json', record)
    lock_identity = identity(LOCK)
    try:
        with LOCK.open('r+') as lock:
            end = time.monotonic()+600
            while True:
                try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB); break
                except BlockingIOError:
                    require(time.monotonic()<end,'canonical queue deadline'); time.sleep(.25)
            require(identity(os.fstat(lock.fileno())) == identity(LOCK) == lock_identity and LOCK.resolve(strict=True) == LOCK, 'canonical route changed')
            DEADLINE = time.monotonic()+180; record.update(admitted_at=time.time(),free_bytes_before=capacity())
            allocated = 0; seen = set()
            for row in selected:
                path = Path(row['path']); s = path.lstat()
                require(identity(s) == row['identity'] and s.st_nlink == 1 and path.resolve(strict=True) == path, 'selected current stamp/route differs')
                require(stat.S_ISREG(s.st_mode) and 0 < s.st_size <= 16*2**20, 'bounded ordinary executable')
                key = (s.st_dev,s.st_ino); require(key not in seen, 'selected alias'); seen.add(key)
                row['allocated_bytes_observation'] = s.st_blocks*512; allocated += s.st_blocks*512
            write(OUT/'selection.json',dict(status='preservation-only-no-removal',members=selected,selected_files=274,logical_bytes=352273936,allocated_bytes_observation=allocated,
                original1456_plan=plan_ref,original9952_retention_declaration_preserved=True,subsequent_transition_requires_separate_review=True,all_directories_retained=True,inventories=inventories))
            archive_path = OUT/'evidence.tar.gz'
            with archive_path.open('xb') as raw:
                with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=6) as gz:
                    with tarfile.open(fileobj=gz,mode='w|',format=tarfile.PAX_FORMAT) as archive:
                        for row in selected:
                            capacity(); path = Path(row['path']); require(identity(path) == row['identity'], 'file changed before preservation')
                            with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as stream:
                                require(identity(os.fstat(stream.fileno())) == row['identity'], 'opened executable differs')
                                data = stream.read(row['identity']['size']+1)
                                require(len(data) == row['identity']['size'] and stream.read(1) == b'', 'complete source EOF differs')
                                require(hashlib.sha256(data).hexdigest() == row['sha256'] and identity(os.fstat(stream.fileno())) == row['identity'], 'source bytes differ')
                            require(identity(path) == row['identity'], 'source route changed while copying')
                            member = tarfile.TarInfo(row['member']); member.size = len(data); member.mode = row['identity']['mode'] & 0o7777; member.mtime = 0
                            member.uid = member.gid = 0; member.uname = member.gname = ''
                            archive.addfile(member,io.BytesIO(data))
                            require(raw.tell() <= 128*2**20, 'compressed archive bound')
                raw.flush(); os.fsync(raw.fileno())
            require(archive_path.stat().st_size <= 128*2**20, 'closed archive bound')
            archive_ref = ref(archive_path,128*2**20); wanted = {r['member']:r for r in selected}; observed = set()
            with tarfile.open(archive_path,'r|gz') as archive:
                for member in archive:
                    capacity(); require(member.isfile() and member.name in wanted and member.name not in observed, 'unexpected archived member')
                    row = wanted[member.name]; require(member.size == row['identity']['size'], 'archived size differs')
                    h = hashlib.sha256(); size = 0
                    with archive.extractfile(member) as stream:
                        while block := stream.read(2**20): capacity(); h.update(block); size += len(block)
                    require(size == member.size and h.hexdigest() == row['sha256'], 'archived full member SHA differs'); observed.add(member.name)
            require(observed == set(wanted), 'archive membership incomplete')
            expanded = 0
            with gzip.open(archive_path,'rb') as stream:
                while block := stream.read(2**20):
                    capacity(); expanded += len(block); require(expanded <= 400*2**20, 'expanded gzip bound')
            # Repeat full original EOF SHA after archive verification; no originals are removed.
            for row in selected:
                current = ref(row['path']); require(current['identity'] == row['identity'] and current['sha256'] == row['sha256'], 'original changed after archive readback')
            require(ref(PLAN) == plan_ref and ref(Path(__file__).resolve()) == source, 'plan/publisher source changed')
            manifest = dict(status='preserved-not-retired',archive=archive_ref,members=selected,logical_bytes=352273936,allocated_original_bytes_observation=allocated,source=source,original1456_plan=plan_ref,
                selected_files=274,full_member_sha_and_eof=True,full_gzip_eof_crc=True,expanded_tar_bytes=expanded,originals_current_unchanged=True,
                scope='Optional later resource-only transition; existing1,456 plan/9,952 retained declaration remain unchanged. No deletion authorized by this capsule.')
            write(OUT/'manifest.json',manifest)
            archive_allocated = archive_path.stat().st_blocks*512
            # Bound future metadata allocation conservatively; final exact capsule allocation is separately recorded below.
            record.update(status='preserved-not-retired',archive=archive_ref,manifest=ref(OUT/'manifest.json'),selected_files=274,allocated_original_bytes=allocated,
                archive_allocated_bytes=archive_allocated,net_before_metadata_bytes=allocated-archive_allocated,full_original_readback=True,full_member_readback=True,full_gzip_eof_crc=True,finished_at=time.time())
        record['canonical_parent_lock_closed_at'] = time.time()
    except BaseException as error:
        record.update(status='failed',error=repr(error),observation_finished_at=time.time()); raise
    finally: write(OUT/'record.json',record)
    members = sorted(p.name for p in OUT.iterdir()); require(members == ['evidence.tar.gz','manifest.json','record.json','selection.json','started.json'], 'finite capsule membership differs')
    capsule_allocated = OUT.stat().st_blocks*512 + sum((OUT/n).stat().st_blocks*512 for n in members)
    readback = dict(status='verified-preservation-only',checked_at=time.time(),archive=archive_ref,manifest=ref(OUT/'manifest.json'),record=ref(OUT/'record.json'),
        exact_members=members,original_files=274,original_allocated_bytes=allocated,capsule_allocated_bytes_before_readback=capsule_allocated,
        net_after_capsule_before_readback_bytes=allocated-capsule_allocated,readback_allocation_reserve_bytes=16384,
        conservative_net_after_readback_bytes=allocated-capsule_allocated-16384,original_files_unchanged=True,deletions=0)
    write(OUT/'READBACK.json',readback)
    print(json.dumps(dict(path=str(OUT),record_sha256=ref(OUT/'record.json')['sha256'],readback_sha256=ref(OUT/'READBACK.json')['sha256'],
        archive_bytes=archive_ref['bytes'],original_allocated_bytes=allocated,conservative_net_bytes=readback['conservative_net_after_readback_bytes']),sort_keys=True))


if __name__ == '__main__': main()
