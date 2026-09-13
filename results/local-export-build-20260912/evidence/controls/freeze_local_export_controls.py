from pathlib import Path
import datetime, hashlib, json
b = Path(__file__).resolve().parent
root = b.parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
source = json.loads((b / 'local-export-prebuild-source/source.json').read_text())
for name, row in source['files'].items(): assert sha(root / name) == row['sha256'], name
for name, digest in source['qualification_input_hashes'].items():
    assert sha(b / name) == digest, name
expected = json.loads((b / 'local-export-expected-validation-inputs.json').read_text())
assert len(expected['inputs_sha256']) == 27
assert expected['source_manifest_sha256'] == sha(b / 'local-export-composition-manifest.json')
assert expected['baseline_qualification_sha256'] == sha(b / 'owned-analysis-pre-screen-qualification.json')
for name, digest in expected['inputs_sha256'].items(): assert sha(root / name) == digest, name
commands = json.loads((b / 'local-export-qualification-commands.json').read_text())
assert commands['cwd'] == str(root) and commands['source_key'] == source['tool_key']
names = list(dict.fromkeys(list(source['qualification_input_hashes']) + [
    'qualify_local_export.py', 'owned-analysis-tools.json', 'owned-analysis-pre-screen-qualification.json',
    'local-export-expected-validation-inputs.json', 'freeze_local_export_controls.py']))
receipt = dict(recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               source_snapshot_receipt_sha256=sha(b / 'local-export-prebuild-source/source.json'),
               reason='All core qualification source and controls fixed prospectively before tests; only the reviewed local-layout fixture differs from the prior full suite.',
               qualification_input_hashes={name: sha(b / name) for name in names})
with (b / 'local-export-prebuild-controls.json').open('x') as f: json.dump(receipt, f, indent=2); f.write('\n')
print(json.dumps(dict(frozen_control_inputs=len(names), fixed_fixture_inputs=len(expected['inputs_sha256'])), indent=2))
