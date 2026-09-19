#!/usr/bin/env python3
"""Run the ordinary Ruff workflow once, retaining instrumented HIR evidence."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import time

OWNER = Path(__file__).resolve().parents[2]
R_OWNER = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
WORK = OWNER / '.work/ruff-hir-diagnostic-supervision-01'
RUN_ID = 'runtime-ruff-hir-diagnostic-01'
SOURCE = R_OWNER / '.work/sources/ruff'
RUNTIME_KEY = 'eca3d1317ba4c852d64de435aa0f0e5d87ae63bd4eb96cfafacc7b0a85841d03'
STD_KEY = 'e4d1cd29bf4dbac5f9cbf6a92c77a562b89f7079c4474653f180346a00f24b63'
CANONICAL_LOCK = '/Users/danluu/dev/rust-interp/.work/benchmark.lock'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def stamp(path):
    value = Path(path).lstat()
    return [value.st_dev, value.st_ino, value.st_mode, value.st_nlink, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns]


def provider(path):
    path = Path(path)
    resolved = path.resolve(strict=True)
    before, target = stamp(path), stamp(resolved)
    require(resolved.is_file(), 'provider must resolve to a file')
    result = dict(resolved=str(resolved), link_text=os.readlink(path) if path.is_symlink() else None,
                  stamp=before, target_stamp=target, sha256=sha(resolved))
    require(before == stamp(path) and target == stamp(resolved) and path.resolve(strict=True) == resolved,
            'provider changed during hashing')
    return result


def flags(mode):
    enabled = 'true' if mode == 'candidate' else 'false'
    require(mode in ('baseline', 'candidate'), 'unknown HIR diagnostic mode')
    return ['-Zmir-opt-level=3', '-Zhir-body-cache-capture=' + enabled,
            '-Zhir-body-cache-reuse=' + enabled, '-Zincremental-info=true']


def command(tool_key, python):
    result = [python, '-B', str(R_OWNER / 'scripts/bench_e2e_workflow.py'),
        '--project', 'ruff', '--run-id', RUN_ID, '--batch', '--cycles', '1',
        '--jobs', '2', '--native-jobs', '2', '--baseline-jobs', '2', '--candidate-jobs', '2',
        '--native-profile', 'repository', '--native-toolchain', 'nightly-2026-09-08',
        '--native-test-threads', '1', '--initial-mode-order', 'native,baseline,candidate',
        '--runtime-compiler-key', RUNTIME_KEY, '--std-mir', '--std-mir-key', STD_KEY,
        '--baseline-tool-key', tool_key, '--candidate-tool-key', tool_key,
        '--comparison-engine', 'jit', '--build-metrics', '--verify-restoration',
        '--guest-mir-opt-level', '3', '--inline-leaves', '--baseline-inline-leaves',
        '--candidate-jit-resumable-calls', '--baseline-jit-resumable-calls',
        '--candidate-jit-persistent-registers', '--baseline-jit-persistent-registers',
        '--trap-unsupported-calls', '--run-try-callbacks', '--instruction-limit', '1000000000',
        '--allocation-limit', '150000', '--cargo-timings', '--minimum-free-gib', '16',
        '--workload-lock', CANONICAL_LOCK, '--lock-wait-seconds', '600']
    for mode, option in [('baseline', '--baseline-guest-rustflag='), ('candidate', '--guest-rustflag=')]:
        result += [option + flag for flag in flags(mode)[1:]]
    return result


def observed_hir(rows):
    captures = re.compile(r'^\[hir-body-capture\] (\S+) (\S+) (.+)$')
    hits = re.compile(r'^\[hir-body-reuse\] (\S+) hit cache_hits=1 verify_tree=1 verify_journal=1 verify_poststate=1 S=(\d+) E=(\d+)$')
    events = []
    for row in rows:
        if row['mode'] == 'native':
            continue
        for index, call in enumerate(row['calls']):
            for line_number, line in enumerate(call['stderr'].splitlines(), 1):
                if not line.startswith(('[hir-body-capture]', '[hir-body-reuse]')):
                    continue
                event = dict(mode=row['mode'], cycle=row['cycle'], state=row['state'], phase=row['phase'],
                    call=index, stderr_line=line_number, raw=line)
                hit = hits.fullmatch(line)
                if hit:
                    name, start, end = hit.groups()
                    require(0 < int(start) < int(end) <= 0xFFFFFF00, 'invalid verified HIR hit bounds')
                    event.update(name=name, kind='hit', start=int(start), end=int(end), cache_hits=1)
                else:
                    capture = captures.fullmatch(line)
                    require(capture is not None, 'malformed HIR diagnostic event')
                    name, state_name, fields = capture.groups()
                    parts = fields.split()
                    values = {}
                    for part in parts:
                        key, value = part.split('=', 1)
                        require(key not in values and value.isdecimal(), 'malformed HIR event field')
                        values[key] = int(value)
                    require(set(values) == {'S', 'E', 'events', 'cache_hits', 'body_codec', 'prepared_values',
                        'cold_materialization_audit', 'hit_materializer', 'body_bytes', 'body_ast', 'param_ast',
                        'trait_entries', 'trait_candidates', 'external_refs'} and values['cache_hits'] == 0
                        and values['body_codec'] == values['prepared_values'] == values['cold_materialization_audit'] == 1
                        and values['hit_materializer'] == 0 and 0 <= values['S'] <= values['E'] <= 0xFFFFFF00,
                        'HIR event assurance fields differ')
                    event.update(name=name, kind=state_name, fields=values, cache_hits=0)
                require(row['mode'] == 'candidate', 'cache-off compiler reported a HIR cache event')
                events.append(event)
    counts = Counter(event['kind'] for event in events)
    return dict(events=events, event_counts=dict(sorted(counts.items())), observed_hits=counts['hit'],
        coverage_scope='Observed stderr events only; prefilter rejections are silent and function names are not globally unique.',
        instrumented=True, timing_scope='diagnostic only; incremental-info and Cargo timing reports enabled',
        performance_target_qualified=False)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--freeze-sha256', required=True)
    args = parser.parse_args()
    require(Path.cwd() == OWNER and sys.dont_write_bytecode and sys.flags.optimize == 0, 'fixed owner/Python required')
    require(sha(args.freeze) == args.freeze_sha256, 'Ruff diagnostic freeze differs')
    frozen, plan = read(args.freeze), read(args.plan)
    require(plan['owner'] == str(OWNER) and plan['runtime_owner'] == str(R_OWNER)
            and plan['command'] == command(plan['tool_key'], plan['python']['path'])
            and dict(os.environ) == plan['environment'] and plan['environment']['CARGO_TERM_VERBOSE'] == 'true',
            'Ruff diagnostic plan/environment differs')
    def sources():
        require(sha(args.freeze) == args.freeze_sha256 and str(args.plan) in frozen['files'], 'diagnostic plan freeze changed')
        for name, digest in frozen['files'].items():
            path = Path(name)
            require(path.resolve(strict=True) == path and path.is_file() and sha(path) == digest,
                    'diagnostic source/proof/provider changed: ' + name)
        require(str(Path(sys.executable).resolve()) == plan['python']['resolved']
                and sha(sys.executable) == plan['python']['sha256'], 'diagnostic Python differs')
        require(list(os.uname()) == plan['platform'], 'diagnostic host platform changed')
        for name, row in plan['executors'].items():
            require(provider(name) == row, 'executor route or bytes changed')
    sources()
    spec = importlib.util.spec_from_file_location('ruff_diagnostic_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
    owned = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owned)
    sys.path.insert(0, str(R_OWNER / 'scripts'))
    from runtime_compiler import load_runtime_compiler
    from runtime_tools import validate_tool_runtime
    from interpreter import installed_tools
    from std_mir_source_paths import load as load_std, namespace_for, tree_files
    from verify_repeated_workflow import verify
    from qualify_custom_compiler import compiler_routes
    compiler = load_runtime_compiler(R_OWNER, RUNTIME_KEY)
    tools, key = installed_tools(plan['tool_key'])
    std = load_std(R_OWNER, STD_KEY, compiler, namespace_for('source-paths-v2-shared', 'unused'), rehash=True)
    inventory = read(plan['source_inventory']['path'])
    require(sha(plan['source_inventory']['path']) == plan['source_inventory']['sha256'], 'Ruff source inventory differs')
    def guard():
        sources()
        require(load_runtime_compiler(R_OWNER, RUNTIME_KEY) == compiler, 'runtime compiler changed')
        require(installed_tools(key) == (tools, key), 'tool selection changed')
        validate_tool_runtime(tools, key, compiler)
        require(read(tools / 'compiler.json') == plan['runtime_composition'], 'tool composition changed')
        require(load_std(R_OWNER, STD_KEY, compiler, namespace_for('source-paths-v2-shared', 'unused')) == std,
                'prepared shared std changed')
        for module in list(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename and filename.startswith('/Users/danluu/dev/rust-interp'):
                require(str(Path(filename).resolve()) in frozen['files'], 'unfrozen diagnostic module: ' + filename)
        for name, row in plan['configuration'].items():
            path = Path(name)
            require(path.exists() == row['exists'] and not path.is_symlink(), 'diagnostic configuration route changed')
            if row['exists']:
                require(sha(path) == row['sha256'], 'diagnostic configuration changed')
    def source_bytes():
        total = 0
        for index, (name, row) in enumerate(inventory.items()):
            if index % 256 == 0:
                owned.disk(OWNER, 9)
            path = SOURCE / name
            require(path.parent.resolve(strict=True) == path.parent, 'indirect Ruff source parent')
            before = path.lstat()
            if row['kind'] == 'symlink':
                require(path.is_symlink() and os.readlink(path) == row['target']
                        and path.resolve(strict=True).is_relative_to(SOURCE), 'Ruff source link changed')
                data = os.fsencode(os.readlink(path))
            else:
                require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                        and bool(before.st_mode & 0o111) == (row['mode'] == '100755'), 'Ruff source mode changed')
                data = path.read_bytes()
            require(len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], 'Ruff source bytes changed')
            after = path.lstat()
            require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                    (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'Ruff changed during validation')
            total += len(data)
        found = set()
        for directory, dirs, files in os.walk(SOURCE, followlinks=False):
            if Path(directory) == SOURCE:
                require('.git' in dirs and not (SOURCE / '.git').is_symlink(), 'Ruff Git owner differs')
                dirs.remove('.git')
            for name in [*dirs, *files]:
                path = Path(directory) / name
                if path.is_symlink() or not path.is_dir():
                    found.add(str(path.relative_to(SOURCE)))
        require(len(inventory) == 11119 and total == 89102713
                and found == set(inventory) | {'.rust-interp-owned.json'}, 'Ruff source membership differs')
    def payloads():
        require(tree_files(compiler.sysroot) == compiler.identity['files'], 'installed runtime bytes changed')
        require(tree_files(std[0]) == std[3]['sysroot_files'], 'prepared std bytes changed')
        for name, row in plan['providers'].items():
            owned.disk(OWNER, 9)
            require(provider(name) == row, 'native compiler or SDK provider changed: ' + name)
        for name, row in plan['provider_directories'].items():
            path = Path(name)
            require(path.is_dir() and str(path.resolve(strict=True)) == row['resolved']
                    and (os.readlink(path) if path.is_symlink() else None) == row['link_text'],
                    'native compiler or SDK directory route changed')
    require(not WORK.exists() and not (R_OWNER / '.work/runs' / RUN_ID).exists()
            and not (R_OWNER / 'results' / RUN_ID).exists(), 'Ruff diagnostic outputs must be fresh')
    WORK.mkdir(parents=True)
    (WORK / 'tmp').mkdir()
    record = dict(status='starting', owner=str(OWNER), runtime_owner=str(R_OWNER), pid=os.getpid(), parent_pid=os.getppid(),
        started_at=time.time(), freeze_sha256=args.freeze_sha256, plan_sha256=sha(args.plan), instrumented=True,
        performance_qualified=False, timing_scope='diagnostic only')
    def save():
        owned.write(WORK / 'receipt.json', record)
    save()
    try:
        guard()
        source_bytes()
        payloads()
        total = 0
        for name, digest in frozen['files'].items():
            owned.disk(OWNER, 9)
            data = Path(name).read_bytes()
            total += len(data)
            require(len(data) <= 32 * 2**20 and total <= 96 * 2**20, 'Ruff diagnostic input retention exceeds bound')
            path = WORK / 'inputs' / name.lstrip('/')
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as output:
                output.write(data)
            require(sha(path) == digest and path.stat().st_nlink == 1, 'Ruff diagnostic input copy differs')
        record.update(status='running', free_bytes_before=owned.disk(OWNER, 16), retained_input_bytes=total)
        save()
        # The ordinary workflow owns the canonical lock. Holding another
        # descriptor here would deadlock the child at admission.
        try:
            owned.run(plan['command'], cwd=R_OWNER, env=plan['environment'], out=WORK / 'workflow', capacity_root=R_OWNER)
        finally:
            if (WORK / 'workflow/receipt.json').exists():
                record['child'] = read(WORK / 'workflow/receipt.json')
                save()
                try:
                    source_bytes()
                    record['restored_source_bytes_verified'] = True
                except BaseException as source_error:
                    record['restored_source_bytes_verified'] = False
                    record['source_validation_error'] = repr(source_error)
                    raise
                finally:
                    save()
        guard()
        source_bytes()
        payloads()
        report_path = R_OWNER / 'results' / RUN_ID / 'summary.json'
        report = read(report_path)
        verification = verify(report, compiler_flags={mode: flags(mode) for mode in ['baseline', 'candidate']})
        rows = read(R_OWNER / report['raw'] / 'records.json')
        for row in rows:
            for call in row['calls']:
                require(re.search(r'(?mi)stripping debug info with .?rust-objcopy.? failed|'
                    r'failed to execute rust-objcopy|Library not loaded:|dyld\[',
                    call['stdout'] + '\n' + call['stderr']) is None,
                    'application history contains a strip or loader failure')
        argument_proof = []
        for row in rows:
            if row['mode'] == 'native':
                continue
            for call_index, call in enumerate(row['calls']):
                routes = compiler_routes(call['stderr'], tools / 'rust-interp-rustc-wrapper', compiler.rustc)
                selected = [route for route in routes if route['crate'] == 'ruff_linter'
                            and route['target'] == compiler.host and '--test' in route['argv']]
                require(len(selected) == 1, 'missing or ambiguous actual Ruff library-test compiler invocation')
                argv = selected[0]['argv']
                for flag in flags(row['mode']):
                    require([value for value in argv if value.split('=')[0] == flag.split('=')[0]] == [flag],
                            'actual Ruff compiler HIR or diagnostic arguments differ')
                argument_proof.append(dict(mode=row['mode'], cycle=row['cycle'], state=row['state'],
                    call=call_index, actual_route=selected[0], stderr_sha256=hashlib.sha256(call['stderr'].encode()).hexdigest()))
        observations = observed_hir(rows)
        owned.write(WORK / 'workflow-verification.json', verification)
        owned.write(WORK / 'actual-compiler-arguments.json', argument_proof)
        owned.write(WORK / 'hir-observations.json', observations)
        record.update(status='passed', finished_at=time.time(), free_bytes_after=owned.disk(OWNER, 9),
            report=dict(path=str(report_path), sha256=sha(report_path)), observed_hits=observations['observed_hits'],
            event_counts=observations['event_counts'], verification_sha256=sha(WORK / 'workflow-verification.json'),
            hir_observations_sha256=sha(WORK / 'hir-observations.json'))
        save()
    except BaseException as error:
        record.update(status='failed', finished_at=time.time(), error=repr(error))
        save()
        raise


if __name__ == '__main__':
    main()
