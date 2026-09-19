#!/usr/bin/env python3
"""Qualify saved metadata and execute only its two missing final Git guards."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time

HERE = Path(__file__).resolve().parent
OWNER = HERE.parents[2]
ORIGINAL = OWNER/'experiments/hir-options-hash/compiler-metadata-03'
WORK = OWNER/'.work/hir-options-hash-compiler-metadata-continuation-01'
PRIOR = OWNER/'.work/hir-options-hash-compiler-metadata-03'
OUTER = OWNER/'.work/experiments/hir-options-hash-compiler-metadata-supervisor-03'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

# Preserve the original module's import association; the revised parser has
# a separate name and is used only to assess already retained ld output.
load('linker_parser', ORIGINAL/'linker_parser.py')
m = load('continued_metadata_original', ORIGINAL/'metadata.py')
parser = load('continued_linker_parser', HERE/'linker_parser.py')
owned = m.owned
read, sha = m.read, m.sha

def saved(plan):
    """Reconcile raw saved children and the exact terminal failure, no probes."""
    terminal = read(PRIOR/'receipt.json')
    outer = read(OUTER/'status.json')
    assert sha(PRIOR/'receipt.json') == plan['prior_receipt_sha256']
    assert terminal['status'] == 'failed' and terminal['compiler_builds'] == 0
    assert terminal['error'] == "RuntimeError('unknown linker architecture grammar')"
    assert len(terminal['commands']) == 48
    assert outer['status'] == 'finished' and outer['returncode'] == 1
    assert outer['child_pid'] == terminal['pid'] and outer['supervisor_pid'] == terminal['parent_pid']
    assert sha(OUTER/'plan.json') == outer['plan_sha256']
    assert sha(OUTER/'command.log') == outer['log_sha256']
    assert outer['started_at'] <= terminal['started_at'] <= terminal['admitted_at'] <= terminal['finished_at'] <= outer['finished_at']
    previous = terminal['admitted_at']
    outputs = []
    for index, (ref, expected) in enumerate(zip(terminal['commands'], plan['original_plan']['children'][:48], strict=True)):
        directory = PRIOR/'commands'/f'{index:03}'
        child = read(directory/'receipt.json')
        assert ref['path'] == str(directory/'receipt.json') and sha(directory/'receipt.json') == ref['sha256']
        assert ref['pid'] == child['pid'] and ref['command'] == child['command'] == expected['argv']
        assert child['cwd'] == expected['cwd'] and child['environment'] == expected['environment']
        assert child['status'] == 'finished' and child['returncode'] in expected['expected']
        assert child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
        assert previous <= child['started_at'] <= child['finished_at'] <= terminal['finished_at']
        previous = child['finished_at']
        streams = []
        for stream in ['stdout', 'stderr']:
            raw = (directory/stream).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == child[stream+'_sha256']
            if stream in expected:
                assert raw == expected[stream].encode()
            streams.append(raw)
        outputs.append((child, *streams))
    assert not (PRIOR/'metadata.json').exists() and not (PRIOR/'linker-probe.json').exists()
    return terminal, outputs

class Stage:
    def __init__(self, digest):
        assert sha(HERE/'inputs.json') == digest
        self.freeze = read(HERE/'inputs.json')
        assert sha(HERE/'plan.json') == self.freeze['plan_sha256']
        self.plan = read(HERE/'plan.json')
        self.original = self.plan['original_plan']
        self.oldfreeze = read(ORIGINAL/'inputs.json')
        assert sha(ORIGINAL/'inputs.json') == self.plan['original_inputs_sha256']
        assert sha(ORIGINAL/'plan.json') == self.oldfreeze['plan_sha256']
        assert read(ORIGINAL/'plan.json') == self.original
        assert Path.cwd() == OWNER and sys.dont_write_bytecode and not sys.flags.optimize
        assert str(Path(sys.executable).resolve(strict=True)) == self.oldfreeze['python']
        expected = self.freeze['launch_environment']
        self.environment = dict(os.environ)
        extra = set(self.environment)-set(expected)
        assert all(self.environment.get(k) == v for k,v in expected.items()) and extra <= {'__CF_USER_TEXT_ENCODING'}
        if extra:
            cf = self.environment['__CF_USER_TEXT_ENCODING'].split(':')
            assert len(cf) == 3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})', v) for v in cf)
            assert int(cf[0], 16 if cf[0].lower().startswith('0x') else 10) == os.getuid() == 501
        for module in list(sys.modules.values()):
            path = getattr(module, '__file__', None)
            if path and path.startswith('/Users/danluu/dev/'):
                assert str(Path(path).resolve(strict=True)) in self.freeze['files'] or str(Path(path).resolve(strict=True)) in self.oldfreeze['files']
        assert not WORK.exists()
        WORK.mkdir();(WORK/'commands').mkdir()
        self.receipt = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
                            commands=[], saved_children=48, compiler_builds=0,
                            candidate_revision=self.original['candidate_revision'], prior_receipt_sha256=self.plan['prior_receipt_sha256'])
        self.save()

    def save(self):
        owned.write(WORK/'receipt.json', self.receipt)

    def guard(self, full):
        assert dict(os.environ) == self.environment
        for name, row in self.freeze['files'].items():
            path = Path(name)
            assert path.resolve(strict=True) == path and m.stamp(path) == row['stamp']
            if full:
                assert sha(path) == row['sha256']
        for name, members in self.plan['prior_membership'].items():
            root = Path(name)
            assert sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()) == members
        m.guard(self.original, self.oldfreeze, full)

    def replay(self):
        terminal, outputs = saved(self.plan)
        cursor = 0
        def consume(argv):
            nonlocal cursor
            expected = self.original['children'][cursor]
            assert expected['argv'] == argv
            child, raw, err = outputs[cursor]
            cursor += 1
            return child, raw, err
        for row in self.original['prefix_children']:
            consume(row['argv'])
        closures = {}
        for name, path in self.original['closure_roots']:
            def inspect(argv, *, text):
                assert text is True
                child, raw, err = consume(argv)
                assert not err
                return m.linker_loads(argv, raw.decode()) if name == 'ld' else raw.decode()
            identity, state = m.loaders.library_closure(Path(path), m.HOST, inspect=inspect)
            closures[name] = dict(identity=identity, state=state)
            assert closures[name] == self.original['closures'][name]
        llvm_row, linker_row, *remaining = self.original['suffix_children']
        assert llvm_row['llvm_version_probe'] and linker_row['linker_probe']
        _, llvm, err = consume(llvm_row['argv'])
        assert not err and llvm.decode() == self.original['llvm']['provider_version']+'\n'
        child, raw, err = consume(linker_row['argv'])
        assert not raw
        linker = parser.parse(err, child['pid'], self.original['linker_expected_loaded'])
        assert cursor == 48 and remaining == self.plan['children']
        return closures, llvm.decode().strip(), linker

    def command(self, row):
        assert row == self.plan['children'][len(self.receipt['commands'])]
        self.guard(False);owned.disk(OWNER, 9)
        directory = WORK/'commands'/f'{len(self.receipt["commands"]):03}'
        try:
            owned.run(row['argv'], cwd=Path(row['cwd']), env=row['environment'], out=directory,
                      expected=tuple(row['expected']), capacity_root=OWNER)
        finally:
            if (directory/'receipt.json').is_file():
                child = read(directory/'receipt.json')
                self.receipt['commands'].append(dict(path=str(directory/'receipt.json'), sha256=sha(directory/'receipt.json'),
                                                      pid=child.get('pid'), command=row['argv']))
                self.save()
        for stream in ['stdout', 'stderr']:
            assert (directory/stream).read_bytes() == row[stream].encode()

    def run(self):
        try:
            with owned.workload_lock(owned.CANONICAL_LOCK, 600):
                self.receipt.update(status='running', admitted_at=time.time(), free_bytes_before=owned.disk(OWNER, 24));self.save()
                self.guard(True)
                closures, llvm, linker = self.replay()
                owned.write(WORK/'linker-probe.json', linker)
                for row in self.plan['children']:
                    self.command(row)
                assert len(self.receipt['commands']) == 2
                self.guard(True)
                # Repeat current loader states after the missing postguards.
                for closure in closures.values():
                    assert m.loaders.library_state(closure['identity']) == closure['state']
                owned.write(WORK/'metadata.json', dict(status='metadata-qualified-not-built', candidate_revision=self.original['candidate_revision'],
                    source_identity=read(m.ACQUIRED)['source_identity'], closures=closures, seeds=self.original['seeds'],
                    sdk_inventory_sha256=hashlib.sha256(json.dumps(self.original['sdk_inventory'], sort_keys=True).encode()).hexdigest(),
                    platform=self.original['platform'], llvm_version=self.original['llvm']['numeric_version'], llvm_provider_version=llvm,
                    network_block=self.original['network_block'], build_environment=self.original['build_environment'],
                    prior_receipt_sha256=self.plan['prior_receipt_sha256'], prior_children=48, continuation_children=2,
                    linker_probe_sha256=sha(WORK/'linker-probe.json')))
                self.receipt.update(status='passed', metadata_sha256=sha(WORK/'metadata.json'), free_bytes_after=owned.disk(OWNER, 9))
        except BaseException as error:
            self.receipt.update(status='failed', error=repr(error));raise
        finally:
            self.receipt['finished_at'] = time.time();self.save()

def main():
    arguments = argparse.ArgumentParser();arguments.add_argument('--inputs-sha256', required=True)
    Stage(arguments.parse_args().inputs_sha256).run()

if __name__ == '__main__':
    main()
