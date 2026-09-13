#!/usr/bin/env python3
"""Package completed Cargo info-cache qualification without running workloads."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(path):
    payload = path.read_bytes()
    return dict(path=str(path), bytes=len(payload), sha256=sha(payload))


def member(path):
    payload = path.read_bytes()
    return dict(path=str(path), bytes=len(payload), sha256=sha(payload), utf8=payload.decode())


def compress(payload):
    stream = io.BytesIO()
    with gzip.GzipFile(filename='', fileobj=stream, mode='wb', mtime=0, compresslevel=9) as output:
        output.write(payload)
    data = stream.getvalue()
    require(gzip.decompress(data) == payload, 'archive does not round-trip')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid run ID')
    report_path = args.report.resolve(strict=True)
    require(report_path.is_relative_to(ROOT / '.work'), 'input is not owned evidence')
    raw = report_path.parent
    report = json.loads(report_path.read_bytes())
    require(report['status'] == 'passed' and report['owner'] == str(ROOT) and
            report['candidate_source_restored'] is True and report['performance_measurement'] is False,
            'expected passed owned correctness qualification')
    require(report['stock_expected_regression_failures'] == 1 and report['stock_existing_tests_passed'] == 2
            and report['candidate_tests_passed'] == 3, 'test counts differ')
    files = [member(report_path)]
    commands = []
    labels = ['compiler-version', 'format-check', 'fetch-locked', 'stock-build', 'stock-regression',
              'candidate-build', 'candidate-regression']
    require([c['label'] for c in report['commands']] == labels, 'qualification sequence differs')
    for command in report['commands']:
        label = command['label']
        path = raw / 'logs' / (label + '-process.json')
        receipt = json.loads(path.read_bytes())
        require(receipt['status'] == 'finished' and receipt['returncode'] == command['returncode'] ==
                command['expected_returncode'] and receipt['command'] == command['command'] and
                receipt['pid'] == command['pid'] and receipt['parent_pid'] == report['supervisor_pid'] and
                receipt['cwd'] == report['source'] and report['lock_acquired_at'] <= receipt['started_at'] <=
                receipt['finished_at'] <= report['finished_at'], 'process receipt differs')
        files.append(member(path))
        for stream in ['stdout', 'stderr']:
            item = member(raw / 'logs' / (label + '.' + stream))
            require(item['sha256'] == command[stream + '_sha256'], 'saved command output differs')
            files.append(item)
        commands.append(dict(**command, receipt=identity(path)))
    stock_log = (raw / 'logs/stock-regression.stdout').read_text()
    candidate_log = (raw / 'logs/candidate-regression.stdout').read_text()
    require('2 passed; 1 failed;' in stock_log and
            re.search(r'failures:\n\s+rustc_info_cache::rustc_info_cache_with_empty_wrappers\s+\ntest result:', stock_log)
            and '3 passed; 0 failed; 0 ignored;' in candidate_log, 'test outcomes do not match the claimed control')
    tools, compositions = [], {}
    for tool in report['tools']:
        for item in [tool['binary'], tool['source_manifest']]:
            require(identity(Path(item['path'])) == item, 'installed tool changed')
        manifest_path = Path(tool['source_manifest']['path'])
        manifest = json.loads(manifest_path.read_bytes())
        composition = manifest['composition']
        require(sha(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()) ==
                tool['tool_key'] == manifest['tool_key'] and composition['cargo_sha256'] ==
                tool['binary']['sha256'] and composition['source_revision'] == report['source_revision'] and
                composition['compiler'] == report['compiler'] and
                composition['environment_overrides'] == report['environment_overrides'],
                'matched tool composition differs')
        require(json.loads((manifest_path.parent / 'ready.json').read_bytes()) ==
                {'cargo': tool['binary']['sha256']}, 'tool ready record differs')
        compositions[tool['mode']] = composition
        tools.append(tool)
        files += [member(manifest_path), member(manifest_path.parent / 'ready.json')]
    require(set(compositions) == {'stock', 'candidate'}, 'missing matched arm')
    stock, candidate = compositions['stock'], compositions['candidate']
    changed = sorted(p for p in stock['source_inventory'] if
                     stock['source_inventory'][p] != candidate['source_inventory'].get(p))
    require(set(stock['source_inventory']) == set(candidate['source_inventory']) and
            changed == [report['source_only_production_difference']] == ['src/util/rustc.rs'],
            'unexpected source difference between matched tools')
    require(all(stock[k] == candidate[k] for k in stock
                if k not in ['mode', 'source_inventory', 'cargo_sha256']), 'build profiles or features differ')
    require(candidate['source_inventory'] == report['original_candidate_inventory'] and
            report['environment_overrides']['CARGO_PROFILE_RELEASE_DEBUG'] == '1', 'candidate source/profile differs')
    for tool in tools:
        mode = tool['mode']
        expected = sha(json.dumps(compositions[mode]['source_inventory'], sort_keys=True).encode())
        require(all(c['source_inventory_sha256'] == expected for c in commands if c['label'].startswith(mode + '-')),
                'build/test source inventory differs from installed tool')
    for item in report['harness'].values():
        require(identity(Path(item['path'])) == item, 'qualified harness changed')
        files.append(member(Path(item['path'])))
    for item in report['compiler_files'].values():
        require(identity(Path(item['path'])) == item, 'compiler/build tools changed')
    source = Path(report['source'])
    for name in ['src/util/rustc.rs', 'tests/testsuite/rustc_info_cache.rs',
                 'tests/testsuite/utils/ext.rs', 'crates/cargo-util/src/process_builder.rs',
                 'Cargo.toml', 'Cargo.lock', 'tests/info_cache_focused.rs']:
        item = member(source / name)
        require(sha(b'file\0' + item['utf8'].encode()) == candidate['source_inventory'][name],
                'retained source snapshot differs')
        files.append(item)
    fixture_files = []
    for moved in report['fixture_moves']:
        directory = Path(moved['retained'])
        require(directory.is_relative_to(raw / 'fixtures'), 'fixture archive escapes owned run')
        for path in sorted(directory.rglob('*')):
            if path.is_file() and not path.is_symlink() and (path.suffix == '.rs' or
                    path.name in ['Cargo.toml', 'Cargo.lock', 'config.toml', '.rustc_info.json']):
                item = member(path)
                files.append(item)
                fixture_files.append({k: item[k] for k in ['path', 'bytes', 'sha256']})
    files.append(member(Path(__file__).resolve()))
    unique = {item['path']: item for item in files}
    payload = json.dumps(dict(schema_version=1, encoding='exact UTF-8 members',
        files=list(unique.values())), separators=(',', ':')).encode() + b'\n'
    archive = compress(payload)
    for item in json.loads(gzip.decompress(archive))['files']:
        data = item['utf8'].encode()
        require(len(data) == item['bytes'] and sha(data) == item['sha256'], 'archived member differs')
    summary = dict(schema_version=1, status='passed', performance_measurement=False,
        source_report=identity(report_path), source_revision=report['source_revision'],
        compiler=report['compiler'], compiler_files=report['compiler_files'],
        environment_overrides=report['environment_overrides'], environment_sha256=report['environment_sha256'],
        source_only_production_difference=changed, source_inputs=len(candidate['source_inventory']),
        candidate_source_restored=True, stock_existing_tests_passed=2, stock_expected_new_regression_failures=1,
        candidate_tests_passed=3, new_regression_wrapper_cases=['normal', 'workspace', 'both'],
        commands=commands, matched_tools=tools, fixture_moves=report['fixture_moves'],
        fixture_source_and_info_cache_files=fixture_files,
        archive=dict(path='evidence.json.gz', bytes=len(archive), sha256=sha(archive),
                     uncompressed_bytes=len(payload), uncompressed_sha256=sha(payload),
                     members=len(unique), all_member_hashes_verified=True, exact_round_trip_verified=True))
    output = ROOT / 'results' / args.run_id
    output.mkdir(exist_ok=False)
    (output / 'evidence.json.gz').write_bytes(archive)
    require(identity(output / 'evidence.json.gz')['sha256'] == summary['archive']['sha256'], 'written archive differs')
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    modes = {t['mode']: t for t in tools}
    (output / 'assessment.md').write_text(f"""# Empty-wrapper Cargo info-cache correctness qualification

