"""One bounded control suite and twelve balanced lookup pairs; no compilation."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
WORK = ROOT / '.work/runtime-lookup-comparison-01'
FROZEN = HERE / 'inputs.json'
PLAN = HERE / 'plan.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, text):
    if not ok:
        raise RuntimeError(text)


def main():
    require(len(sys.argv) == 2 and sha(FROZEN) == sys.argv[1], 'exact input freeze required')
    frozen, plan = json.loads(FROZEN.read_text()), json.loads(PLAN.read_text())
    require(Path.cwd() == ROOT and sys.dont_write_bytecode and not sys.flags.optimize, 'fixed Python invocation required')
    def guard():
        require(sha(FROZEN) == sys.argv[1], 'freeze changed')
        for path, digest in frozen['files'].items():
            require(sha(path) == digest, 'frozen source changed: ' + path)
        require(str(Path(sys.executable).resolve()) == frozen['python']['path']
                and sha(sys.executable) == frozen['python']['sha256'], 'Python changed')
    guard()
    spec = importlib.util.spec_from_file_location('lookup_owned', ROOT / 'experiments/stable-cgu/owned_stage.py')
    owned = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owned)
    WORK.mkdir(exist_ok=False)
    receipt = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(),
        started_at=time.time(), inputs_sha256=sys.argv[1], children=[], observations=[],
        compiler_commands=0, application_benchmark=False, environment=dict(os.environ))
    def save():
        owned.write(WORK / 'receipt.json', receipt)
    save()
    try:
        with owned.workload_lock(Path(plan['lock']), 600):
            receipt.update(status='running', admitted_at=time.time(), free_bytes_before=owned.disk(ROOT, 16))
            save()
            guard()
            (WORK / 'inputs').mkdir()
            for path, digest in frozen['files'].items():
                owned.disk(ROOT, 9)
                dest = WORK / 'inputs' / digest
                if not dest.exists():
                    with dest.open('xb') as stream:
                        stream.write(Path(path).read_bytes())
                require(sha(dest) == digest, 'retained input differs')
            for index, child in enumerate(plan['children']):
                guard()
                owned.disk(ROOT, 9)
                out = WORK / 'commands' / f'{index:03d}'
                try:
                    result = owned.run(child['command'], cwd=ROOT, env=plan['environment'], out=out, capacity_root=ROOT)
                finally:
                    if (out / 'receipt.json').exists():
                        receipt['children'].append(dict(path=str(out / 'receipt.json'), sha256=sha(out / 'receipt.json')))
                        save()
                stdout, stderr = (out / 'stdout').read_text(), (out / 'stderr').read_text()
                if child['kind'] == 'controls':
                    require(not stdout and stderr.endswith('\nOK\n') and 'skipped=' not in stderr,
                            'complete unfiltered runtime controls required')
                    receipt['controls_output'] = stderr
                else:
                    require(not stderr, 'lookup emitted diagnostics')
                    row = json.loads(stdout)
                    require(row['mode'] == child['mode'] and row['runtime_key'] == row['identity_digest'] == plan['runtime_key']
                            and row['std_key'] == plan['std_key'] and row['runtime_sysroot'] == plan['runtime_sysroot']
                            and row['std_sysroot'] == plan['std_sysroot'], 'lookup changed the installation identity')
                    row.update(pair=child['pair'], warmup=child['warmup'], child_index=index,
                        command_seconds=result['finished_at']-result['started_at'], child_cpu=result['child_cpu'])
                    receipt['observations'].append(row)
                guard()
                save()
            require(len(receipt['children']) == 27 and len(receipt['observations']) == 26, 'incomplete comparison')
            pairs = []
            for index in range(12):
                rows = {r['mode']: r for r in receipt['observations'] if not r['warmup'] and r['pair'] == index}
                require(set(rows) == {'baseline', 'candidate'}, 'missing paired lookup')
                pairs.append(dict(pair=index, lookup_difference_seconds=rows['candidate']['lookup_seconds']-rows['baseline']['lookup_seconds'],
                    cpu_difference_seconds=rows['candidate']['lookup_cpu_seconds']-rows['baseline']['lookup_cpu_seconds']))
            receipt.update(status='passed', finished_at=time.time(), pairs=pairs,
                median_lookup_seconds={mode:statistics.median(r['lookup_seconds'] for r in receipt['observations']
                    if r['mode'] == mode and not r['warmup']) for mode in ['baseline','candidate']},
                free_bytes_after=owned.disk(ROOT, 9))
            for digest in frozen['files'].values():
                require(sha(WORK / 'inputs' / digest) == digest, 'retained input changed')
            save()
            print(json.dumps(dict(status=receipt['status'], medians=receipt['median_lookup_seconds'], pairs=pairs)))
    except BaseException as error:
        receipt.update(status='failed', error=repr(error), finished_at=time.time())
        save()
        raise


if __name__ == '__main__':
    main()
