"""Enable the function census only in the owned launcher's Cargo check child."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import interpreter

original_run = interpreter.subprocess.run
dependency_census = os.environ.get('RUST_INTERP_FUNCTION_DEPENDENCIES') == '1'


def observed_run(command, *args, **kwargs):
    if (len(command) > 2 and command[0] == 'cargo' and command[2] == 'check'
            and '--message-format=json-render-diagnostics' in command):
        env = dict(kwargs['env'])
        if not env.get('RUSTC_WRAPPER', '').endswith('/rust-interp-rustc-wrapper'):
            raise RuntimeError('census expected the qualified Cargo wrapper')
        env.update(RUST_INTERP_EXPORT_TIMINGS='1', RUST_INTERP_FUNCTION_COSTS='1')
        if dependency_census:
            env['RUST_INTERP_FUNCTION_DEPENDENCIES'] = '1'
        kwargs['env'] = env
    return original_run(command, *args, **kwargs)


if __name__ == '__main__':
    interpreter.subprocess.run = observed_run
    try:
        raise SystemExit(interpreter.main())
    finally:
        interpreter.subprocess.run = original_run
