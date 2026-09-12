"""Run the unchanged launcher with timers enabled only for its Cargo child."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
import interpreter

original_run=interpreter.subprocess.run


def observed_run(command, *args, **kwargs):
    # The VM and tool/sysroot probes keep their original environment. Only the
    # launcher's explicit library-test Cargo check receives this diagnostic.
    if (len(command)>2 and command[0]=='cargo' and command[2]=='check'
            and '--message-format=json-render-diagnostics' in command):
        env=dict(kwargs['env'])
        if not env.get('RUSTC_WRAPPER','').endswith('/rust-interp-rustc-wrapper'):
            raise RuntimeError('observer expected the qualified Cargo wrapper')
        env['RUST_INTERP_EXPORT_TIMINGS']='1'
        kwargs['env']=env
    return original_run(command,*args,**kwargs)


if __name__=='__main__':
    interpreter.subprocess.run=observed_run
    try:
        raise SystemExit(interpreter.main())
    finally:
        interpreter.subprocess.run=original_run
