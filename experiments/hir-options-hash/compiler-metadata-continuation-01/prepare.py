#!/usr/bin/env python3
"""Freeze a separate, two-probe continuation and its saved-output controls."""
import ast
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('metadata_continuation', HERE/'continue.py')
c = importlib.util.module_from_spec(spec);sys.modules[spec.name] = c;spec.loader.exec_module(c)

def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True);stream.write('\n')

def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    assert not c.WORK.exists()
    original = c.read(c.ORIGINAL/'plan.json')
    oldfreeze = c.read(c.ORIGINAL/'inputs.json')
    assert c.sha(c.ORIGINAL/'plan.json') == oldfreeze['plan_sha256']
    assert c.sha(c.ORIGINAL/'inputs.json') == '04af101aceaa3ee52ccacf93d7f5ca85b8bcd82c418f020e3bcd473340d74e88'
    terminal = c.read(c.PRIOR/'receipt.json')
    assert c.sha(c.PRIOR/'receipt.json') == '0aa470640dcbe112aadca653753bf90c3ea0178e1a5afa647844af7491cddc9f'
    assert terminal['status'] == 'failed' and len(terminal['commands']) == 48 and len(original['children']) == 50
    prior_membership = {str(root): sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file())
                        for root in [c.PRIOR, c.OUTER]}
    plan = dict(status='prepared-unrun', original_plan=original,
                original_inputs_sha256=c.sha(c.ORIGINAL/'inputs.json'),
                prior_receipt_sha256=c.sha(c.PRIOR/'receipt.json'), prior_membership=prior_membership,
                children=original['children'][48:], saved_children=48, compiler_builds=0,
                capacity=original['capacity'], canonical_lock=str(c.owned.CANONICAL_LOCK), wait_seconds=600)
    c.saved(plan)
    write(HERE/'plan.json', plan)
    environment = oldfreeze['launch_environment']
    python = Path(sys.executable).resolve(strict=True)
    files = {}
    def add(path):
        path = Path(path);files[str(path)] = c.m.file(path)
    for path in HERE.glob('*'):
        if path.is_file():
            add(path)
            if path.suffix == '.py':ast.parse(path.read_text())
    for path in [c.ORIGINAL/'inputs.json',c.ORIGINAL/'plan.json',c.ORIGINAL/'launch.json',python,
                 c.OWNER/'scripts/supervise_experiment.py',c.OWNER/'experiments/stable-cgu/owned_stage.py',
                 Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/options-hash-metadata03-failure-independent-actual-verification.json')]:
        add(path)
    for root_name, members in prior_membership.items():
        for name in members:add(Path(root_name)/name)
    for suffix in ['actual.json','stdout','stderr']:
        add(c.OWNER/('.work/hir-options-hash-compiler-metadata-launch-03.'+suffix))
    freeze = dict(files=files, original_inputs_sha256=plan['original_inputs_sha256'],
                  plan_sha256=c.sha(HERE/'plan.json'), launch_environment=environment)
    write(HERE/'inputs.json', freeze)
    launch = dict(status='prepared-unrun-awaiting-review', owner=str(c.OWNER), environment=environment,
        command=[str(python),'-B',str(c.OWNER/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-compiler-metadata-continuation-supervisor-01','--',
                 str(python),'-B',str(HERE/'continue.py'),'--inputs-sha256',c.sha(HERE/'inputs.json')],
        helper_sha256=c.sha(HERE/'continue.py'),inputs_sha256=c.sha(HERE/'inputs.json'),plan_sha256=c.sha(HERE/'plan.json'),
        expected_children=2,saved_children=48,compiler_builds=0,capacity=plan['capacity'])
    write(HERE/'launch.json', launch)
    tree = ast.parse((HERE/'test_linker_parser.py').read_text())
    control_names = sorted(node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'))
    assert control_names and len(control_names) == len(set(control_names))
    control_paths = [HERE/'run_controls.py',HERE/'test_linker_parser.py',HERE/'linker_parser.py',python,
                     c.OWNER/'scripts/supervise_experiment.py',c.OWNER/'experiments/stable-cgu/owned_stage.py',
                     c.PRIOR/'commands/047/receipt.json',c.PRIOR/'commands/047/stderr',c.ORIGINAL/'plan.json']
    controls = dict(files={str(p):c.m.file(p) for p in control_paths}, environment=environment,
                    command=[str(python),'-B','-m','unittest','test_linker_parser','-v'], expected_names=control_names)
    write(HERE/'control-inputs.json', controls)
    control_launch = dict(status='prepared-unrun-awaiting-review',owner=str(c.OWNER),environment=environment,
        command=[str(python),'-B',str(c.OWNER/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-metadata-parser-controls-supervisor-01','--',
                 str(python),'-B',str(HERE/'run_controls.py'),'--inputs-sha256',c.sha(HERE/'control-inputs.json')],
        inputs_sha256=c.sha(HERE/'control-inputs.json'),helper_sha256=c.sha(HERE/'run_controls.py'),expected_children=1,controls=len(control_names),
        capacity=dict(entry_gib=16,stop_gib=9,floor_gib=8))
    write(HERE/'control-launch.json', control_launch)
    print(json.dumps(dict(launch_sha256=c.sha(HERE/'launch.json'),freeze_sha256=c.sha(HERE/'inputs.json'),plan_sha256=c.sha(HERE/'plan.json'),
                         files=len(files),bytes=sum(row['stamp'][3] for row in files.values()),children=2,
                         control_launch_sha256=c.sha(HERE/'control-launch.json'),control_freeze_sha256=c.sha(HERE/'control-inputs.json'),controls=len(control_names)),indent=2))

if __name__ == '__main__':main()
