"""Pure explicit compiler-arm selection; callbacks own all provider validation.

There are no compiler imports, filesystem reads, ambient environment changes,
timers or workload calls here. The existing shared CLI is left to its original
implementation when no new arm argument is present.
"""
import argparse
import copy
import re

MODES = ('baseline', 'candidate')
POLICY = 'explicit-workflow-runtime-arms-v1'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def key(value):
    require(type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None,
            'runtime/std keys must be exact lowercase SHA256 strings')
    return value


class UniqueKey(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if getattr(namespace, self.dest, None) is not None:
            parser.error('duplicate explicit arm option: '+option_string)
        try:
            value = key(value)
        except RuntimeError as error:
            parser.error(str(error))
        setattr(namespace, self.dest, value)


def add_arguments(parser):
    for mode in MODES:
        parser.add_argument('--'+mode+'-runtime-compiler-key', action=UniqueKey,
                            help='explicit installed runtime for this custom arm; requires both arm keys')
        parser.add_argument('--'+mode+'-std-mir-key', action=UniqueKey,
                            help='prepared std for this arm runtime; requires both std keys and --std-mir')


def select(args):
    """Return None for the untouched legacy CLI, otherwise a detached selection."""
    runtimes = {m: getattr(args, m+'_runtime_compiler_key', None) for m in MODES}
    standards = {m: getattr(args, m+'_std_mir_key', None) for m in MODES}
    if all(v is None for v in [*runtimes.values(), *standards.values()]):
        return None
    require(args.runtime_compiler_key is None and args.std_mir_key is None,
            'shared and per-arm runtime/std declarations cannot be combined')
    require(all(v is not None for v in runtimes.values()), 'both explicit arm runtime keys are required')
    for value in runtimes.values():
        key(value)
    require(args.batch and args.baseline_tool_key is not None and args.candidate_tool_key is not None,
            'per-arm runtimes require a batched comparison with explicit toolsets')
    require(args.build_tool_opt_level is None, 'per-arm runtimes require repository host build profiles')
    require(type(args.std_mir) is bool, 'explicit standard-library selection required')
    require(all((v is not None) == args.std_mir for v in standards.values()),
            '--std-mir requires both explicit arm std keys; without it neither is allowed')
    for value in standards.values():
        if value is not None:
            key(value)
    if args.aa_control:
        require(runtimes['baseline'] == runtimes['candidate']
                and standards['baseline'] == standards['candidate'],
                'A/A requires identical runtime and standard-library selections')
    return dict(policy=POLICY, arms={m: dict(runtime_key=runtimes[m], std_key=standards[m]) for m in MODES})


def selection(value):
    require(type(value) is dict and set(value) == {'policy', 'arms'} and value['policy'] == POLICY,
            'exact per-arm selection schema required')
    require(type(value['arms']) is dict and set(value['arms']) == set(MODES), 'two exact custom arms required')
    for row in value['arms'].values():
        require(type(row) is dict and set(row) == {'runtime_key', 'std_key'}, 'exact arm key schema required')
        key(row['runtime_key'])
        if row['std_key'] is not None:
            key(row['std_key'])
    require((value['arms']['baseline']['std_key'] is None) == (value['arms']['candidate']['std_key'] is None),
            'both arms must use the same declared std policy')
    return copy.deepcopy(value)


def arguments(value, mode):
    value = selection(value)
    require(mode in MODES, 'native or unknown mode cannot use a custom runtime')
    row = value['arms'][mode]
    result = ['--runtime-compiler-key', row['runtime_key']]
    if row['std_key'] is not None:
        result += ['--std-mir-policy', 'source-paths-v2-shared', '--std-mir-key', row['std_key']]
    return result


def bind(value, tools, *, load_runtime, validate_tool, environment, runtime_receipt):
    """Validate each selected toolset with its actual runtime before any sample.

    Load/read callbacks are supplied by the ordinary runner. Sharing a runtime
    key may reuse the loaded immutable object, but never skips either tool check.
    """
    value = selection(value)
    require(type(tools) is dict and set(tools) == set(MODES), 'exact paired toolsets required')
    loaded, runtimes, proofs = {}, {}, {}
    for mode in MODES:
        expected = value['arms'][mode]['runtime_key']
        if expected not in loaded:
            compiler = load_runtime(expected)
            require(compiler.key == expected, 'loaded runtime key differs from explicit selection')
            compiler.environment(environment)
            loaded[expected] = compiler
        compiler = loaded[expected]
        validate_tool(tools[mode]['directory'], tools[mode]['tool_key'], compiler)
        proof = runtime_receipt(compiler)
        require(type(proof) is dict and proof.get('key') == expected
                and proof.get('policy') == 'owned-native-runtime-compiler-v1', 'actual runtime receipt differs')
        runtimes[mode], proofs[mode] = compiler, copy.deepcopy(proof)
    return runtimes, proofs


def receipts(value, proofs, standards, tools):
    value = selection(value)
    require(all(type(v) is dict and set(v) == set(MODES) for v in [proofs, standards, tools]),
            'complete proof/std/tool maps required')
    answer = {}
    for mode in MODES:
        row, runtime, standard = value['arms'][mode], proofs[mode], standards[mode]
        require(type(runtime) is dict and set(runtime) == {'key', 'policy', 'rustc', 'rustc_sha256', 'compiler'}
                and runtime['key'] == row['runtime_key'] and runtime['policy'] == 'owned-native-runtime-compiler-v1',
                'exact runtime proof must bind this arm')
        key(runtime['rustc_sha256'])
        require(type(runtime['rustc']) is str and runtime['rustc'].startswith('/')
                and type(runtime['compiler']) is str and runtime['compiler'].startswith('rustc '),
                'actual runtime route/compiler verbose version required')
        require((standard is None) == (row['std_key'] is None), 'prepared standard policy differs')
        if standard is not None:
            require(type(standard) is dict and set(standard) == {'key', 'sysroot', 'target'}
                    and standard['key'] == row['std_key'] and type(standard['sysroot']) is str
                    and standard['sysroot'].startswith('/') and type(standard['target']) is str
                    and standard['target'], 'prepared std selection differs from this arm')
        answer[mode] = dict(runtime=copy.deepcopy(runtime), prepared_std=copy.deepcopy(standard),
                            tool_key=key(tools[mode]['tool_key']))
    return dict(policy=POLICY, selection=value, arms=answer)


def validate_receipts(value, tools):
    require(type(value) is dict and set(value) == {'policy', 'selection', 'arms'} and value['policy'] == POLICY,
            'exact per-arm receipt envelope required')
    require(type(value['arms']) is dict and set(value['arms']) == set(MODES), 'two exact arm receipts required')
    for row in value['arms'].values():
        require(type(row) is dict and set(row) == {'runtime', 'prepared_std', 'tool_key'}, 'exact arm receipt required')
    require(type(tools) is dict and set(tools) == set(MODES), 'two actual tool records required')
    require(all(value['arms'][m]['tool_key'] == tools[m]['tool_key'] for m in MODES),
            'recorded toolset is associated with another arm')
    rebuilt = receipts(value['selection'], {m:value['arms'][m]['runtime'] for m in MODES},
                       {m:value['arms'][m]['prepared_std'] for m in MODES}, tools)
    require(rebuilt == value, 'per-arm receipt differs from its explicit selection')
    return copy.deepcopy(rebuilt)


def verify_call(value, mode, call, *, verify_runtime_call):
    require(mode in MODES, 'custom runtime proof cannot attach to native')
    row = value['arms'][mode]
    require(call['launch']['tool_key'] == row['tool_key'], 'executed tool belongs to another arm')
    verify_runtime_call(call, row['runtime'], row['prepared_std'])
