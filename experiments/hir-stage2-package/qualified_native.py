"""Read the completed native prerequisite from immutable archived bytes."""
import hashlib
import json
from pathlib import Path
import re
import tarfile

HERE = Path(__file__).resolve().parent
CHECKPOINT = '8416694357ee7ac8ff8b1d3c262b61e7e1f52ca8'
SOURCE_REVISION = '7efc0d9484da82cd327deb3b48616f8ec81eaf8d'
SOURCE_RECORD_SHA = 'fd0cc030b76bce5f8733cce975c0bb1e00cf226ed495439e36d6e5bdb320e020'
EVID = Path('/Users/danluu/dev/rust-interp-hir-native-controls-evidence-20260913')
NATIVE = Path('/Users/danluu/dev/rust-interp-hir-arena-native-20260913')
ORIGINAL_PLAN = NATIVE / 'experiments/hir-arena-native/planned-native-01.json'
ORIGINAL_PLAN_SHA = 'c30a65cfb2c00ce67bdbea27df460f248a3f9b4ae324333a590b1aaea5301819'
FAILED = NATIVE / '.work/hir-arena-native-01/stages/native-01/receipt.json'
FAILED_SHA = '075c9bb98df60bdfdbe9a466c88ecc774cc4844e6dbafbc9095e10beb1a9af37'
REPLAY_PLAN = EVID / 'experiments/hir-arena-native-replay/planned-replay-01.json'
REPLAY_PLAN_SHA = '8cf8da2a8ece01297b14d11a8d12f1838af8df845d5f24ba902bbb072d312609'
TERMINAL = EVID / '.work/hir-arena-native-replay-01/stages/run-01/receipt.json'
TERMINAL_SHA = 'ddc2171ee78662f8a4f4b99405e7a91b9f5cf9dbaa541314e006e71cc2d17176'
SUPERVISOR = EVID / '.work/experiments/hir-arena-native-replay-run-supervisor-01'
ARCHIVE_ROOT = EVID / 'results/hir-arena-native-qualification-01'
ARCHIVE_HASHES = {'archive': '373719cd01be1ba923581345481ff4b1dfd2e2623cf37cc6c5de7cc0a8fcd700',
    'manifest': '7ed53cfe7d283546195e5ef8fdd84f7877206ed8477200da0c5444072bafcb49',
    'summary': '7f382f1cda0937b388ed52d4f93447d27d226fcdc64bc362cbe20ad346b060ca'}
ARCHIVE_PATHS = {name: str(ARCHIVE_ROOT / filename) for name, filename in
    [('archive', 'evidence.tar.gz'), ('manifest', 'manifest.json'), ('summary', 'summary.json')]}


def require(condition, message):
    if not condition: raise RuntimeError(message)


def digest(data): return hashlib.sha256(data).hexdigest()


def checkpoint(native):
    origins = json.loads((HERE / 'inputs/origin.json').read_bytes())
    require(set(origins) == {'capture.patch', 'patch.json'}, 'arena checkpoint input set changed')
    for name, row in origins.items():
        require(row['git_revision'] == CHECKPOINT and digest((HERE/'inputs'/name).read_bytes()) == row['sha256'],
                'immutable arena checkpoint changed')
    patch = (HERE/'inputs/capture.patch').read_bytes()
    manifest = json.loads((HERE/'inputs/patch.json').read_bytes())
    require(digest(patch) == manifest['patch_sha256'] == '485194f2f9e995b6ad1ee2c39d66d05deb776df7b6e26b22085925c28edd6671'
        and manifest['base_commit'] == native.old.BASE and manifest['actual_cache_hit_path'] is True
        and manifest['cached_body_materialization'] is True and len(manifest['files']) == 25, 'wrong arena source patch')
    names = re.findall(r'^\+\s*#\[test\]\n\+\s*fn ([a-z0-9_]+)', patch.decode(), re.M)
    require(len(names) == len(set(names)) == 27 and set(native.old.REQUIRED_TESTS) <= set(names)
        and 'candidate_identity_uses_worker_arena_and_rejects_wrapper_or_foreign_arena' in names, 'all27 controls required')
    return manifest, sorted(names)


