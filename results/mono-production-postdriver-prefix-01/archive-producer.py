"""Archive the completed setup/qualification prefix, including its failed attempts."""
import hashlib, io, json, os, re, stat, sys, tarfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock
from workflow_io import write_json, require_space

LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
WORK = ROOT / '.work/mono-postdriver-prefix-archive-01'
OUT = ROOT / 'results/mono-production-postdriver-prefix-01'
NAMES = ['mono-production-import-01', 'mono-production-import-02',
         'mono-production-tools-01', 'mono-production-tools-02',
         'mono-production-workspace-01', 'mono-production-workspace-02',
         'mono-workspace-path-tests-01', 'mono-production-std-off-01',
         'mono-production-std-on-01', 'mono-production-integration-01',
         'mono-production-source-observables-01']
SCOPES = {
    'mono-production-import-01': ['driver-proof'],
    'mono-production-import-02': ['source', 'driver-proof'],
    'mono-production-workspace-01': ['source'],
    'mono-production-workspace-02': ['source'],
    'mono-workspace-path-tests-01': ['source'],
    'mono-production-std-off-01': ['probe-native', 'probe-prepared'],
    'mono-production-std-on-01': ['probe-native', 'probe-prepared'],
    'mono-production-integration-01': ['fixture', 'compiler-argv', 'source-snapshots'],
    'mono-production-source-observables-01': ['application', 'compiler-argv', 'source-snapshots',
        'source-histories', 'verified-standard-sources', 'mapping-configuration'],
}
SUPERVISORS = ['mono-production-import-supervisor-01', 'mono-production-import-supervisor-02',
    'mono-production-tools-supervisor-01', 'mono-production-tools-supervisor-02',
    'mono-production-workspace-supervisor-01', 'mono-production-workspace-supervisor-02',
    'mono-workspace-path-tests-supervisor-01', 'mono-production-std-off-supervisor-01',
    'mono-production-std-on-supervisor-01', 'mono-production-integration-supervisor-01',
    'mono-production-source-observables-supervisor-01', 'mono-production-screen-source-supervisor-01']

def sha(data):
    return hashlib.sha256(data).hexdigest()

def require(value, message):
    if not value:
        raise RuntimeError(message)

WORK.mkdir(exist_ok=False)
record = dict(status='waiting', owner=str(ROOT), pid=os.getpid(), parent_pid=os.getppid(),
              started_at=time.time(), lock=str(LOCK), wait_seconds=600, builds=0, benchmarks=0)
