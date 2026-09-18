"""Validate installed tools' compiler association without importing the installer."""
import hashlib
import json

TOOL_POLICY = 'owned-compiler-tools-v1'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read_json(path):
    require(not path.is_symlink() and path.is_file() and path.stat().st_size <= 32 * 1024 * 1024,
            'missing or invalid compiler manifest: ' + str(path))
    return json.loads(path.read_bytes())


def validate_tool_compiler(directory, key, compiler):
    path = directory / 'compiler.json'
    if compiler is None:
        require(not path.exists() and not path.is_symlink(),
                'custom compiler tools require --compiler-key')
        return
    try:
        composition = read_json(path)
        require(digest(composition) == key and composition['kind'] == TOOL_POLICY,
                'custom tool composition identity mismatch')
        require(composition['compiler_key'] == compiler.key
                and composition['compiler_sysroot'] == str(compiler.sysroot),
                'tool was built with a different compiler')
        require(composition['binaries'] == read_json(directory / 'ready.json'),
                'custom tool composition binary mismatch')
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError('invalid custom tool compiler association: ' + str(error)) from error
