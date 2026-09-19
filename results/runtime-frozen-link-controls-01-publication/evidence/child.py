"""Real temporary-filesystem controls; no compiler, network or child processes."""
import ast
import hashlib
from importlib.util import cache_from_source
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HERE = ROOT/'experiments/runtime-frozen-link-controls-01'
SOURCE = ROOT/'experiments/runtime-frozen-link-reader-01'
OUT = ROOT/'results/runtime-frozen-link-controls-01'
TMP = OUT/'tmp'
FIELDS = ('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def stamp(path):
    info = Path(path).lstat()
    return {key:getattr(info,'st_'+key) for key in FIELDS}


plan = json.loads((HERE/'plan.json').read_bytes())
require(Path(__file__) == HERE/'child.py' and Path.cwd() == SOURCE, 'exact child source/cwd')
require(TMP.resolve(strict=True) == TMP and stat.S_ISDIR(TMP.lstat().st_mode), 'ordinary owned temporary root')
require(os.environ.get('TMPDIR') == str(TMP), 'owned explicit temporary root required')
for name, row in plan['test_sources'].items():
    path = Path(name); before = stamp(path); raw = path.read_bytes()
    require(before == stamp(path) == row['identity'] and len(raw) == row['bytes']
        and hashlib.sha256(raw).hexdigest() == row['sha256'], 'exact source before import')
allowed = {str(SOURCE/'links.py'),str(SOURCE/'test_links.py'),str(Path(__file__))}
caches = {cache_from_source(name) for name in allowed}
require(not any(os.path.lexists(name) for name in caches), 'no cached candidate modules')
test_ast = ast.parse((SOURCE/'test_links.py').read_bytes())
names = sorted('test_links.'+cls.name+'.'+node.name for cls in test_ast.body if isinstance(cls,ast.ClassDef)
    for node in cls.body if isinstance(node,ast.FunctionDef) and node.name.startswith('test_'))
require(names == plan['test_names'] and len(names) == 24, 'source-derived exact24 tests')
tempfile.tempdir = str(TMP)
events = []; denied = []


def owned_parent(value, directory_fd=-1):
    require(isinstance(value,(str,bytes,os.PathLike)), 'named temporary mutation required')
    p = Path(os.fsdecode(value))
    if not p.is_absolute():
        require(directory_fd not in (-1,None), 'relative mutation requires an owned held directory')
        info = os.fstat(directory_fd); found = []
        count = 0
        for root, dirs, files in os.walk(TMP,followlinks=False):
            count += 1; require(count <= 256, 'bounded temporary directory search')
            path = Path(root); st = path.lstat()
            if (st.st_dev,st.st_ino) == (info.st_dev,info.st_ino):
                found.append(path)
        require(len(found) == 1, 'directory descriptor is outside owned temporary tree')
        p = found[0]/p
    require(p.name not in ('','.', '..'), 'explicit temporary member required')
    parent = p.parent.resolve(strict=True)
    require(parent == TMP or TMP in parent.parents, 'mutation outside owned temporary tree')
    return parent/p.name


def note(event, names):
    require(len(events) < 1024, 'bounded temporary mutation events')
    events.append(dict(event=event,paths=[str(name) for name in names]))


def audit(event, args):
    if event.startswith(('subprocess.','os.exec','os.posix_spawn','socket.','ctypes.')) or event in (
            'os.system','os.kill','os.killpg','os.fork','os.forkpty','os.chdir','os.fchdir','os.link',
            'os.truncate','os.chown','os.putenv','os.unsetenv'):
        denied.append(event)
        raise RuntimeError('controls deny process/network/signal or unrelated mutation: '+event)
    if event == 'open':
        name, mode, flags = args
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            path = owned_parent(name)
            resolved = path.resolve(strict=False)
            require(resolved == TMP or TMP in resolved.parents, 'write follows link outside temporary tree')
            note(event,[path])
        elif isinstance(name,(str,bytes)):
            raw = Path(os.fsdecode(name))
            if not raw.is_absolute():
                # os.open's audit event omits dir_fd. The authenticated link
                # helper uses bare components with held directory descriptors;
                # read-only descriptor-relative metadata/file opens are allowed.
                require(len(raw.parts) == 1 and raw.name not in ('.','..'), 'bounded relative read component')
                return
            path = str(raw)
            if path in caches:
                require(not os.path.lexists(path), 'cached target module appeared')
            elif path.startswith('/Users/danluu/dev/'):
                require(path in allowed or path == str(TMP) or path.startswith(str(TMP)+'/'),
                        'unrelated workspace/provider read refused')
    elif event in ('os.remove','os.rmdir','os.mkdir'):
        directory_fd = args[2] if event == 'os.mkdir' else args[1]
        path = owned_parent(args[0],directory_fd)
        note(event,[path])
    elif event == 'os.rename':
        source = owned_parent(args[0],args[2]); destination = owned_parent(args[1],args[3])
        note(event,[source,destination])
    elif event == 'os.symlink':
        destination = owned_parent(args[1],args[2]); target = Path(os.fsdecode(args[0]))
        resolved = (target if target.is_absolute() else destination.parent/target).resolve(strict=False)
        require(resolved == TMP or TMP in resolved.parents, 'temporary symlink target escapes owned tree')
        note(event,[destination])
    elif event in ('os.chmod','os.utime'):
        directory_fd = args[2] if event == 'os.chmod' else args[3]
        path = owned_parent(args[0],directory_fd); resolved = path.resolve(strict=True)
        require(resolved == TMP or TMP in resolved.parents, 'temporary metadata mutation escapes owned tree')
        note(event,[path])


sys.addaudithook(audit)
require('links' not in sys.modules and 'test_links' not in sys.modules, 'fresh fixture module imports')
sys.path.insert(0,str(SOURCE))
suite = unittest.defaultTestLoader.loadTestsFromName('test_links')
require(suite.countTestCases() == 24, 'exact loaded test count')
require(Path(sys.modules['links'].__file__) == SOURCE/'links.py'
    and Path(sys.modules['test_links'].__file__) == SOURCE/'test_links.py', 'exact imported source routes')


class Result(unittest.TextTestResult):
    def startTest(self, test):
        observed.append(test.id())
        super().startTest(test)


observed = []
result = unittest.TextTestRunner(stream=sys.stdout,verbosity=2,resultclass=Result).run(suite)
passed = result.wasSuccessful() and result.testsRun == 24 and not result.skipped and sorted(observed) == names
require(not list(TMP.iterdir()), 'temporary fixtures must clean their own members')
proof = dict(status='passed' if passed else 'failed',tests=result.testsRun,test_names=observed,
    skipped=len(result.skipped),failures=len(result.failures),errors=len(result.errors),
    child_pid=os.getpid(),parent_pid=os.getppid(),cwd=str(Path.cwd()),observed_environment=dict(os.environ),
    io_policy=dict(owned_tmp=str(TMP),temporary_members_after=[],mutation_events=len(events),
        provider_writes=False,subprocess_calls=False,network_calls=False,signal_calls=False,
        denied_events=denied),test_sources=plan['test_sources'])
print('FROZEN_LINK_CONTROL_RESULT '+json.dumps(proof,sort_keys=True),flush=True)
raise SystemExit(0 if passed else 1)
