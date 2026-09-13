#!/usr/bin/env python3
"""Separate real source-path/observable prerequisite; never a timed build screen."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import stat
import sys

from compare_saved_runtime import acquire_lock, lock_wait_seconds
from custom_compiler import digest, file_digest, load_compiler, require, tree_stamps, validate_tool_compiler
from interpreter import ROOT, TOOLCHAIN, installed_tools, require_export_option
from mono_qualification import decode_record, validate_flags
from qualify_custom_compiler import environment, diagnostic_records, core_diagnostics, validate_launch
from standard_diagnostic_mapping import prepare_standard_diagnostic_mapping
from std_mir_source_paths import SOURCE, load as load_std, tree_files, validate_probe
from workflow_io import SourceEdit, capture, require_space, write_json
import stable_mono_cgu

POLICY = 'std-source-observables-v1'
PHASES = ('unmapped', 'std-only', 'application-map', 'restored')
APP_PREFIX = '/owned-source-observable/src'
COORDINATES = ('byte_start', 'byte_end', 'line_start', 'line_end', 'column_start', 'column_end')


def nested_spans(value):
    if isinstance(value, list):
        for child in value:
            yield from nested_spans(child)
    elif isinstance(value, dict):
        if 'file_name' in value:
            yield value
        for child in value.values():
            yield from nested_spans(child)


def position_control(original, edited, path, prefix):
    def positions(records):
        return sorted(tuple(span[k] for k in COORDINATES) for span in nested_spans(records)
                      if span['file_name'] == str(path))
    before, after = positions(original), positions(edited)
    require(before and after == [tuple(v + (len(prefix) if i < 2 else prefix.count(b'\n') if i < 4 else 0)
                                       for i, v in enumerate(values)) for values in before],
            'actual application diagnostic coordinates did not follow the source position edit')


def fixture(directory):
    (directory / 'src/core/src').mkdir(parents=True)
    (directory / 'macros/src').mkdir(parents=True)
    (directory / 'Cargo.toml').write_text('[package]\nname="std-source-observables"\nversion="0.0.0"\nedition="2024"\n'
        '[workspace]\nmembers=["macros"]\nresolver="2"\n'
        '[dependencies]\npath-probe={path="macros"}\n'
        '[profile.dev]\ncodegen-units=2\nincremental=true\n[profile.dev.build-override]\ncodegen-units=2\n')
    (directory / 'macros/Cargo.toml').write_text('[package]\nname="path-probe"\nversion="0.0.0"\nedition="2024"\n'
                                               '[lib]\nproc-macro=true\n')
    (directory / 'macros/src/lib.rs').write_text('extern crate proc_macro;\n'
        '#[proc_macro] pub fn observe(input: proc_macro::TokenStream) -> proc_macro::TokenStream {\n'
        ' let span = input.into_iter().next().expect("marker token").span();\n'
        ' let local = span.local_file().expect("actual source path");\n'
        ' format!("({:?}, {:?}, {}u32, {}u32)", span.file(), local.to_str().unwrap(), '
        'span.line(), span.column()).parse().unwrap()\n}\n')
    (directory / 'src/main.rs').write_text('// phase:000000000000000\n'
        '#[path="core/src/panic.rs"] mod std_looking;\n'
        'pub fn show(label: &str, file: &str, value: (&str, &str, u32, u32)) {\n'
        ' println!("{}|{}|{}|{}|{}|{}", label, file, value.0, value.1, value.2, value.3);\n}\n'
        'pub fn entry() { show("main", file!(), path_probe::observe!(marker)); std_looking::run(); }\n'
        'fn main() { entry(); }\n')
    (directory / 'src/core/src/panic.rs').write_text(
        'pub fn run() { crate::show("std-looking", file!(), path_probe::observe!(marker)); }\n')


def cargo_configuration(flags, host):
    array = json.dumps(flags)
    return ('target-applies-to-host=false\n[unstable]\nhost-config=true\ntarget-applies-to-host=true\n'
            '[host]\nrustflags=' + array + '\n[host.' + json.dumps(host) + ']\nrustflags=' + array +
            '\n[target.' + json.dumps(host) + ']\nrustflags=' + array + '\n').encode()


def observable_values(output, workspace, source):
    result = {}
    expected = {'main': 'src/main.rs', 'std-looking': 'src/core/src/panic.rs'}
    for line in output.splitlines():
        parts = line.split('|')
        require(len(parts) == 6 and parts[0] in expected and parts[0] not in result,
                'unexpected source-observable output')
        label, file, display, local, line_number, column = parts
        relative = expected[label]
        def actual_file(name):
            path = Path(name)
            return path if path.is_absolute() else workspace / path
        require(actual_file(file) == workspace / relative and actual_file(local) == workspace / relative,
                'file! or local_file does not name the actual owned source')
        require(display.startswith(APP_PREFIX + '/') or actual_file(display) == workspace / relative,
                'Span::file does not name the expected owned source')
        lines = (source / relative).read_text().splitlines()
        index = next(i for i, text in enumerate(lines) if 'observe!(marker)' in text)
        require((int(line_number), int(column)) == (index + 1, lines[index].index('marker') + 1),
                'proc-macro line/column differs from actual source coordinates')
        result[label] = dict(file=file, span_file=display, local_file=local,
                             line=int(line_number), column=int(column), relative=relative)
    require(set(result) == set(expected), 'missing source-observable function')
    return result


def compare_observables(values):
    require(set(values) == set(PHASES), 'incomplete mapped/unmapped history')
    require(values['unmapped'] == values['std-only'] == values['restored'],
            'std-only diagnostic remapping changed application source observables')
    changed = copy.deepcopy(values['application-map'])
    for label, value in changed.items():
        require(value['span_file'] == APP_PREFIX + '/' + value['relative'].removeprefix('src/'),
                'application remap did not change Span::file as the pinned API specifies')
        require(value['span_file'] != values['unmapped'][label]['span_file'],
                'application remap sensitivity was not exercised')
        value['span_file'] = values['unmapped'][label]['span_file']
    # This comparison view is only for program observables. Raw outputs remain
    # in every command; compiler diagnostic records are never transformed here.
    require(changed == values['unmapped'], 'diagnostic-only remap changed file!/local_file/coordinates')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler-key', required=True)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--std-mir-off-key', required=True)
    parser.add_argument('--std-mir-on-key', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--lock-wait-seconds', type=lock_wait_seconds, default=600)
    args = parser.parse_args()
    require(__debug__ and args.run_id and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.run_id),
            'invalid source qualification run or disabled assertions')
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    rows, histories, negatives, observables, argv_records = [], [], [], [], []
    controls = dict(diagnostic_histories=histories, negatives=negatives,
                    observable_histories=observables, actual_compiler_argv=argv_records,
                    standard_source_files={})
    scripts = {str(p): file_digest(p) for p in (ROOT / 'scripts').glob('*.py')}
    env = environment()
    try:
        with (Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')).open('r+') as lock:
            acquire_lock(lock, args.lock_wait_seconds)
            compiler = load_compiler(ROOT, args.compiler_key)
            tools, key = installed_tools(args.tool_key)
            validate_tool_compiler(tools, key, compiler)
            wrapper = stable_mono_cgu.require_tool_capability(tools, compiler)
            for option in ['stable-mono-cgu-partitioning', 'compiler-argv-record-v1', 'function-cache-auto',
                           'inline-leaves', 'trap-unsupported-calls', 'run-try-callbacks']:
                require_export_option(tools, key, option)
            compiler.require_option('stable-mono-cgu-partitioning')
            stds, ready = {}, {}
            for mode in ['off', 'on']:
                selected = load_std(ROOT, getattr(args, 'std_mir_' + mode + '_key'), compiler,
                                    'stable-mono-cgu:' + mode, rehash=True)
                stds[mode] = dict(key=selected[2], sysroot=str(selected[0]), target=selected[1])
                ready[mode] = selected[3]
            source_files = {p[len(SOURCE):]: h for p, h in compiler.identity['files'].items() if p.startswith(SOURCE)}
            (work / 'source-snapshots').mkdir()
            for path in scripts:
                shutil.copy2(path, work / 'source-snapshots' / Path(path).name)
            copy_guards, controlled_files = {}, {}
            def guard():
                require(load_compiler(ROOT, compiler.key) == compiler, 'compiler identity changed')
                installed_tools(key)
                require(all(file_digest(Path(p)) == h for p, h in scripts.items()), 'qualification source changed')
                for mode, std in stds.items():
                    require(load_std(ROOT, std['key'], compiler, 'stable-mono-cgu:' + mode)[3] == ready[mode],
                            'prepared standard identity changed')
                for path, stamps in copy_guards.items():
                    require(tree_stamps(path) == stamps, 'second-prefix copy changed')
                for path, expected in controlled_files.items():
                    require(not path.is_symlink() and file_digest(path) == expected,
                            'owned observable fixture changed unexpectedly')
            def invoke(label, command, cwd=work, expected=0, actual_env=None):
                guard(); require_space(work, 8)
                index = len(rows)
                command = list(map(str, command))
                child, stdout, stderr = capture(command, cwd=cwd, env=env if actual_env is None else actual_env,
                    receipt_path=work / f'{index:03d}-child.json', receipt=dict(label=label))
                row = dict(label=label, command=command, cwd=str(cwd), returncode=child.returncode,
                           stdout=stdout, stderr=stderr, expected_returncode=expected)
                rows.append(row); write_json(work / 'commands.json', rows)
                require(child.returncode == expected, 'source qualification command failed: ' + label)
                guard()
                return row
            public_path = Path(invoke('public-location', ['rustup', 'which', '--toolchain', TOOLCHAIN, 'rustc'])['stdout'].strip()).resolve(strict=True)
            public = dict(rustc=str(public_path), sha256=file_digest(public_path),
                          compiler=invoke('public-version', [public_path, '-vV'])['stdout'])
            mapping_fixture = work / 'mapping-configuration'; mapping_fixture.mkdir()
            mapping = prepare_standard_diagnostic_mapping(mapping_fixture, compiler,
                public_path.parent.parent / SOURCE, {m: Path(s['sysroot']) for m, s in stds.items()}, env,
                public_compiler=public)
            write_json(work / 'diagnostic-mapping.json', mapping.evidence())
            selected_roots = dict(native=compiler.sysroot, **{m: Path(s['sysroot']) for m, s in stds.items()})
            # Copies are independent files, never hard links into an installed
            # compiler/std tree. Reserve all planned logical bytes plus the floor.
            projected = sum(p.stat().st_size for root in selected_roots.values() for p in root.rglob('*') if p.is_file())
            projected += 2 * sum(p.stat().st_size for p in selected_roots['off'].rglob('*') if p.is_file())
            require(shutil.disk_usage(work).free >= projected + 8 * 2**30, 'insufficient space for independent source-control copies')
            copies = {}
            for role, root in selected_roots.items():
                target = work / 'second-prefix' / role
                shutil.copytree(root, target, symlinks=False)
                require(tree_files(target) == tree_files(root), 'second-prefix copy differs')
                copies[role] = target
                copy_guards[target] = tree_stamps(target)
            second_rustc = copies['native'] / 'bin/rustc'
            require(invoke('second-prefix-version', [second_rustc, '-vV'])['stdout'] == compiler.identity['compiler'],
                    'relocated compiler version differs')
            require(invoke('second-prefix-sysroot', [second_rustc, '--print', 'sysroot'])['stdout'].strip() == str(copies['native']),
                    'relocated compiler uses a different prefix')
            plan = dict(policy=POLICY, owner=str(ROOT), compiler_key=compiler.key, tool_key=key,
                compiler_sysroot=str(compiler.sysroot), compiler=compiler.identity, std_mir=stds, std_readiness=ready,
                tools=json.loads((tools / 'ready.json').read_text()), scripts=scripts,
                copied_sources={k: str(v) for k, v in copies.items()}, source_files=source_files,
                projected_copy_bytes=projected, environment_sha256=digest(env), benchmark=False,
                expected_application_remap='Span::file only; pinned prefer_remapped_unconditionally API')
            write_json(work / 'plan.json', plan)
            initial = b'const UNCALLED: u32 = panic!("source position control");\n'
            shift = '// café\n\n'.encode()
            for prefix_name, roots, rustc in [('original', selected_roots, compiler.rustc), ('second', copies, second_rustc)]:
                for role, sysroot in roots.items():
                    directory = work / 'source-histories' / prefix_name / role; directory.mkdir(parents=True)
                    source = directory / 'source.rs'; source.write_bytes(initial)
                    states = {}
                    with SourceEdit(source, initial) as edit:
                        for state, payload in [('cold', initial), ('position-edited', shift + initial), ('restored', initial)]:
                            edit.replace(payload)
                            row = invoke('-'.join([prefix_name, role, state]), [rustc, source,
                                '--crate-type=lib', '--edition=2024', '--emit=metadata', '--error-format=json',
                                '--sysroot', sysroot, '-Cincremental=' + str(directory / 'incremental'),
                                '-Zstable-cgu-partitioning=no', '-Zstable-mono-cgu-partitioning=' + ('yes' if role == 'on' else 'no'),
                                '-o', directory / 'unused.rmeta'], directory, expected=1)
                            records = diagnostic_records(row['stderr'])
                            validate_probe(records, sysroot / SOURCE, source_files)
                            for span in nested_spans(records):
                                filename = Path(span['file_name'])
                                if filename.is_absolute() and filename.is_relative_to(sysroot / SOURCE):
                                    relative = str(filename.relative_to(sysroot / SOURCE))
                                    destination = work / 'verified-standard-sources' / relative
                                    destination.parent.mkdir(parents=True, exist_ok=True)
                                    if not destination.exists():
                                        shutil.copy2(compiler.sysroot / SOURCE / relative, destination)
                                    require(file_digest(destination) == source_files[relative], 'retained source payload differs')
                                    controls['standard_source_files'][relative] = dict(
                                        path=str(destination.relative_to(work)), sha256=source_files[relative])
                            require(source.read_bytes() == payload, 'source probe changed during compilation')
                            row.update(source_sha256=file_digest(source), validated=True)
                            states[state] = dict(command_index=len(rows)-1, source_sha256=file_digest(source),
                                                 diagnostics=records)
                    position_control(states['cold']['diagnostics'], states['position-edited']['diagnostics'], source, shift)
                    require(core_diagnostics(states['cold']['diagnostics'], ROOT) ==
                            core_diagnostics(states['restored']['diagnostics'], ROOT), 'restored diagnostics differ')
                    require(source.read_bytes() == initial, 'source position fixture was not restored')
                    histories.append(dict(prefix=prefix_name, role=role, sysroot=str(sysroot), source=str(source), states=states))
                    write_json(work / 'controls.json', controls)
            for kind in ['missing', 'corrupt']:
                sysroot = work / ('negative-' + kind)
                shutil.copytree(selected_roots['off'], sysroot, symlinks=False)
                victim = sysroot / SOURCE / 'core/src/panic.rs'
                require(file_digest(victim) == source_files['core/src/panic.rs'], 'negative copy starts with different source')
                victim.parent.chmod(0o755)
                if kind == 'missing':
                    victim.unlink()
                else:
                    victim.chmod(0o644); victim.write_bytes(b'X' * victim.stat().st_size)
                source = work / ('negative-' + kind + '.rs'); source.write_bytes(initial)
                row = invoke('negative-' + kind, [compiler.rustc, source, '--crate-type=lib', '--edition=2024',
                    '--emit=metadata', '--error-format=json', '--sysroot', sysroot,
                    '-o', work / ('negative-' + kind + '.rmeta')], expected=1)
                records = diagnostic_records(row['stderr'])
                require(any(d.get('code', {}) and d['code'].get('code') == 'E0080' for d in records),
                        'negative source probe did not retain ordinary E0080 rejection')
                rejected = None
                try:
                    validate_probe(records, sysroot / SOURCE, source_files)
                except (RuntimeError, OSError, UnicodeError) as error:
                    rejected = str(error)
                require(rejected is not None, 'bad source copy passed raw diagnostic verification')
                negatives.append(dict(kind=kind, command_index=len(rows)-1, changed_source=str(victim),
                    sysroot=str(sysroot), expected_sha256=source_files['core/src/panic.rs'],
                    after_files=tree_files(sysroot), validator_rejection=rejected))
            application = work / 'application'; fixture(application)
            invoke('application-lockfile', ['cargo', '+' + TOOLCHAIN, 'generate-lockfile',
                '--manifest-path', application / 'Cargo.toml', '--offline'], application)
            controlled_files.update({p: file_digest(p) for p in application.rglob('*') if p.is_file()})
            (application / '.cargo').mkdir()
            config_path = application / '.cargo/config.toml'
            main_source = application / 'src/main.rs'; original_main = main_source.read_bytes()
            for mode in ['off', 'on']:
                policy_flags = ['-Zstable-cgu-partitioning=no', '-Zstable-mono-cgu-partitioning=' + ('yes' if mode == 'on' else 'no')]
                for route in ['native', 'exported']:
                    values, states = {}, {}
                    cache = work / 'observable-cache' / (mode + '-' + route); cache.mkdir(parents=True)
                    workspace = application
                    with SourceEdit(main_source, original_main) as edit:
                        for phase_index, phase in enumerate(PHASES):
                            # Same-width comments force actual selected recompilation
                            # while preserving every observed source coordinate.
                            edit.replace(original_main.replace(b'000000000000000', (str(phase_index) * 15).encode())
                                         if phase != 'restored' else original_main)
                            controlled_files[main_source] = file_digest(main_source)
                            flags = [] if phase in ['unmapped', 'restored'] else list(mapping.rustc_flags)
                            if phase == 'application-map':
                                flags += ['--remap-path-prefix=src=' + APP_PREFIX]
                            config_path.write_bytes(cargo_configuration(flags, compiler.host))
                            controlled_files[config_path] = file_digest(config_path)
                            if route == 'native':
                                macro = cache / 'libpath_probe.dylib'
                                invoke(mode + '-' + phase + '-macro', [compiler.rustc, 'macros/src/lib.rs',
                                    '--crate-name=path_probe', '--crate-type=proc-macro', '--edition=2024',
                                    '-Zunstable-options', '--jobs-backend=2',
                                    '-Ccodegen-units=2', '-Cincremental=' + str(cache / 'macro-incremental'),
                                    *policy_flags, *flags, '-o', macro], application)
                                output = cache / 'native'
                                row = invoke(mode + '-' + phase + '-native-build', [compiler.rustc, 'src/main.rs',
                                    '--crate-name=std_source_observables', '--edition=2024', '--extern', 'path_probe=' + str(macro),
                                    '-Zunstable-options', '--jobs-backend=2',
                                    '-Ccodegen-units=2', '-Cincremental=' + str(cache / 'app-incremental'),
                                    *policy_flags, *flags, '-o', output], application)
                                compiler_index = len(rows)-1
                                snapshot = work / (mode + '-' + phase + '.native')
                                shutil.copy2(output, snapshot)
                                row = invoke(mode + '-' + phase + '-native-run', [output], application)
                                require(file_digest(output) == file_digest(snapshot), 'executed native artifact changed')
                                row.update(artifact_sha256=file_digest(snapshot), artifact_snapshot=snapshot.name)
                                argv_records.append(dict(mode=mode, phase=phase, route=route, command_index=compiler_index,
                                                         argv=rows[compiler_index]['command']))
                            else:
                                directory = work / 'compiler-argv' / (mode + '-' + phase); directory.mkdir(parents=True)
                                row = invoke(mode + '-' + phase + '-exported', [sys.executable, ROOT / 'scripts/interpreter.py',
                                    '--manifest-path', application / 'Cargo.toml', '--package', 'std-source-observables', '--entry', 'entry',
                                    '--compiler-key', compiler.key, '--tool-key', key, '--stable-cgu-partitioning', 'off',
                                    '--stable-mono-cgu-partitioning', mode, '--std-mir', '--std-mir-policy', 'source-paths-v2',
                                    '--std-mir-key', stds[mode]['key'], '--toolchain-lookup', 'cached',
                                    '--workspace-cache-root', cache, '--cache-namespace', args.run_id,
                                    '--jobs', '2', '--engine', 'jit', '--function-cache', 'auto', '--inline-leaves',
                                    '--jit-resumable-calls', '--jit-persistent-registers', '--trap-unsupported-calls',
                                    '--run-try-callbacks', '--instruction-limit', '100000000', '--allocation-limit', '150000',
                                    '--compiler-argv-record-dir', directory], application)
                                report, artifact = validate_launch(row, compiler, mode, key, stds[mode], cache,
                                    stable_mono_cgu.receipt(mode, compiler, wrapper))
                                workspace = Path(report['workspace_path'])
                                selected = []
                                for path in sorted(directory.glob('*.argv')):
                                    record = decode_record(path); validate_flags(record['argv'], mode)
                                    require(record['compiler_sysroot'] == str(compiler.sysroot), 'recorded compiler differs')
                                    if record['role'] == 'exported' and '--crate-name' in record['argv'] and record['argv'][record['argv'].index('--crate-name')+1] == 'std_source_observables':
                                        selected.append(record['argv'])
                                        argv_records.append(dict(mode=mode, phase=phase, route=route,
                                            command_index=len(rows)-1, argv=record['argv'], raw=str(path.relative_to(work)), raw_sha256=file_digest(path)))
                                require(selected, 'no actual selected compiler argv for observable state')
                                snapshot = work / (mode + '-' + phase + '.rbc'); snapshot.write_bytes(artifact.read_bytes())
                                row.update(artifact_sha256=file_digest(snapshot), artifact_snapshot=snapshot.name)
                            values[phase] = observable_values(row['stdout'], workspace, application)
                            states[phase] = dict(command_index=len(rows)-1, values=values[phase],
                                source_sha256=file_digest(main_source), workspace=str(workspace),
                                rustc_flags=flags, configuration_sha256=file_digest(config_path))
                            for proof in [r for r in argv_records if (r['mode'], r['phase'], r['route']) == (mode, phase, route)]:
                                actual = proof['argv']
                                require([a for a in actual if a.startswith('--remap-path-')] == flags,
                                        'actual compiler diagnostic remaps differ from configured flags')
                        compare_observables(values)
                    require(main_source.read_bytes() == original_main, 'observable source restoration failed')
                    controlled_files[main_source] = file_digest(main_source)
                    observables.append(dict(mode=mode, route=route, states=states))
                    write_json(work / 'controls.json', controls)
            # Native and exported paths may have distinct local absolute roots.
            # Compare their source-relative file identities and exact coordinates,
            # while retaining every raw path/output above.
            for mode in ['off', 'on']:
                pair = [h for h in observables if h['mode'] == mode]
                for phase in PHASES:
                    signatures = [{k: {f: v[f] for f in ['relative', 'line', 'column']} for k, v in h['states'][phase]['values'].items()} for h in pair]
                    require(signatures[0] == signatures[1], 'native/exported source observable identities differ')
            mapping.recheck(); guard()
            require(tree_files(copies['native']) == compiler.identity['files'], 'second compiler copy changed')
            write_json(work / 'commands.json', rows); write_json(work / 'controls.json', controls)
            evidence = {}
            for path in [*work.glob('*.json'), *work.glob('*.rs'), *work.glob('*.rbc'), *work.glob('*.native'),
                         *[p for name in ['compiler-argv', 'source-snapshots', 'application', 'source-histories', 'verified-standard-sources']
                           for p in (work / name).rglob('*') if p.is_file() and 'incremental' not in p.parts]]:
                if path.name != 'result.json':
                    evidence[str(path.relative_to(work))] = file_digest(path)
            result = dict(status='passed', policy=POLICY, owner=str(ROOT), compiler_key=compiler.key, tool_key=key,
                compiler_sysroot=str(compiler.sysroot), std_mir=stds, benchmark=False, diagnostics_rewritten=False,
                source_restored=True, qualification_only=True, unmapped_source_paths='passed',
                std_only_application_observables='unchanged', application_remap_sensitivity='expected-span-file-only-change',
                disposable_source_negatives='rejected-by-raw-source-validator', commands=len(rows),
                plan_sha256=file_digest(work / 'plan.json'), evidence_files=evidence)
            require(len(rows) == 57, 'source-observable prerequisite command contract changed')
            write_json(work / 'result.json', result)
            from std_source_observables import validate_source_observables
            validate_source_observables(work / 'result.json', ROOT, compiler.key, key, stds,
                                        compiler_sysroot=compiler.sysroot)
            print(json.dumps(result))
    except BaseException as error:
        write_json(work / 'commands.json', rows); write_json(work / 'controls.json', controls)
        write_json(work / 'result.json', dict(status='failed', policy=POLICY, benchmark=False,
            error=repr(error), completed_commands=len(rows), compiler_key=args.compiler_key, tool_key=args.tool_key))
        raise


if __name__ == '__main__':
    main()
