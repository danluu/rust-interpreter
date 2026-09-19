"""Source-only exact retention preparer; do not execute before source review.

No stage workload is run. A later invocation creates a fresh freeze/launch for
only the closed scopes below. It does not copy or inventory live candidate,
SDK, registry or compiler/binary payload trees, or mutable build02 evidence.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
W = X / '.work'
H = X / 'experiments/hir-options-hash'
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work')
ARCHIVER = W / 'archive_hir_options_admission_evidence_01.py'
F = W / 'hir-options-admission-evidence-inputs-01.json'
L = W / 'hir-options-admission-evidence-launch-01.json'
# X's sparse checkout no longer materializes the landed result. Bind the
# existing identical retained main copy without duplicating its archive.
PRIOR = ROOT.parent / 'results/hir-options-hash-preparation-01'
PRIOR_ARCHIVE_SHA = '88420663870dbb118df5a4fbe791a59e9ddc684d789c61260c3638a075822415'
PRIOR_MANIFEST_SHA = '7718547a9c461545106e76a3cef27ddb6214b0a5720abb688900b0225796c290'
ANCESTOR = H / 'compiler-build-02/ancestor-Cargo.before.toml'
ANCESTOR_SHA = '8fda5c18467187220cda8913ae3b2fa17ba96862a6f32c75f6a68dc1e837e7bb'
FIXTURE = Path('/Users/danluu/dev/rust-interp-cargo-workspace-controls-20260918')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, data):
    with Path(path).open('x') as stream:
        json.dump(data, stream, sort_keys=True, indent=2); stream.write('\n')


def main():
    assert Path.cwd() == X and sys.dont_write_bytecode and not sys.flags.optimize
    assert not F.exists() and not L.exists() and not (X / 'results/hir-options-hash-admission-01').exists()
    assert not (W / 'hir-options-admission-evidence-retention-01').exists()
    spec = importlib.util.spec_from_file_location('admission_retention_source', ARCHIVER)
    archive = importlib.util.module_from_spec(spec); spec.loader.exec_module(archive)
    files, directories = {}, {}
    def add(path):
        path = Path(path)
        assert path.resolve(strict=True) == path and path.is_file() and not path.is_symlink()
        before = archive.stamp(path)
        assert stat.S_ISREG(before[2]) and before[3] <= archive.LIMITS['file_bytes']
        digest = sha(path); assert archive.stamp(path) == before
        row = dict(sha256=digest, bytes=before[3], stamp=before)
        assert str(path) not in files or files[str(path)] == row
        files[str(path)] = row
    def tree(path):
        members = archive.membership(path); directories[str(path)] = members
        for name in members: add(Path(name))
    def audit(path, status, receipt_field='receipt_sha256'):
        add(path); return dict(path=str(path), status=status, receipt_field=receipt_field)
    # These source directories and evidence roots are all completed. Do not
    # traverse the parent H or W, which also contain mutable build02 inputs.
    for name in ['compiler-metadata-03', 'compiler-metadata-continuation-01', 'compiler-build-01', 'workspace-controls-01']:
        tree(H / name)
    descriptions = [
        dict(kind='metadata-failure', name='hir-options-hash-compiler-metadata-03', source='compiler-metadata-03',
             actual='hir-options-hash-compiler-metadata-launch-03', status='failed', count=48, outer_returncode=1),
        dict(kind='metadata-continuation', name='hir-options-hash-compiler-metadata-continuation-01', source='compiler-metadata-continuation-01',
             actual='hir-options-hash-compiler-metadata-continuation-launch-01', status='passed', count=2, outer_returncode=0),
        dict(kind='parser-controls', name='hir-options-hash-metadata-parser-controls-01', source='compiler-metadata-continuation-01',
             actual='hir-options-hash-metadata-parser-controls-launch-01', status='passed', count=1, outer_returncode=0),
        dict(kind='build-failure', name='hir-options-hash-compiler-build-01', source='compiler-build-01',
             actual='hir-options-hash-compiler-build-launch-01', status='failed', count=3, outer_returncode=1),
        dict(kind='workspace-controls', name='hir-options-hash-workspace-controls-01', source='workspace-controls-01',
             actual='hir-options-hash-workspace-controls-launch-01', status='passed', count=6, outer_returncode=0),
    ]
    stages = []
    for description in descriptions:
        name, source = description['name'], H / description['source']
        work = W / name; outer = W / 'experiments' / (name[:-3] + '-supervisor-' + name[-2:])
        tree(work); tree(outer)
        for suffix in ['actual.json', 'stdout', 'stderr']: add(W / (description['actual'] + '.' + suffix))
        prefix = 'control-' if description['kind'] == 'parser-controls' else ''
        item = dict(kind=description['kind'], work=str(work), outer=str(outer), status=description['status'],
            children=description['count'], outer_returncode=description['outer_returncode'],
            inputs=str(source / (prefix + 'inputs.json')), launch=str(source / (prefix + 'launch.json')),
            actual=str(W / (description['actual'] + '.actual.json')), audits=[])
        item['child_results'] = [['finished', 0] for _ in range(description['count'])]
        if description['kind'] != 'parser-controls': item['plan'] = str(source / 'plan.json')
        else: item['cwd'] = str(source)
        if description['kind'] == 'metadata-failure':
            item['child_results'] = []
            for row in read(source / 'plan.json')['children'][:description['count']]:
                expected = row.get('expected', [0]); assert len(expected) == 1
                item['child_results'].append(['finished', expected[0]])
            assert item['child_results'][15] == ['finished', 86]
            item['audits'].append(audit(O / 'options-hash-metadata03-failure-independent-actual-verification.json', 'retained-failure-audit-passed', 'terminal_sha256'))
            add(O / 'review-options-hash-metadata03-failure.py')
        elif description['kind'] == 'metadata-continuation':
            item['audits'].extend([
                audit(W / 'hir-options-hash-compiler-metadata-continuation-verification-01.json', 'verified'),
                audit(O / 'options-hash-metadata-continuation-independent-actual-verification.json', 'passed', 'terminal_sha256'),
                audit(ROOT / 'root-options-hash-metadata-continuation-actual-verification-01.json', 'passed', 'terminal_sha256')])
            add(W / 'verify_hir_options_metadata_continuation_01.py'); add(O / 'review-options-hash-metadata-continuation.py')
        elif description['kind'] == 'parser-controls':
            item['audits'].extend([
                audit(W / 'hir-options-hash-metadata-parser-controls-verification-01.json', 'verified'),
                audit(O / 'options-hash-metadata-parser-controls-independent-verification.json', 'passed', 'terminal_sha256')])
            add(W / 'verify_hir_options_metadata_parser_controls_01.py')
        elif description['kind'] == 'build-failure':
            item['child_results'][-1] = ['failed', 1]
            item['audits'].append(audit(W / 'hir-options-hash-compiler-build-failure-verification-01.json', 'verified-failed-attempt'))
        elif description['kind'] == 'workspace-controls':
            item['child_results'] = [['finished', code] for code in [0, 101, 0, 0, 0, 101]]
            item['audits'].extend([
                audit(W / 'hir-options-hash-workspace-controls-verification-01.json', 'verified'),
                audit(ROOT / 'root-workspace-isolation-controls-actual-verification-01.json', 'verified', 'terminal_sha256')])
            add(W / 'verify_hir_options_workspace_controls_01.py')
        stages.append(item)
    # Retain the generated, closed fourteen-file manifest fixture, without any
    # package/build cache. Metadata-only controls created no target directory.
    assert not (FIXTURE / 'target').exists()
    fixture_members = archive.membership(FIXTURE)
    assert len(fixture_members) == 14 and sum(Path(p).stat().st_size for p in fixture_members) <= 4*2**20
    tree(FIXTURE)
    assert sha(ANCESTOR) == ANCESTOR_SHA; add(ANCESTOR)
    add(W / 'hir-options-admission-evidence-preparation-01.failed.json')
    # Add only imported control/harness Python source outside the four closed
    # source roots. Their historical catalogs are retained wholesale, but do
    # not follow catalog entries into live compiler/SDK/registry payloads.
    for item in stages:
        original = read(item['inputs'])
        for name, row in original['files'].items():
            path = Path(name)
            permitted = path.is_relative_to(X / 'scripts') or path.is_relative_to(X / 'experiments/stable-cgu')
            if permitted and path.suffix == '.py':
                expected = row['sha256'] if isinstance(row, dict) else row
                assert sha(path) == expected; add(path)
    for path in [ARCHIVER, Path(__file__).resolve(), archive.OWNED, X / 'scripts/supervise_experiment.py',
                 W / 'archive_hir_options_preparation_03.py', W / 'prepare_hir_options_retention_03.py']:
        add(path)
        if path.suffix == '.py': ast.parse(path.read_bytes())
    assert sha(PRIOR / 'evidence.tar.gz') == PRIOR_ARCHIVE_SHA and sha(PRIOR / 'manifest.json') == PRIOR_MANIFEST_SHA
    add(PRIOR / 'manifest.json'); add(PRIOR / 'verification.json')
    previous = dict(path=str(PRIOR / 'evidence.tar.gz'), sha256=PRIOR_ARCHIVE_SHA,
                    stamp=archive.stamp(PRIOR / 'evidence.tar.gz'), payload_included=False)
    python = Path(sys.executable).resolve(strict=True)
    environment = dict(HOME='/Users/danluu', PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
                       LANG='C', LC_ALL='C', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    freeze = dict(owner=str(X), files=files, directories=directories, stages=stages, prior_archive=previous,
        absent_paths=[str(FIXTURE / 'target')],
        historical_parent_manifest=dict(original_path=str(X / 'Cargo.toml'), preserved_path=str(ANCESTOR), sha256=ANCESTOR_SHA,
                                        meaning='historical before-fix bytes; current parent manifest is intentionally not asserted unchanged'),
        limits=archive.LIMITS, environment=environment, python=dict(path=str(python), sha256=sha(python), stamp=archive.stamp(python)),
        canonical_lock='/Users/danluu/dev/rust-interp/.work/benchmark.lock', wait_seconds=600,
        logical_bytes=sum(row['bytes'] for row in files.values()),
        unique_bytes=sum(size for _, size in {(row['sha256'], row['bytes']) for row in files.values()}),
        exclusion='No live compiler/source build tree, SDK, registry, provider or executable payload; input catalogs preserve their identity. Mutable build02 excluded except the explicitly named immutable historical parent manifest.')
    assert len(files) <= archive.LIMITS['files'] and freeze['logical_bytes'] <= archive.LIMITS['logical_bytes']
    assert freeze['unique_bytes'] <= archive.LIMITS['unique_bytes']
    # This preparer intentionally does not call verify_history: source review
    # precedes freezing, and actual retention performs its full exact checks.
    write(F, freeze)
    launch = dict(status='prepared-unrun-awaiting-review', owner=str(X), environment=environment,
        command=[str(python), '-B', str(X / 'scripts/supervise_experiment.py'), '--run-id', 'hir-options-admission-evidence-supervisor-01',
                 '--', str(python), '-B', str(ARCHIVER), '--inputs-sha256', sha(F)], inputs_sha256=sha(F),
        capacity=dict(entry_gib=9, live_floor_gib=9, reservation_bytes=archive.LIMITS['reservation_bytes']),
        metadata_probes_rerun=0, compiler_builds=0, tests_rerun=0)
    write(L, launch)
    print(json.dumps(dict(files=len(files), logical_bytes=freeze['logical_bytes'], unique_bytes=freeze['unique_bytes'],
                         inputs_sha256=sha(F), launch_sha256=sha(L)), indent=2))


if __name__ == '__main__':
    main()
