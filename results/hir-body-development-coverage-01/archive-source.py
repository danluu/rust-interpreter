#!/usr/bin/env python3
"""Archive already completed body-v2 development evidence; no compiler work."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import time
from collections import Counter

ROOT = Path('/Users/danluu/dev/rust-interp-mono-post-driver-20260913')
sys.path.insert(0, str(ROOT / '.work/hir-owner-coverage-setup-01/helpers'))
from owned_stage import workload_lock, write

LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
OUT = ROOT / 'results/hir-body-development-coverage-01'
RAW = ROOT / '.work/hir-body-development-coverage-01'
SETUP = ROOT / '.work/hir-body-development-setup-01'
SOURCE_SETUP = ROOT / '.work/hir-owner-development-setup-03'
RECEIPT = ROOT / '.work/hir-body-development-archive-01.json'
BODY_ROLES = ('free-function', 'inherent-impl-method', 'provided-trait-method', 'trait-impl-method')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def totals(rows):
    counts, reasons = {}, Counter()
    for row in rows:
        reasons.update(row['reasons'])
        for role, metrics in row['counts'].items():
            total = counts.setdefault(role, Counter())
            total.update(metrics)
    eligible = sum(counts.get(role, {}).get('input_eligible', 0) for role in BODY_ROLES)
    return dict(invocations=len(rows), resolver_owners=sum(row['resolver_owners'] for row in rows),
                body_scope_owners=sum(counts.get(role, {}).get('owners', 0) for role in BODY_ROLES),
                structurally_eligible=eligible, counts=counts, first_rejections=reasons)


def main():
    receipt = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
                   canonical_lock=str(LOCK), wait_seconds=600, compiler_commands=0)
    write(RECEIPT, receipt)
    print(json.dumps(receipt), flush=True)
    try:
        with workload_lock(LOCK, 600):
            receipt.update(status='running', lock_acquired_at=time.time())
            write(RECEIPT, receipt)
            result = json.loads((RAW / 'result.json').read_text())
            plan = json.loads((SETUP / 'plan.json').read_text())
            assert result['status'] == 'passed' and result['cargo_commands'] == 1 and result['cargo_exit'] == 0
            assert sha(SETUP / 'plan.json') == result['plan_sha256']
            assert sha(RAW / 'coverage.json') == result['coverage_sha256']
            assert sha(SOURCE_SETUP / 'source-inventory.json') == plan['source_inventory_sha256']
            coverage = json.loads((RAW / 'coverage.json').read_text())
            assert len(coverage['report_files']) == result['reports'] == 742
            assert len(coverage['per_invocation']) + len(coverage['probes']) == result['reports']
            assert coverage['missing_owners'] == 0 and not coverage['hir_ids_observed']
            assert not coverage['benchmark'] and not coverage['cache_effects_qualified'] and not coverage['cache_hits']
            for name, expected in coverage['report_files'].items():
                assert sha(RAW / 'reports' / name) == expected, name
            sources = {}

            def add(path, name):
                assert name not in sources, name
                sources[name] = Path(path)

            for prefix, directory in [('setup', SETUP), ('run', RAW)]:
                for path in sorted(directory.iterdir()):
                    if path.is_file():
                        add(path, prefix + '/' + path.name)
            for directory in ['reports', 'cargo-check']:
                for path in sorted((RAW / directory).iterdir()):
                    if path.is_file():
                        add(path, 'run/' + directory + '/' + path.name)
            for path_text, expected in plan['frozen_proofs'].items():
                path = Path(path_text)
                assert sha(path) == expected, path_text
                add(path, 'frozen-inputs/' + str(path.relative_to(ROOT)))
            for name in ['summary.json', 'inventory.json', 'archive-receipt.json']:
                add(ROOT / 'results/hir-body-coverage-native-01' / name, 'native-qualification/' + name)
            add(Path(__file__), 'archive-source.py')
            source_inventory = json.loads((SOURCE_SETUP / 'source-inventory.json').read_text())
            inventory = {}
            OUT.mkdir(parents=True, exist_ok=False)
            with tarfile.open(OUT / 'evidence.tar.gz', 'w:gz', compresslevel=6) as archive:

                def member(name, raw, source, kind='file'):
                    assert name not in inventory
                    inventory[name] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                                           source=str(source), stored_kind=kind)
                    entry = tarfile.TarInfo(name)
                    entry.size, entry.mode, entry.mtime = len(raw), 0o644, 0
                    archive.addfile(entry, io.BytesIO(raw))

                for name, path in sorted(sources.items()):
                    member(name, path.read_bytes(), path)
                for relative, expected in source_inventory.items():
                    path = Path(plan['source']) / relative
                    link = expected['kind'] == 'symlink'
                    raw = os.fsencode(os.readlink(path)) if link else path.read_bytes()
                    assert hashlib.sha256(raw).hexdigest() == expected['sha256'], relative
                    member('source/nushell/' + relative, raw, path, 'git-symlink-link-text' if link else 'file')
            with tarfile.open(OUT / 'evidence.tar.gz', 'r:gz') as archive:
                entries = archive.getmembers()
                assert len(entries) == len(inventory)
                for entry in entries:
                    assert entry.isfile()
                    raw = archive.extractfile(entry).read()
                    assert hashlib.sha256(raw).hexdigest() == inventory[entry.name]['sha256']
            for name, path in sources.items():
                assert sha(path) == inventory[name]['sha256'], name
            write(OUT / 'inventory.json', inventory)
            rows = coverage['per_invocation']
            selected = [row for row in rows if row['crate'] == 'nu_protocol']
            by_incremental = {str(mode).lower(): totals([row for row in rows if row['incremental_session'] == mode])
                              for mode in [False, True]}
            summary = dict(status='passed', policy=plan['policy'], source_commit='fc74f953',
                diagnostic_source_commit='501d992e', source_revision=plan['source_revision'],
                source_inventory_sha256=plan['source_inventory_sha256'], driver_sha256=plan['driver_sha256'],
                gate_sha256=plan['gate_sha256'], compiler_commit='cea272fa356e94bd2ee2cadf376630aa0683867a',
                plan_sha256=result['plan_sha256'], coverage_sha256=result['coverage_sha256'],
                command=plan['command'], cargo_invocations=1, cargo_returncode=0,
                run_supervisor_pid=result['pid'], cargo_pid=result['cargo_pid'],
                canonical_lock_acquired_at=result['lock_acquired_at'], completed_at=result['completed_at'],
                report_count=len(coverage['report_files']), compiler_probes=len(coverage['probes']),
                compiler_invocations=len(rows), groups=len(coverage['groups']), totals=totals(rows),
                by_incremental_session=by_incremental, selected_nu_protocol=selected,
                missing_owners=0, instrumentation_mismatches=0, source_unchanged=True,
                raw_diagnostics_retained=True, invocation_weighted=True,
                accepted_input_fields=['owner DefPathHash', 'StableSourceFileId', 'function role',
                    'full owner source bytes', 'typed ordered AST-field atoms',
                    'owner-relative root-hygiene span byte ranges', 'stable visited AST-node ordinals',
                    'parameter binding patterns, modes and current local resolution',
                    'partial resolution presence, base resolution and unresolved segment count',
                    'current local/external DefPathHash identities',
                    'trait-map presence and ordered candidates, import chains and ambiguity flags'],
                unavailable_cache_proofs=['actual entry/exit HIR IDs S/E', 'body output codec/capture',
                    'complete lowering state/event journal', 'replay equality and fallible materialization',
                    'actual cache hits', 'latency benefit'],
                first_rejection_counts_are_not_widening_gains=True,
                benchmark=False, strict_14_test_workflow=False, holdout=False,
                cache_effects_qualified=False, hir_ids_observed=False, cache_hits=False,
                compiler_cache_implemented=False, latency_target_qualification=False,
                archive_members=len(inventory), archive_bytes=(OUT / 'evidence.tar.gz').stat().st_size,
                archive_sha256=sha(OUT / 'evidence.tar.gz'),
                exclusions='compiler/driver binaries, Cargo targets/caches and Git object database',
                native_qualification_archive=dict(path='results/hir-body-coverage-native-01/evidence.tar.gz',
                    sha256='b8db7a70231929cc469c88f03fc49eb2faf4c4afc3106edd44b0b599bd37513b'),
                prior_v1_archive=dict(path='results/hir-owner-development-coverage-01/evidence.tar.gz',
                    sha256='7fab100fbfaf772652b58af1b9335def9801b3e75e6912b9cf2325d3131985e5'))
            write(OUT / 'summary.json', summary)
            receipt.update(status='passed', finished_at=time.time(), archive_members=len(inventory),
                           archive_sha256=summary['archive_sha256'], archive_bytes=summary['archive_bytes'])
            write(RECEIPT, receipt)
            write(OUT / 'archive-receipt.json', receipt)
            (OUT / 'archive-source.py').write_bytes(Path(__file__).read_bytes())
            print(json.dumps(receipt), flush=True)
    except BaseException as error:
        receipt.update(status='failed', error=repr(error), finished_at=time.time())
        write(RECEIPT, receipt)
        raise


if __name__ == '__main__':
    main()
