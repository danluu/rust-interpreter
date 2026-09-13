"""Explicit custom-compiler per-item policy; legacy omission stays unchanged."""
import json
import subprocess

POLICY = 'stable-mono-cgu-routing-v1'
OPTION = 'stable-mono-cgu-partitioning'
WRAPPER = 'rust-interp-rustc-wrapper'


def validate_selection(args, environment):
    mode = args.stable_mono_cgu_partitioning
    if mode is None:
        return
    if (args.compiler_key is None or args.stable_cgu_partitioning != 'off'
            or getattr(args, 'cargo_key', None) is not None
            or getattr(args, 'frontend_workers', None) is not None
            or getattr(args, 'host_proc_macro_opt', 'off') != 'off'
            or getattr(args, 'host_library_opt', 'off') != 'off'
            or getattr(args, 'borrowck_cache', 'off') != 'off'):
        raise ValueError('stable-MonoItem policy requires a custom compiler with module, Cargo, worker, macro and borrowck policies off')
    for name in ('RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUST_INTERP_FRONTEND_WORKERS'):
        if environment.get(name):
            raise ValueError('stable-MonoItem policy conflicts with ' + name)
    for name in ('RUST_INTERP_STABLE_CGU_PARTITIONING', 'RUST_INTERP_HOST_PROC_MACRO_OPT',
                 'RUST_INTERP_HOST_LIBRARY_OPT',
                 'RUST_INTERP_BORROWCK_CACHE'):
        if environment.get(name, 'off') != 'off':
            raise ValueError('stable-MonoItem policy conflicts with ' + name)
    # Cargo configuration flags are checked again by the shared compiler router.
    # These environment checks reject visible conflicts before any std setup.
    for name, value in environment.items():
        if name == 'CARGO_ENCODED_RUSTFLAGS':
            arguments = value.split('\x1f')
        elif name.endswith('RUSTFLAGS'):
            arguments = value.split()
        else:
            continue
        for index, argument in enumerate(arguments):
            unstable = ((arguments[index + 1] if index + 1 < len(arguments) else '')
                        if argument == '-Z' else argument[2:] if argument.startswith('-Z') else '')
            if (argument.startswith('@') or argument == '--jobs' or argument.startswith('--jobs=')
                    or argument.startswith('-j') or argument == '--jobs-frontend'
                    or argument.startswith('--jobs-frontend=')
                    or unstable.split('=', 1)[0].replace('_', '-') in (
                        'stable-cgu-partitioning', OPTION, 'threads', 'proc-macro-execution-strategy')):
                raise ValueError('stable-MonoItem policy conflicts with ' + name + ' flags or response files')


def namespace(mode):
    if mode not in ('off', 'on'):
        raise ValueError('stable-MonoItem policy must be off or on')
    return 'stable-mono-cgu:' + mode


def bind_wrapper_capability(directory, manifest, capabilities, compiler, environment):
    """Publication-only probe of the actual adjacent native wrapper."""
    if OPTION not in capabilities.get('export_options', []):
        return
    probe = subprocess.run([str(directory / WRAPPER), '--rust-interp-stable-mono-capability'],
                           env=environment, capture_output=True, text=True, timeout=10, check=True)
    if probe.stdout != POLICY + '\n' + str(compiler.sysroot) + '\n':
        raise RuntimeError('stable-MonoItem wrapper capability or compiled sysroot differs')
    capabilities['stable_mono_cgu_wrapper'] = dict(policy=POLICY,
        sha256=manifest[WRAPPER], compiler_sysroot=str(compiler.sysroot))


def require_tool_capability(directory, compiler):
    capabilities = json.loads((directory / 'capabilities.json').read_text())
    manifest = json.loads((directory / 'ready.json').read_text())
    expected = dict(policy=POLICY, sha256=manifest.get(WRAPPER),
                    compiler_sysroot=str(compiler.sysroot))
    if (WRAPPER not in manifest or capabilities.get('compiler_sysroot') != str(compiler.sysroot)
            or capabilities.get('stable_mono_cgu_wrapper') != expected):
        raise RuntimeError('installed tools lack matching stable-MonoItem exporter/wrapper capability')
    return expected


def receipt(mode, compiler, wrapper):
    return dict(policy=POLICY, mode=mode, namespace=namespace(mode),
                rustc_options=['-Zstable-cgu-partitioning=no',
                               '-Zstable-mono-cgu-partitioning=' + ('yes' if mode == 'on' else 'no')],
                compiler_option_help_sha256=compiler.identity['unstable_options']['sha256'],
                wrapper=wrapper, scope='Cargo host and guest compiler invocations',
                cargo_jobs_policy='unchanged', backend_jobs_policy='unchanged',
                std_preparation_flags_policy='unchanged')
