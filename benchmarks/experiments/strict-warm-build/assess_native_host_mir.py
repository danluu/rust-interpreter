#!/usr/bin/env python3
"""Archive a saved native-host-MIR correctness run; execute no build or test."""
import argparse
import gzip
import json
from pathlib import Path
import re

from analyzer import compressed, identity, member
from assess import ROOT, require, sha


def read(path):
    return json.loads(path.read_bytes())


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def verify_file(path, expected):
    found = identity(path)
    require(found['sha256'] == expected, f'file hash differs: {path}')
    return found


def assessment(summary):
    return f"""# Native host MIR correctness qualification

The saved first run passed **91 Rust tests and all four real compiler/Cargo histories**, with no skipped tests. This package qualifies the candidate's tested correctness scope; it contains no performance comparison or claim that the 0.5 s target was met.

The policy omits the wrapper-added `-Zalways-encode-mir=yes` only for unselected native host libraries with complete standard-library MIR context, an unambiguous link emission, and no target or response-file arguments. Explicit user flags remain intact. Selected guest export and metadata-only compilation retain their existing policy.

| Retained correctness history | Evidence |
| --- | --- |
| Uncalled type, borrow, constant evaluation and unconditional-panic errors | Candidate, forced full MIR and stock rustc all reject each fixture; the test compares structured diagnostics. All 12 expected failures are retained. |
| Generic, inline and const native consumers | Candidate, forced full MIR and stock rustc produce 39, 43, then 39 across dependency-body edit and restoration; all nine native executions pass. |
| Metadata-only non-generic dependency | Candidate and forced full MIR produce identical selected guest bytecode; both VM executions return 23. |
| Cargo shared host/guest dependency, build script and proc macro | Original/edit/restored states pass in all three modes; six selected guest VM runs and three stock Cargo tests pass. Build-script and proc-macro values follow the real dependency edit. Candidate and forced full MIR bytecode match in each state, differ after the edit, then reproduce the original bytes on restoration. |

The Cargo fixture records separate native-host and target-side dependency invocations, procedural-macro compilation and the selected test artifact. The fixture's selected assertions remain unchanged during edits. The source-state ledger records values 3, 7, 3, and the retained source and final bytecode hashes match restoration. Earlier bytecode snapshots were not retained separately: their hashes and equality/restoration checks come from the saved passing test and ledger. Final bytecode and build-script outputs were rechecked while packaging.

This preserves ordinary native checking within the tested scope. Metadata-only calls remain forced because omitting full MIR there can change diagnostics for otherwise uncalled constant-panic bodies. Internal `rustc_force_inline` diagnostics in otherwise uninstantiated bodies can be forced only by legacy full MIR; that remains a known limitation of the native-host scope. These results do **not** establish universal diagnostic-byte identity for every unstable compiler feature.

Source revision: `{summary['source_commit']}`. Installed tool key: `{summary['tool']['tool_key']}`. The compiler is pinned nightly-2026-09-08, rustc commit `cea272fa356e94bd2ee2cadf376630aa0683867a`, aarch64-apple-darwin, LLVM 23.1.1. The exporter and wrapper were qualified with release debug level 1 (`CARGO_PROFILE_RELEASE_DEBUG=1`) and tool-build incremental compilation disabled. The retained VM was unchanged: all 110 recorded VM source inputs were checked against the candidate source manifest, its current files and the retained VM source manifest. No alternate compiler optimization profile is introduced here.

[summary.json](summary.json) records source, compiler, installed binary, capability, standard-library MIR and test-harness hashes, the three supervisor/child receipts, and compact history outcomes. [evidence.json.gz](evidence.json.gz) retains exact UTF-8 bytes of the build/install records, command logs, stdout/stderr, fixture sources, wrapper traces, source-state ledger and provenance manifests. Every archived member hash and gzip round trip was checked. Compiled outputs and caches remain in `.work`; only their identities are published. Build/test elapsed times in the original receipts are setup/correctness records, not performance samples.

Repackage saved evidence into a fresh directory without executing a workload:

```sh
python3 benchmarks/experiments/strict-warm-build/assess_native_host_mir.py \\
  {summary['source_report']['path']} \\
  --run-id native-host-mir-build-01-reproduced
```
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid output run ID')
    report_path = args.report.resolve(strict=True)
    require(report_path.is_relative_to(ROOT / '.work'), 'report escapes owned worktree')
    raw = report_path.parent
    report, installed = read(report_path), read(raw / 'installed.json')
    require(report['status'] == installed['status'] == 'passed' and report['cwd'] == str(ROOT)
            and report['source_unchanged'] is True, 'expected passed owned correctness run')
    require(report['rust_tests'] == 91 and report['real_native_cargo_tests'] == 4,
            'unexpected qualification suite')
    verify_file(report_path, installed['build_summary_sha256'])
    tool_dir = Path(installed['destination']).resolve(strict=True)
    tool_source = read(tool_dir / 'source.json')
    verify_file(tool_dir / 'source.json', installed['source_manifest_sha256'])
    composition = tool_source['composition']
    require(sha(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()) ==
            installed['tool_key'] == tool_source['tool_key'], 'tool composition key differs')
    require(tool_source['source'] == str(ROOT) and tool_source['source_commit'] ==
            composition['source_commit'] == report['source_commit'], 'tool source identity differs')
    require(tool_source['files'] == composition['source_files'] == report['source_files'],
            'frozen source manifest differs')
    require(composition['compiler'] == installed['compiler'] and
            composition['build_environment'] == report['build_environment'] and
            report['build_environment']['CARGO_PROFILE_RELEASE_DEBUG'] == '1' and
            report['build_environment']['CARGO_INCREMENTAL'] == '0', 'tool build profile differs')
    for name, digest in report['source_files'].items():
        path = (ROOT / name).resolve(strict=True)
        require(path.is_relative_to(ROOT), 'source input escapes worktree')
        verify_file(path, digest)
    binaries = {name: verify_file(tool_dir / name, digest)
                for name, digest in installed['binaries'].items()}
    require(read(tool_dir / 'ready.json') == composition['binaries'] == installed['binaries'],
            'installed binary declarations differ')
    for name, digest in report['binaries'].items():
        require(installed['binaries'][name] == digest, 'tested binary differs from installed binary')
        verify_file(ROOT / '.work/host-mir-target/release' / name, digest)
    capabilities = read(tool_dir / 'capabilities.json')
    require(capabilities['tool_key'] == installed['tool_key'] and
            capabilities['exporter_sha256'] == binaries['rust-interp-mir-export']['sha256'] and
            'native-host-mir-policy' in capabilities['export_options'], 'capability identity differs')
    vm = Path(report['vm']).resolve(strict=True)
    verify_file(vm, report['vm_sha256'])
    require(report['vm_sha256'] == installed['binaries']['rust-interp-vm'], 'retained VM differs')
    vm_source = read(vm.parent / 'source.json')
    require(vm_source['tool_key'] == composition['retained_vm_tool_key'], 'VM provenance differs')
    proof = tool_source['retained_vm_source_proof']
    require(len(proof) == installed['vm_source_inputs_verified'] == 110, 'VM input proof count differs')
    for name, digest in proof.items():
        require(report['source_files'].get(name) == vm_source['files'].get(name) == digest,
                f'retained VM source input differs: {name}')

    archive_paths = [p for p in raw.iterdir() if p.is_file()]
    archive_paths += [tool_dir / name for name in ['source.json', 'ready.json', 'capabilities.json']]
    archive_paths += [vm.parent / 'source.json', ROOT / 'tests/test_native_host_mir.py',
                      ROOT / 'tests/test_borrowck_cache.py', ROOT / 'scripts/workflow_io.py']
    receipts = []
    for command in report['commands']:
        receipt_path = raw / (command['label'] + '-process.json')
        receipt = read(receipt_path)
        require(receipt['status'] == 'finished' and receipt['returncode'] == command['returncode'] == 0
                and receipt['pid'] == command['pid'] and receipt['command'] == command['command']
                and receipt['cwd'] == str(ROOT) and receipt['parent_pid'] == report['supervisor_pid']
                and report['lock_acquired_at'] <= receipt['started_at'] <= receipt['finished_at'] <=
                report['finished_at'], 'process receipt differs')
        receipts.append(dict(**command, receipt=identity(receipt_path)))
    require(len(receipts) == 3, 'missing build/test command')
    rust_log = (raw / 'rust-tests.stdout').read_text() + (raw / 'rust-tests.stderr').read_text()
    counts = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', rust_log)
    require(sum(int(p) for p, _, _ in counts) == 91 and
            all(int(f) == int(i) == 0 for _, f, i in counts), 'Rust suite counts differ')
    python_log = (raw / 'native-cargo-tests.stderr').read_text()
    require('Ran 4 tests' in python_log and '\nOK\n' in python_log and 'skipped' not in python_log,
            'real compiler/Cargo suite did not fully pass')

    histories, compiler_paths, artifacts = [], set(), []
    for fixture in sorted((raw / 'fixtures').iterdir()):
        commands = rows(fixture / 'commands.jsonl')
        invocations = rows(fixture / 'host-mir-invocations.jsonl')
        require(len(commands) == len(invocations) and
                all(a['command'] == b['command'] for a, b in zip(commands, invocations)),
                'fixture environment ledger differs from commands')
        require(commands[0]['command'][1:] == ['-vV'] and commands[0]['returncode'] == 0 and
                commands[0]['stdout'] == installed['compiler'], 'fixture compiler version differs')
        compiler_paths.add(commands[0]['command'][0])
        name = fixture.name.rsplit('-', 1)[0]
        require(re.search(re.escape(name) + r' .* \.\.\. ok\n', python_log),
                'fixture missing from successful test output')
        archive_paths += [p for p in fixture.iterdir() if p.is_file() and p.suffix in {'.jsonl', '.rs', '.py'}]
        runs = [c for c in commands if Path(c['command'][0]).name == 'rust-interp-vm']
        history = dict(test=name, commands=len(commands), passed=True, vm_runs=len(runs),
                       command_log=identity(fixture / 'commands.jsonl'))
        if 'uncalled_errors' in name:
            require(len(commands) == 13 and all(c['returncode'] == 1 for c in commands[1:]),
                    'negative diagnostic cases differ')
            codes = []
            for command in commands[1:]:
                diagnostics = [json.loads(l) for l in command['stderr'].splitlines() if l.startswith('{')]
                codes.append([d['code']['code'] for d in diagnostics if d.get('code')])
            expected = ['E0308'] * 3 + ['E0515'] * 3 + ['E0080'] * 3 + ['unconditional_panic'] * 3
            require(all(code in observed for code, observed in zip(expected, codes)),
                    'expected negative diagnostic code missing')
            history.update(expected_failures=12, diagnostic_codes=sorted(set(expected)))
        else:
            require(all(c['returncode'] == 0 for c in commands), 'positive fixture command failed')
        if 'native_generic' in name:
            outputs = [c['stdout'] for c in commands if Path(c['command'][0]).name == 'consumer']
            require(len(commands) == 28 and outputs == ['39\n'] * 3 + ['43\n'] * 3 + ['39\n'] * 3,
                    'native edit/restoration outputs differ')
            history.update(native_executions=9, outputs_by_state=[39, 43, 39],
                           restored_source=identity(fixture / 'host_helper.rs'))
        if 'metadata_only' in name:
            require(len(commands) == 7 and [c['stdout'] for c in runs] == ['23\n'] * 2,
                    'metadata-only guest did not execute both modes')
            bytecodes = [identity(fixture / mode / 'guest.rbc') for mode in ['candidate', 'legacy']]
            require(bytecodes[0]['sha256'] == bytecodes[1]['sha256'], 'metadata guest bytecode differs')
            artifacts += bytecodes
            history['guest_bytecode_equal'] = True
        if 'cargo_shared' in name:
            require(len(commands) == 16 and [c['stdout'] for c in runs] == ['0\n'] * 6,
                    'Cargo selected guest did not execute every state/mode')
            states = rows(fixture / 'source-states.jsonl')
            require([s['state'] for s in states] == [0, 1, 2] and
                    [s['value'] for s in states] == [3, 7, 3], 'Cargo source history differs')
            for key in ['source_sha256', 'bytecode_sha256']:
                require(states[0][key] == states[2][key] != states[1][key], 'edit/restoration hash differs')
            restored = verify_file(fixture / 'package/shared/src/lib.rs', states[2]['source_sha256'])
            artifacts += [verify_file(fixture / (mode + '.rbc'), states[2]['bytecode_sha256'])
                          for mode in ['candidate', 'legacy']]
            archive_paths += list((fixture / 'traces').rglob('*.json'))
            archive_paths += [p for p in (fixture / 'package').rglob('*') if p.is_file()]
            cargo_commands = [c for c in commands if Path(c['command'][0]).name == 'cargo']
            require(len(cargo_commands) == 9, 'missing Cargo history')
            selected_artifacts = []
            for index, command in enumerate(cargo_commands):
                events = [json.loads(l) for l in command['stdout'].splitlines() if l.startswith('{')]
                outputs = [Path(e['out_dir']) for e in events if e.get('reason') == 'build-script-executed']
                require(len(outputs) == 1, 'Cargo build-script output missing')
                if index >= 6:
                    require((outputs[0] / 'host-value.txt').read_text() == '30', 'restored host value differs')
                    archive_paths += [outputs[0] / 'host-value.txt', outputs[0] / 'generated.rs']
                if index % 3 == 2:
                    require('1 passed' in command['stdout'], 'stock Cargo control test failed')
                    continue
                selected = [e for e in events if e.get('reason') == 'compiler-artifact' and
                            e['target']['name'] == 'host_mir_fixture' and e['profile']['test']]
                require(len(selected) == 1, 'selected Cargo test artifact is ambiguous')
                selected_artifacts.append(dict(state=index // 3, mode=['candidate', 'legacy'][index % 3],
                    filenames=selected[0]['filenames'], test_profile=selected[0]['profile']['test']))
                if index >= 6:
                    sidecars = [Path(p + '.rbc') for p in selected[0]['filenames'] if Path(p + '.rbc').is_file()]
                    require(len(sidecars) == 1, 'selected bytecode sidecar missing')
                    artifacts.append(verify_file(sidecars[0], states[2]['bytecode_sha256']))
            roles = []
            for mode in ['candidate', 'legacy']:
                for state in range(3):
                    traces = [read(p) for p in sorted((fixture / 'traces' / mode / str(state)).glob('*.json'))]
                    helpers = [t for t in traces if '--crate-name' in t['original'] and
                               t['original'][t['original'].index('--crate-name') + 1] == 'host_mir_shared']
                    host = [t for t in helpers if '--target' not in t['original']]
                    guest = [t for t in helpers if '--target' in t['original']]
                    require(len(host) == len(guest) == 1 and host[0]['forced_legacy'] == (mode == 'legacy')
                            and guest[0]['forced_legacy'] is False and
                            any('proc-macro' in t['original'] for t in traces), 'Cargo host/guest roles differ')
                    roles.append(dict(mode=mode, state=state, wrapper_invocations=len(traces),
                                      host_pid=host[0]['pid'], guest_pid=guest[0]['pid']))
            history.update(states=states, restored_source=restored, stock_test_runs=3,
                           guest_bytecode_equal_each_state=True, selected_artifacts=selected_artifacts,
                           cargo_roles=roles, assertions_unchanged_as_checked_by_saved_test=True)
        histories.append(history)
    require(len(histories) == 4 and sum(h['commands'] for h in histories) == 64 and
            sum(h['vm_runs'] for h in histories) == 8 and len(compiler_paths) == 1,
            'fixture inventory differs')
    compiler_path = Path(compiler_paths.pop()).resolve(strict=True)
    compiler_files = [identity(compiler_path), identity(compiler_path.with_name('cargo'))]
    compiler_files += [identity(p) for p in sorted((compiler_path.parent.parent / 'lib').glob('librustc_driver-*.dylib'))]
    std_ready_path = Path(report['std_sysroot']).parent / 'ready.json'
    std_ready = read(std_ready_path)
    require(std_ready['identity']['compiler'] == installed['compiler'], 'std MIR compiler differs')
    std_artifacts = [verify_file(std_ready_path.parent / p, meta['sha256'])
                     for p, meta in std_ready['artifacts'].items()]
    archive_paths.append(std_ready_path)
    archive_paths += [Path(__file__).resolve(), Path(__file__).with_name('analyzer.py'),
                      Path(__file__).with_name('assess.py')]
    members = [member(p) for p in sorted(set(archive_paths))]
    bundle = dict(schema_version=1, description='Exact saved UTF-8 evidence; binaries and caches excluded',
                  members=members)
    payload = json.dumps(bundle, sort_keys=True, separators=(',', ':')).encode() + b'\n'
    archive = compressed(payload)
    decoded = json.loads(gzip.decompress(archive))
    for item in decoded['members']:
        data = item['utf8'].encode()
        require(len(data) == item['bytes'] and sha(data) == item['sha256'] and
                Path(item['path']).read_bytes() == data, 'archived member changed or does not round-trip')
    summary = dict(schema_version=1, status='passed', performance_measurement=False,
        source_commit=report['source_commit'], source_report=identity(report_path),
        source_inputs_verified=len(report['source_files']), source_unchanged=True,
        build_environment=report['build_environment'], rust_tests=91, real_native_cargo_histories=4,
        fixture_commands=64, expected_negative_commands=12, vm_executions=8, commands=receipts,
        tool=dict(tool_key=installed['tool_key'], source_manifest=identity(tool_dir / 'source.json'),
                  capabilities=identity(tool_dir / 'capabilities.json'), binaries=binaries),
        retained_vm=dict(tool_key=vm_source['tool_key'], inputs_verified=110,
                         source_manifest=identity(vm.parent / 'source.json'), binary=identity(vm)),
        compiler=dict(version=installed['compiler'], files=compiler_files),
        std_mir=dict(sysroot=report['std_sysroot'], ready=identity(std_ready_path),
                     metadata_files_verified=len(std_artifacts), artifacts=std_artifacts),
        test_harness=identity(ROOT / 'tests/test_native_host_mir.py'), histories=histories,
        retained_artifacts=artifacts,
        archive=dict(file='evidence.json.gz', bytes=len(archive), sha256=sha(archive),
                     uncompressed_bytes=len(payload), uncompressed_sha256=sha(payload),
                     members=len(members), all_member_hashes_verified=True, exact_round_trip_verified=True))
    out = ROOT / 'results' / args.run_id
    require(not out.exists(), 'refuse to overwrite existing evidence')
    out.mkdir(parents=True)
    (out / 'evidence.json.gz').write_bytes(archive)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    (out / 'assessment.md').write_text(assessment(summary))
    verify_file(out / 'evidence.json.gz', summary['archive']['sha256'])
    print(json.dumps(dict(output=str(out), archive_members=len(members), archive_bytes=len(archive),
                          rust_tests=91, real_histories=4, source_inputs=160, vm_inputs=110)))


if __name__ == '__main__':
    main()
