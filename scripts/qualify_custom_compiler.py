#!/usr/bin/env python3
"""Real owned stage2 integration checks; this is not a performance qualification.

Requires the matching toolset from build_custom_tools.py. Prepares both std-MIR
namespaces, then uses the ordinary launcher on a fresh local Cargo workspace.
No network fetching, tool rebuilding, sample retries, or holdout access.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

from build_custom_tools import cargo_identity, source_identity
from compare_saved_runtime import acquire_lock, lock_wait_seconds
from custom_compiler import digest, file_digest, load_compiler, require, validate_tool_compiler
from interpreter import ROOT, TOOLCHAIN, installed_tools, require_export_option
from std_mir import FLAGS, POLICY, stamp
from verified_std_diagnostics import VerifiedStandardSources
from workflow_io import SourceEdit, capture, require_space, write_json


MODES = ('off', 'on')
ERRORS = {
    'type': ('fn uncalled() -> u32 { false }', 'E0308'),
    'borrow': ("fn uncalled() -> &'static u32 { let local = 1; &local }", 'E0515'),
    'constant': ('const UNCALLED: u32 = panic!("must be checked");', 'E0080'),
    'panic': ('#[deny(unconditional_panic)]\nfn uncalled() -> u32 { let a = [1]; a[1] }',
              'unconditional_panic'),
}


def environment():
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
           and k not in {'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                         'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR',
                         'CARGO_BUILD_TARGET', 'RUST_TEST_THREADS'}}
    require(not any(k.startswith(('LD_', 'DYLD_')) for k in env), 'loader override is unsupported')
    env.update(CARGO_TERM_COLOR='never', CARGO_TERM_VERBOSE='true', RUST_INTERP_LAUNCH_STATS='1')
    return env


def shared_source(value):
    # More source modules than configured CGUs force the actual native merge
    # branch. This is a mechanism correctness fixture, never a latency sample.
    modules = ''.join(f'pub mod m{i} {{ pub fn part() -> u32 {{ {i} }} }}\n' for i in range(8))
    return ('#![allow(dead_code)]\n' + modules +
            'pub fn value() -> u32 { ' + str(value) + ' + ' +
            ' + '.join(f'm{i}::part()' for i in range(8)) + ' }\n'
            'pub fn generic<T: Copy>(value: T) -> T { value }\n'
            '#[inline] pub fn inlined(value: u32) -> u32 { value + 5 }\n'
            'pub const fn constant() -> u32 { 17 }\n').encode()


def fixture(directory):
    for name in ['src', 'shared/src', 'macros/src']:
        (directory / name).mkdir(parents=True)
    files = {
        'Cargo.toml': '[package]\nname="custom-compiler-fixture"\nversion="0.0.0"\nedition="2024"\n'
            '[workspace]\nmembers=["shared","macros"]\nresolver="2"\n'
            '[dependencies]\ncustom-shared={path="shared"}\ncustom-macros={path="macros"}\n'
            '[build-dependencies]\ncustom-shared={path="shared"}\n'
            '[profile.dev]\ncodegen-units=2\nincremental=true\n'
            '[profile.dev.build-override]\ncodegen-units=2\n',
        'shared/Cargo.toml': '[package]\nname="custom-shared"\nversion="0.0.0"\nedition="2024"\n',
        'macros/Cargo.toml': '[package]\nname="custom-macros"\nversion="0.0.0"\nedition="2024"\n'
            '[lib]\nproc-macro=true\n[dependencies]\ncustom-shared={path="../shared"}\n',
    }
    calculation = ('custom_shared::value() + custom_shared::generic(2u32) + '
                   'custom_shared::inlined(3) + custom_shared::constant()')
    files['build.rs'] = ('fn main() {\nlet value = ' + calculation + ';\n'
        'let out = std::path::PathBuf::from(std::env::var_os("OUT_DIR").unwrap());\n'
        'std::fs::write(out.join("generated.rs"), format!("pub const BUILT: u32 = {value};")).unwrap();\n'
        'std::fs::write(out.join("host-value.txt"), value.to_string()).unwrap();\n'
        'println!("cargo:rerun-if-changed=build.rs");\n}\n')
    files['macros/src/lib.rs'] = ('extern crate proc_macro;\n#[proc_macro]\n'
        'pub fn host_value(_: proc_macro::TokenStream) -> proc_macro::TokenStream {\n'
        'let value = ' + calculation + ';\nvalue.to_string().parse().unwrap()\n}\n')
    files['src/lib.rs'] = ('#![allow(dead_code)]\n'
        'include!(concat!(env!("OUT_DIR"), "/generated.rs"));\n'
        'pub const MACRO: u32 = custom_macros::host_value!();\n'
        'pub fn entry() -> u32 { ' + calculation + ' + BUILT + MACRO }\n')
    files['src/main.rs'] = 'fn main() { println!("{}", custom_compiler_fixture::entry()); }\n'
    for name, text in files.items():
        (directory / name).write_text(text)
    (directory / 'shared/src/lib.rs').write_bytes(shared_source(3))


def compiler_routes(stderr, wrapper, rustc):
    result = []
    for line in stderr.splitlines():
        if 'Running `' not in line:
            continue
        words = shlex.split(line.split('Running `', 1)[1].removesuffix('`'))
        if str(wrapper) not in words:
            continue
        args = words[words.index(str(wrapper)) + 1:]
        require(args and args[0] == str(rustc), 'Cargo selected a different rustc')
        def option(name):
            for index, value in enumerate(args):
                if value == name:
                    return args[index + 1]
                if value.startswith(name + '='):
                    return value.split('=', 1)[1]
            return None
        result.append(dict(crate=option('--crate-name'), target=option('--target'),
                           crate_type=option('--crate-type'), argv=args))
    return result


def validate_routes(routes, host):
    require(any(r['crate'] == 'custom_shared' and r['target'] is None for r in routes),
            'no native shared dependency compilation')
    require(any(r['crate'] == 'custom_shared' and r['target'] == host for r in routes),
            'no guest shared dependency compilation')
    require(any(r['crate_type'] == 'proc-macro' and r['target'] is None for r in routes),
            'no native proc-macro compilation')
    require(any(r['crate'] == 'build_script_build' and r['target'] is None for r in routes),
            'no native build-script compilation')
    require(any(r['crate'] == 'custom_compiler_fixture' and r['target'] == host for r in routes),
            'no selected guest compilation')


def validate_launch(row, compiler, mode, key, std, cache):
    reports = [json.loads(line.removeprefix('rust-interp-launch: '))
               for line in row['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
    require(row['returncode'] == 0 and len(reports) == 1, 'launcher did not complete exactly once')
    report = reports[0]
    require(report['tool_key'] == key and report['custom_compiler'] == dict(key=compiler.key,
        rustc=str(compiler.rustc), rustc_sha256=compiler.identity['files']['bin/rustc'],
        compiler=compiler.identity['compiler'], stable_cgu_partitioning=mode), 'compiler or tools differ')
    require(report['std_mir'] == std and report['toolchain_lookup'] ==
            dict(mode='cached', outcome='owned-manifest'), 'selected std namespace differs')
    workspace = Path(report['workspace_path'])
    artifact = Path(report['artifact_path'])
    require(workspace.resolve(strict=True) == workspace and workspace.is_relative_to(cache),
            'workspace escaped its policy cache')
    require(artifact.resolve(strict=True) == artifact and artifact.is_relative_to(workspace / 'target')
            and file_digest(artifact) == report['artifact_sha256'], 'invalid selected bytecode')
    return report, artifact


def validate_failure(row, code):
    require(row['returncode'] != 0 and code in row['stderr'], 'uncalled error was not rejected')
    require(not any(line.startswith(('rust-interp-launch: ', 'rust-interp-vm: '))
                    for line in row['stderr'].splitlines()) and row['stdout'] == '',
            'failed compilation executed a guest or reported success')


def diagnostic_records(text):
    records = []
    for line in text.splitlines():
        if not line.startswith('{'):
            continue
        value = json.loads(line)
        if value.get('reason') == 'compiler-message':
            records.append(value['message'])
        elif value.get('$message_type') == 'diagnostic':
            records.append(value)
    return records


def core_diagnostics(records, owned_root):
    def normalize(value):
        if isinstance(value, dict):
            return {k: normalize(v) for k, v in value.items() if k != 'rendered'}
        if isinstance(value, list):
            return [normalize(v) for v in value]
        if isinstance(value, str):
            return value.replace(str(owned_root), '<owned-checkout>')
        return value
    result = [normalize(dict(level=r['level'], code=(r.get('code') or {}).get('code'),
                             message=r['message'], spans=r.get('spans', []), children=r.get('children', [])))
              for r in records if r['level'] in ('warning', 'error', 'failure-note')]
    # Concurrent Cargo units may deliver identical warnings in different order.
    # Preserve duplicate records and every semantic field while sorting records.
    return sorted(result, key=lambda value: json.dumps(value, sort_keys=True))


def diagnostic_files(target):
    return {str(path): stamp(path) for path in target.rglob('output-*') if path.is_file()}


def changed_diagnostics(target, before):
    records, files = [], {}
    for name, current in diagnostic_files(target).items():
        if before.get(name) == current:
            continue
        payload = Path(name).read_text()
        found = diagnostic_records(payload)
        if found:
            records.extend(found)
            files[name] = payload
    require(records, 'Cargo did not retain structured diagnostics for the failed invocation')
    return records, files


def public_command(source, host, target):
    # Cargo's json-render-diagnostics consumes compiler-message JSON and emits
    # rendered stderr. Plain json retains the structured diagnostic payloads.
    return ['cargo', '+' + TOOLCHAIN, 'run', '--manifest-path', source / 'Cargo.toml',
        '--package', 'custom-compiler-fixture', '--bin', 'custom-compiler-fixture',
        '--locked', '--offline', '--jobs', '2', '--target', host, '--target-dir', target,
        '--message-format=json']


def argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler-key', required=True)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--lock-wait-seconds', type=lock_wait_seconds, default=45)
    parser.add_argument('--std-mir-policy', choices=['v1', 'source-paths-v2'], default='v1')
    parser.add_argument('--std-mir-off-key', help='preinstalled v2 off namespace')
    parser.add_argument('--std-mir-on-key', help='preinstalled v2 on namespace')
    parser.add_argument('--diagnostic-comparison', choices=['strict', 'verified-std-source'], default='strict',
        help='Explicit preliminary mechanism mode may compare verified std source aliases; '
             'missing snippets remain an unresolved presentation gap, never final qualification.')
    return parser


def qualification_scope(mode, gaps):
    preliminary = mode == 'verified-std-source'
    return dict(diagnostic_comparison=mode,
        qualification_scope='preliminary-mechanism-only' if preliminary else 'strict-integration',
        diagnostic_presentation='incomplete' if gaps else
            ('not-qualified-in-mechanism-mode' if preliminary else 'strict-structured-match'),
        full_presentation_qualified=False if preliminary else None,
        presentation_gap_count=len(gaps), final_target_eligible=False, adoption_eligible=False)


def main():
    args = argument_parser().parse_args()
    std_keys = dict(off=args.std_mir_off_key, on=args.std_mir_on_key)
    if args.std_mir_policy != 'v1' or any(std_keys.values()):
        require(args.std_mir_policy == 'source-paths-v2' and all(std_keys.values())
                and args.diagnostic_comparison == 'strict',
                'std v2 requires both explicit prepared keys and strict diagnostics')
    require(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid run ID')
    work = ROOT / '.work' / args.run_id
    work.mkdir(parents=True, exist_ok=False)
    rows = []
    standard_sources = None
    try:
        require((ROOT / '.work/benchmark.lock').is_file(), 'configure the shared campaign lock before qualification')
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            acquire_lock(lock, args.lock_wait_seconds)
            compiler = load_compiler(ROOT, args.compiler_key)
            tools, key = installed_tools(args.tool_key)
            validate_tool_compiler(tools, key, compiler)
            composition = json.loads((tools / 'compiler.json').read_text())
            require(composition['source_files'] == source_identity(), 'installed tools use different Rust sources')
            require(composition['cargo'] == cargo_identity(), 'Cargo differs from the matching tool build')
            for capability in ['stable-cgu-partitioning', 'function-cache-auto', 'inline-leaves',
                               'trap-unsupported-calls', 'run-try-callbacks']:
                require_export_option(tools, key, capability)
            env = environment()
            compiler.environment(env)
            public_rustc = Path(subprocess.check_output(['rustup', 'which', '--toolchain', TOOLCHAIN,
                                                         'rustc'], text=True).strip()).resolve(strict=True)
            public_identity = dict(rustc=str(public_rustc), sha256=file_digest(public_rustc),
                compiler=subprocess.check_output([str(public_rustc), '-vV'], text=True, env=env))
            frozen = {str(p): file_digest(p) for p in (ROOT / 'scripts').glob('*.py')}
            write_json(work / 'plan.json', dict(kind='real-custom-compiler-integration',
                compiler_key=compiler.key, tool_key=key, compiler=compiler.identity,
                tool_composition=composition, environment_sha256=digest(env), scripts=frozen,
                modes=MODES, benchmark=False, retries='none', minimum_free_gib=8,
                std_mir_policy=args.std_mir_policy, prepared_std_keys=std_keys,
                **qualification_scope(args.diagnostic_comparison, []),
                lock_path=str(Path(lock.name).resolve()), public_reference=public_identity))

            def invoke(label, command, cwd=ROOT, actual_env=None):
                require_space(work, 8)
                require(load_compiler(ROOT, compiler.key) == compiler, 'installed compiler changed')
                require(all(file_digest(Path(p)) == sha for p, sha in frozen.items()), 'harness changed')
                index = len(rows)
                started = time.perf_counter()
                child, stdout, stderr = capture(list(map(str, command)), cwd=cwd, env=env if actual_env is None else actual_env,
                    receipt_path=work / f'{index:02d}-child.json', receipt=dict(label=label))
                row = dict(label=label, command=list(map(str, command)), returncode=child.returncode,
                           seconds=time.perf_counter() - started, stdout=stdout, stderr=stderr)
                rows.append(row)
                write_json(work / 'commands.json', rows)
                print(label, child.returncode, flush=True)
                return row

            stds, prepared = {}, {}
            for mode in MODES:
                std_selection = [] if args.std_mir_policy == 'v1' else [
                    '--std-mir-policy', args.std_mir_policy, '--std-mir-key', std_keys[mode]]
                row = invoke('std-' + mode, [sys.executable, ROOT / 'scripts/std_mir.py',
                    '--compiler-key', compiler.key, '--stable-cgu-partitioning', mode, *std_selection])
                require(row['returncode'] == 0, 'custom std setup failed')
                result = json.loads(row['stdout'])
                std = {field: result[field] for field in ['key', 'sysroot', 'target']}
                ready_path = ROOT / '.work/std-mir' / std['key'] / 'ready.json'
                ready = json.loads(ready_path.read_text())
                identity = ready['identity']
                if args.std_mir_policy != 'v1':
                    from std_mir_source_paths import load as load_std_v2
                    loaded = load_std_v2(ROOT, std_keys[mode], compiler, 'stable-cgu:' + mode, rehash=True)
                    require(std == dict(key=loaded[2], sysroot=str(loaded[0]), target=loaded[1]),
                            'std v2 selected key differs')
                    stds[mode], prepared[mode] = std, ready_path
                    continue
                require(ready['owner'] == str(ROOT) and identity['compiler_key'] == compiler.key
                        and identity['namespace'] == 'stable-cgu:' + mode
                        and identity['source_sha256'] == compiler.identity['source_sha256']
                        and identity['flags'] == FLAGS and identity['policy'] == POLICY
                        and identity['compiler'] == compiler.identity['compiler'], 'std provenance differs')
                require(std == dict(key=hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest(),
                    sysroot=str(ready_path.parent / 'sysroot'), target=compiler.host), 'std identity differs')
                for name, proof in ready['artifacts'].items():
                    path = ready_path.parent / name
                    require(stamp(path) == proof['stamp'] and file_digest(path) == proof['sha256'],
                            'std artifact differs')
                stds[mode] = std
                prepared[mode] = ready_path
            require(stds['off']['key'] != stds['on']['key'], 'std policies share a namespace')
            source = work / 'fixture'
            fixture(source)
            if args.diagnostic_comparison == 'verified-std-source':
                standard_sources = VerifiedStandardSources(compiler,
                    public_rustc.parent.parent / 'lib/rustlib/src/rust/library', prepared)
                write_json(work / 'standard-source-comparison.json', standard_sources.evidence())
            row = invoke('lockfile', ['cargo', '+' + TOOLCHAIN, 'generate-lockfile',
                '--offline', '--manifest-path', source / 'Cargo.toml'], source)
            require(row['returncode'] == 0, 'local fixture lockfile failed')
            shared, guest = source / 'shared/src/lib.rs', source / 'src/lib.rs'
            original_shared, original_guest = shared.read_bytes(), guest.read_bytes()
            caches = work / 'caches'
            caches.mkdir()
            workspaces, artifacts, diagnostics = {}, {}, {}

            def comparison(row, core, messages):
                if standard_sources is None:
                    return core
                result = core_diagnostics(standard_sources.comparison(
                    messages, row['label'], [source, *workspaces.values()]), ROOT)
                row['source_derived_diagnostics'] = result
                write_json(work / 'standard-source-comparison.json', standard_sources.evidence())
                return result

            def public(label, value=None, code=None):
                require(file_digest(public_rustc) == public_identity['sha256'], 'public rustc changed')
                before = diagnostic_files(work / 'public-target') if code else {}
                row = invoke(label + '-public', public_command(source, compiler.host,
                    work / 'public-target'), source,
                    dict(env, RUSTC=str(public_rustc), RUSTC_WRAPPER='', RUSTC_WORKSPACE_WRAPPER=''))
                output = '\n'.join(line for line in row['stdout'].splitlines() if not line.startswith('{'))
                messages = diagnostic_records(row['stdout'])
                core = core_diagnostics(messages, ROOT)
                if code:
                    require(row['returncode'] != 0 and output == ''
                            and any(d['code'] == code and d['level'] == 'error' for d in core),
                            'ordinary public compiler did not reject the expected uncalled error')
                    # Cargo's JSON stream omits compiler abort summaries. Use
                    # the same unfiltered fingerprint records as custom modes.
                    row['cargo_diagnostics'] = core
                    messages, files = changed_diagnostics(work / 'public-target', before)
                    core = core_diagnostics(messages, ROOT)
                    require(any(d['code'] == code and d['level'] == 'error' for d in core),
                            'retained public diagnostics lack the expected error')
                    row['diagnostic_outputs'] = files
                    row['diagnostics'] = core
                    diagnostics[label, 'public'] = comparison(row, core, messages)
                else:
                    require(row['returncode'] == 0 and output == str(3 * (value + 55)),
                            'ordinary native execution produced a wrong result')
                row.update(validated=True, diagnostics=core,
                           source_sha256={'shared': file_digest(shared), 'guest': file_digest(guest)})
                write_json(work / 'commands.json', rows)

            def launch(label, mode, value=None, code=None):
                sources = {'shared': file_digest(shared), 'guest': file_digest(guest)}
                before = diagnostic_files(workspaces[mode] / 'target') if code else {}
                std_selection = [] if args.std_mir_policy == 'v1' else [
                    '--std-mir-policy', args.std_mir_policy, '--std-mir-key', std_keys[mode]]
                row = invoke(label + '-' + mode, [sys.executable, ROOT / 'scripts/interpreter.py',
                    '--manifest-path', source / 'Cargo.toml', '--package', 'custom-compiler-fixture',
                    '--entry', 'entry', '--compiler-key', compiler.key, '--tool-key', key,
                    '--stable-cgu-partitioning', mode, '--std-mir', '--toolchain-lookup', 'cached',
                    '--workspace-cache-root', caches, '--cache-namespace', args.run_id,
                    '--jobs', '2', '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                    '--function-cache', 'auto', '--inline-leaves', '--trap-unsupported-calls',
                    '--run-try-callbacks', '--instruction-limit', '100000000', '--allocation-limit', '150000',
                    *std_selection], source)
                row['source_sha256'] = sources
                require(sources == {'shared': file_digest(shared), 'guest': file_digest(guest)},
                        'source changed during a launcher command')
                if code:
                    validate_failure(row, code)
                    messages, files = changed_diagnostics(workspaces[mode] / 'target', before)
                    core = core_diagnostics(messages, ROOT)
                    require(any(d['code'] == code and d['level'] == 'error' for d in core),
                            'retained compiler diagnostics lack the expected error')
                    row.update(diagnostics=core, diagnostic_outputs=files)
                    compared = comparison(row, core, messages)
                    diagnostics[label, mode] = compared
                    require(compared == diagnostics[label, 'public'], 'structured public/custom diagnostics differ')
                else:
                    report, artifact = validate_launch(row, compiler, mode, key, stds[mode], caches)
                    require(row['stdout'] == str(3 * (value + 55)) + '\n', 'host/guest computed a stale or wrong value')
                    workspace = Path(report['workspace_path'])
                    require(workspaces.get(mode, workspace) == workspace, 'policy workspace changed')
                    workspaces[mode] = workspace
                    require(len(set(workspaces.values())) == len(workspaces), 'policies share a Cargo workspace')
                    generated = list((workspace / 'target').rglob('host-value.txt'))
                    require(len(generated) == 1 and generated[0].read_text() == str(value + 55),
                            'build-script dependency did not follow the source edit')
                    snapshot = work / (label + '-' + mode + '.rbc')
                    snapshot.write_bytes(artifact.read_bytes())
                    row.update(launch=report, artifact=str(snapshot), artifact_sha256=file_digest(snapshot))
                    artifacts[label, mode] = snapshot.read_bytes()
                    if label == 'original':
                        routes = compiler_routes(row['stderr'], tools / 'rust-interp-rustc-wrapper', compiler.rustc)
                        validate_routes(routes, compiler.host)
                        row['cargo_routes'] = routes
                row['validated'] = True
                write_json(work / 'commands.json', rows)

            with SourceEdit(shared, original_shared) as shared_edit, SourceEdit(guest, original_guest) as guest_edit:
                public('original', 3)
                for mode in MODES:
                    launch('original', mode, 3)
                shared_edit.replace(shared_source(7))
                public('edited', 7)
                for mode in MODES:
                    launch('edited', mode, 7)
                for location, edit, original in [('host', shared_edit, original_shared),
                                                   ('guest', guest_edit, original_guest)]:
                    shared_edit.replace(original_shared)
                    guest_edit.replace(original_guest)
                    for label, (body, code) in ERRORS.items():
                        edit.replace(original + body.encode() + b'\n')
                        public(location + '-' + label, code=code)
                        for mode in MODES:
                            launch(location + '-' + label, mode, code=code)
                shared_edit.replace(original_shared)
                guest_edit.replace(original_guest)
                public('restored', 3)
                for mode in MODES:
                    launch('restored', mode, 3)
            require(shared.read_bytes() == original_shared and guest.read_bytes() == original_guest,
                    'fixture restoration failed')
            for label in ['original', 'edited', 'restored']:
                require(artifacts[label, 'off'] == artifacts[label, 'on'], 'off/on bytecode differs: ' + label)
            for mode in MODES:
                require(artifacts['original', mode] == artifacts['restored', mode]
                        and artifacts['original', mode] != artifacts['edited', mode],
                        'edit/restoration artifact control failed')
            require(cargo_identity() == composition['cargo'], 'Cargo changed during qualification')
            installed_tools(key)
            if standard_sources is not None:
                standard_sources.recheck()
                write_json(work / 'standard-source-comparison.json', standard_sources.evidence())
            result = dict(status='passed', kind='real-custom-compiler-integration', benchmark=False,
                compiler_key=compiler.key, tool_key=key, std_mir=stds, commands=len(rows),
                std_mir_policy=args.std_mir_policy,
                launcher_commands=22, public_commands=11, expected_rejections=24, source_restored=True,
                public_reference=public_identity, semantic_controls='passed',
                **qualification_scope(args.diagnostic_comparison, standard_sources.gaps if standard_sources else []))
            write_json(work / 'result.json', result)
            print(json.dumps(result))
    except BaseException as error:
        # Preserve raw records even when a comparison or source proof fails
        # after the child receipt was initially written.
        write_json(work / 'commands.json', rows)
        if standard_sources is not None:
            write_json(work / 'standard-source-comparison.json', standard_sources.evidence())
        write_json(work / 'result.json', dict(status='failed', error=str(error), completed_commands=len(rows),
            kind='real-custom-compiler-integration', benchmark=False, semantic_controls='not-qualified',
            **qualification_scope(args.diagnostic_comparison, standard_sources.gaps if standard_sources else [])))
        raise


if __name__ == '__main__':
    main()
