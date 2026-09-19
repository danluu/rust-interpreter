"""Pure explicit launcher environment derivation; no process or ambient reads.

The workload mapping remains unchanged. The only platform addition admitted
from actual preparation observations is the bounded Darwin CF context already
accepted by the qualified hash stage. Every raw string survives unchanged.
"""
import json
import re

POLICY = 'explicit-startup-launch-environment-v1'
CF = '__CF_USER_TEXT_ENCODING'
OBSERVATIONS = ('before_factory_definitions', 'after_factory_definitions', 'before_packet')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False)+'\n').encode()


def mapping(value):
    require(type(value) is dict and all(type(k) is str and k and '=' not in k
        and '\0' not in k and type(v) is str and '\0' not in v for k,v in value.items()),
        'exact string environment mapping required')
    return dict(value)


def decode(value):
    def unique(pairs):
        result = {}
        for key, item in pairs:
            require(key not in result, 'duplicate environment key')
            result[key] = item
        return result
    return mapping(json.loads(value, object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value))))


def context(value, *, platform, uid):
    require(platform == 'darwin', 'CF startup context requires Darwin')
    parts = value.split(':')
    require(len(parts) == 3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})', p)
        for p in parts), 'bounded CF triple required')
    require(int(parts[0], 16 if parts[0].lower().startswith('0x') else 10) == uid,
            'CF context does not belong to actual UID')


def derive(workload, passed, observations, *, platform, uid):
    workload, passed = mapping(workload), mapping(passed)
    require(type(platform) is str and platform and type(uid) is int and uid >= 0,
            'actual platform and integer UID required')
    require(type(observations) is dict and set(observations) == set(OBSERVATIONS),
            'complete preparation observations required')
    observed = {name: mapping(observations[name]) for name in OBSERVATIONS}
    first = observed[OBSERVATIONS[0]]
    require(all(value == first for value in observed.values()), 'preparation environment changed')
    require(all(first.get(k) == v for k,v in passed.items()), 'passed preparation environment changed')
    require(set(first)-set(passed) <= ({CF} if platform == 'darwin' else set()),
            'unadmitted startup environment addition')
    if CF in first:
        context(first[CF], platform=platform, uid=uid)
    launch = dict(workload)
    if CF in launch:
        context(launch[CF], platform=platform, uid=uid)
        require(first.get(CF) == launch[CF], 'workload CF conflicts with actual preparation')
    if CF in first:
        launch[CF] = first[CF]
    return dict(policy=POLICY, platform=platform, uid=uid, passed=passed,
                observations=observed, launch_environment=launch)


def validate(workload, proof):
    require(type(proof) is dict and set(proof) == {'policy', 'platform', 'uid', 'passed',
        'observations', 'launch_environment'}, 'exact startup derivation schema required')
    rebuilt = derive(workload, proof['passed'], proof['observations'],
                     platform=proof['platform'], uid=proof['uid'])
    require(encoded(rebuilt) == encoded(proof), 'startup derivation differs')
    return dict(rebuilt['launch_environment'])