class Archive:
    def __init__(self, native, paths=ARCHIVE_PATHS):
        self.native, self.paths = native, dict(paths)
        require(set(self.paths) == set(ARCHIVE_HASHES), 'three archive files required')
        self.hashes = {self.paths[name]: expected for name, expected in ARCHIVE_HASHES.items()}
        self.guard()
        self.manifest = json.loads(Path(self.paths['manifest']).read_bytes())
        self.summary = json.loads(Path(self.paths['summary']).read_bytes())
        require(len(self.manifest) == self.summary['archive']['members'] == 1012
            and self.summary['archive']['sha256'] == ARCHIVE_HASHES['archive'], 'complete qualification archive required')
        self.data = {}
        with tarfile.open(self.paths['archive'], 'r:gz') as tar:
            seen = set()
            for member in tar:
                require(member.isfile() and member.name not in seen and member.name in self.manifest,
                        'unexpected qualification archive member')
                row = self.manifest[member.name]; source = row['source']; data = tar.extractfile(member).read()
                require(Path(source).is_absolute() and member.name == source.lstrip('/')
                    and '..' not in Path(member.name).parts and source not in self.data
                    and len(data) == row['bytes'] and digest(data) == row['sha256'], 'archived origin or bytes changed')
                self.data[source] = data; seen.add(member.name)
            require(seen == set(self.manifest), 'qualification archive member omitted')
        self.guard()

    def guard(self):
        for path, expected in self.hashes.items():
            require(self.native.sha(self.native.ordinary(path)) == expected, 'qualification archive changed')

    def read(self, path, expected=None):
        # Deliberately never falls back to the live historical file. Bootstrap
        # may replace old rmake/support outputs during the new stage2 sequence.
        key = str(path)
        require(key in self.data, 'required archived source/evidence is missing: ' + key)
        value = self.data[key]
        require(expected is None or digest(value) == expected, 'archived evidence digest differs')
        return value

    def json(self, path, expected=None): return json.loads(self.read(path, expected))


def child(archive, ref, parent):
    path = Path(ref['path'])
    require(path.is_relative_to(parent/'commands'), 'archived child escaped stage')
    row = archive.json(path, ref['sha256'])
    require(row['status'] == 'finished' and row['returncode'] == 0 and row['command'] == ref['command'],
            'archived child failed or invocation changed')
    text = ''.join(archive.read(path.parent/name, row[name+'_sha256']).decode() for name in ['stdout','stderr'])
    return row, text


def checked_replay_terminal(row):
    require(row.get('status') == 'passed' and row.get('stage') == 'run' and row.get('owner') == str(EVID)
        and row.get('actual_direct_recipe_passed') == 1 and row.get('expected_plan_sha256') == REPLAY_PLAN_SHA
        and row.get('original_outer_native_status') == 'failed' and len(row.get('commands', [])) == 14
        and row.get('original_build_passed') is True and row.get('original_option_test_passed') == 1
        and row.get('original_compiletest_recipe_passed') == 1 and row.get('performance_claim') is False
        and row['started_at'] <= row['admitted_at'] <= row['finished_at'], 'complete direct replay required')


