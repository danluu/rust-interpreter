import fcntl, hashlib, json, lzma, os
from pathlib import Path
import shutil, sys, tarfile, time

ROOT = Path('/Users/danluu/dev/rust-interp-mono-completion-evidence-20260913')
OUT = ROOT / 'results/mono-production-compiler-complete-01'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
OLD = ROOT / '.work/compiler-complete-initial-evidence.tar.xz'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def main():
    result = {'status': 'waiting', 'pid': os.getpid(), 'parent_pid': os.getppid(),
              'argv': sys.argv, 'cwd': str(Path.cwd()), 'started_at': time.time(),
              'lock': str(LOCK), 'lock_wait_seconds': 600, 'runner_sha256': sha(__file__),
              'compiler_commands': 0, 'test_commands': 0, 'benchmark_commands': 0}
    result_path = OUT / 'compression-receipt.json'
    assert not result_path.exists()
    save(result_path, result)
    with LOCK.open('a+b') as lock:
        try:
            deadline = time.monotonic() + 600
            while True:
                try:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    assert time.monotonic() < deadline, 'canonical admission expired'
                    time.sleep(.25)
            result.update(status='compressing', admitted_at=time.time())
            save(result_path, result)
            original = OUT / 'evidence.tar.xz'
            summary = json.loads((OUT / 'summary.json').read_bytes())
            members = json.loads((OUT / 'members.json').read_bytes())
            assert sha(original) == summary['archive']['sha256']
            assert not OLD.exists()
            shutil.copyfile(original, OLD)
            shutil.copyfile(OUT / 'summary.json', OUT / 'initial-summary.json')
            fresh = ROOT / '.work/compiler-complete-recompressed.tar.xz'
            assert not fresh.exists()
            with lzma.open(original, 'rb') as src, lzma.open(fresh, 'wb', filters=[{
                'id': lzma.FILTER_LZMA2, 'preset': 3, 'dict_size': 64 * 1024 * 1024,
            }]) as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            seen = set()
            with tarfile.open(fresh, 'r:xz') as tar:
                for member in tar:
                    assert member.isfile() and member.name in members and member.name not in seen
                    seen.add(member.name)
                    h = hashlib.sha256()
                    with tar.extractfile(member) as stream:
                        for b in iter(lambda: stream.read(1024 * 1024), b''): h.update(b)
                    assert h.hexdigest() == members[member.name]['sha256']
                    assert member.size == members[member.name]['size']
            assert seen == set(members)
            for item in members.values(): assert sha(item['source']) == item['sha256']
            final_sha = sha(fresh)
            initial_archive = summary['archive'].copy()
            assert fresh.stat().st_size < original.stat().st_size
            fresh.replace(original)
            summary['initial_archive'] = initial_archive
            summary['archive'].update(sha256=final_sha, bytes=original.stat().st_size)
            summary['compression_receipt'] = 'compression-receipt.json'
            save(OUT / 'summary.json', summary)
            result.update(status='passed', finished_at=time.time(), archive_sha256=final_sha,
                          archive_bytes=original.stat().st_size, original_archive=initial_archive,
                          original_archive_preserved_at=str(OLD), members=len(members),
                          all_members_and_sources_rechecked=True, dictionary_bytes=64 * 1024 * 1024,
                          summary_sha256=sha(OUT / 'summary.json'))
            save(result_path, result)
            shutil.copyfile(__file__, OUT / 'compression-runner.py')
            print(json.dumps({'status': 'passed', 'pid': os.getpid(), 'sha256': final_sha,
                              'bytes': original.stat().st_size}), flush=True)
        except BaseException as error:
            result.update(status='failed', error=repr(error), finished_at=time.time())
            save(result_path, result)
            raise

if __name__ == '__main__': main()
