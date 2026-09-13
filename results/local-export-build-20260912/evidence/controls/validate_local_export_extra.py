"""Bind unchanged audit/inline validators to the actually qualified 14af bundle.

Run audit/inline modes under run_locked.py; these validators do not self-lock.
The freeze mode records controls only and never imports a validator.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
B = Path(__file__).resolve().parent
KEY = '14af97a36405cc925ce89529e5bc9ff2db9ecdbd0f8b816095ace66235fc4c75'
BASE = 'eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d'
OLD = '0d0d7b9092fe9e29320b35d7b04eed4655a81b7d21e0cd90bff9abaecf85ed34'
CONTROLS = B / 'local-export-extra-controls.json'


def sha(path):
    path = Path(path)
    assert path.is_relative_to(ROOT) and path.resolve(strict=True) == path and path.is_file(), path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    sha(path)
    return json.loads(Path(path).read_text())


def write_new(path, value):
    with Path(path).open('x') as target:
        json.dump(value, target, indent=2, allow_nan=False)
        target.write('\n')


def verify(proofs):
    for name, digest in proofs.items():
        assert sha(ROOT / name) == digest, name


def bind(proofs, path, digest=None):
    path = Path(path)
    name = str(path.relative_to(ROOT))
    actual = sha(path)
    assert digest is None or actual == digest, name
    assert name not in proofs or proofs[name] == actual, name
    proofs[name] = actual


def freeze():
    assert not os.path.lexists(CONTROLS)
    expected_path = B / 'local-export-extra-inputs.json'
    expected = read(expected_path)
    assert expected['candidate_tool_key'] == KEY and expected['baseline_tool_key'] == BASE
    proofs = dict(expected['files'])
    verify(proofs)
    bind(proofs, expected_path)
    core_path = B / 'local-export-qualification.json'
    core = read(core_path)
    assert core['qualification_pass'] is True and core['tool_key'] == KEY
    assert core['baseline_tool_key'] == BASE and core['frozen_baseline_runtime'] is True
    assert core['tests'] == {mode: dict(passed=408, failed=0, ignored=1) for mode in ['debug', 'release']}
    assert core['full_validation']['completed_commands'] == 23727
    for name, digest in core['proofs'].items():
        bind(proofs, ROOT / name, digest)
    bind(proofs, core_path)
    bundles = {}
    for mode, name, key in [('candidate', 'local-export-tools.json', KEY), ('baseline', 'owned-analysis-tools.json', BASE)]:
        path = B / name
        bundle = read(path)
        directory = ROOT / '.work/interpreter-tools' / key
        assert bundle['tool_key'] == key and Path(bundle['directory']) == directory
        assert set(bundle['binaries']) == {'rust-interp-mir-export', 'rust-interp-vm', 'rust-interp-rustc-wrapper'}
        assert read(directory / 'ready.json') == bundle['binaries']
        for binary, digest in bundle['binaries'].items():
            bind(proofs, directory / binary, digest)
        for item in [path, directory / 'ready.json', directory / 'capabilities.json']:
            bind(proofs, item)
        bundles[mode] = bundle
    for binary in ['rust-interp-vm', 'rust-interp-rustc-wrapper']:
        assert bundles['candidate']['binaries'][binary] == bundles['baseline']['binaries'][binary]
    # Preserve the original leaf-inline validator's optional old-tool rejection.
    old_dir = ROOT / '.work/interpreter-tools' / OLD
    old_present = (old_dir / 'ready.json').exists()
    old_caps_present = (old_dir / 'capabilities.json').exists()
    if old_present:
        old = read(old_dir / 'ready.json')
        bind(proofs, old_dir / 'ready.json')
        for binary, digest in old.items():
            bind(proofs, old_dir / binary, digest)
        if old_caps_present:
            bind(proofs, old_dir / 'capabilities.json')
    commands = {
        'audit': [sys.executable, str(B / 'validate_local_export_extra.py'), 'audit'],
        'inline': [sys.executable, str(B / 'validate_local_export_extra.py'), 'inline'],
        'audit-parity': [sys.executable, str(B / 'validate_local_export_audit_parity.py')],
    }
    verify(proofs)
    write_new(CONTROLS, dict(tool_key=KEY, baseline_tool_key=BASE, source_commit=core['source_commit'],
        created_at=time.time(), commands=commands, expected_commands={'audit': 79, 'inline': 23 + int(old_present), 'audit-parity': 8},
        optional_legacy_exporter_check=old_present, optional_legacy_capabilities_present=old_caps_present,
        bundles=bundles, proofs=proofs, performance_claim=False))
    print(json.dumps({'status': 'frozen', 'controls': str(CONTROLS)}, indent=2))


def checked_controls():
    controls = read(CONTROLS)
    assert controls['tool_key'] == KEY and controls['baseline_tool_key'] == BASE
    verify(controls['proofs'])
    old_dir = ROOT / '.work/interpreter-tools' / OLD
    assert (old_dir / 'ready.json').exists() == controls['optional_legacy_exporter_check']
    assert (old_dir / 'capabilities.json').exists() == controls['optional_legacy_capabilities_present']
    return controls


def validate(mode):
    assert mode in ['audit', 'inline']
    controls = checked_controls()
    tools = controls['bundles']['candidate']
    name = {'audit': 'validate_audit_artifacts.py', 'inline': 'validate_leaf_inlining.py'}[mode]
    path = B / ('local-export-' + mode + '-validation.json')
    assert not os.path.lexists(path)
    sys.path.insert(0, str(ROOT / 'scripts'))
    spec = importlib.util.spec_from_file_location('local_export_extra_' + mode, ROOT / 'scripts' / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.ROOT == ROOT
    module.checked_tools = lambda: (Path(tools['directory']), tools['tool_key'])
    receipt = dict(status='running', mode=mode, script=name, source_sha256=sha(ROOT / 'scripts' / name),
        tool_key=KEY, binaries=tools['binaries'], controls_sha256=sha(CONTROLS),
        controller_pid=os.getpid(), started_at=time.time())
    write_new(path, receipt)
    top = ROOT / 'results/audit-artifact-validation.json'
    saved = top.read_bytes() if mode == 'audit' and top.exists() else None
    if mode == 'audit' and saved is not None:
        with (B / 'local-export-audit-prior-top-level.json').open('xb') as target:
            target.write(saved)
        receipt['prior_top_level_sha256'] = hashlib.sha256(saved).hexdigest()
    try:
        module.main()
        if mode == 'audit':
            summary = read(top)
            assert summary['tool_key'] == KEY and summary['source_restored'] is True
            with (B / 'local-export-audit-top-level-validation.json').open('xb') as target:
                target.write(top.read_bytes())
            receipt['summary'] = summary
        checked_controls()
        receipt.update(status='passed', finished_at=time.time())
    except BaseException as error:
        receipt.update(status='failed', error=repr(error), finished_at=time.time())
        raise
    finally:
        if mode == 'audit':
            if saved is not None:
                top.write_bytes(saved)
                assert hashlib.sha256(top.read_bytes()).hexdigest() == receipt['prior_top_level_sha256']
            elif top.exists():
                top.unlink()
            receipt['prior_top_level_restored'] = True
        path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    assert len(sys.argv) == 2
    if sys.argv[1] == 'freeze':
        freeze()
    else:
        validate(sys.argv[1])
