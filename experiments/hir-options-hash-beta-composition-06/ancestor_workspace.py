"""Explicit build02 workspace transition and current manifest closure.

The metadata03 catalog predates the ancestor-workspace fix and does not bind
X/Cargo.toml. Its guard remains unchanged. The build02 plan separately binds
every Cargo.toml ancestor of each acquired source manifest, including absent
paths; the six-control historical catalog retains the pre-fix parent bytes.
No historical input catalog is rewritten or treated as a current stamp.
"""
import json
from pathlib import Path
import stat
import tomllib

from compose_sysroot import digest, require


def read(path):
    return json.loads(Path(path).read_bytes())


def manifest_paths(acquired, source):
    source = Path(source)
    result = set()
    for root, records in [(source, acquired['source_files']),
                          (source / 'library/backtrace', acquired['backtrace_files'])]:
        for name in records:
            relative = Path(name)
            require(str(relative) == name and not relative.is_absolute()
                    and '..' not in relative.parts, 'noncanonical acquired source member')
            if relative.name == 'Cargo.toml':
                parent = (root / relative).parent
                result.update(str(directory / 'Cargo.toml') for directory in [parent, *parent.parents])
    require(result, 'acquired source has no Cargo manifests')
    return result


def contract(plan, acquired, owner, source, before_raw, after_raw, controls_freeze):
    """Pure relation between original proof, approved change and full path set."""
    owner, source = Path(owner), Path(source)
    workspace = plan['ancestor_workspace']
    require(plan['owner'] == str(owner) and workspace['path'] == str(owner / 'Cargo.toml'),
            'workspace owner differs')
    require(digest(before_raw) == workspace['before_sha256']
            and digest(after_raw) == workspace['after_sha256'], 'workspace transition bytes differ')
    before, after = tomllib.loads(before_raw.decode()), tomllib.loads(after_raw.decode())
    before['workspace']['exclude'] = ['.work']
    require(before == after, 'workspace change exceeds generated .work exclusion')
    require(controls_freeze['files'][str(owner / 'Cargo.toml')]['sha256'] == workspace['before_sha256'],
            'original workspace-control catalog does not bind pre-fix bytes')
    paths = manifest_paths(acquired, source)
    require(str(owner / 'Cargo.toml') in paths and str(source / 'src/bootstrap/Cargo.toml') in paths,
            'workspace/bootstrap ancestors omitted')
    require(set(plan['ancestor_manifests']) == paths, 'complete ancestor manifest path set differs')
    require(plan['ancestor_manifests'][str(owner / 'Cargo.toml')]['sha256'] == workspace['after_sha256'],
            'current ancestor catalog does not bind post-fix parent')
    return paths


def guard_manifests(records, stamp, sha, full):
    """Existing and absent paths are checked before/after every B3 operation."""
    for name, expected in records.items():
        path = Path(name)
        require(path.resolve(strict=False) == path and not path.is_symlink(),
                'ancestor manifest route changed: ' + name)
        if expected is None:
            require(not path.exists(), 'previously absent ancestor manifest appeared: ' + name)
        else:
            require(path.is_file() and stat.S_ISREG(path.lstat().st_mode)
                    and stamp(path) == expected['stamp'], 'ancestor manifest identity changed: ' + name)
            if full:
                require(sha(path) == expected['sha256'] and stamp(path) == expected['stamp'],
                        'ancestor manifest bytes changed: ' + name)


def historical_controls(plan, owner, build_source, frozen, sha):
    """Reconcile the actual six controls separately from current source guards.

    `frozen` must validate each required ordinary file against the new B3
    freeze. Historical file records inside inputs.json are evidence only.
    """
    owner, build_source = Path(owner), Path(build_source)
    here = owner / 'experiments/hir-options-hash/workspace-controls-01'
    work = owner / '.work/hir-options-hash-workspace-controls-01'
    outer = owner / '.work/experiments/hir-options-hash-workspace-controls-supervisor-01'
    proof = plan['workspace_controls']
    require(set(proof['membership']) == {str(work), str(outer)}, 'workspace proof roots differ')
    for name, members in proof['membership'].items():
        root = Path(name)
        actual = []
        for path in root.rglob('*'):
            require(not path.is_symlink(), 'workspace evidence contains a link')
            if path.is_file():
                actual.append(str(path.relative_to(root)))
                frozen(path)
            else:
                require(path.is_dir(), 'workspace evidence contains a special file')
        require(sorted(actual) == members, 'workspace evidence membership differs')
    for path in [here / 'plan.json', here / 'inputs.json', build_source / 'ancestor-Cargo.before.toml']:
        frozen(path)
    terminal, status = read(work / 'receipt.json'), read(outer / 'status.json')
    control_plan, freeze = read(here / 'plan.json'), read(here / 'inputs.json')
    require(sha(work / 'receipt.json') == proof['receipt_sha256']
            and sha(here / 'inputs.json') == proof['inputs_sha256']
            and sha(here / 'plan.json') == freeze['plan_sha256'], 'workspace control receipt/plan differs')
    require(terminal['status'] == 'passed' and terminal['controls_passed'] == 6
            and terminal['compiler_builds'] == 0 and len(terminal['commands']) == 6,
            'actual six metadata-only workspace controls required')
    require(status['status'] == 'finished' and status['returncode'] == 0
            and status['child_pid'] == terminal['pid'] and status['supervisor_pid'] == terminal['parent_pid']
            and sha(outer / 'plan.json') == status['plan_sha256']
            and sha(outer / 'command.log') == status['log_sha256'], 'workspace supervisor association differs')
    require(status['started_at'] <= terminal['started_at'] <= terminal['admitted_at']
            <= terminal['finished_at'] <= status['finished_at'], 'workspace supervisor time association differs')
    result = read(work / 'controls.json')
    require(sha(work / 'controls.json') == terminal['controls_sha256'] and result['status'] == 'passed'
            and result['metadata_commands'] == 6 and result['compiler_builds'] == 0
            and result['candidate_workspace']['exclude'] == ['.work'], 'workspace controls result differs')
    require(freeze['files'][str(owner / 'Cargo.toml')]['sha256']
            == sha(build_source / 'ancestor-Cargo.before.toml') == plan['ancestor_workspace']['before_sha256'],
            'workspace control historical parent differs')
    previous = terminal['admitted_at']
    for index, (ref, wanted, observed) in enumerate(zip(terminal['commands'], control_plan['children'], result['rows'], strict=True)):
        directory = work / 'commands' / f'{index:03}'
        child = read(directory / 'receipt.json')
        require(ref == dict(label=wanted['label'], path=str(directory / 'receipt.json'),
                            sha256=sha(directory / 'receipt.json'), pid=child['pid']), 'workspace command reference differs')
        require(child['command'] == wanted['argv'] and child['cwd'] == wanted['cwd']
                and child['environment'] == wanted['environment'] and child['status'] == 'finished'
                and child['returncode'] == wanted['expected_returncode'] == observed['expected_returncode']
                and observed['label'] == wanted['label'] and child['supervisor_pid'] == terminal['pid']
                and child['parent_pid'] == terminal['parent_pid'], 'workspace actual command association differs')
        require(previous <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                'workspace child time association differs')
        previous = child['finished_at']
        for stream in ['stdout', 'stderr']:
            require(sha(directory / stream) == child[stream + '_sha256'] == observed[stream + '_sha256'],
                    'workspace actual raw stream differs')
    return freeze
