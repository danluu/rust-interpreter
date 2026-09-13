"""Explicit frontend worker routing for the pinned stock compiler."""
import json
import subprocess

POLICY = 'frontend-workers-v1'
COMPILER_COMMIT = 'cea272fa356e94bd2ee2cadf376630aa0683867a'
CAPABILITY = dict(schema_version=1, policy=POLICY, counts=[1, 2], flag='-Zthreads',
                  compiler_commit=COMPILER_COMMIT)


def validate_selection(args, environment):
    if args.frontend_workers is None:
        return
    if (getattr(args, 'compiler_key', None) is not None
            or getattr(args, 'cargo_key', None) is not None
            or getattr(args, 'stable_cgu_partitioning', 'off') != 'off'
            or getattr(args, 'host_proc_macro_opt', 'off') != 'off'
            or args.borrowck_cache != 'off'):
        raise ValueError('frontend workers cannot be combined with compiler, Cargo, macro, or borrowck policies')
    for name in ('RUSTC', 'CARGO_BUILD_RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                 'RUST_INTERP_COMPILER_RUSTC'):
        if environment.get(name):
            raise ValueError('frontend workers conflict with '+name)
    for name in ('RUST_INTERP_STABLE_CGU_PARTITIONING', 'RUST_INTERP_HOST_PROC_MACRO_OPT'):
        if environment.get(name, 'off') != 'off':
            raise ValueError('frontend workers conflict with '+name)
    for name, value in environment.items():
        if name == 'CARGO_ENCODED_RUSTFLAGS':
            arguments = value.split('\x1f')
        elif name.endswith('RUSTFLAGS'):
            arguments = value.split()
        else:
            continue
        for index, argument in enumerate(arguments):
            zoption = (arguments[index+1] if index+1 < len(arguments) else '') if argument == '-Z' else argument[2:] if argument.startswith('-Z') else ''
            zname = zoption.split('=', 1)[0].replace('_', '-')
            if (argument.startswith('@') or argument == '--jobs' or argument.startswith('--jobs=')
                    or argument.startswith('-j') or argument == '--jobs-frontend'
                    or argument.startswith('--jobs-frontend=') or zname in (
                        'threads', 'stable-cgu-partitioning', 'stable-mono-cgu-partitioning',
                        'proc-macro-execution-strategy')):
                raise ValueError('frontend worker policy conflicts with '+name+' compiler flags or response files')


def bind_wrapper_capability(directory, manifest, capabilities):
    """Run only when publishing a toolset, outside launcher measurements."""
    if POLICY not in capabilities.get('export_options', []):
        return
    name = 'rust-interp-rustc-wrapper'
    probe = subprocess.run([str(directory/name), '--rust-interp-frontend-worker-capability'],
                           capture_output=True, text=True, timeout=10, check=True)
    wrapper = json.loads(probe.stdout)
    if wrapper != capabilities.get('frontend_workers'):
        raise RuntimeError('exporter and light wrapper frontend worker capabilities differ')
    capabilities['frontend_worker_wrapper'] = dict(sha256=manifest[name], capability=wrapper)


def require_capability(directory, capabilities, manifest):
    wrapper = capabilities.get('frontend_worker_wrapper', {})
    if (not isinstance(wrapper,dict) or capabilities.get('frontend_workers') != CAPABILITY
            or wrapper.get('capability') != CAPABILITY
            or 'rust-interp-rustc-wrapper' not in manifest
            or wrapper.get('sha256') != manifest['rust-interp-rustc-wrapper']):
        raise RuntimeError('installed tools lack matching pinned exporter/wrapper frontend worker capability: '+str(directory))


def namespace(count, identity):
    return POLICY+'\0'+str(count)+'\0'+identity


def receipt(count, capability):
    return dict(policy=POLICY, workers=count, compiler_arg='-Zthreads='+str(count),
                scope='Cargo host and guest compiler invocations',
                compiler_commit=COMPILER_COMMIT, wrapper=capability['frontend_worker_wrapper'],
                std_preparation_policy='unchanged', cargo_jobs_policy='unchanged',
                backend_jobs_policy='unchanged', linker_jobs_policy='unchanged')