write_json(WORK / 'summary.json', record)
try:
    with LOCK.open('r+') as lock:
        acquire_lock(lock, 600)
        require_space(ROOT, 8)
        record.update(status='running', admitted_at=time.time())
        write_json(WORK / 'summary.json', record)
        files = {}
        def add(path):
            require(path.resolve(strict=True) == path and not path.is_symlink(), 'linked archive input: ' + str(path))
            require(stat.S_ISREG(path.stat().st_mode), 'nonregular archive input: ' + str(path))
            name = str(path.relative_to(ROOT))
            data = path.read_bytes()
            require(data[:4] not in [b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe'],
                    'native executable reached evidence selection: ' + name)
            files[name] = dict(path=str(path), bytes=len(data), sha256=sha(data))
        def tree(directory):
            require(directory.is_dir() and not directory.is_symlink(), 'missing source evidence: ' + str(directory))
            for path in sorted(directory.rglob('*')):
                require(not path.is_symlink(), 'linked evidence subtree: ' + str(path))
                require(not any(p in ['target', 'caches', 'observable-cache', 'second-prefix'] for p in path.relative_to(directory).parts),
                        'cache reached evidence selection: ' + str(path))
                if path.is_file(): add(path)
        for name in NAMES:
            directory = ROOT / '.work' / name
            require(directory.is_dir(), 'completed run missing: ' + name)
            for path in sorted(directory.iterdir()):
                if path.is_file() and path.suffix != '.native': add(path)
            for sub in SCOPES.get(name, []): tree(directory / sub)
        for name in SUPERVISORS:
            directory = ROOT / '.work/experiments' / name
            status = json.loads((directory / 'status.json').read_bytes())
            require(status['status'] == 'finished', 'outer supervisor has not finished: ' + name)
            tree(directory)
        tree(ROOT / '.work/strict-warm-build/mono-production-source-setup-01')
        for path in sorted((ROOT / '.work').iterdir()):
            if path.is_file() and path.suffix in ['.py', '.json'] and ('mono-production' in path.name or 'mono-workspace-path' in path.name):
                add(path)
        add(ROOT / '.work/strict-warm-build/mono-production-source-preparation-01.json')
        add(Path(__file__))

        integration = json.loads((ROOT / '.work/mono-production-integration-01/result.json').read_bytes())
        failed = json.loads((ROOT / '.work/mono-production-source-observables-01/result.json').read_bytes())
        require(integration['status'] == 'passed' and integration['commands'] == 36 and
                integration['full_presentation_qualified'] and integration['source_restored'], 'strict36 did not pass')
        require(failed['status'] == 'failed' and failed['completed_commands'] == 38 and
                'off-unmapped-exported' in failed['error'], 'unexpected observable failure prefix')
        commands = json.loads((ROOT / '.work/mono-production-source-observables-01/commands.json').read_bytes())
        require(len(commands) == 38 and commands[-1]['returncode'] != 0, 'failed command prefix differs')
        launches = [json.loads(line.removeprefix('rust-interp-launch: ')) for line in commands[-1]['stderr'].splitlines()
                    if line.startswith('rust-interp-launch: ')]
        require(len(launches) == 1, 'failed export lacks actual launch receipt')
        launch = launches[0]
        artifact = Path(launch['artifact_path'])
        require(artifact.is_relative_to(ROOT / '.work/mono-production-source-observables-01/observable-cache'),
                'failed artifact not in owned run')
        require(sha(artifact.read_bytes()) == launch['artifact_sha256'] ==
                'efda5fa41a9896f3f66c39c0871e76dd6101aadda2eec28c4eda607bbc960bad', 'failed exported bytes changed')
        add(artifact)
        for name in ['mono-production-std-off-01', 'mono-production-std-on-01']:
            result = json.loads((ROOT / '.work' / name / 'result.json').read_bytes())
            require(result['status'] == 'passed', 'std preparation did not pass')
        workspace = json.loads((ROOT / '.work/mono-production-workspace-02/result.json').read_bytes())
        require(workspace['status'] == 'passed', 'workspace qualification did not pass')
        counts = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored',
                            (ROOT / '.work/mono-production-workspace-02/workspace-tests.stdout').read_text())
        rust_passed = sum(int(row[0]) for row in counts)
        rust_ignored = sum(int(row[2]) for row in counts)
        require(rust_passed == 505 and rust_ignored == 2 and all(int(row[1]) == 0 for row in counts),
                'workspace Rust test counts differ')

        OUT.mkdir(exist_ok=False)
        archive = OUT / 'evidence.tar.xz'
        with tarfile.open(archive, 'w:xz', preset=6) as tar:
            for name, item in sorted(files.items()):
                data = Path(item['path']).read_bytes()
                require(len(data) == item['bytes'] and sha(data) == item['sha256'], 'source changed while archiving: ' + name)
                info = tarfile.TarInfo(name)
                info.size = len(data); info.mode = 0o644; info.mtime = 0
                tar.addfile(info, io.BytesIO(data))
        seen = set()
        with tarfile.open(archive, 'r:xz') as tar:
            for member in tar:
                require(member.isfile() and member.name in files and member.name not in seen, 'archive member differs')
                data = tar.extractfile(member).read(); item = files[member.name]
                require(len(data) == item['bytes'] and sha(data) == item['sha256'], 'archive bytes differ')
                seen.add(member.name)
        require(seen == set(files), 'archive member set differs')
        for name, item in files.items():
            require(sha(Path(item['path']).read_bytes()) == item['sha256'], 'source changed after archival: ' + name)
        write_json(OUT / 'members.json', files)
        summary = dict(status='passed', kind='completed-qualification-prefix-with-preserved-failures',
            compiler_key=failed['compiler_key'], tool_key=failed['tool_key'],
            strict_commands=36, strict_qualification='passed', workspace_rust_passed=rust_passed, workspace_rust_ignored=rust_ignored,
            std_preparations='both passed', observable_commands=38, observable_qualification='failed',
            failed_observable_command='off-unmapped-exported', failure='VM unavailable foreign call pthread_mutexattr_init',
            failed_export_artifact_sha256=launch['artifact_sha256'], performance_claim=False,
            archive=dict(path=archive.name, bytes=archive.stat().st_size, sha256=sha(archive.read_bytes()),
                         members=len(files), raw_bytes=sum(item['bytes'] for item in files.values()),
                         all_member_hashes_verified=True, all_original_hashes_rechecked=True),
            source_runs=NAMES, original_raw_data_retained=True, compiler_binaries_and_targets_included=False)
        write_json(OUT / 'summary.json', summary)
        record.update(status='passed', finished_at=time.time(), archive=summary['archive'])
        write_json(WORK / 'summary.json', record)
        write_json(OUT / 'packaging-receipt.json', record)
        print(json.dumps(summary))
except BaseException as error:
    record.update(status='failed', error=repr(error), finished_at=time.time())
    write_json(WORK / 'summary.json', record)
    raise
