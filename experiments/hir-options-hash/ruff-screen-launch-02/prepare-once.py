#!/usr/bin/env python3
"""Bind actual closed proofs and normally wait for one metadata preparation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
OUT = ROOT / '.work/ruff-options-hash-screen02-preparation-execution-01'
SOURCE_SHA = 'a25b8ff8ab4bf873c5a4ba8e6e74b985374281058bcd65263499e88c19ad14d6'
TEMPLATE_SHA = '06a087bf9b67663aca0c235c1c54a4879dea55f4ed79819cec9e9c29275903e4'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ref(path):
    return dict(path=str(path), sha256=sha(path))


def read(path):
    path = Path(path)
    require(path.resolve(strict=True) == path and path.is_file()
            and path.stat().st_size <= 32*2**20, 'bounded ordinary metadata required')
    return json.loads(path.read_bytes())


def write(path, value, mode='x'):
    with path.open(mode) as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    require(Path.cwd() == R and sys.dont_write_bytecode and not sys.flags.optimize,
            'R cwd and unoptimized Python -B required')
    require(sha(HERE/'sources.json') == SOURCE_SHA
            and sha(HERE/'binding-template.json') == TEMPLATE_SHA, 'reviewed source bindings changed')
    sources = read(HERE/'sources.json')
    require(len(sources['files']) == 124, 'source count differs')
    for path, digest in sources['files'].items():
        require(sha(path) == digest, 'reviewed source changed: '+path)
    require(not os.path.lexists(OUT) and not os.path.lexists(HERE/'packet-01'), 'fresh preparation required')
    binding = read(HERE/'binding-template.json')
    binding['proofs']['publication_outer']['path'] = str(
        X/'.work/experiments/hir-options-hash-exporter-publication-supervisor-02/status.json')
    for row in binding['proofs'].values():
        row['sha256'] = sha(row['path'])
    published = read(binding['proofs']['published_tools']['path'])
    require(published['tool_key'] == '89cb2751d9e6cfd4a9572dd8ab5405fae7480350bc9198bc5f1bc79fc35bceac',
            'actual qualified candidate differs')
    binding['candidate_tool_key'] = published['tool_key']
    strict = read(binding['proofs']['strict_plan']['path'])
    cf = os.environ.get('__CF_USER_TEXT_ENCODING')
    require(type(cf) is str and cf, 'observed CF startup environment required')
    environment = dict(strict['child_environment'], TMPDIR=str(OUT/'tmp')+'/', __CF_USER_TEXT_ENCODING=cf)
    binding['preparation_environment'] = environment
    OUT.mkdir()
    (OUT/'tmp').mkdir()
    write(OUT/'binding.json', binding)
    argv = ['/opt/homebrew/bin/python3', '-B', str(HERE/'prepare.py'),
            '--binding', str(OUT/'binding.json'), '--binding-sha256', sha(OUT/'binding.json')]
    record = dict(status='starting', parent_pid=os.getpid(), parent_parent_pid=os.getppid(),
        started_at=time.time(), source=ref(__file__), sources=ref(HERE/'sources.json'),
        binding=ref(OUT/'binding.json'), command=argv, cwd=str(R), environment=environment,
        signals=0, retries=0, child_may_be_live=True,
        canonical_policy='Child preparer owns canonical lock; parent holds none.')
    write(OUT/'record.json', record)
    with (OUT/'stdout').open('xb') as stdout, (OUT/'stderr').open('xb') as stderr:
        child = subprocess.Popen(argv, cwd=R, env=environment, stdin=subprocess.DEVNULL,
                                 stdout=stdout, stderr=stderr)
        try:
            record.update(child_pid=child.pid, child_started_at=time.time())
            write(OUT/'record.json', record, 'w')
        finally:
            code = child.wait()
    record.update(status='finished', returncode=code, finished_at=time.time(), child_may_be_live=False,
                  stdout=ref(OUT/'stdout'), stderr=ref(OUT/'stderr'))
    write(OUT/'record.json', record, 'w')
    require(code == 0, 'preparation child failed; actual closed attempt retained')
    packet = HERE/'packet-01'
    require(sorted(p.name for p in packet.iterdir()) ==
            ['inputs.json', 'launch-ab.json', 'plan.json', 'preparation.json'], 'packet membership differs')
    prepared = read(packet/'preparation.json')
    require(prepared['status'] == 'passed' and prepared['pid'] == child.pid
            and prepared['parent_pid'] == os.getpid()
            and record['child_started_at'] <= prepared['finished_at'] <= record['finished_at'],
            'preparation proof differs')
    record.update(packet={p.name:ref(p) for p in sorted(packet.iterdir())}, preparation_verified=True)
    write(OUT/'record.json', record, 'w')
    print(json.dumps(ref(OUT/'record.json'), sort_keys=True))


if __name__ == '__main__':
    main()
