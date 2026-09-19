"""Read an already-published blob without restoring its sparse working copy."""
import hashlib
import json
import os
from pathlib import Path
import selectors
import stat
import subprocess
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
OUT = ROOT/'.work/published-failure-archive-git-proof-01'
RELATIVE = 'results/hir-options-hash-driver-failure-01/evidence.tar.gz'
COMMIT = '075141b3d11a5172ab59ecbdeface0d340fac016'
BLOB = '09c50202c9b3241d7c620053cd47c3f283136c88'
EXPECTED_SHA = 'ff7870ea202cd33b7c91e2afe8b3784780fee1d9239a7df6394eaf0560417216'
EXPECTED_BYTES = 13134758
ENV = dict(HOME='/Users/danluu', PATH='/usr/bin:/bin:/usr/sbin:/sbin',
           LANG='C', LC_ALL='C', TZ='UTC', GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
FIELDS = ('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()

def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())

def file_row(path):
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size < 2**20, 'ordinary small proof file')
    raw = path.read_bytes()
    after = path.lstat()
    require(all(getattr(before,'st_'+k)==getattr(after,'st_'+k) for k in FIELDS), 'proof file changed')
    return dict(path=str(path), size=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                identity={k:getattr(before, 'st_'+k) for k in FIELDS})

def absent():
    require(not os.path.lexists(ROOT/RELATIVE), 'ordinary published archive must remain absent')
    return True

def command(name, args, blob=False):
    directory = OUT/'commands'/name
    directory.mkdir()
    argv = ['/usr/bin/git', *args]
    started = time.time(); start = time.monotonic()
    process = subprocess.Popen(argv, cwd=ROOT, env=ENV, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    record = dict(argv=argv, cwd=str(ROOT), environment=ENV, parent_pid=os.getpid(),
                  child_pid=process.pid, started_at=started,
                  command_timeout_seconds=30, signals_sent=[])
    selector = None
    sizes = dict(stdout=0, stderr=0); hashes = {k:hashlib.sha256() for k in sizes}
    values = dict(stdout=[], stderr=[])
    try:
        save(directory/'launch.json', encoded(record))
        selector = selectors.DefaultSelector()
        for name_, stream in [('stdout',process.stdout),('stderr',process.stderr)]:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name_)
        while selector.get_map():
            require(time.monotonic()-start < 30, 'Git read deadline; child is not signalled')
            for key, _ in selector.select(.1):
                data = os.read(key.fd, 65536)
                if not data:
                    selector.unregister(key.fileobj); key.fileobj.close(); continue
                label = key.data; sizes[label] += len(data)
                require(sizes[label] <= (16*2**20 if blob and label=='stdout' else 65536), 'Git stream cap')
                hashes[label].update(data)
                if not (blob and label=='stdout'):
                    values[label].append(data)
        while process.poll() is None:
            require(time.monotonic()-start < 30, 'Git closure deadline; child is not signalled')
            time.sleep(.01)
        record.update(status='closed',returncode=process.returncode, finished_at=time.time(),
                      full_stdout_eof=True, full_stderr_eof=True,
                      streams={k:dict(bytes=sizes[k],sha256=hashes[k].hexdigest(),
                                     retained=not(blob and k=='stdout')) for k in sizes})
    except BaseException as error:
        observed = process.poll()
        record.update(status='failed-closed' if observed is not None else 'unresolved-live-child-not-signalled',
                      error=repr(error),observed_returncode=observed,failure_observed_at=time.time(),
                      child_may_remain_live=observed is None)
        raise
    finally:
        if selector is not None:
            selector.close()
        for stream in [process.stdout,process.stderr]:
            if not stream.closed:
                stream.close()
        for key in values:
            if not(blob and key=='stdout'):
                save(directory/key, b''.join(values[key]))
        save(directory/'record.json', encoded(record))
    require(process.returncode==0 and sizes['stderr']==0, 'Git command failed or emitted stderr')
    return record, b''.join(values['stdout'])

def main():
    require(Path.cwd()==ROOT and Path(__file__).resolve()==Path(__file__), 'exact proof cwd/source')
    source = Path(__file__).read_bytes()
    OUT.mkdir(); (OUT/'commands').mkdir()
    save(OUT/'source.py', source)
    started = time.time(); before_absent=absent()
    records={}; texts={}
    checks=[('head-before',['rev-parse','HEAD']),
            ('sparse-before',['config','--get','core.sparseCheckout']),
            ('entry-before',['ls-files','-t','--',RELATIVE]),
            ('published-blob',['rev-parse',COMMIT+':'+RELATIVE]),
            ('current-blob',['rev-parse','HEAD:'+RELATIVE]),
            ('blob-type',['cat-file','-t',BLOB]),
            ('blob-size',['cat-file','-s',BLOB])]
    for name, argv in checks:
        records[name], raw = command(name, argv); texts[name]=raw.decode('utf-8')
    require(texts['published-blob']==texts['current-blob']==BLOB+'\n', 'committed blob association differs')
    require(texts['blob-type']=='blob\n' and texts['blob-size']==str(EXPECTED_BYTES)+'\n', 'blob type or length differs')
    records['blob-content'], _ = command('blob-content',['cat-file','blob',BLOB],blob=True)
    actual=records['blob-content']['streams']['stdout']
    require(actual['bytes']==EXPECTED_BYTES and actual['sha256']==EXPECTED_SHA, 'full committed blob bytes differ')
    for name, argv in [('head-after',['rev-parse','HEAD']),
                       ('sparse-after',['config','--get','core.sparseCheckout']),
                       ('entry-after',['ls-files','-t','--',RELATIVE])]:
        records[name], raw = command(name,argv); texts[name]=raw.decode('utf-8')
    require(texts['head-before']==texts['head-after'], 'HEAD changed during proof')
    require(texts['sparse-before']==texts['sparse-after']=='true\n', 'sparse checkout not enabled')
    require(texts['entry-before']==texts['entry-after']=='S '+RELATIVE+'\n', 'exact sparse omitted entry differs')
    after_absent=absent()
    require(Path(__file__).read_bytes()==source, 'proof source changed during execution')
    files=[file_row(p) for p in sorted(OUT.rglob('*')) if p.is_file()]
    report=dict(schema='published-sparse-archive-git-proof-v1',status='verified',
                started_at=started,finished_at=time.time(),parent_pid=os.getpid(),parent_parent_pid=os.getppid(),
                cwd=str(ROOT),source=file_row(Path(__file__)),retained_source=file_row(OUT/'source.py'),
                publication=dict(commit=COMMIT,relative_path=RELATIVE,path=str(ROOT/RELATIVE),git_blob=BLOB,
                                 sha256=EXPECTED_SHA,bytes=EXPECTED_BYTES),
                working_copy=dict(absent_before=before_absent,absent_after=after_absent,
                                  sparse_enabled=True,index_skip_worktree=True,restored=False),
                head=texts['head-before'].strip(),commands=records,text_outputs=texts,files=files,
                actual_git_children=len(records),all_children_closed=True,signals_sent=[],
                full_git_blob_read=True,blob_stdout_retained=False,original_inode_claimed=False)
    save(OUT/'report.json',encoded(report))
    print(json.dumps(file_row(OUT/'report.json'),sort_keys=True))

if __name__=='__main__':
    main()