The candidate passed all three compiler-info-cache integration tests. The matched stock tool passed both existing tests and failed only the newly added empty-wrapper regression, as expected. This qualifies the behavior change; it is not performance evidence or a claim that the 0.5 s target passed.

The fix makes fingerprinting follow Cargo's existing execution semantics: empty normal/workspace wrappers are not executables. Explicit empty environment values still disable wrappers from Cargo configuration. Nonempty wrapper paths, compiler identities, rustup state, query arguments and query environment remain part of their existing cache validation.

The new test covers empty normal, workspace and both wrapper overrides against nonexistent configured executables. For every case, candidate cold commands miss/update the info cache, warm commands hit without miss/update, and `CARGO_CACHE_RUSTC_INFO=0` continues to disable caching. Existing tests validate ordinary cache reuse, changed compiler paths/timestamps and replacement of real normal/workspace wrappers. The focused integration entry includes the entire upstream info-cache test module, preserving its two existing tests and adding the new regression, plus its ordinary Cargo invocation helper; it does not replace Cargo or compiler work with stubs.

Stock and candidate use Cargo revision `{report['source_revision']}`, the same owned source path, pinned nightly-2026-09-08 compiler, release debug level 1, default Cargo features, two build jobs and disabled incremental tool compilation. Dependencies, compiler settings and build/test command lines are shared. The only differing production input is `src/util/rustc.rs`; both states include the same regression and focused test entry. Executables were retained after test builds so dependency-feature unification cannot silently leave a differently built executable outside qualification.

- Stock key: `{modes['stock']['tool_key']}`.
- Candidate key: `{modes['candidate']['tool_key']}`.
- Candidate source restored; all commands ran while holding the shared workload lock.

[summary.json](summary.json) records matched tool/source/compiler/profile identities, every exact command receipt, expected/actual test outcomes and fixture paths. [evidence.json.gz](evidence.json.gz) retains exact logs, the original supervisor report, source manifests, patch, harness, relevant Cargo implementation/test snapshots, fixture source/configuration and rustc-info cache files. Every archived member and gzip round trip was verified. Executable binaries, build caches and other compiled artifacts stay in `.work`.

Build/test timings in the exact receipts describe setup and correctness work. Any later performance assessment must compare these two matched local executables; comparing this candidate with a differently built distributed Cargo would confound the source change. Cargo has previous optimization exposure and remains excluded from fresh holdouts.

Repackage saved evidence without executing a workload:

```sh
python3 benchmarks/experiments/cargo-info-cache/assess.py \\
  {report_path} --run-id cargo-info-cache-build-01-reproduced
```
""")
    print(json.dumps(dict(output=str(output), archive=summary['archive'], matched_tools=len(tools))))


if __name__ == '__main__':
    main()
