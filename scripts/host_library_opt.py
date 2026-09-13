"""Explicit O1 native host-library policy; publication probes stay outside launches."""
import json
from pathlib import Path
import subprocess

POLICY = 'host-library-opt-v1'
WRAPPER = 'rust-interp-rustc-wrapper'
COMPILER_COMMIT = 'cea272fa356e94bd2ee2cadf376630aa0683867a'
CAPABILITY = dict(schema_version=1, policy=POLICY, compiler_commit=COMPILER_COMMIT,
                  opt_level=1, mir_opt_level=1, lto='off', preserve_checks=True)


def validate_selection(args, environment):
    if args.host_library_opt == 'off':
        return
    if (not args.std_mir or args.compiler_key is not None or args.cargo_key is not None
            or args.stable_cgu_partitioning != 'off'
            or args.stable_mono_cgu_partitioning is not None
            or args.frontend_workers is not None or args.host_proc_macro_opt != 'off'
            or args.borrowck_cache != 'off'):
        raise ValueError('--host-library-opt=on requires --std-mir, public compiler/stock Cargo and other compiler policies off')
    for name in ('RUSTC', 'CARGO_BUILD_RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                 'RUST_INTERP_COMPILER_RUSTC', 'RUST_INTERP_FRONTEND_WORKERS'):
        if environment.get(name):
            raise ValueError('host library optimization conflicts with ' + name)
    for name in ('RUST_INTERP_STABLE_CGU_PARTITIONING', 'RUST_INTERP_STABLE_MONO_CGU_PARTITIONING',
                 'RUST_INTERP_HOST_PROC_MACRO_OPT', 'RUST_INTERP_BORROWCK_CACHE'):
        if environment.get(name, 'off') != 'off':
            raise ValueError('host library optimization conflicts with ' + name)
    # Optimization/default-check grammar lives only in the shared Rust parser.
    # Cargo-configured flags are checked there on each actual host invocation.


def bind_wrapper_capability(directory, manifest, capabilities):
    """The existing tool publisher may call this for newly capable binaries."""
    if POLICY not in capabilities.get('export_options', []):
        return
    probe = subprocess.run([str(directory / WRAPPER), '--rust-interp-host-library-capability'],
                           capture_output=True, text=True, timeout=10, check=True)
    bind_recorded_wrapper_capability(manifest, capabilities, probe.stdout)


def bind_recorded_wrapper_capability(manifest, capabilities, stdout):
    """Bind an already captured probe; shared publication never reprobes tools."""
    lines = (stdout.decode('utf-8') if isinstance(stdout, bytes) else stdout).splitlines()
    if (len(lines) != 2 or capabilities.get('host_library_opt') != CAPABILITY
            or json.loads(lines[0]) != CAPABILITY or 'host_library_wrapper' in capabilities
            or lines[1] != capabilities.get('compiler_sysroot')):
        raise RuntimeError('host library exporter/wrapper capability or compiled sysroot differs')
    capabilities['host_library_wrapper'] = dict(sha256=manifest[WRAPPER],
        capability=json.loads(lines[0]), compiler_sysroot=lines[1])


def require_capability(directory, capabilities, manifest):
    sysroot = capabilities.get('compiler_sysroot')
    expected = dict(sha256=manifest.get(WRAPPER), capability=CAPABILITY, compiler_sysroot=sysroot)
    if (not isinstance(sysroot, str) or not Path(sysroot).is_absolute()
            or WRAPPER not in manifest or capabilities.get('host_library_opt') != CAPABILITY
            or capabilities.get('host_library_wrapper') != expected):
        raise RuntimeError('installed tools lack matching pinned host library exporter/wrapper capability: ' + str(directory))


def namespace(identity):
    return POLICY + '\0on\0' + identity


def receipt(capabilities):
    return dict(policy=POLICY, mode='on', compiler_commit=COMPILER_COMMIT,
        wrapper=capabilities['host_library_wrapper'],
        scope='unselected linked native Cargo lib/rlib units',
        opt_level=1, mir_opt_level=1, lto='off', preserve_checks=True,
        std_preparation_policy='unchanged', cargo_profiles_policy='unchanged',
        build_script_environment_policy='unchanged', cargo_jobs_policy='unchanged',
        backend_jobs_policy='unchanged', linker_jobs_policy='unchanged')
