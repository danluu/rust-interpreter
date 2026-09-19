"""Explicit uname identity policy; nodename is retained only as context.

Compiler/provider/source/configuration checks belong to the admission controller
and remain mandatory. This policy does not claim every application is independent
of its hostname; each admitted workload must separately justify that scope.
"""
FIELDS = ('sysname', 'nodename', 'release', 'version', 'machine')
IDENTITY_FIELDS = ('sysname', 'release', 'version', 'machine')
POLICY = 'uname-kernel-and-machine-v1'


def observation(value):
    if type(value) not in (list, tuple) or len(value) != len(FIELDS):
        raise ValueError('complete uname observation required')
    if not all(type(item) is str and 0 < len(item) <= 4096
               and all(ord(c) >= 32 and ord(c) != 127 for c in item) for item in value):
        raise ValueError('invalid uname observation field')
    return dict(zip(FIELDS, value))


def identity(value):
    fields = observation(value)
    return dict(policy=POLICY, **{key: fields[key] for key in IDENTITY_FIELDS})


def validate(value, expected):
    current = identity(value)
    if type(expected) is not dict or current != expected:
        raise ValueError('runtime admission kernel or machine identity changed')
    return observation(value)
