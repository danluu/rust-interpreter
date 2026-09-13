#!/usr/bin/env python3
"""Package existing stable-CGU receipts and logs; launches no build or test."""
import hashlib
import json
from pathlib import Path
import tarfile

root = Path(__file__).resolve().parents[2]
setup = root / '.work/stable-cgu-compiler-setup-01'
build = root / '.work/stable-cgu-compiler-build-01'
out = root / 'results/stable-cgu-compiler-01'
out.mkdir(parents=True, exist_ok=False)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


package = json.loads((build / 'package-05/receipt.json').read_text())
package_provenance = json.loads((build / 'package-05/provenance.json').read_text())
native = json.loads((build / 'native-entry-02/result.json').read_text())
assert native['status'] == 'passed' and len(native['histories']) == 15
assert native['package_provenance_sha256'] == digest(build / 'package-05/provenance.json')
assert native['compiler_sha256'] == package['files']['bin/rustc']
assert native['compiler_unchanged'] and native['package_files_unchanged'] == len(package['files'])
assert package_provenance['package_receipt_sha256'] == digest(build / 'package-05/receipt.json')
controls = {}
for name in ['stage2', 'stage2-option-hash', 'stage2-tests', 'stage2-dist-04']:
    path = build / name / 'receipt.json'
    receipt = json.loads(path.read_text())
    assert receipt['returncode'] == 0
    assert receipt['source_revision'] == package_provenance['source_commit']
    assert receipt['config_sha256'] == package_provenance['bootstrap_sha256']
    controls[name] = {key: receipt.get(key) for key in [
        'command', 'supervisor_pid', 'pid', 'started_at', 'finished_at',
        'lock_wait_seconds', 'free_bytes_before', 'free_bytes_after',
        'returncode', 'log_sha256', 'config_sha256']}
    controls[name]['receipt_sha256'] = digest(path)

members = {}
for path in sorted(setup.iterdir()):
    if path.is_file() and path.suffix != '.xz':
        members['setup/' + path.name] = path
for attempt in sorted(build.iterdir()):
    if attempt.is_file():
        if attempt.suffix == '.py':
            members['build/' + attempt.name] = attempt
        continue
    if attempt.name.startswith('packaged-stage2'):
        continue
    for path in sorted(attempt.iterdir()):
        if path.is_file() and path.suffix in ['.json', '.log', '.toml', '.stdout', '.stderr', '.rs']:
            members['build/' + attempt.name + '/' + path.name] = path
    snapshot = attempt / 'output-snapshot'
    if snapshot.is_dir():
        for path in sorted(snapshot.rglob('*')):
            if path.is_file():
                members['build/' + attempt.name + '/output-snapshot/' + str(path.relative_to(snapshot))] = path
for path in sorted((root / 'experiments/stable-cgu').iterdir()):
    if path.is_file():
        members['experiment/' + path.name] = path

inventory = {name: {'size': path.stat().st_size, 'sha256': digest(path)}
             for name, path in sorted(members.items())}
archive = out / 'evidence.tar.xz'
# A 16MiB dictionary deduplicates repeated exact compiler-source inventories
# across receipts while preserving every original receipt byte.
with tarfile.open(archive, mode='w:xz', preset=7) as tar:
    for name, path in sorted(members.items()):
        info = tar.gettarinfo(str(path), arcname=name)
        info.uid = info.gid = info.mtime = 0
        info.uname = info.gname = ''
        with path.open('rb') as source:
            tar.addfile(info, source)

summary = {
    'schema_version': 1,
    'status': 'final stage2 compiler package and focused correctness controls passed',
    'performance_claim': None,
    'source_commit': package_provenance['source_commit'],
    'base_source_commit': package_provenance['base_source_commit'],
    'patch_sha256': package_provenance['patch_sha256'],
    'bootstrap_sha256': package_provenance['bootstrap_sha256'],
    'package_provenance': package_provenance,
    'controls': controls,
    'final_test_results': {'tracked_option_hash': 1, 'partitioning': 14,
                           'run_make_history': 1, 'native_binary_states': 15},
    'native_control_result_sha256': digest(build / 'native-entry-02/result.json'),
    'native_control_compiler_sha256': native['compiler_sha256'],
    'package_file_count': len(package['files']),
    'qualified_runtime_files_preserved': package['qualified_runtime_files_preserved'],
    'package_files_unchanged_after_native_controls': native['package_files_unchanged'],
    'ordinary_std_uplift': 'Stock bootstrap stage2 distribution uses the matching stage1-built std; no manual stage mixing.',
    'failed_attempts': [
        'format: unsupported per-file ./x fmt invocation',
        'stage1: missing dynamic LLVM after external-path setup; fixed by stock managed CI LLVM',
        'stage2-dist, stage2-dist-02, stage2-dist-03: admission-only timeouts; no build child',
        'package-01: admission-only timeout; no package copied; original helper and supplemental observation retained',
        'package-04: admission-only 600-second timeout; no package copied',
        'package-02: rejected bootstrap live compiler-source directory symlink; partial package preserved; final package uses inventoried rustc-dev sources'],
    'superseded_package': 'Package03/native01 passed 15 native states, but final completeness audit found omitted host libLLVM alias; complete package05/native02 supersedes it.',
    'preliminary_stage1_note': '14 partition tests and 1 run-make history passed before final omit-git-hash=false config; kept separate from final stage2 qualification.',
    'resource_policy': 'Canonical shared flock, at most 2 build/backend jobs, projected space plus 8GiB admission floor; no peer process controls.',
    'archive': {'name': archive.name, 'size': archive.stat().st_size, 'sha256': digest(archive)},
    'members': inventory,
}
(out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
(out / 'README.md').write_text('''# Stable-CGU compiler correctness and provenance

The opt-in compiler experiment passed the tracked-option hash test, all 14 partitioning tests, the run-make edit/reuse history, and 15 actual native binary compile/execute states. This is correctness and setup evidence, not a performance result. The complete build-to-validated-artifact target remains unmeasured for this compiler here.

The compiler is built from the exact pinned base plus the recorded patch, with optimized compiler code, enabled debug/overflow assertions, two jobs, and exact downloaded CI LLVM. Final stage2 runtime/std bytes match the original successful build; only the qualified test-generated rustdoc was added. Stock bootstrap's rustc-dev and rust-std distribution images are bound to exact output inventories, and rust-src is compared file by file with the matching source. The package still goes through the separate immutable installer and full interpreter integration before use in a performance comparison.

The native states cover counts 1, 4 and 64, cold/edit/restoration/off/on transitions, actual main entrypoints, generic/inline code, statics, thread-local values, and empty buckets. The Rust run-make history additionally checks new modules, invalid unused bodies, restored builds, coverage fallback, unmerged fallback, count transitions and source-item placement. The same-width edit in that one grouping fixture is an isolation technique for correctness; real benchmark edits remain unchanged and must include their normal span changes.

The archive contains exact saved logs, receipts, source/config hashes, test output snapshots, original failed setup attempts, and admission-only failures. Runtime binaries, LLVM archives, mutable compiler caches and native test caches are omitted; their hashes remain in the receipts. Setup/build durations include their explicitly recorded lock waits where stated and are not warm-build measurements. No peer workloads or caches were changed.
''')
print(json.dumps({'result': str(out), 'archive_bytes': archive.stat().st_size,
                  'archive_sha256': digest(archive), 'members': len(members)}, indent=2))
