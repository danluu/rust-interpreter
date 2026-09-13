"""Set one diagnostic option only on the launcher's owned Cargo-check child."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import interpreter


def child_environment(command, env, value, replay=None):
    if (len(command) > 2 and command[0] == 'cargo' and command[2] == 'check'
            and '--message-format=json-render-diagnostics' in command):
        env = dict(env)
        assert env.get('RUSTC_WRAPPER', '').endswith('/rust-interp-rustc-wrapper')
        assert 'RUST_INTERP_REUSE_MISSES' not in env
        if value is not None:
            env['RUST_INTERP_REUSE_MISSES'] = value
        if replay is not None:
            assert 'RUST_INTERP_REPLAY_COSTS' not in env
            env['RUST_INTERP_REPLAY_COSTS'] = replay
    return env


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--reuse-misses')
    parser.add_argument('--also-replay-costs')
    args, remaining = parser.parse_known_args()
    original = interpreter.subprocess.run

    def run(command, *positional, **kwargs):
        if 'env' in kwargs:
            kwargs['env'] = child_environment(command, kwargs['env'], args.reuse_misses, args.also_replay_costs)
        return original(command, *positional, **kwargs)

    interpreter.subprocess.run = run
    original_argv = sys.argv
    try:
        sys.argv = [sys.argv[0], *remaining]
        return interpreter.main()
    finally:
        interpreter.subprocess.run = original
        sys.argv = original_argv


if __name__ == '__main__':
    raise SystemExit(main())
