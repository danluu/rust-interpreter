#!/usr/bin/env python3
"""Read-only candidate admission; never installs, compiles a crate, or publishes."""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
from pathlib import Path
import stat
import sys
import time
import tomllib

OWNER = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PLAN = HERE / 'inspection-plan-03.json'
FROZEN = HERE / 'inspection-inputs-03.json'
WORK = OWNER / '.work/runtime-installation-inspection-03'
POLICY = 'runtime-installation-metadata-inspection-v1'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Inspection:
    def __init__(self, args):
        self.args = args
        require(sha(FROZEN) == args.frozen_sha, 'inspection freeze changed')
        self.frozen = read(FROZEN)
        self.check_sources()
        self.plan = read(PLAN)
        require(self.plan['policy'] == POLICY and self.plan['owner'] == str(OWNER), 'foreign plan')
        self.owned = load('runtime_inspection_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
        sys.path.insert(0, str(OWNER / 'scripts'))
        self.runtime = load('runtime_inspection_policy', OWNER / 'scripts/runtime_compiler.py')
        self.stage2 = load('runtime_inspection_source_guard', self.plan['guard_script'])
        for module in list(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename and str(filename).startswith('/Users/danluu/dev/rust-interp'):
                require(str(Path(filename).resolve()) in self.frozen['files'], 'unfrozen import: ' + filename)
        require(not WORK.exists() and not WORK.is_symlink(), 'inspection output must be fresh')
        WORK.mkdir(parents=True)
        self.env = self.plan['environment']
        self.record = dict(schema_version=1, policy=POLICY, status='waiting', owner=str(OWNER),
            pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), command=sys.argv,
            cwd=os.getcwd(), frozen_sha256=args.frozen_sha, plan_sha256=sha(PLAN),
            canonical_lock=str(self.owned.CANONICAL_LOCK), wait_seconds=600, commands=[],
            environment=self.env, python=self.frozen['python'], installation=False,
            application_qualified=False, benchmark=False)
        self.save()

    def save(self):
        self.owned.write(WORK / 'receipt.json', self.record)

    def capacity(self):
        return self.owned.disk(OWNER, 8)

    def check_sources(self):
        require(sha(FROZEN) == self.args.frozen_sha, 'inspection freeze changed during run')
        for filename, expected in self.frozen['files'].items():
            path = Path(filename)
            require(path.resolve(strict=True) == path and path.is_file() and not path.is_symlink()
                    and sha(path) == expected, 'frozen source changed: ' + filename)
        python = self.frozen['python']
        require(str(Path(sys.executable).resolve()) == python['resolved']
                and sha(sys.executable) == python['sha256'], 'Python identity changed')

    def bound(self, ref, *, retain=True):
        path = Path(ref['path'])
        require(path.resolve(strict=True) == path and path.is_file() and not path.is_symlink(),
                'indirect/missing saved evidence: ' + str(path))
        before = self.runtime.stamp(path.lstat())
        require(stat.S_ISREG(before[2]), 'nonordinary saved evidence')
        row = dict(sha256=ref['sha256'], size=before[3], mode=stat.S_IMODE(before[2]))
        retained = WORK / 'inputs' / str(path).lstrip('/') if retain else None
        target = retained if retained is not None and not retained.exists() else None
        self.runtime.transfer(path, row, before, self.capacity, target)
        require(self.runtime.stamp(path.lstat()) == before, 'saved evidence changed after read')
        if retained is not None:
            copied = self.runtime.stamp(retained.lstat())
            require(retained.resolve(strict=True) == retained and stat.S_ISREG(copied[2])
                    and copied[6] == 1 and stat.S_IMODE(copied[2]) == row['mode'],
                    'retained proof is not an ordinary fresh copy')
            self.runtime.transfer(retained, row, copied, self.capacity)
            require(self.runtime.stamp(retained.lstat()) == copied, 'retained proof changed during readback')
        self.record.setdefault('read_inputs', {})[str(path)] = dict(row, stamp=before, retained=retain)
        return path

    def run(self, argv, *, cwd=None, env=None):
        self.check_sources()
        self.capacity()
        cwd, env = Path(cwd or OWNER), env or self.env
        argv = list(map(str, argv))
        git = any(argv == r['argv'] and str(cwd) == r['cwd'] for r in self.plan['git_commands'])
        probe = str(cwd) == str(OWNER) and (argv in self.plan['compiler_probes']
                or argv == self.plan['tool_selection_probe']
                or argv in getattr(self, 'allowed_otool', []))
        require((git and env == self.prior['old_plan']['environment']) or (probe and env == self.env),
                'command/cwd/environment is outside the read-only inspection allowlist')
        if argv in getattr(self, 'allowed_otool', []):
            require(self.host_tool_snapshot() == self.record['selected_otool'], 'host tool route changed before use')
        executable = Path(shutil.which(str(argv[0]), path=(env or self.env)['PATH']) or str(argv[0])).resolve(strict=True)
        tool = dict(path=str(executable), sha256=sha(executable), stamp=self.runtime.stamp(executable.lstat()))
        out = WORK / 'commands' / f'{len(self.record["commands"]):03}'
        try:
            child = self.owned.run(argv, cwd=cwd or OWNER, env=env or self.env,
                out=out, capacity_root=OWNER)
        finally:
            if (out / 'receipt.json').exists():
                child = read(out / 'receipt.json')
                self.record['commands'].append(dict(path=str(out / 'receipt.json'),
                    sha256=sha(out / 'receipt.json'), command=child['command'],
                    pid=child.get('pid'), returncode=child.get('returncode'), executable=tool))
                self.save()
        require(sha(executable) == tool['sha256'] and self.runtime.stamp(executable.lstat()) == tool['stamp'],
                'command executable changed during probe')
        if argv in getattr(self, 'allowed_otool', []):
            require(self.host_tool_snapshot() == self.record['selected_otool'], 'host tool route changed during use')
        return dict(stdout=(out / 'stdout').read_bytes(), stderr=(out / 'stderr').read_bytes(), receipt=child)

    def historical(self):
        refs = self.plan['evidence']
        for ref in refs.values():
            self.bound(ref, retain=ref.get('retain', True))
        failure = read(refs['failed01']['path'])
        require(failure['files'].items() <= self.frozen['files'].items()
                and failure['phase'] == 'startup-before-lock' and not failure['canonical_admission']
                and not failure['stage_receipt_created'], 'failed01 history binding differs')
        failed_outer = read(failure['outer'])
        require(failed_outer['status'] == 'finished' and failed_outer['returncode'] == 1
                and failed_outer['supervisor_pid'] == 41368 and failed_outer['child_pid'] == 41371
                and failure['error'] in Path(failure['log']).read_text(), 'failed01 startup error changed')
        self.record['predecessor_failures'] = [refs['failed01'], refs['failed02']]
        failure02 = read(refs['failed02']['path'])
        require(failure02['files'].items() <= self.frozen['files'].items(), 'failed02 files omitted')
        failed_stage, failed_outer = read(failure02['stage']), read(failure02['outer'])
        require(failed_stage['status'] == 'failed' and failed_stage['error'] == 'indirect selected Mach-O inspector'
                and failed_outer['status'] == 'finished' and failed_outer['returncode'] == 1
                and failed_stage['pid'] == failed_outer['child_pid'] == 61519
                and failed_stage['parent_pid'] == failed_outer['supervisor_pid'] == 61516
                and failed_outer['started_at'] <= failed_stage['started_at'] <= failed_stage['admitted_at']
                    <= failed_stage['finished_at'] <= failed_outer['finished_at']
                and failed_stage['commands'] == failure02['commands'] and len(failed_stage['commands']) == 6,
                'failed02 terminal/process association differs')
        for ref in failed_stage['commands']:
            child = read(ref['path'])
            require(sha(ref['path']) == ref['sha256'] and child['command'] == ref['command']
                    and child['returncode'] == 0 and child['status'] == 'finished'
                    and child['supervisor_pid'] == 61519 and child['parent_pid'] == 61516
                    and failed_stage['admitted_at'] <= child['started_at'] <= child['finished_at']
                        <= failed_stage['finished_at'], 'failed02 successful child association differs')
            for name in ('stdout', 'stderr'):
                require(sha(Path(ref['path']).parent / name) == child[name + '_sha256'], 'failed02 raw output differs')
        prior = read(refs['stage2_plan']['path'])['previous']
        require(prior['source']['revision'] == self.plan['revision'] and prior['actual_complete_direct_replay'],
                'native source/replay prerequisite changed')
        require(prior['stage1'] == read(refs['runtime']['path']), 'recorded runtime maps differ')
        summary = read(refs['native_summary']['path'])
        manifest = read(refs['native_manifest']['path'])
        require(summary['archive']['sha256'] == refs['native_archive']['sha256']
                and summary['manifest_sha256'] == refs['native_manifest']['sha256']
                and summary['source_revision'] == self.plan['revision']
                and summary['original_build_passed'] and summary['original_option_test_passed']
                and summary['original_compiletest_recipe_passed'] and summary['replay_recipe_passed']
                and summary['original_outer_native_status'] == 'failed', 'native history relabeled')
        require(refs['native_terminal']['path'] == prior['terminal']
                and refs['native_terminal']['sha256'] == prior['files'][prior['terminal']],
                'native terminal differs from qualified plan')
        terminal = read(refs['native_terminal']['path'])
        require(terminal['status'] == 'passed' and terminal['actual_direct_recipe_passed']
                and terminal['original_build_passed'] and terminal['original_option_test_passed']
                and terminal['original_compiletest_recipe_passed']
                and terminal['expected_plan_sha256'] == prior['plan_sha256'], 'native prerequisite failed')
        for name in ('native_terminal', 'original_terminal', 'native005', 'original_outer', 'replay_outer'):
            ref = refs[name]
            entry = manifest[ref['path'].lstrip('/')]
            require(entry['source'] == ref['path'] and entry['sha256'] == ref['sha256'],
                    'native envelope/archive association differs')
        old = read(refs['original_terminal']['path'])
        require(old['status'] == 'failed', 'original native parser failure must remain failed')
        require(len(old['commands']) + len(terminal['commands']) == self.plan['historical_child_count'],
                'historical command count differs')
        for name, envelope in [('original', old), ('replay', terminal)]:
            outer = read(refs[name + '_outer']['path'])
            expected = self.plan['historical_envelopes'][name]
            require(outer['status'] == 'finished' and outer['returncode'] == expected['returncode']
                    and envelope['pid'] == outer['child_pid'] == expected['helper_pid']
                    and envelope['parent_pid'] == outer['supervisor_pid'] == expected['supervisor_pid']
                    and outer['started_at'] <= outer['child_started_at'] <= envelope['started_at']
                        <= envelope['admitted_at'] <= envelope['finished_at'] <= outer['finished_at'],
                    'historical native outer/helper identity or time association differs')
            for ref in envelope['commands']:
                path = self.bound(ref)
                row = read(path)
                require(row['status'] == 'finished' and row['returncode'] == 0
                        and row['command'] == ref['command'] and type(row['pid']) is int and row['pid'] > 0
                        and row['supervisor_pid'] == envelope['pid']
                        and row['parent_pid'] == envelope['parent_pid']
                        and list(map(int, row['identity']['ps'].split()[:2])) == [row['pid'], envelope['pid']]
                        and envelope['admitted_at'] <= row['started_at'] <= row['finished_at']
                            <= envelope['finished_at'], 'historical native child/process association changed')
                for filename in (path, path.parent / 'stdout', path.parent / 'stderr'):
                    expected_sha = ref['sha256'] if filename == path else row[filename.name + '_sha256']
                    entry = manifest[str(filename).lstrip('/')]
                    require(entry['source'] == str(filename) and entry['sha256'] == expected_sha,
                            'historical raw/archive association differs')
                    self.bound(dict(path=str(filename), sha256=expected_sha))
        build = read(refs['native005']['path'])
        require(build['command'] == self.plan['native005_argv'] and build['returncode'] == 0,
                'native005 build proof differs')
        self.prior = prior

    def source_guard(self):
        self.check_sources()
        require(self.stage2.inputs() == self.plan['guard_inputs'], 'qualified guard import closure changed')
        def git(argv, cwd=self.stage2.SOURCE):
            require(argv[:1] == ['git'], 'source guard may only invoke Git')
            row = self.run(argv, cwd=cwd, env=self.prior['old_plan']['environment'])
            require(not row['stderr'], 'source guard stderr')
            return dict(stdout=row['stdout'].decode(), stderr='')
        self.stage2.engine.source_guard(self.prior['source'], git, self.plan['old_plan_sha256'])
        require(self.stage2.native.artifacts() == self.prior['stage1'], 'qualified E runtime changed')

    def provider(self):
        ready = read(self.plan['evidence']['provider_ready']['path'])
        identity, stamps = ready['identity'], ready['stamps']
        require(ready['key'] == self.plan['provider_key'] == self.runtime.digest(identity),
                'source provider immutable identity differs')
        comparison = read(self.plan['evidence']['source_comparison']['path'])
        provenance = identity['provenance']
        require(provenance['rust_src_comparison_sha256'] == self.plan['evidence']['source_comparison']['sha256']
                and provenance['llvm_source_proof_sha256'] == self.plan['evidence']['support_proof']['sha256']
                and provenance['source_commit'] == comparison['source_commit']
                and not comparison['mismatched'] and not comparison['backtrace']['mismatched'],
                'source provider qualification differs')
        components = []
        for role, prefix in [('source', self.plan['source_prefix']), ('support', self.plan['support_prefix'])]:
            files = {name[len(prefix)+1:]: dict(sha256=digest, size=stamps[name][3],
                        mode=stat.S_IMODE(stamps[name][2]))
                     for name, digest in identity['files'].items() if name.startswith(prefix + '/')}
            component = dict(role=role, root=str(Path(self.plan['provider_sysroot']) / prefix),
                             destination=prefix, files=files, links={})
            if role == 'source':
                component['source_receipt_sha256'] = self.plan['evidence']['source_comparison']['sha256']
            components.append(component)
        source_files = components[0]['files']
        recorded = {n.removeprefix('library/'): h for n, h in comparison['checked'].items()}
        backtrace = {'backtrace/' + n: h for n, h in comparison['backtrace']['checked'].items()}
        extras = {n.removeprefix('library/'): h for n, h in comparison['distribution_only'].items()}
        require(not (recorded.keys() & backtrace.keys() or recorded.keys() & extras.keys()
                     or backtrace.keys() & extras.keys()), 'overlapping source classifications')
        require({n: r['sha256'] for n, r in source_files.items()} == recorded | backtrace | extras,
                'ordinary source provider membership differs from complete comparison')
        current = {n: r['sha256'] for n, r in self.prior['source']['files'].items()
                   if n.startswith('library/') and r['kind'] == 'file'}
        current_backtrace = {n: r['sha256'] for n, r in self.prior['source']['backtrace_files'].items()
                             if r['kind'] == 'file'}
        require({n: h for n, h in current.items() if n not in comparison['missing']} == comparison['checked']
                and sorted(set(current) - set(comparison['checked'])) == sorted(comparison['missing'])
                and {n: h for n, h in current_backtrace.items() if n not in comparison['backtrace']['missing']}
                    == comparison['backtrace']['checked']
                and sorted(set(current_backtrace) - set(comparison['backtrace']['checked']))
                    == sorted(comparison['backtrace']['missing']), 'E library/source provider mismatch or omission')
        require(all(n.startswith('vendor/') or n == '.cargo/config.toml' for n in extras),
                'unclassified distribution-only source')
        proof = read(self.plan['evidence']['support_proof']['path'])
        require(set(components[1]['files']) == {'rust-objcopy'}
                and proof['member_sha256'] == provenance['objcopy_sha256']
                    == components[1]['files']['rust-objcopy']['sha256']
                and proof['archive_sha256'] == provenance['llvm_archive_sha256'], 'support provenance differs')
        for name in self.plan['llvm_paths']:
            require(identity['files'][name] == self.prior['stage1']['files'][name]['sha256'],
                    'support tool provider and E LLVM differ')
        self.record['source_classification'] = dict(tracked=len(recorded), backtrace=len(backtrace),
            distribution_only=len(extras), vendor_packages=len(comparison['vendor_packages']),
            missing=comparison['missing'], backtrace_missing=comparison['backtrace']['missing'],
            preserved_provider_modes=True, std_source_paths_qualified=False)
        return components, stamps, comparison

    def components(self):
        runtime = self.prior['stage1']
        files = {}
        root = Path(self.plan['runtime_root'])
        for name, row in runtime['files'].items():
            path = root / name
            value = path.lstat()
            require(path.resolve(strict=True) == path and stat.S_ISREG(value.st_mode)
                    and not value.st_mode & 0o7000, 'nonordinary runtime input')
            files[name] = dict(row, mode=stat.S_IMODE(value.st_mode))
        links = {name: dict(text=row['link_text'], resolved_target=row['resolved_target'],
                 **self.plan['source_links'][name]) for name, row in runtime['source_links'].items()}
        provider, provider_stamps, comparison = self.provider()
        components = [dict(role='runtime', root=str(root), destination='', files=files, links=links), *provider]
        snapshots = []
        for component in components:
            before = self.runtime.inspect_component(component)
            if component['role'] != 'runtime':
                prefix = component['destination']
                expected = {name.removeprefix(prefix + '/') if name != prefix else '.': value
                            for name, value in provider_stamps.items()
                            if name == prefix or name.startswith(prefix + '/')}
                require({name: row[:6] for section in ('files', 'directories')
                         for name, row in before[section].items()} == expected,
                        'immutable provider subtree stamp/membership differs')
            for name, row in component['files'].items():
                self.runtime.transfer(Path(component['root']) / name, row, before['files'][name], self.capacity)
            require(self.runtime.inspect_component(component) == before, 'component changed while hashing')
            snapshots.append(before)
        self.vendor_check(provider[0], comparison)
        return components, snapshots

    def vendor_check(self, source, comparison):
        root = Path(source['root'])
        lock = tomllib.loads((root / 'Cargo.lock').read_text())
        packages = {(r['name'], r['version']): r.get('checksum') for r in lock['package']}
        names = {Path(n).parts[1] for n in source['files'] if n.startswith('vendor/')}
        require(names == set(comparison['vendor_packages']), 'vendor package membership differs')
        for name in sorted(names):
            prefix = 'vendor/' + name + '/'
            checksum = read(root / prefix / '.cargo-checksum.json')
            package = tomllib.loads((root / prefix / 'Cargo.toml').read_text())['package']
            expected = comparison['vendor_packages'][name]
            require(expected == dict(package=package['name'], version=package['version'],
                    checksum=checksum['package'], checksum_file=source['files'][prefix + '.cargo-checksum.json']['sha256'])
                    and checksum['package'] == packages[(package['name'], package['version'])],
                    'vendor Cargo lock/checksum association differs')
            actual = {n[len(prefix):]: r['sha256'] for n, r in source['files'].items() if n.startswith(prefix)}
            require(actual == checksum['files'] | {'.cargo-checksum.json': expected['checksum_file']},
                    'vendor content/checksum differs')
        require(comparison['distribution_only_configuration'] ==
                {'library/.cargo/config.toml': (root / '.cargo/config.toml').read_text()},
                'distributed Cargo configuration differs')

    def host_tool_snapshot(self):
        declaration = self.plan['selected_host_tool']
        selected, resolved = Path(declaration['selected']), Path(declaration['resolved'])
        parents = {str(p): self.runtime.stamp(p.lstat()) for p in {*selected.parents, *resolved.parents}}
        require(all(Path(p).resolve(strict=True) == Path(p) and stat.S_ISDIR(row[2])
                    for p, row in parents.items()), 'indirect host-tool parent route')
        link = self.runtime.stamp(selected.lstat())
        require(stat.S_ISLNK(link[2]) and os.readlink(selected) == declaration['link_text']
                and selected.resolve(strict=True) == resolved and resolved.resolve(strict=True) == resolved,
                'selected host tool link differs')
        ordinary = self.runtime.stamp(resolved.lstat())
        require(stat.S_ISREG(ordinary[2]) and ordinary[2] & 0o111, 'resolved host tool is not ordinary executable')
        digest = sha(resolved)
        require(self.runtime.stamp(selected.lstat()) == link and os.readlink(selected) == declaration['link_text']
                and self.runtime.stamp(resolved.lstat()) == ordinary
                and all(self.runtime.stamp(Path(p).lstat()) == row for p, row in parents.items()),
                'host tool/link/parent changed during inspection')
        return dict(selected=str(selected), link_text=declaration['link_text'], link_stamp=link,
                    resolved=str(resolved), resolved_stamp=ordinary, sha256=digest, parents=parents)

    def inspect(self):
        self.historical()
        self.source_guard()
        components, snapshots = self.components()
        self.owned.write(WORK / 'components-initial.json', dict(components=components, snapshots=snapshots))
        self.record['initial_components_sha256'] = sha(WORK / 'components-initial.json')
        self.save()
        by_destination = {str(Path(c['destination']) / n) if c['destination'] else n:
                          (str(Path(c['root']) / n), r)
                          for c in components if c['role'] != 'source' for n, r in c['files'].items()}
        images = sorted(n for n, (_, row) in by_destination.items()
                        if n.endswith(('.dylib', '.so')) or row['mode'] & 0o111)
        require(images == self.plan['loader_images'], 'native image/mode inventory differs from proposed commands')
        selected = self.run(['/usr/bin/xcrun', '--find', 'otool'])
        require(not selected['stderr'], 'otool selection emitted stderr')
        require(selected['stdout'].decode() == self.plan['selected_host_tool']['selected'] + '\n',
                'selected SDK tool differs from retained xcrun selection')
        self.record['selected_otool'] = self.host_tool_snapshot()
        otool = self.record['selected_otool']['resolved']
        self.allowed_otool = [[otool, '-l', by_destination[name][0]] for name in images]
        loader = {}
        for name in images:
            result = self.run([otool, '-l', by_destination[name][0]])
            require(not result['stderr'], 'Mach-O inspection emitted stderr')
            loader[name] = self.runtime.macho_commands(result['stdout'].decode())
        outputs = []
        for argv in self.plan['compiler_probes']:
            result = self.run(argv)
            require(not result['stderr'], 'compiler identity probe emitted stderr')
            outputs.append(result['stdout'].decode())
        require(outputs[1] == self.plan['runtime_root'] + '\n', 'original E sysroot differs')
        spec = dict(schema_version=1, host=self.plan['host'], loader_policy=self.runtime.LOADER_POLICY,
            compiler=outputs[0], unstable_options=self.runtime.option_proof(outputs[2]), loader=loader,
            components=components, provenance=dict(source_commit=self.plan['revision'],
                source_checkout=self.plan['source'], bootstrap_sha256=self.prior['source']['config_sha256'],
                build_receipt_sha256=self.plan['evidence']['native005']['sha256'],
                qualification_receipt_sha256=self.plan['evidence']['native_terminal']['sha256'],
                source_comparison_sha256=self.plan['evidence']['source_comparison']['sha256'],
                support_proof_sha256=self.plan['evidence']['support_proof']['sha256']))
        identity = self.runtime.identity_for(spec)
        require('std_source_paths' not in identity['provenance'], 'unqualified E source capability')
        self.source_guard()
        for component, snapshot in zip(components, snapshots):
            require(self.runtime.inspect_component(component) == snapshot, 'component changed during probes')
        self.check_sources()
        require(self.host_tool_snapshot() == self.record['selected_otool'], 'host tool route changed after probes')
        for filename, proof in self.record['read_inputs'].items():
            require(self.runtime.stamp(Path(filename).lstat()) == proof['stamp'],
                    'admitted source/evidence changed during inspection')
        require(len(self.record['commands']) == self.plan['planned_child_count'], 'metadata command count differs')
        require([len(c['files']) for c in components] == self.plan['expected_component_files']
                and sum(r['size'] for c in components for r in c['files'].values())
                    == self.plan['expected_logical_copy_bytes'], 'admitted component totals differ')
        self.owned.write(WORK / 'components-and-stamps.json', dict(components=components, snapshots=snapshots))
        self.owned.write(WORK / 'candidate-specification.json', spec)
        self.record.update(status='inspected-pending-review', specification_sha256=sha(WORK / 'candidate-specification.json'),
            components_sha256=sha(WORK / 'components-and-stamps.json'),
            candidate_key=self.runtime.digest(identity), component_file_counts=[len(c['files']) for c in components],
            output_file_count=len(identity['files']), logical_copy_bytes=sum(r['size'] for c in components for r in c['files'].values()),
            source_unchanged=True, runtime_unchanged=True, std_source_paths_qualified=False,
            candidate_is_not_installation=True, final_root_probes_run=False,
            std_mir_admission='blocked until E-specific source qualification and an explicitly bound immutable policy')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--frozen-sha', required=True)
    args = parser.parse_args()
    stage = Inspection(args)
    try:
        with stage.owned.workload_lock(stage.owned.CANONICAL_LOCK, 600):
            stage.record.update(status='running', admitted_at=time.time(), free_bytes_before=stage.capacity())
            stage.save()
            for path, digest in stage.frozen['files'].items():
                stage.bound(dict(path=path, sha256=digest))
            stage.bound(dict(path=str(FROZEN), sha256=args.frozen_sha))
            stage.inspect()
            stage.record.update(finished_at=time.time(), free_bytes_after=stage.capacity())
            stage.save()
    except Exception as error:
        stage.record.update(status='failed', error=str(error), error_type=type(error).__name__, finished_at=time.time())
        stage.save()
        raise


if __name__ == '__main__':
    main()
