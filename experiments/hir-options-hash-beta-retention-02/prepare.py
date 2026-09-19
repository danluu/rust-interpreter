"""Prepare only: rehash closed evidence, write a finite archive proposal, never copy payloads."""
import ast
import json
from pathlib import Path
import stat
import sys

import history
import retain as r

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')


def main():
    r.require(Path.cwd() == r.A and sys.dont_write_bytecode and not sys.flags.optimize, 'explicit owner/Python')
    for path in [r.HERE/'inputs.json', r.HERE/'launch.json', r.WORK, r.OUT]:
        r.require(not path.exists() and not path.is_symlink(), 'fresh preparation/output')
    files, routes, sources, directories, original_catalogs = {}, {}, set(), {}, []

    def add(path, expected=None, archive=True):
        path = Path(path)
        before = r.stamp(path)
        r.require(path.resolve(strict=True) == path and stat.S_ISREG(before[2]) and before[3] <= r.BOUNDS['file_bytes'], 'ordinary bounded input: '+str(path))
        row = dict(stamp=before, bytes=before[3], sha256=r.sha(path))
        r.require(r.stamp(path) == before, 'input changed while read')
        if expected:
            r.require(row['sha256'] == expected['sha256'], 'historical hash changed: '+str(path))
            if 'stamp' in expected:
                r.require(row['stamp'] == expected['stamp'], 'historical identity changed: '+str(path))
            if 'size' in expected:
                r.require(row['bytes'] == expected['size'], 'historical size changed')
        r.require(str(path) not in files or files[str(path)] == row, 'conflicting input')
        files[str(path)] = row
        if archive:
            r.require(path.suffix not in ['.dylib', '.rlib', '.rmeta', '.o', '.xz'], 'live compiler payload excluded')
            sources.add(str(path))
        if path.suffix == '.py':
            ast.parse(path.read_bytes(), filename=str(path))
        return row

    def directory(path, exclude=()):
        exclude = list(map(str, exclude))
        names = r.members(path, exclude)
        directories[str(path)] = dict(members=names, excluded_future_outputs=exclude)
        for name in names:
            add(name)

    for stage in history.stages():
        packet = Path(stage['packet'])
        catalog = packet/'inputs.json'; original_catalogs.append(str(catalog))
        original = r.read(catalog)
        for name, row in original['files'].items():
            archive = name.startswith('/Users/danluu/dev/')
            if not archive:
                r.require(Path(name).name in ['python3.14', 'ps', 'lsof'], 'unclassified excluded executor')
            add(name, row, archive)
        for route, resolved in original['routes'].items():
            r.require(route not in routes or routes[route] == resolved, 'conflicting executor route')
            routes[route] = resolved
        for key in ['packet', 'work', 'outer', 'launcher']:
            directory(Path(stage[key]))
        add(stage['audit'])

    for number in ['03', '04', '05', '06', '07']:
        source = r.A/f'experiments/hir-options-hash-beta-composition-{number}'
        # Source07 may acquire exactly these separately reviewed preparation outputs later.
        # The closed source/control archive neither reads nor claims those outputs.
        exclude = [source/name for name in ['inputs.json', 'plan.json', 'launch.json']] if number == '07' else []
        directory(source, exclude)
        bindings = r.read(source/'source-bindings.json')
        for group in ['references', 'predecessor_draft', 'timing_sources', 'provider_grammar_references']:
            for row in bindings.get(group, {}).values():
                add(row['path'], row)

    extras = [r.OWNED, r.A/'scripts/supervise_experiment.py']
    for number in ['02', '03', '04', '05']:
        extras += [r.A/f'.work/launch_beta_controls_{number}.py',
                   r.A/f'.work/verify_beta_controls_{"failure_" if number == "04" else ""}{number}.py']
    for name in ['launch_sysroot_inventory_controls_01.py', 'verify_sysroot_inventory_controls_01.py',
                 'sysroot-inventory-controls-verification-01.stdout', 'sysroot-inventory-controls-verification-01.stderr',
                 'sysroot-inventory-controls-preparation-01.stdout', 'sysroot-inventory-controls-preparation-01.stderr',
                 'beta-controls-preparation-04.stdout', 'beta-controls-preparation-04.stderr',
                 'beta-controls-preparation-05.stdout', 'beta-controls-preparation-05.stderr',
                 'beta-controls-failure-verification-04.stdout', 'beta-controls-failure-verification-04.stderr',
                 'beta-controls-verification-05.stdout', 'beta-controls-verification-05.stderr']:
        extras.append(r.A/'.work'/name)
    for number in ['04', '06']:
        extras += [r.A/f'.work/beta-composition-discovery-failure-{number}.json',
                   *[r.A/f'.work/beta-composition-discovery-{number}.{stream}' for stream in ['stdout', 'stderr']]]
    for name in ['root-beta-controls02-plan-verification-01.json', 'root-beta-controls04-plan-verification-01.json',
                 'root-beta-controls05-plan-verification-01.json', 'root-sysroot-inventory-controls-plan-verification-01.json']:
        extras.append(ROOT/'.work'/name)
    extras += [X/'.work/beta-composition-output-classifier-source-review-05.json',
               O/'.work/beta-composition06-control05-source-review.json']
    prior = r.A/'results/hir-options-hash-beta-composition-02'
    for name in ['README.md', 'manifest.json']:
        extras.append(prior/name)
    directory(prior/'retention')
    extras += [r.A/'.work/beta-retention-independent-verification-01.json',
               ROOT/'.work/root-beta-composition-retention-actual-verification-01.json']
    for path in [*extras, *sorted(r.HERE.iterdir())]:
        add(path)
    prior_file = prior/'evidence.tar.gz'
    prior_row = add(prior_file, archive=False)
    r.require(prior_row['sha256'] == '4a7a5bdfc9789b96d237e2a46d34ef2ff7963837e59ecaeae80638226e777fd1', 'prior archive identity')
    observed = history.validate_all()
    original = r.read(original_catalogs[-1])
    python = str(Path(sys.executable).resolve(strict=True))
    r.require(python == original['python'], 'qualified Python')
    environment = dict(original['environment'], TMPDIR='/tmp')
    excluded = {name: row for name, row in files.items() if name not in sources}
    logical = sum(files[name]['bytes'] for name in sources)
    physical = sum(size for _, size in {(files[n]['sha256'], files[n]['bytes']) for n in sources})
    r.require(len(files) < r.BOUNDS['members']-1 and logical < r.BOUNDS['logical_bytes']-4*r.MIB
              and physical < r.BOUNDS['physical_bytes']-4*r.MIB, 'preparation finite bounds')
    absent = []
    for number in ['04', '06']:
        absent += [str(r.A/f'experiments/hir-options-hash-beta-composition-{number}'/name) for name in ['inputs.json', 'plan.json', 'launch.json']]
    frozen = dict(status='prepared-unrun', owner=str(r.A), files=files, routes=routes, python=python,
        environment=environment, archive_sources=sorted(sources), directories=directories,
        original_input_catalogs=original_catalogs, absent_paths=absent, history=observed, bounds=r.BOUNDS,
        input_bytes=sum(row['bytes'] for row in files.values()), archive_logical_bytes_before_freeze=logical,
        archive_physical_bytes_before_freeze=physical,
        prior_archive=dict(path=str(prior_file), sha256=prior_row['sha256'], bytes=prior_row['bytes'], included=False),
        payload_exclusions=dict(files=excluded, explanation='Executors and the already retained 49-control archive are hash-bound references, not duplicated payloads. Compiler/SDK/registry/native binaries and derived caches are never selected; their existing catalogs/raw/source proofs are retained.'),
        capacity=dict(entry_gib=9, stop_gib=9, floor_gib=8, reservation_bytes=r.BOUNDS['expanded_bytes']),
        canonical_lock='/Users/danluu/dev/rust-interp/.work/benchmark.lock', wait_seconds=600, workload_children=0)
    r.guard(frozen, history)
    def write(path, value):
        with path.open('x') as stream:
            json.dump(value, stream, indent=2, sort_keys=True); stream.write('\n')
    write(r.HERE/'inputs.json', frozen)
    launch = dict(status='prepared-unrun-awaiting-review', owner=str(r.A), environment=environment,
        command=[python, '-B', str(r.A/'scripts/supervise_experiment.py'), '--run-id',
                 'beta-producer-evidence-supervisor-02', '--', python, '-B', str(r.HERE/'retain.py'),
                 '--inputs-sha256', r.sha(r.HERE/'inputs.json')],
        inputs_sha256=r.sha(r.HERE/'inputs.json'), helper_sha256=r.sha(r.HERE/'retain.py'),
        expected_workload_children=0, bounds=r.BOUNDS, capacity=frozen['capacity'])
    write(r.HERE/'launch.json', launch)
    print(json.dumps(dict(files=len(files), archive_members=len(sources)+1, logical_bytes=logical,
        physical_bytes=physical, launch_sha256=r.sha(r.HERE/'launch.json'), inputs_sha256=launch['inputs_sha256']), indent=2))


if __name__ == '__main__':
    main()