def previous(native, recipe, archive, plan_path, plan_hash, terminal_path, supervisor, stage1_contract):
    require(str(plan_path) == str(REPLAY_PLAN) and plan_hash == REPLAY_PLAN_SHA
        and str(terminal_path) == str(TERMINAL) and str(supervisor) == str(SUPERVISOR), 'exact completed replay required')
    manifest, names = checkpoint(native)
    plan = archive.json(REPLAY_PLAN, REPLAY_PLAN_SHA)
    original = archive.json(ORIGINAL_PLAN, ORIGINAL_PLAN_SHA)
    prior = original['previous']
    require(original['checkpoint'] == CHECKPOINT and original['required_units'] == names
        and prior['source']['revision'] == SOURCE_REVISION and prior['source']['config_sha256'] == native.CONFIG_SHA
        and all(prior['source']['files'].get(p) == dict(kind='file',sha256=row['after_sha256'])
                for p,row in manifest['files'].items()), 'archive source/all27 checkpoint mismatch')
    # The new controller needs the original helper's bytes as historical proof,
    # not as a live dependency. Every original plan-input hash is read here.
    referenced_tars = {ref['paths']['archive']: ref['hashes'][ref['paths']['archive']]
                       for ref in archive.summary['historical_archives']}
    for path, expected in original['inputs'].items():
        if path in referenced_tars: require(referenced_tars[path] == expected, 'archived input/reference mismatch')
        else: archive.read(path, expected)
    unit_path = Path(prior['terminal']); unit = archive.json(unit_path)
    require(unit['status'] == 'passed' and unit['stage'] == 'unit' and unit['source_record_sha256'] == SOURCE_RECORD_SHA,
            'actual arena all27 unit stage required')
    units = [text for ref in unit['commands'] for row,text in [child(archive,ref,unit_path.parent)]
             if row['command'] == native.old.COMMANDS['unit']]
    require(len(units) == 1, 'one actual selected unit command required')
    native.engine.checked_tests(units[0], names, []); native.checked_result(units[0], 27, unfiltered=True)
    failed = archive.json(FAILED, FAILED_SHA)
    require(failed['status'] == 'failed' and failed['error'] == "RuntimeError('no actual verified cache hit in retained native output')"
        and len(failed['commands']) == 21 and failed['expected_plan_sha256'] == ORIGINAL_PLAN_SHA,
        'original failed history must remain failed')
    old_children = [child(archive,ref,FAILED.parent) for ref in failed['commands']]
    require(old_children[5][0]['command'] == native.COMMANDS['build']
        and old_children[14][0]['command'] == native.COMMANDS['option']
        and old_children[20][0]['command'] == native.COMMANDS['native'], 'original build/option/native association changed')
    require(all(row['environment'] == prior['old_plan']['environment'] for row,_ in old_children), 'old native environment changed')
    native.checked_option(old_children[14][1]); native.checked_result(old_children[20][1], 1)
    def identity(children, indexes):
        probes = [children[i] for i in indexes]
        require([row['command'] for row,_ in probes] == native.PROBES
            and all(row['cwd'] == str(native.SOURCE) for row,_ in probes)
            and 'commit-hash: '+SOURCE_REVISION in probes[0][1]
            and probes[1][1].strip() == str(native.SYSROOT)
            and all(re.search(r'(?m)^\s*-Z\s+'+flag+r'=',probes[2][1])
                    for flag in ['hir-body-cache-capture','hir-body-cache-reuse']), 'actual native identity differs')
    identity(old_children,[11,12,13])
    route = recipe.recipe_environment(old_children[20][1], prior['old_plan']['environment'], stage1_contract)
    require(plan['route'] == route and plan['source_revision'] == SOURCE_REVISION, 'archived replay route differs')
    terminal = archive.json(TERMINAL, TERMINAL_SHA)
    checked_replay_terminal(terminal)
    new_children = [child(archive,ref,TERMINAL.parent) for ref in terminal['commands']]
    identity(new_children,[5,6,7])
    direct, raw = new_children[8]
    require(direct['command'] == plan['command'] == [stage1_contract['recipe']]
        and direct['cwd'] == plan['cwd'] and direct['environment'] == route['environment'], 'actual direct recipe route changed')
    for index,(row,_) in enumerate(new_children):
        if index != 8: require(row['environment'] == prior['old_plan']['environment'], 'replay guard/probe environment changed')
    observations = recipe.checked_replay(raw)
    require(observations == archive.json(TERMINAL.parent/'observations.json',terminal['observations_sha256'])
        and observations['actual_verified_hits'] == 335, 'complete raw hit proof changed')
    status = archive.json(SUPERVISOR/'status.json')
    require(status['status'] == 'finished' and status['returncode'] == 0 and status['child_pid'] == terminal['pid']
        and status['supervisor_pid'] == terminal['parent_pid'], 'direct replay supervisor association changed')
    archive.read(SUPERVISOR/'plan.json',status['plan_sha256']);archive.read(SUPERVISOR/'command.log',status['log_sha256'])
    summary = archive.summary
    require(summary['source_revision'] == SOURCE_REVISION and summary['source_checkpoint'] == CHECKPOINT
        and summary['replay_commands'] == 14 and summary['controls'] == 4 and summary['skipped'] == 0
        and summary['observations'] == observations, 'qualification summary differs')
    control_root = EVID/'.work/hir-arena-native-replay-controls-01'
    control = archive.json(control_root/'summary.json')
    require(control['status'] == 'passed' and control['expected_controls'] == 4 and control['all_inputs_unchanged'],
            'actual four replay controls required')
    test = archive.json(control_root/'command/receipt.json',control['command_receipt_sha256'])
    require(test['returncode'] == 0 and test['command'][1:] ==
            ['-B','-m','unittest','-v','test_hir_arena_native_replay'], 'replay control command changed')
    text = archive.read(control_root/'command/stderr',test['stderr_sha256']).decode()
    actual = re.findall(r'^test_[^\n]* \(([^)]+)\) \.\.\. ok$',text,re.M)
    require(sorted(actual) == control['required_tests'] == sorted(control['actual_tests'])
        and len(actual) == 4 and text.rstrip().endswith('OK'), 'all four raw control passes required')
    post_path = EVID/'.work/hir-arena-native-qualification-archive-01/source-postguard.json'
    post = archive.json(post_path,summary['source_postguard_sha256'])
    require(post['full_source_verified_twice'] and post['source_revision'] == SOURCE_REVISION
        and post['source_record_sha256'] == SOURCE_RECORD_SHA, 'full current-source postguard required')
    require(archive.json(post['source_record_path'],SOURCE_RECORD_SHA) == prior['source'], 'source receipt differs from plan')
    runtime = archive.json(post_path.parent/'runtime-inventory.json',post['runtime_inventory_sha256'])
    require(runtime == plan['runtime'] and len(runtime['stage1']['files']) == 64, 'qualified runtime inventory differs')
    references = summary['historical_archives']
    require([r['members'] for r in references] == [334,322,250,324,203,314,318], 'seven full archive references required')
    archive.guard()
    return dict(plan_path=str(REPLAY_PLAN),plan_sha256=REPLAY_PLAN_SHA,terminal=str(TERMINAL),supervisor=str(SUPERVISOR),
        files={row['source']:row['sha256'] for row in archive.manifest.values()}, source=prior['source'],
        old_plan=prior['old_plan'],old_plan_path=prior['old_plan_path'],stage1=runtime['stage1'],
        historical_archives=references,historical_source={str(native.SOURCE/p):row['after_sha256'] for p,row in manifest['files'].items()},
        archived_qualification_paths=archive.paths, archived_qualification_hashes=archive.hashes,
        original_outer_native_status='failed', actual_complete_direct_replay=True)
