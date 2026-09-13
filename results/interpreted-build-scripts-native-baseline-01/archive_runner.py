"""Archive the three fixed completed native-baseline attempts, without targets."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/stable-cgu'))
from owned_stage import CANONICAL_LOCK, workload_lock, sha, write, require, disk

def main():
    output = ROOT / 'results/interpreted-build-scripts-native-baseline-01'
    receipt_path = ROOT / '.work/interpreted-build-scripts-archive-01.json'
    receipt = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
        canonical_lock=str(CANONICAL_LOCK), wait_seconds=600, runner_sha256=sha(Path(__file__)),
        compiler_or_test_commands=0)
    write(receipt_path, receipt)
    try:
        with workload_lock(CANONICAL_LOCK, 600):
            disk(ROOT); receipt.update(status='running', admitted_at=time.time()); write(receipt_path, receipt)
            selected, controls, plans, natives = set(), [], [], []
            def select(path):
                path = Path(path)
                require(path.resolve(strict=True) == path and not path.is_symlink(), 'unexpected archive input alias')
                if path.is_dir():
                    for child in sorted(path.iterdir()): select(child)
                else:
                    require(path.is_file() and path.is_relative_to(ROOT), 'unowned archive input')
                    selected.add(path)
            def snapshots(work, expected):
                stage_path = work / ('receipt.json' if (work / 'receipt.json').exists() else 'summary.json')
                stage = json.loads(stage_path.read_bytes())
                require(sha(work / 'source-snapshots.json') == stage['source_snapshots_sha256'],
                    'historical source snapshot index differs')
                rows = json.loads((work / 'source-snapshots.json').read_bytes())
                require({path: row['sha256'] for path, row in rows.items()} == expected,
                    'historical source index differs from frozen inputs')
                for row in rows.values(): require(sha(row['copy']) == row['sha256'], 'historical source snapshot changed')
                select(work / 'source-snapshots.json'); select(work / 'sources')
            def child(path):
                row = json.loads(path.read_bytes())
                require(row['status'] == 'finished' and type(row['returncode']) is int, 'child is not terminal')
                for stream in ['stdout', 'stderr']:
                    require(sha(path.parent / stream) == row[stream + '_sha256'], 'raw child stream changed')
                return row
            def supervisor(kind, number, expected):
                base = ROOT / '.work/experiments' / f'interpreted-build-scripts-{kind}-supervisor-{number:02d}'
                row = json.loads((base / 'status.json').read_bytes())
                require(row['status'] == 'finished' and row['returncode'] == expected
                    and sha(base / 'plan.json') == row['plan_sha256']
                    and sha(base / 'command.log') == row['log_sha256'], 'supervisor terminal/proof mismatch')
                select(base)
                return row
            timeout = ROOT / '.work/interpreted-build-scripts-controls-03'
            failed = json.loads((timeout / 'summary.json').read_bytes())
            require(failed['status'] == 'failed' and failed.get('admitted_at') is None
                and failed['lock_wait_seconds'] == 600 and not (timeout / 'command').exists()
                and failed['finished_at'] - failed['started_at'] >= 600,
                'historical zero-child admission failure differs')
            for name in ['runner.py', 'frozen-inputs.json', 'summary.json']: select(timeout / name)
            failed_sup = supervisor('controls', 3, 1)
            require(failed_sup['child_pid'] == failed['pid'], 'timeout helper differs')
            controls.append(dict(attempt=3, tests=0, status='failed before admission',
                error=failed['error'], source=failed['source_revision'], helper=failed['pid']))
            for number, count, control_number in [(1, 6, 1), (2, 7, 2), (3, 8, 4)]:
                work = ROOT / '.work' / f'interpreted-build-scripts-controls-{control_number:02d}'
                row = json.loads((work / 'summary.json').read_bytes()); actual = child(work / 'command/receipt.json')
                require(row['status'] == 'passed' and row['tests'] == count and actual['returncode'] == 0
                    and sha(work / 'command/receipt.json') == row['command_receipt_sha256'], 'pure control proof differs')
                text = (work / 'command/stderr').read_text()
                require(re.findall(r'^Ran (\d+) tests in [\d.]+s$', text, re.M) == [str(count)]
                    and re.search(r'^OK$', text, re.M), 'actual pure controls differ')
                for name in ['runner.py', 'frozen-inputs.json', 'summary.json', 'command']: select(work / name)
                snapshots(work, row['inputs']); sup = supervisor('controls', control_number, 0)
                require(actual['supervisor_pid'] == row['pid'] == sup['child_pid'], 'pure control process binding differs')
                controls.append(dict(attempt=control_number, tests=count, status='passed', helper=row['pid'], child=actual['pid'], source=row['source_revision']))
                work = ROOT / '.work' / f'interpreted-build-scripts-plan-{number:02d}'
                plan_path = ROOT / 'experiments/interpreted-build-scripts' / f'planned-native-{number:02d}.json'
                plan = json.loads(plan_path.read_bytes()); row = json.loads((work / 'receipt.json').read_bytes())
                require(row['status'] == 'passed' and sha(plan_path) == row['plan_sha256']
                    and len(row['commands']) == 14, 'metadata plan qualification differs')
                for ref in row['commands']:
                    path = Path(ref['path']); require(sha(path) == ref['sha256'] and child(path)['returncode'] == 0, 'metadata child differs')
                select(work); select(plan_path); snapshots(work, plan['inputs'])
                supervisor('plan', number, 0); plans.append(dict(attempt=number, sha256=sha(plan_path), metadata_children=14))
                work = ROOT / '.work' / f'interpreted-build-scripts-native-{number:02d}'
                row = json.loads((work / 'receipt.json').read_bytes())
                require(row['status'] in ['passed', 'failed'] and row['sources_restored'] is True, 'native attempt not terminal/restored')
                if number < 3: require(row['status'] == 'failed', 'historical failure was relabeled')
                require({str(p.relative_to(work / 'fixture')): sha(p) for p in (work / 'fixture').rglob('*') if p.is_file()}
                    == plan['fixture'], 'actual restored fixture differs')
                snapshots(work, plan['inputs'])
                for name in ['receipt.json', 'fixture', 'commands']: select(work / name)
                completed = []
                if (work / 'records.json').exists():
                    select(work / 'records.json'); completed = json.loads((work / 'records.json').read_bytes())
                    if row['status'] == 'passed':
                        require(sha(work / 'records.json') == row['records_sha256']
                            and len(completed) == row['cargo_commands'] == 28
                            and row['successful_cases'] == 19 and row['compile_rejections'] == 8
                            and row['wrong_value_rejections'] == 1, 'successful native baseline result differs')
                    for state in completed:
                        for artifact in state['retained_artifacts'].values():
                            require(sha(artifact['copy']) == artifact['sha256'], 'retained native artifact differs')
                cargo = []
                for ref in row['commands']:
                    path = Path(ref['path']); require(sha(path) == ref['sha256'], 'native child receipt changed')
                    actual = child(path); cargo.append(dict(pid=actual['pid'], returncode=actual['returncode']))
                # A terminal validator failure can precede that command's normal
                # artifact copy. Preserve exact paths from its raw Cargo JSON.
                if len(completed) < len(cargo):
                    last = work / 'commands' / f'{len(cargo)-1:03d}' / 'cargo/stdout'
                    for line in last.read_text().splitlines():
                        if not line.startswith('{'): continue
                        message = json.loads(line)
                        if message.get('reason') == 'compiler-artifact':
                            for name in message['filenames']:
                                path = Path(name); require(path.is_relative_to(work / 'targets'), 'native artifact escaped owned target'); select(path)
                        elif message.get('reason') == 'build-script-executed':
                            path = Path(message['out_dir']); require(path.is_relative_to(work / 'targets'), 'script output escaped target')
                            select(path)
                            for name in ['stdout', 'stderr', 'root-output']: select(path.parent / 'run' / name)
                sup = supervisor('native', number, 0 if row['status'] == 'passed' else 1)
                require(sup['child_pid'] == row['pid'], 'native helper process differs')
                natives.append(dict(attempt=number, status=row['status'], error=row.get('error'), sources_restored=True,
                    cargo_commands=cargo, fully_validated_states=len(completed), helper=row['pid'], supervisor=sup['supervisor_pid']))
            select(Path(__file__))
            output.mkdir(parents=True, exist_ok=False)
            manifest = {}
            archive = output / 'evidence.tar.gz'
            with tarfile.open(archive, 'w:gz', compresslevel=6) as tar:
                for path in sorted(selected):
                    disk(ROOT); data = path.read_bytes(); name = str(path.relative_to(ROOT))
                    info = tarfile.TarInfo(name); info.size = len(data); info.mode = path.stat().st_mode & 0o777; info.mtime = 0
                    tar.addfile(info, io.BytesIO(data))
                    manifest[name] = dict(source=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            with tarfile.open(archive, 'r:gz') as tar:
                members = tar.getmembers(); require(len(members) == len(manifest), 'archive member count differs')
                for member in members:
                    require(member.isfile() and member.name in manifest
                        and hashlib.sha256(tar.extractfile(member).read()).hexdigest() == manifest[member.name]['sha256'], 'archive member differs')
            for item in manifest.values(): require(sha(item['source']) == item['sha256'], 'input changed while archiving')
            write(output / 'manifest.json', manifest)
            result = dict(controls=controls, plans=plans, native_attempts=natives, interpreted_build_scripts=False,
                performance_claim=False, archive=dict(path='evidence.tar.gz', sha256=sha(archive), bytes=archive.stat().st_size,
                members=len(manifest), all_member_hashes_verified=True))
            write(output / 'summary.json', result)
            receipt.update(status='passed', finished_at=time.time(), archive=result['archive'])
            write(receipt_path, receipt); write(output / 'archive-receipt.json', receipt)
            print(json.dumps(result, indent=2))
    except BaseException as error:
        receipt.update(status='failed', finished_at=time.time(), error=repr(error)); write(receipt_path, receipt); raise

if __name__ == '__main__': main()
