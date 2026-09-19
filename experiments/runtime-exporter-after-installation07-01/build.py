#!/usr/bin/env python3
"""Build the two ordinary exporter tools after separately closed metadata.

This source does not rebuild a compiler or VM, run a guest, publish tools, or
qualify application/frontend behavior. The single Cargo call retains its locked,
offline, release, jobs=2 recipe; build-script compiler probes remain real calls.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-exporter-after-installation07-01')
NAMES = ('rust-interp-mir-export', 'rust-interp-rustc-wrapper')


def bootstrap(digest, build_digest):
    """Authenticate the complete selected source set before any local import."""
    manifest = HERE/'sources.json'; data = manifest.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise RuntimeError('reviewed exporter source manifest differs')
    sources = json.loads(data)['files']
    build_manifest = HERE/'build-sources.json'; build_data = build_manifest.read_bytes()
    if hashlib.sha256(build_data).hexdigest() != build_digest:
        raise RuntimeError('reviewed build source manifest differs')
    build_inventory = json.loads(build_data)
    build_sources = build_inventory['files']
    required = {str(HERE/name) for name in
                ('build.py', 'metadata.py', 'common.py', 'build_checks.py', 'cargo_output.py')}
    if (not required <= set(build_sources)
            or build_inventory['metadata_sources'] != dict(path=str(manifest), sha256=digest)
            or build_sources.get(str(manifest)) != digest
            or any(build_sources.get(path) != sha for path, sha in sources.items())
            or set(build_sources) != set(sources) | required | {str(manifest)}):
        raise RuntimeError('build import source authentication is incomplete')
    for name, expected in build_sources.items():
        path = Path(name)
        if (path.resolve(strict=True) != path or path.is_symlink()
                or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected):
            raise RuntimeError('authenticated source changed: '+name)
    if str(Path(__file__).resolve()) != str(HERE/'build.py'):
        raise RuntimeError('fixed build source route required')

    def load(name):
        private = '_exporter07_build_'+name
        if private in sys.modules:
            raise RuntimeError('unexpected existing build module')
        spec = importlib.util.spec_from_file_location(private, HERE/(name+'.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[private] = module
        spec.loader.exec_module(module)
        return module
    return load('common'), load('metadata'), load('build_checks'), load('cargo_output'), sources, build_sources


def build_class(metadata, checks, parser):
    """Select the authenticated metadata base without importing old controllers."""
    class Build(metadata.Stage):
        def __init__(self, c, mods, sources, build_sources, args):
            args.phase = 'build'
            super().__init__(c, mods, sources, args)
            self.build_sources = build_sources
            self.protected = {}
            self.binaries = {}
            self.schedule = []
            self.record.update(metadata_receipt_sha256=args.metadata_receipt_sha256,
                build_sources_sha256=args.build_sources_sha256,
                environment=dict(os.environ), canonical_lock=str(c.LOCK), wait_seconds=600,
                capacity=dict(entry_gib=16, stop_gib=9, floor_gib=8),
                direct_children=7, expected_build_script_compiler_identity_probes=4,
                frontend_qualified=False, published=False)
            self.save()

        def protect(self, path, expected=None):
            row = self.c.file(path, expected)
            previous = self.protected.setdefault(row['path'], row)
            self.c.require(previous == row, 'protected build evidence/output changed')
            return row

        def guard(self, full=False):
            super().guard(full=full)
            self.c.file(HERE/'build-sources.json', self.args.build_sources_sha256)
            for name, digest in self.build_sources.items():
                self.c.file(name, digest)
            for path, row in getattr(self, 'protected', {}).items():
                self.c.require(self.c.file(path) == row, 'completed build evidence/output changed: '+path)

        def command(self, row):
            c = self.c
            index = len(self.record['commands'])
            c.require(index < len(self.schedule) and row == self.schedule[index],
                      'unreviewed build child or child order')
            if index == 0:
                c.require(not os.path.lexists(c.TARGET)
                    and c.TARGET.parent.resolve(strict=True) == c.TARGET.parent
                    and c.TARGET.parent.is_dir(), 'fresh ordinary target required after admission')
            result = super().command(row)
            self.protect(result['path'])
            for stream in ('stdout', 'stderr'):
                self.protect(Path(result['path']).parent/stream, result['receipt'][stream+'_sha256'])
            return result

        def metadata_receipts(self):
            c = self.c
            receipt_path = c.WORK/'receipt.json'
            self.protect(receipt_path, self.args.metadata_receipt_sha256)
            receipt = c.read(receipt_path, self.args.metadata_receipt_sha256)
            c.require(receipt['status'] == 'passed' and receipt['phase'] == 'metadata'
                and receipt['inputs_sha256'] == self.args.inputs_sha256
                and receipt['sources_sha256'] == self.args.sources_sha256
                and receipt['plan_sha256'] == self.inputs['plan']['sha256']
                and receipt['runtime_key'] == c.KEY and receipt['cwd'] == str(c.X)
                and receipt['exporter_builds'] == receipt['compiler_builds'] == receipt['VM_builds'] == 0
                and receipt['signals'] == receipt['retries'] == 0 and 'error' not in receipt
                and 0 < receipt['started_at'] <= receipt['admitted_at'] <= receipt['finished_at']
                    <= self.record['started_at']
                and len(receipt['commands']) == len(self.plan['children']),
                'complete successful prior metadata required')
            observed = {}; previous_finish = receipt['admitted_at']; loader_rows = []
            for index, (saved, wanted) in enumerate(zip(receipt['commands'], self.plan['children'], strict=True)):
                path = c.WORK/'commands'/f'{index:03d}'/'receipt.json'
                c.require(saved['path'] == str(path) and saved['label'] == wanted['label'],
                          'metadata command path/label differs')
                self.protect(path, saved['sha256']); actual = c.read(path, saved['sha256'])
                c.require(actual['status'] == 'finished' and actual['returncode'] == saved['returncode'] == 0
                    and actual['pid'] == saved['pid'] and actual['command'] == wanted['command']
                    and actual['environment'] == wanted['environment'] and actual['cwd'] == wanted['cwd']
                    and actual['supervisor_pid'] == receipt['pid'] and actual['parent_pid'] == receipt['parent_pid']
                    and previous_finish <= actual['started_at'] <= actual['finished_at'] <= receipt['finished_at'],
                    'metadata command closure association differs')
                previous_finish = actual['finished_at']
                for stream in ('stdout', 'stderr'):
                    self.protect(path.parent/stream, actual[stream+'_sha256'])
                result = dict(receipt=actual, path=str(path), stdout=(path.parent/'stdout').read_bytes(),
                              stderr=(path.parent/'stderr').read_bytes())
                c.require(wanted['label'] not in observed, 'repeated metadata child label')
                observed[wanted['label']] = result
                argv = wanted['command']
                if argv[:3] == ['/usr/bin/otool', '-arch', 'arm64']:
                    c.require(len(argv) == 5 and argv[3] in ('-L', '-l') and not result['stderr'],
                              'metadata loader command/diagnostics differ')
                    key = (str(Path(argv[-1]).resolve(strict=True)), argv[3])
                    c.require(key not in self.cache, 'repeated metadata loader input')
                    self.cache[key] = result
                    loader_rows.append(dict(path=key[0], flag=key[1], receipt=str(path),
                                            stdout_sha256=actual['stdout_sha256']))
                if wanted.get('expected_stdout_sha256') is not None:
                    c.require(not result['stderr'] and actual['stdout_sha256'] == wanted['expected_stdout_sha256'],
                              'saved SDK query no longer matches prepared declaration')
            result_path = c.WORK/'planned.json'
            result_ref = receipt['result']
            c.require(result_ref['path'] == str(result_path)
                and self.protect(result_path, result_ref['sha256']) == result_ref,
                'metadata result reference differs')
            result = c.read(result_path, result_ref['sha256'])
            c.require(result['status'] == 'metadata-passed-build-unexecuted'
                and result['binding'] == self.plan['binding']
                and result['plan_sha256'] == self.inputs['plan']['sha256']
                and result['actual_children'] == len(self.plan['children'])
                and result['application_qualified'] is False and result['performance_measurement'] is False
                and result['loader_observations'] == sorted(loader_rows, key=lambda r: (r['path'], r['flag'])),
                'metadata result/complete loader observations differ')
            cargo = observed['cargo-metadata']
            c.require(not cargo['stderr'], 'saved Cargo metadata diagnostics')
            self.protect(c.WORK/'cargo-metadata.json', cargo['receipt']['stdout_sha256'])
            prior = self.plan['historical_cargo_metadata']
            dependencies = c.dependency_contract(json.loads(cargo['stdout']),
                c.read(prior['path'], prior['sha256']), c.PREFIX)
            c.require(result['dependencies'] == dependencies, 'saved ordinary metadata dependency contract differs')
            c.require(c.read(c.PACKET/'compiler-roles.json') == self.plan['binding'], 'prepared compiler roles differ')
            self.record['metadata'] = dict(receipt=self.protected[str(receipt_path)], result=result_ref,
                                          actual_children=len(observed))
            self.save()
            return result

        def child_schedule(self):
            c = self.c; future = self.plan['future_build']; binding = self.plan['binding']
            cargo_rows = [r for r in self.plan['children'] if r['label'] == 'cargo-metadata']
            c.require(len(cargo_rows) == 1, 'one selected Cargo metadata executor required')
            cargo = cargo_rows[0]['command'][0]
            expected = [cargo, 'build', '--release', '--locked', '--offline', '--jobs', '2', '-vv',
                '--message-format=json-render-diagnostics', '--manifest-path', str(c.PREFIX/'Cargo.toml'),
                '--target-dir', str(c.TARGET), '-p', 'rust-interp-mir-export',
                '--bin', NAMES[0], '--bin', NAMES[1]]
            environment = self.plan['build_environment'] | {'TMPDIR':str(self.work/'tmp')+'/'}
            c.require(future == dict(command=expected, cwd=str(c.PREFIX), environment=environment,
                                    exporter_builds=1, compiler_builds=0, VM_builds=0),
                      'exact ordinary locked/offline jobs=2 build recipe required')
            c.require(self.plan['build_environment'] | {'CARGO_TARGET_DIR':str(c.WORK/'cargo-target')}
                    == cargo_rows[0]['environment']
                and environment['RUSTC'] == str(c.D2/'bin/rustc')
                and environment['RUSTDOC'] == str(c.D2/'bin/rustdoc')
                and environment['RUSTC_BOOTSTRAP'] == '1'
                and environment['RUST_INTERP_COMPILER_ROLES'] == str(c.PACKET/'compiler-roles.json')
                and environment['CARGO_ENCODED_RUSTFLAGS'] == '\x1f'.join(binding['build_rustflags'])
                and not any(name in environment for name in ('RUSTC_FORCE_RUSTC_VERSION',
                    'RUSTC_OVERRIDE_VERSION_STRING', 'RUSTFLAGS', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER')),
                'ordinary separate-role build environment differs')
            env = self.plan['launch_environment']
            rows = [dict(label='cargo-build', command=expected, cwd=str(c.PREFIX), environment=environment, expected=[0])]
            for name in NAMES:
                for flag in ('-L', '-l'):
                    rows.append(dict(label=name+flag,
                        command=['/usr/bin/otool', '-arch', 'arm64', flag, str(c.TARGET/'release'/name)],
                        cwd=str(c.X), environment=env, expected=[0]))
            rows.extend([
                dict(label='exporter-capabilities', command=[str(c.TARGET/'release'/NAMES[0]), '--rust-interp-capabilities'],
                     cwd=str(c.X), environment=env|{'DYLD_PRINT_LIBRARIES':'1'}, expected=[0]),
                dict(label='wrapper-roles', command=[str(c.TARGET/'release'/NAMES[1]), '--rust-interp-compiler-roles'],
                     cwd=str(c.X), environment=env, expected=[0])])
            return rows

        def build(self):
            c = self.c; saved_metadata = self.metadata_receipts()
            self.schedule = self.child_schedule()
            built = self.command(self.schedule[0])
            self.record['exporter_builds'] = 1; self.save()
            checks.check_build_diagnostics(built['stderr'])
            parsed = parser.parse_cargo_output(built['stdout'], saved_metadata['dependencies']['packages'])
            compiled = checks.cargo_compiles(built['stderr'], self.plan['binding'], c.PREFIX, set(self.plan['files']))
            for name in NAMES:
                self.binaries[name] = self.protect(c.TARGET/'release'/name)
            artifacts = [row for row in parsed['messages'] if row.get('reason') == 'compiler-artifact'
                         and 'bin' in row.get('target', {}).get('kind', []) and row.get('executable')]
            c.require({row['executable'] for row in artifacts} == {r['path'] for r in self.binaries.values()},
                      'Cargo executable set differs')
            for name in NAMES:
                found = [row for row in artifacts if row['executable'] == self.binaries[name]['path']]
                c.require(len(found) == 1 and found[0]['target']['name'] == name
                    and found[0]['fresh'] is False, 'exact fresh named exporter/wrapper artifact required')
            generated = []
            for message in parsed['messages']:
                if message.get('reason') == 'build-script-executed' and message.get('out_dir'):
                    out = Path(message['out_dir'])
                    c.require(out.is_relative_to(c.TARGET) and out.resolve(strict=True) == out,
                              'Cargo build-script output outside ordinary owned target')
                    path = out/'compiler_roles.rs'
                    if os.path.lexists(path):
                        generated.append(self.protect(path))
            c.require(len(generated) == 1, 'exact generated role binding required')
            tool_closures = {}
            for name in NAMES:
                path = self.binaries[name]['path']
                for flag in ('-L', '-l'):
                    self.cache[(path, flag)] = self.command(self.schedule[len(self.record['commands'])])
                tool_closures[name] = self.closure(path)
            capabilities = self.command(self.schedule[len(self.record['commands'])])
            caps = json.loads(capabilities['stdout']); exporter = self.binaries[NAMES[0]]['path']
            allowed = {exporter} | {r['resolved'] for r in tool_closures[NAMES[0]]['identity']['libraries']}
            loaded = metadata.loaded_libraries(c, capabilities['stderr'], capabilities['receipt']['pid'],
                                              allowed, self.plan['binding']['runtime_driver']['path'])
            c.require(caps['schema_version'] == 1 and caps['bytecode_version'] == 5
                and caps['compiler_sysroot'] == str(c.RUNTIME) and caps['compiler_roles'] == self.plan['binding'],
                'built exporter capability/role binding differs')
            wrapper = self.command(self.schedule[len(self.record['commands'])])
            c.require(not wrapper['stderr'], 'wrapper role diagnostics')
            binary_map = {name: row['sha256'] for name, row in self.binaries.items()}
            vm = self.plan['adopted_VM']['binary']
            c.require(c.file(vm['path']) == self.plan['files'][vm['path']], 'adopted VM changed')
            binary_map['rust-interp-vm'] = vm['sha256']
            compiler = self.mods.runtime.load_runtime_compiler(c.R, c.KEY)
            self.mods.tools.bind_recorded_wrapper(caps, binary_map, compiler, wrapper['stdout'])
            c.require(len(self.record['commands']) == len(self.schedule) == 7, 'all seven build children required')
            evidence = c.write(self.work/'cargo-build-evidence.json', dict(parsed=parsed, compilers=compiled,
                generated=generated, cargo_receipt=self.protected[built['path']], strip_failures=0,
                build_script_compiler_identity_probes=4,
                nested_probe_scope='Four real role identity probes in the authenticated build script; not separately supervised here.'))
            self.protect(evidence['path'], evidence['sha256'])
            self.guard(full=True)
            for closure in tool_closures.values():
                c.require(self.mods.loaders.library_state(closure['identity']) == closure['state'],
                          'built tool loader resolution changed')
            return c.write(self.work/'built-tools.json', dict(status='build-passed-frontend-unexecuted',
                binaries=binary_map, built_files=self.binaries, capabilities=caps,
                compiler_roles=self.plan['binding'], generated=generated, exporter_loader=loaded,
                tool_closures=tool_closures, evidence=evidence, metadata=self.record['metadata'],
                exporter_probe=self.protected[capabilities['path']], wrapper_probe=self.protected[wrapper['path']],
                VM=self.plan['adopted_VM'], runtime_owner=str(c.R), runtime_key=c.KEY,
                frontend_qualified=False, application_qualified=False, published=False,
                performance_measurement=False))
    return Build


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ('inputs-sha256', 'sources-sha256', 'build-sources-sha256', 'metadata-receipt-sha256'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    c, metadata, checks, cargo, sources, build_sources = bootstrap(args.sources_sha256, args.build_sources_sha256)
    c.require(Path.cwd() == c.X and sys.dont_write_bytecode and not sys.flags.optimize,
              'fixed exporter Python -B/cwd required')
    mods = c.modules(sources)
    def no_signals(event, arguments):
        if event in ('os.kill', 'os.killpg'):
            raise RuntimeError('explicit process signals are forbidden')
    sys.addaudithook(no_signals)
    with c.aliases(mods.public):
        build_class(metadata, checks, cargo)(c, mods, sources, build_sources, args).execute()


if __name__ == '__main__':
    main()
