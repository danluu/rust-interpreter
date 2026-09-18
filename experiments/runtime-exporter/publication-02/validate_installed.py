"""Use the current R owner's ordinary launcher and runtime association readers."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROWNER = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
PLAN = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/runtime-exporter/publication-02/plan.json')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--runtime-compiler-key', required=True)
    args = parser.parse_args()
    assert sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == ROWNER
    plan = json.loads(PLAN.read_bytes())
    assert plan['tool_key'] == args.tool_key and plan['runtime_key'] == args.runtime_compiler_key
    sys.path.insert(0, str(ROWNER / 'scripts'))
    import interpreter
    import runtime_compiler
    import runtime_tools
    assert interpreter.ROOT == ROWNER
    runtime = runtime_compiler.load_runtime_compiler(ROWNER, plan['runtime_key'])
    runtime.revalidate(ROWNER)
    directory, key = interpreter.installed_tools(plan['tool_key'])
    assert directory == Path(plan['publication_directory'])
    runtime_tools.validate_tool_runtime(directory, key, runtime)
    for option in plan['required_export_options']:
        interpreter.require_export_option(directory, key, option)
    loaded = {}
    for module in list(sys.modules.values()):
        raw = getattr(module, '__file__', None)
        if raw and raw.startswith(str(ROWNER / 'scripts') + '/'):
            path = str(Path(raw).resolve(strict=True))
            value = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            assert plan['runtime_launcher_sources'][path] == value
            loaded[path] = value
    print(json.dumps(dict(status='passed', tool_key=key, compiler_key=runtime.key,
        compiler_sysroot=str(runtime.sysroot), owner=str(ROWNER), loaded_launcher_sources=loaded,
        required_export_options=plan['required_export_options'], guest_execution=False), sort_keys=True))


if __name__ == '__main__':
    main()
