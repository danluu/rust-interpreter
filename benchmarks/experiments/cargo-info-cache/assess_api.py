#!/usr/bin/env python3
"""Package saved Cargo import/API contracts; never execute a workload."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from custom_cargo import load_cargo, validate_matched_pair


def require(condition, message):
    if not condition:raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default='cargo-api-contracts-01')
    args = parser.parse_args()
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid output ID')
    files = {}
    def keep(path):
        payload = path.read_bytes()
        result = dict(path=str(path), sha256=sha(payload), bytes=len(payload), utf8=payload.decode())
        files[str(path)] = result
        return {k: result[k] for k in ['path', 'sha256', 'bytes']}
    contracts = ROOT / '.work/cargo-api-contracts-01'
    source = json.loads((contracts / 'summary.json').read_bytes())
    require(source['owner'] == str(ROOT) and source['status'] == 'passed' and
            source['performance_measurement'] is False and len(source['commands']) == 2,
            'expected passed synthetic contracts')
    counts = {}
    for command in source['commands']:
        label = command['label']
        receipt = json.loads((contracts / (label + '-process.json')).read_bytes())
        require(receipt['status'] == 'finished' and receipt['returncode'] == command['returncode'] == 0 and
                receipt['command'] == command['command'] and receipt['pid'] == command['pid'] and
                receipt['parent_pid'] == source['supervisor_pid'] and receipt['cwd'] == str(ROOT) and
                source['lock_acquired_at'] <= receipt['started_at'] <= receipt['finished_at'] <= source['finished_at'],
                'contract receipt differs')
        for stream in ['stdout', 'stderr']:
            require(sha((contracts / (label + '.' + stream)).read_bytes()) == command[stream + '_sha256'],
                    'contract output changed')
        stderr = (contracts / (label + '.stderr')).read_text()
        matches = re.findall(r'^Ran (\d+) tests in ', stderr, re.M)
        require(len(matches) == 1 and stderr.endswith('\nOK\n'), 'contracts are not successful')
        counts[label] = int(matches[0])
    require(counts == dict(api=19, screen=20), 'contract counts differ')
    for path, expected in source['harness'].items():
        require(keep(Path(path))['sha256'] == expected, 'qualified harness changed')
    for path in sorted(contracts.iterdir()):keep(path)
    imports = []
    for name in ['cargo-api-import-01', 'cargo-api-import-02']:
        directory = ROOT / '.work' / name
        report = json.loads((directory / 'summary.json').read_bytes())
        require(report['status'] == 'passed' and report['performance_measurement'] is False and
                [row['mode'] for row in report['commands']] == ['stock', 'candidate'], 'import failed or incomplete')
        for row in report['commands']:
            receipt = json.loads((directory / (row['mode'] + '-process.json')).read_bytes())
            require(receipt['status'] == 'finished' and receipt['returncode'] == row['returncode'] == 0 and
                    receipt['command'] == row['command'] and receipt['pid'] == row['pid'] and
                    receipt['parent_pid'] == report['supervisor_pid'], 'import receipt differs')
            for stream in ['stdout', 'stderr']:
                payload = (directory / (row['mode'] + '.' + stream)).read_bytes()
                require(sha(payload) == row[stream + '_sha256'], 'import output changed')
            require(json.loads((directory / (row['mode'] + '.stdout')).read_bytes()) == row['cargo'],
                    'import result differs')
        for path in sorted(directory.iterdir()):keep(path)
        imports.append(dict(name=name, report=keep(directory / 'summary.json'),
                            selected=name.endswith('02'), cargos=[r['cargo'] for r in report['commands']]))
    cargos = [load_cargo(ROOT, item['key']) for item in imports[-1]['cargos']]
    pair = validate_matched_pair(*cargos)
    require(pair == json.loads((ROOT / '.work/cargo-api-import-02/pair.json').read_bytes()), 'matched pair changed')
    manifests = [keep(cargo.directory / 'ready.json') for cargo in cargos]
    for path in [Path(__file__), ROOT / 'docs/OWNED-CARGO.md',
                 ROOT / 'benchmarks/experiments/strict-warm-build/CARGO_INFO_CACHE_SCREEN.md']:
        keep(path)
    payload = json.dumps(dict(encoding='exact UTF-8 members', files=list(files.values())), separators=(',', ':')).encode() + b'\n'
    stream = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0, compresslevel=9) as output:
        output.write(payload)
    archive = stream.getvalue()
    require(gzip.decompress(archive) == payload, 'archive round trip differs')
    for item in json.loads(gzip.decompress(archive))['files']:
        data = item['utf8'].encode()
        require(len(data) == item['bytes'] and sha(data) == item['sha256'], 'archive member changed')
    dynamic = cargos[0].identity['dynamic_libraries']
    summary = dict(status='passed', performance_measurement=False, contracts=counts,
        total_contract_tests=sum(counts.values()), real_rust_cargo_vm_workloads=0,
        imports=imports, selected_pair=pair, installed_manifests=manifests,
        external_library_logical_paths=len(dynamic['libraries']),
        external_library_resolved_files=len({p['resolved'] for p in dynamic['libraries']}),
        dynamic_library_identity=dynamic,
        qualification='../cargo-info-cache-build-01/assessment.md',
        archive=dict(path='evidence.json.gz', bytes=len(archive), sha256=sha(archive),
            uncompressed_bytes=len(payload), uncompressed_sha256=sha(payload), members=len(files),
            all_member_hashes_verified=True))
    output = ROOT / 'results' / args.run_id; output.mkdir(exist_ok=False)
    (output / 'evidence.json.gz').write_bytes(archive)
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (output / 'assessment.md').write_text('''# Optional Cargo API and screen contracts

All 39 synthetic tests passed on the first attempt under the shared workload lock: 19 Cargo/compiler/launcher API tests and 20 mechanism-screen tests. No Rust build, Cargo build, VM workload, std setup or performance screen was executed. The test fixtures exercise absolute Cargo routing, public/custom compiler selection, conflicting overrides, immutable payloads, dynamic-library mutation/link/runpath invalidation, separate std/project caches, same-tool Cargo A/B selection, and rejection of mismatched Cargo/std receipts. Existing stable-CGU and tool-policy contracts still pass.

The corrected import preserves the previously qualified matched stock/candidate Cargo binaries. It records six logical dependency paths resolving to five non-system libraries: libgit2, libssh2, llhttp, libssl and libcrypto. Full hashes and logical/resolved paths are bound to the content identity; warm validation checks stamps, link targets and runpath search results without subprocesses. System dyld-cache libraries rely on the recorded uname platform/kernel-build identity. The original import01 is retained as superseded because it omitted external-library provenance. Import02 and the copied qualification prove the same compiler/profile/features/settings and 3,073 source inputs, differing only in `src/util/rustc.rs` and actual Cargo executable bytes.

The independent `cargo-info-cache` policy keeps one public compiler/exporter/VM, uses stock Cargo for A/A′ and candidate Cargo for B, and requires separately prepared matching std identities. All 27 complete commands, 14 tests, fresh edits, wrong-edit/recovery/restoration controls and bytecode/catalog parity checks remain in the driver. These synthetic contracts do not establish a speedup, the 0.5 s target, or holdout generalization.

[summary.json](summary.json) records exact keys, library identities, test counts and archive hashes. [evidence.json.gz](evidence.json.gz) retains every original import/test receipt and output, corrected installation manifests and exact tested source snapshots. All member hashes and gzip round trip were verified. Executables, compiler/std caches and Homebrew libraries are excluded; original Cargo build/source evidence remains in [the matched-build qualification](../cargo-info-cache-build-01/assessment.md).

Reproduce from saved evidence only with `python3 benchmarks/experiments/cargo-info-cache/assess_api.py --run-id cargo-api-contracts-01-reproduced`.
''')
    print(json.dumps(dict(output=str(output), archive=summary['archive'])))


if __name__ == '__main__':
    main()
