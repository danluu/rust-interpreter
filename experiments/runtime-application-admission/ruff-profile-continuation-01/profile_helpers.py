"""Retained-output helpers adapted from strict-warm-build/profile.py."""
import hashlib,json,os,stat
from pathlib import Path

def require(c,m):
    if not c:raise RuntimeError(m)
def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def selected_artifact(stdout, target, package):
    selected = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue  # Raw stdout is retained, including any non-JSON output.
        if (event.get('reason') == 'compiler-artifact' and
                event.get('profile', {}).get('test') is True and
                event.get('target', {}).get('name') == package.replace('-', '_') and
                event.get('target', {}).get('kind') == ['lib']):
            for name in event.get('filenames', []):
                if name.endswith('.rmeta'):
                    selected.append((Path(name + '.rbc'), event))
    require(len(selected) == 1, 'Cargo did not select exactly one requested test artifact')
    artifact, event = selected[0]
    require(event['fresh'] is False, 'edited/prime/restoration target unexpectedly reused a fresh Cargo artifact')
    require(not artifact.is_symlink() and artifact.resolve(strict=True).is_relative_to(target) and
            0 < artifact.stat().st_size <= 64*1024*1024, 'invalid selected artifact')
    return artifact, event


def compiler_records(directory):
    records = []
    folders=sorted(directory.iterdir())
    require(len(folders)<=1024,'compiler record count exceeds bound')
    total_profiles=0
    for folder in folders:
        record = json.loads((folder / 'invocation.json').read_text())
        require(not record.get('stderr_overflow',False) and record['status'] == 'finished', 'compiler wrapper did not finish: ' + str(folder))
        phases = []
        for line in (folder / 'stderr.log').read_text(errors='replace').splitlines():
            if line.startswith('time: {'):
                phase = json.loads(line[6:])
                require(isinstance(phase.get('pass'), str) and isinstance(phase.get('time'), (int, float)),
                        'invalid rustc phase output')
                phases.append(phase)
        profiles = []
        profile_directory = folder / 'self-profile'
        if profile_directory.exists():
            require(not profile_directory.is_symlink(), 'self-profile directory is a symlink')
            for path in sorted(profile_directory.rglob('*')):
                require(not path.is_symlink(), 'self-profile output is a symlink')
                if path.is_file():
                    total_profiles += path.stat().st_size
                    require(path.stat().st_size<=256*2**20 and total_profiles<=512*2**20,'self-profile output exceeds bound')
                    profiles.append(dict(path=str(path), bytes=path.stat().st_size, sha256=digest(path)))
        record.update(phases=phases, self_profiles=profiles, stderr_sha256=digest(folder / 'stderr.log'),
                      record_path=str(folder / 'invocation.json'))
        records.append(record)
    return records


def source_inventory(source, inventory, disk):
    total=0
    for index,(name,item) in enumerate(inventory.items()):
        if index%256==0:disk()
        path=source/name
        require(path.parent.resolve(strict=True)==path.parent,'source indirect parent')
        before=path.lstat()
        if item['kind']=='symlink':
            require(path.is_symlink() and os.readlink(path)==item['target'] and path.resolve(strict=True).is_relative_to(source),'source link')
            data=os.fsencode(os.readlink(path))
        else:
            require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and bool(before.st_mode&0o111)==(item['mode']=='100755'),'source mode')
            data=path.read_bytes()
        require(len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],'source content: '+name)
        after=path.lstat()
        require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'source changed during read')
        total+=len(data)
    found=set()
    for directory,dirs,files in os.walk(source,followlinks=False):
        if Path(directory)==source:
            require('.git' in dirs and not (source/'.git').is_symlink(),'source Git directory')
            dirs.remove('.git')
        for name in dirs+files:
            path=Path(directory)/name
            if path.is_symlink() or not path.is_dir():found.add(str(path.relative_to(source)))
    require(found==set(inventory)|{'.rust-interp-owned.json'} and len(inventory)==11119 and total==89102713,'source membership/count')
    return dict(files=len(inventory),bytes=total,exact_membership=True)
