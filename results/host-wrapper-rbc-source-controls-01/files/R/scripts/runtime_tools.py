"""Associate separately built tools with their installed native runtime.

Publication records actual exporter and wrapper probes. Launches only inspect
the immutable records; the binaries independently check the bound runtime files
and loaded driver. Build-time private metadata is not an application sysroot.
"""
import json
from pathlib import Path

from custom_compiler import digest, read_json, require
from runtime_compiler import POLICY as RUNTIME_POLICY

POLICY = 'owned-native-runtime-tools-v1'
WRAPPER = 'rust-interp-rustc-wrapper'


def runtime_binding(compiler, binding):
    """Check the runtime half of the already qualified separate-role binding."""
    identity = compiler.identity
    require(identity['policy'] == RUNTIME_POLICY, 'separate tools require a native runtime installation')
    drivers = [name for name in identity['files'] if name.startswith('lib/librustc_driver-')
               and name.endswith(('.dylib', '.so')) and len(Path(name).parts) == 2]
    require(len(drivers) == 1, 'installed runtime driver is ambiguous')
    require(binding['schema_version'] == 1 and binding['policy'] == 'separate-compiler-roles-v1',
            'tools lack separate compiler roles')
    require(binding['runtime'] == dict(executable=dict(path=str(compiler.rustc),
                sha256=identity['files']['bin/rustc']), verbose_version=identity['compiler'],
                default_sysroot=str(compiler.sysroot))
            and binding['runtime_source_commit'] == identity['provenance']['source_commit']
            and binding['runtime_driver'] == dict(path=str(compiler.sysroot / drivers[0]),
                sha256=identity['files'][drivers[0]]),
            'tools name a different runtime compiler or driver')


def bind_recorded_wrapper(capabilities, binaries, compiler, stdout):
    """Bind a captured wrapper probe without starting a new process."""
    binding = capabilities['compiler_roles']
    runtime_binding(compiler, binding)
    require(capabilities['compiler_sysroot'] == str(compiler.sysroot)
            and json.loads(stdout) == binding and 'runtime_wrapper' not in capabilities,
            'exporter and wrapper compiler roles differ')
    capabilities['runtime_wrapper'] = dict(sha256=binaries[WRAPPER], compiler_roles=binding)


def validate_tool_runtime(directory, key, compiler):
    try:
        composition = read_json(directory / 'compiler.json')
        binaries = read_json(directory / 'ready.json')
        capabilities = read_json(directory / 'capabilities.json')
        require(composition['kind'] == POLICY and digest(composition) == key,
                'native runtime tool composition identity mismatch')
        require(composition['compiler_key'] == compiler.key
                and composition['compiler_sysroot'] == str(compiler.sysroot)
                and composition['binaries'] == binaries,
                'tools belong to a different runtime installation or binary set')
        binding = composition['compiler_roles']
        runtime_binding(compiler, binding)
        require(capabilities['compiler_roles'] == binding
                and capabilities['compiler_sysroot'] == str(compiler.sysroot)
                and capabilities['runtime_wrapper'] == dict(sha256=binaries[WRAPPER], compiler_roles=binding),
                'tools lack matching recorded exporter/wrapper runtime roles')
    except (OSError, KeyError, TypeError, ValueError, AttributeError) as error:
        raise RuntimeError('invalid native runtime tool association: ' + str(error)) from error
