"""Typed host-library screen admission; no compiler or fixture execution."""
import hashlib
from pathlib import Path

from custom_compiler import require
from host_library_opt import POLICY, require_capability
from qualified_public_tools import HOST_LIBRARY_BUILD_POLICY as BUILD_POLICY, validate_public_tool

MODES = dict(baseline='off', candidate='on', duplicate='off')
CAMPAIGN_LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
SCREEN_FILES = ('benchmarks/experiments/strict-warm-build/screen.py',
    'benchmarks/experiments/strict-warm-build/assess_owned_screen.py',
    'benchmarks/experiments/strict-warm-build/analyzer.py',
    'benchmarks/experiments/strict-warm-build/assess.py',
    'benchmarks/experiments/strict-warm-build/PROTOCOL.md',
    'benchmarks/experiments/strict-warm-build/HOST_LIBRARY_SCREEN.md')


def public_build(tool, key, read_bytes):
    public = validate_public_tool(tool, key, read_bytes, qualification_policy=BUILD_POLICY)
    require(public['qualification_scope'] == 'host-library-real-histories',
            'host-library tools lack the actual three-history qualification')
    require_capability(tool, public['capability'], public['composition']['binaries'])
    return public


def standard_binding(public, std):
    compiler = public['composition']['public_compiler']
    shared = public['correctness']['shared_std']
    require(std['rustc'] == compiler['rustc_path'] and std['rustc_sha256'] == compiler['rustc_sha256']
            and std['target'] == compiler['target'] and std['compiler'] == shared['identity']['compiler']
            and std['key'] == shared['key'] and std['sha256'] == shared['ready_sha256']
            and std['sysroot'] == shared['sysroot'], 'host-library screen compiler/std differs from qualification')


def runtime_harness(public, owner, read_bytes):
    """Bind launcher/routing/assessment source to the qualified publication."""
    expected = {name: digest for name, digest in public['plan']['harness'].items()
                if name.startswith('scripts/') or name in SCREEN_FILES}
    require(set(SCREEN_FILES) <= expected.keys() and 'scripts/host_library_screen.py' in expected,
            'host-library screen harness was not included in qualification')
    for name, digest in expected.items():
        require(hashlib.sha256(read_bytes(Path(owner) / name)).hexdigest() == digest,
                'host-library screen harness differs from qualification: ' + name)
    return expected


def amendment(owner):
    return dict(path=str(Path(owner) / SCREEN_FILES[-1]), capability=POLICY,
        optimized_role='unselected linked native Cargo lib/rlib units',
        original_opt_level='0 (no explicit optimization flag)', opt_level=1, mir_opt_level=1,
        lto='off', preserve_effective_debug_assertions=True, preserve_effective_overflow_checks=True,
        preserve_effective_ub_checks=True, application_profiles_changed=False,
        build_script_environment_policy='unchanged', cargo_jobs_policy='unchanged',
        backend_jobs_policy='unchanged', linker_jobs_policy='unchanged',
        std_preparation_policy='unchanged and outside application wrapper')


def validate_launch_policy(launch, mode, capability):
    from host_library_opt import receipt
    require(mode in MODES, 'invalid host-library screen arm')
    if MODES[mode] == 'on':
        require(launch.get('host_library_opt') == receipt(capability), 'host-library launch capability/policy differs')
    else:
        require('host_library_opt' not in launch, 'off arm unexpectedly enables host-library policy')
    require(launch.get('host_proc_macro_opt', 'off') == 'off'
            and launch.get('query_cache_retention', 'off') == 'off'
            and launch.get('borrowck_cache', 'off') == 'off'
            and not any(name in launch for name in ['custom_compiler', 'custom_cargo', 'frontend_workers'])
            and launch.get('compiler_argv_record_dir') is None,
            'host-library launch mixes another policy or qualification instrumentation')
