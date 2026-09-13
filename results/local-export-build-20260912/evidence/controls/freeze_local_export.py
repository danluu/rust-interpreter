from pathlib import Path
import hashlib, json, subprocess

root = Path(__file__).resolve().parents[2]
b = Path(__file__).resolve().parent
manifest = json.loads((b / 'local-export-composition-manifest.json').read_text())
snapshot = b / 'local-export-prebuild-source'
assert not snapshot.exists()
files = manifest['compiler_source_files']
assert len(files) == 146 and list(files) == manifest['compiler_source_input_order']
design = {row['path']: row for row in manifest['additional_bound_files']}
h = hashlib.sha256()
for name, row in files.items():
    data = (root / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['sha256'], name
    h.update(name.encode() + b'\0' + data)
assert h.hexdigest() == manifest['compiler_source_key']
common = json.loads((b / 'common-controls-source/source.json').read_text())
for name, digest in common['files'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
for name, row in design.items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == row['sha256'], name
for name in files:
    path = snapshot / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((root / name).read_bytes())
receipt = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
               tool_key=h.hexdigest(), files=files, common_files=common['files'],
               design_files=design)
for name in ['local-export-qualification-plan.md', 'local-export-composition-manifest.json',
             'local-export-qualification-commands.json', 'local-export-expected-validation-inputs.json',
             'freeze_local_export.py', 'freeze_local_export_controls.py', 'freeze_local_export_inputs.py',
             'install_local_export.py', 'validate_local_export.py', 'qualify_local_export.py', 'run_locked.py',
             'owned-analysis-tools.json', 'owned-analysis-pre-screen-qualification.json']:
    receipt.setdefault('qualification_input_hashes', {})[name] = hashlib.sha256((b / name).read_bytes()).hexdigest()
(snapshot / 'source.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(dict(source_commit=receipt['source_commit'], tool_key=h.hexdigest(), compiler_inputs=len(files)), indent=2))
