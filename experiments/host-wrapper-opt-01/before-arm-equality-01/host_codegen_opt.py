"""Fixed host O3 policy, authenticated through existing native runtime roles.

No compiler/process calls: publication supplies retained query output and
ordinary launches inspect the resulting immutable capability association.
"""
import argparse
import copy
import json
from pathlib import Path

POLICY = 'host-codegen-opt-v1'
ENVIRONMENT = 'RUST_INTERP_HOST_CODEGEN_OPT'
WRAPPER = 'rust-interp-rustc-wrapper'
CAPABILITY = dict(schema_version=1, policy=POLICY, roles=['proc-macro', 'lib', 'rlib'],
                  opt_level=3, mir_opt_level=1, lto='off', preserve_checks=True)
MODES = ('baseline', 'candidate')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def exact(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def validate_selection(args, environment):
    if args.host_codegen_opt == 'off':
        return
    require(args.host_codegen_opt == 'on', 'unknown combined host codegen mode')
    require(args.runtime_compiler_key is not None and args.tool_key is not None
            and args.compiler_key is None and args.cargo_key is None and args.std_mir
            and args.std_mir_policy in ('source-paths-v2', 'source-paths-v2-shared')
            and args.std_mir_key is not None and args.stable_cgu_partitioning == 'off'
            and args.stable_mono_cgu_partitioning is None and args.frontend_workers is None
            and args.host_proc_macro_opt == args.host_library_opt == args.borrowck_cache == 'off',
            'combined host codegen requires a prepared, installed runtime and other compiler policies off')
    for name in ('RUSTC', 'CARGO_BUILD_RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                 'RUST_INTERP_COMPILER_RUSTC', 'RUST_INTERP_FRONTEND_WORKERS'):
        require(not environment.get(name), 'combined host codegen conflicts with '+name)
    for name in (ENVIRONMENT, 'RUST_INTERP_HOST_PROC_MACRO_OPT', 'RUST_INTERP_HOST_LIBRARY_OPT',
                 'RUST_INTERP_BORROWCK_CACHE', 'RUST_INTERP_STABLE_CGU_PARTITIONING',
                 'RUST_INTERP_STABLE_MONO_CGU_PARTITIONING'):
        require(environment.get(name, 'off') == 'off', 'combined host codegen conflicts with '+name)


def _association(binaries, capabilities):
    require(POLICY in capabilities.get('export_options', [])
            and exact(capabilities.get('host_codegen_opt'), CAPABILITY),
            'missing exact combined host codegen capability')
    digest = binaries.get(WRAPPER)
    require(type(digest) is str and len(digest) == 64 and all(c in '0123456789abcdef' for c in digest),
            'missing physical wrapper digest')
    sysroot = capabilities.get('compiler_sysroot')
    require(type(sysroot) is str and Path(sysroot).is_absolute(), 'missing compiled runtime sysroot')
    return dict(sha256=digest, capability=copy.deepcopy(CAPABILITY),
                compiler_sysroot=sysroot, compiler_roles=copy.deepcopy(capabilities['compiler_roles']))


def bind_recorded_wrapper_capability(binaries, capabilities, compiler, stdout):
    from runtime_tools import runtime_binding
    runtime_binding(compiler, capabilities['compiler_roles'])
    expected = _association(binaries, capabilities)
    require(expected['compiler_sysroot'] == str(compiler.sysroot)
            and 'host_codegen_wrapper' not in capabilities, 'wrong runtime or duplicate capability binding')
    lines = (stdout.decode('utf-8') if isinstance(stdout, bytes) else stdout).splitlines()
    require(len(lines) == 3 and exact(json.loads(lines[0]), CAPABILITY)
            and lines[1] == expected['compiler_sysroot']
            and exact(json.loads(lines[2]), expected['compiler_roles']),
            'exporter and wrapper combined policy/runtime association differs')
    capabilities['host_codegen_wrapper'] = expected


def require_capability(directory, key, compiler, capabilities, binaries):
    from runtime_tools import validate_tool_runtime
    validate_tool_runtime(directory, key, compiler)
    expected = _association(binaries, capabilities)
    require(expected['compiler_sysroot'] == str(compiler.sysroot)
            and exact(capabilities.get('host_codegen_wrapper'), expected),
            'installed tools lack the matching combined host codegen wrapper')
    return receipt(capabilities)


def receipt(capabilities):
    return dict(mode='on', policy=POLICY, capability=copy.deepcopy(CAPABILITY),
                wrapper=copy.deepcopy(capabilities['host_codegen_wrapper']),
                cargo_profiles='unchanged', build_script_environment='unchanged',
                std_preparation='unchanged')


def namespace(identity, mode):
    require(mode in ('off', 'on'), 'unknown combined host codegen mode')
    return identity if mode == 'off' else POLICY+'\0on\0'+identity


def arguments(mode):
    require(mode in ('off', 'on'), 'unknown combined host codegen mode')
    return [] if mode == 'off' else ['--host-codegen-opt', 'on']


class UniqueMode(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest, None) is not None:
            parser.error('duplicate '+option_string)
        setattr(namespace, self.dest, values)


def add_arguments(parser):
    for mode in MODES:
        parser.add_argument('--'+mode+'-host-codegen-opt', choices=['off', 'on'], action=UniqueMode)


def select(args):
    modes = {m: getattr(args, m+'_host_codegen_opt') for m in MODES}
    if all(v is None for v in modes.values()):
        return None
    require(all(v in ('off', 'on') for v in modes.values()), 'declare both host codegen arm modes')
    require(args.batch and args.std_mir and args.baseline_tool_key is not None
            and args.baseline_tool_key == args.candidate_tool_key and args.build_tool_opt_level is None,
            'host codegen comparison requires one installed toolset, std, batching and unchanged Cargo profiles')
    if args.runtime_compiler_key is not None:
        require(args.std_mir_key is not None, 'host codegen comparison requires prepared std')
    else:
        require(args.baseline_runtime_compiler_key is not None
                and args.baseline_runtime_compiler_key == args.candidate_runtime_compiler_key
                and args.baseline_std_mir_key is not None
                and args.baseline_std_mir_key == args.candidate_std_mir_key,
                'host codegen comparison requires identical runtime and std selections')
    require(not args.aa_control or modes['baseline'] == modes['candidate'],
            'A/A requires identical host codegen modes')
    require(args.expect_identical_bytecode or args.aa_control, 'host codegen comparison requires RBC equality')
    return dict(policy=POLICY, modes=modes)


def bind_comparison(selection, tools, compilers):
    if selection is None:
        return None
    records = []
    for mode in MODES:
        directory, key = tools[mode]['directory'], tools[mode]['tool_key']
        records.append(require_capability(directory, key, compilers[mode],
            json.loads((directory/'capabilities.json').read_bytes()),
            json.loads((directory/'ready.json').read_bytes())))
    require(exact(records[0], records[1]), 'host codegen arms name different qualified wrappers')
    return dict(selection, receipt=records[0])


def validate_report(report):
    selection = report.get('host_codegen')
    if selection is None:
        return None
    require(type(selection) is dict and set(selection) == {'policy', 'modes', 'receipt'}
            and selection['policy'] == POLICY and type(selection['modes']) is dict
            and set(selection['modes']) == set(MODES)
            and all(v in ('off', 'on') for v in selection['modes'].values()), 'invalid host codegen selection')
    require(report['batch'] and report['comparison']['identical_bytecode_required']
            and report['tool_builds']['baseline']['tool_key'] == report['tool_builds']['candidate']['tool_key'],
            'host codegen comparison changed tools or waived RBC equality')
    require(not report.get('aa_control') or selection['modes']['baseline'] == selection['modes']['candidate'],
            'A/A host codegen modes differ')
    if report.get('runtime_arms') is not None:
        require(exact(report['runtime_arms']['arms']['baseline'], report['runtime_arms']['arms']['candidate']),
                'host codegen runtime/std/tool associations differ')
        runtime = report['runtime_arms']['arms']['baseline']['runtime']
    else:
        require(report.get('runtime_compiler', {}).get('prepared_std') is not None,
                'host codegen comparison lacks prepared runtime/std')
        runtime = report['runtime_compiler']
    expected = selection['receipt']
    require(type(expected) is dict and expected.get('mode') == 'on' and expected.get('policy') == POLICY
            and exact(expected.get('capability'), CAPABILITY), 'missing bound combined policy receipt')
    wrapper = expected['wrapper']
    require(exact(wrapper.get('capability'), CAPABILITY)
            and exact(wrapper['compiler_roles']['runtime'], dict(
                executable=dict(path=runtime['rustc'], sha256=runtime['rustc_sha256']),
                verbose_version=runtime['compiler'], default_sysroot=wrapper['compiler_sysroot']))
            and str(Path(runtime['rustc']).parent.parent) == wrapper['compiler_sysroot'],
            'combined host codegen receipt runtime differs')
    return selection


def verify_call(selection, mode, call):
    expected = 'off' if selection is None else selection['modes'][mode]
    args = call['command']
    indices = [i for i, x in enumerate(args) if x == '--host-codegen-opt' or x.startswith('--host-codegen-opt=')]
    require((not indices) if expected == 'off' else
            (len(indices) == 1 and args[indices[0]:indices[0]+2] == ['--host-codegen-opt', 'on']),
            'recorded combined host codegen argument differs')
    observed = call['launch'].get('host_codegen_opt')
    if expected == 'off':
        require(observed is None, 'off arm has an active host codegen receipt')
    else:
        require(exact(observed, selection['receipt']), 'combined host codegen receipt differs from bound selection')
        require(type(observed) is dict and observed.get('mode') == 'on' and observed.get('policy') == POLICY
                and exact(observed.get('capability'), CAPABILITY)
                and observed.get('cargo_profiles') == observed.get('build_script_environment') == 'unchanged'
                and observed.get('std_preparation') == 'unchanged', 'wrong combined host codegen receipt')
        wrapper = observed.get('wrapper', {})
        require(exact(wrapper.get('capability'), CAPABILITY)
                and wrapper.get('sha256') == call['launch']['compiler_wrapper']['sha256']
                and call['launch']['compiler_wrapper']['name'] == WRAPPER,
                'combined host codegen receipt names another physical wrapper')
