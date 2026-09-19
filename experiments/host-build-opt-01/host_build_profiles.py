"""Explicit host-only Cargo profile selection; pure data operations only."""
import argparse
import copy
from pathlib import Path

POLICY = 'workflow-host-build-opt-v1'
PROFILES = ('DEV', 'TEST')


def require(value, message):
    if not value:
        raise RuntimeError(message)


class UniqueLevel(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if getattr(namespace, self.dest, None) is not None:
            parser.error('duplicate host optimization option: ' + option_string)
        setattr(namespace, self.dest, value)


def add_arguments(parser):
    for mode in ('native', 'baseline', 'candidate'):
        parser.add_argument('--' + mode + '-build-tool-opt-level', type=int,
                            choices=range(4), action=UniqueLevel,
                            help='override the shared host build opt level for this mode only')


def validate(value, modes):
    require(type(value) is dict and set(value) == {'policy', 'modes'}
            and value['policy'] == POLICY, 'exact host profile policy required')
    require(type(value['modes']) is dict and set(value['modes']) == set(modes),
            'exact host profile modes required')
    for level in value['modes'].values():
        require(level is None or (type(level) is int and 0 <= level <= 3),
                'host opt level must be None or an integer in 0..3')
    require(any(v is not None for v in value['modes'].values()), 'empty explicit host profile')
    return copy.deepcopy(value)


def select(args):
    paired = args.baseline_tool_key is not None
    modes = ('native', 'baseline', 'candidate') if paired else ('native', 'interpreter', 'jit')
    explicit = {m: getattr(args, m + '_build_tool_opt_level', None)
                for m in ('native', 'baseline', 'candidate')}
    require(paired or not any(v is not None for v in explicit.values()),
            'per-mode host settings require a paired comparison')
    shared = args.build_tool_opt_level
    if shared is None and all(v is None for v in explicit.values()):
        return None
    return validate(dict(policy=POLICY, modes={m: explicit.get(m)
        if explicit.get(m) is not None else shared for m in modes}), modes)


def level(value, mode):
    return None if value is None else value['modes'][mode]


def expected_environment(value, mode):
    selected = level(value, mode)
    return {} if selected is None else {
        'CARGO_PROFILE_' + p + '_BUILD_OVERRIDE_OPT_LEVEL': str(selected)
        for p in PROFILES}


def environment(base, value, mode):
    """Only declared settings survive; target Cargo profiles are not overridden."""
    env = {k: v for k, v in base.items() if not k.startswith('CARGO_PROFILE_')}
    env.update(expected_environment(value, mode))
    return env


def receipt(env):
    return {k: v for k, v in env.items()
            if k.startswith('CARGO_PROFILE_') and '_BUILD_OVERRIDE_' in k}


def namespace(run_id, mode, value):
    original = run_id + ':' + mode
    if value is None:
        return original
    selected = level(value, mode)
    return original + ':host-build-opt=' + ('repository' if selected is None else str(selected))


def target(work, name, value):
    original = Path(work) / name
    if value is None:
        return original
    selected = level(value, 'native')
    return original / ('host-build-opt-' + ('repository' if selected is None else str(selected)))


def verify_call(call, value, mode):
    require(call.get('host_build_profile') == expected_environment(value, mode),
            'actual command host profile differs')


def verify_summary(report):
    value = report.get('host_build_profiles')
    if value is None:
        require('host_build_opt_level' not in report.get('native_control', {})
                and all('host_build_opt_level' not in r for r in report.get('tool_builds', {}).values()),
                'mode host setting lacks its summary policy')
        return None
    modes = ('native', 'baseline', 'candidate') if 'comparison' in report else ('native', 'interpreter', 'jit')
    value = validate(value, modes)
    for mode in modes:
        setting = report['native_control'] if mode == 'native' else report['tool_builds'][mode]
        require('host_build_opt_level' in setting
                and type(setting['host_build_opt_level']) is type(level(value, mode))
                and setting['host_build_opt_level'] == level(value, mode),
                'summary host profile differs from mode settings')
    if report.get('aa_control'):
        require(level(value, 'baseline') == level(value, 'candidate'),
                'A/A host profiles differ')
    return value
