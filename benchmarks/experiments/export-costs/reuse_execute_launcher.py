"""Enable actual function reuse only inside the owned Cargo check child."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import interpreter

original_run = interpreter.subprocess.run


def cached_run(command, *args, **kwargs):
    if (len(command) > 2 and command[0] == 'cargo' and command[2] == 'check'
            and '--message-format=json-render-diagnostics' in command):
        env = dict(kwargs['env'])
        assert env.get('RUSTC_WRAPPER', '').endswith('/rust-interp-rustc-wrapper')
        assert not any(env.get(k) for k in ['RUST_INTERP_FUNCTION_COSTS', 'RUST_INTERP_BINDING_REPLAY', 'RUST_INTERP_ALLOCATION_TRACE'])
        env['RUST_INTERP_FUNCTION_CACHE'] = 'reuse'
        kwargs['env'] = env
    return original_run(command, *args, **kwargs)


if __name__ == '__main__':
    interpreter.subprocess.run = cached_run
    try:
        raise SystemExit(interpreter.main())
    finally:
        interpreter.subprocess.run = original_run
