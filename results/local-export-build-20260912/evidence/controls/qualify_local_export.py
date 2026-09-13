from pathlib import Path
import hashlib, json, math, re, shutil

root = Path(__file__).resolve().parents[2]
b = Path(__file__).resolve().parent
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def pid(value):
    assert type(value) is int and value > 0, value
    return value
def interval(record):
    start, finish = record['started_at'], record['finished_at']
    assert all(type(t) in (int, float) and math.isfinite(t) and t > 0 for t in [start, finish])
    assert start <= finish
    return start, finish
def completed(record, command, earliest):
    assert record['returncode'] == 0 and record['command'] == command
    assert record['cwd'] == str(root)
    assert pid(record['child_pid']) != pid(record['controller_pid'])
    start, finish = interval(record)
    assert earliest <= start, (earliest, start)
    return finish

source = json.loads((b / 'local-export-prebuild-source/source.json').read_text())
for name, row in source['files'].items(): assert sha(root / name) == row['sha256'], name
for name, digest in source['common_files'].items(): assert sha(root / name) == digest, name
for name, row in source['design_files'].items(): assert sha(root / name) == row['sha256'], name
controls = json.loads((b / 'local-export-prebuild-controls.json').read_text())
assert controls['source_snapshot_receipt_sha256'] == sha(b / 'local-export-prebuild-source/source.json')
for name, digest in controls['qualification_input_hashes'].items(): assert sha(b / name) == digest, name
for name, digest in source['qualification_input_hashes'].items():
    assert controls['qualification_input_hashes'][name] == digest, name
expected = json.loads((b / 'local-export-expected-validation-inputs.json').read_text())
assert len(expected['inputs_sha256']) == 27
assert expected['source_manifest_sha256'] == sha(b / 'local-export-composition-manifest.json')
assert expected['baseline_qualification_sha256'] == sha(b / 'owned-analysis-pre-screen-qualification.json')
commands = json.loads((b / 'local-export-qualification-commands.json').read_text())
assert commands['schema_version'] == 1 and commands['cwd'] == str(root)
assert commands['source_key'] == source['tool_key'] == '14af97a36405cc925ce89529e5bc9ff2db9ecdbd0f8b816095ace66235fc4c75'
assert len(source['files']) == 146
freeze = json.loads((b / 'local-export-input-freeze.json').read_text())
assert freeze['status'] == 'passed' and freeze['returncode'] == 0
assert freeze['command'] == commands['freeze']['command'] and freeze['cwd'] == str(root)
assert freeze['commands_sha256'] == sha(b / 'local-export-qualification-commands.json')
assert freeze['log_sha256'] == sha(b / 'local-export-input-freeze.log')
assert freeze['shared_lock_acquired'] is False and freeze['workloads_executed'] is False
assert pid(freeze['controller_pid']) != pid(freeze['controller_ppid'])
freeze_start, freeze_finish = interval(freeze)
assert len(freeze['steps']) == len(commands['freeze']['steps']) == 2
previous = freeze_start
for actual, planned in zip(freeze['steps'], commands['freeze']['steps']):
    assert actual['label'] == planned['label'] and actual['controller_pid'] == freeze['controller_pid']
    previous = completed(actual, planned['command'], previous)
assert previous <= freeze_finish
assert set(freeze['outputs_sha256']) == {'local-export-prebuild-source/source.json', 'local-export-prebuild-controls.json'}
for name, digest in freeze['outputs_sha256'].items(): assert sha(b / name) == digest, name
executions = {}
profiles = {'local-export-debug-tests': 'debug', 'local-export-release-tests': 'release',
            'local-export-tools-build': 'release', 'local-export-tools-install': None,
            'local-export-fixture-tests': None}
assert set(commands['qualification']) == set(profiles)
for label, profile in profiles.items():
    specification = commands['qualification'][label]
    assert specification['profile'] == profile
    command = specification['command']
    if profile is not None:
        assert command[:2] == ['cargo', '+nightly-2026-09-08']
        assert ('--release' in command) == (profile == 'release')
        assert ('profile.dev.debug=0' in command) == (profile == 'debug')
        assert ('profile.test.debug=0' in command) == (profile == 'debug')
    record = json.loads((b / (label + '.json')).read_text())
    assert record['owner'] == 'build-general-20260912'
    assert pid(record['controller_ppid']) != pid(record['controller_pid'])
    completed(record, command, freeze_finish)
    executions[label] = record
assert executions['local-export-tools-build']['finished_at'] <= executions['local-export-tools-install']['started_at']
assert executions['local-export-tools-install']['finished_at'] <= executions['local-export-fixture-tests']['started_at']
q = dict(source_commit=source['source_commit'], tool_key=source['tool_key'], tests={}, frozen_baseline_runtime=True)
required = [
    'minimal_program_has_literal_v5_fixint_encoding',
    'existing_call_copy_programs_keep_their_complete_bytes',
    'all_program_fields_and_opcode_payloads_match_the_retained_serializer',
    'buffer_growth_preserves_code_strings_and_byte_payloads',
    'encoding_does_not_introduce_validation_or_change_validation_errors',
    'colored_and_dedicated_checks_match_the_original_verifier',
    'both_layout_modes_preserve_slot_and_extent_failure_order',
    'later_checked_overflow_precedes_earlier_certificate_mismatches',

    'promotion_and_capture_removal_move_calls_branches_and_diagnostics',
    'zero_removal_keeps_forwarded_reads_and_cross_block_capture',
    'declined_promotion_keeps_original_owned_fields_and_register_count',
    'stale_capture_cannot_cross_a_join_even_when_source_version_is_unchanged',
    'generation_wrap_clears_ancient_aliases_before_restarting_at_one',
    'epoch_niche_preserves_alias_slot_size_on_this_host',
    'all_scalar_widths_preserve_capture_and_source_writer_decisions',
    'deterministic_branches_calls_writers_and_casts_match_full_reset_algorithm',
    'terminal_ended_single_blocks_keep_storage_and_exact_reports',
    'nonterminal_final_bodies_keep_the_existing_whole_body_skip_policy',
    'earlier_terminals_and_terminal_branches_still_use_the_full_transform',
    'validation_rejects_every_body_before_any_optimization_and_keeps_error_order',
]
proofs = ['local-export-qualification-plan.md', 'local-export-composition-manifest.json',
          'local-export-prebuild-source/source.json', 'local-export-source/source.json',
          'install_local_export.py', 'validate_local_export.py', 'freeze_local_export.py',
          'qualify_local_export.py', 'run_locked.py', 'local-export-tools.json',
          'local-export-capabilities.json', 'local-export-fixture-validation.json',
          'local-export-prebuild-controls.json', 'local-export-expected-validation-inputs.json',
          'freeze_local_export_controls.py', 'freeze_local_export_inputs.py',
          'local-export-qualification-commands.json', 'local-export-input-freeze.json',
          'local-export-input-freeze.log']
proofs += list(controls['qualification_input_hashes'])
proofs += list(source['qualification_input_hashes'])
for mode in ['debug', 'release']:
    label = 'local-export-' + mode + '-tests'
    text = (b / (label + '.log')).read_text()
    rows = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', text)
    counts = dict(zip(['passed', 'failed', 'ignored'], [sum(int(row[i]) for row in rows) for i in range(3)]))
    assert counts == dict(passed=408, failed=0, ignored=1), counts
    for name in required: assert re.search(r'test [^\n]*::' + name + r' \.\.\. ok', text), (mode, name)
    q['tests'][mode] = counts
    proofs += [label + '.json', label + '.log']
for label in ['local-export-tools-build', 'local-export-tools-install', 'local-export-fixture-tests']:
    proofs += [label + '.json', label + '.log']
validation = json.loads((b / 'local-export-fixture-validation.json').read_text())
assert validation['status'] == 'passed' and validation['tool_key'] == source['tool_key']
assert validation['controller_pid'] == executions['local-export-fixture-tests']['child_pid']
validation_start, validation_finish = interval(validation)
assert executions['local-export-fixture-tests']['started_at'] <= validation_start <= validation_finish <= executions['local-export-fixture-tests']['finished_at']
assert validation['source_sha256'] == expected['inputs_sha256']['scripts/validate_interpreter.py']
assert validation['fixture_sha256'] == expected['inputs_sha256']['tests/local_layout_fixture.rs']
assert validation['fixture_native_seed_count'] == 111 and validation['fixture_engines'] == ['interpreter', 'jit']
summary = json.loads((b / 'local-export-fixture-tests.log').read_text())
assert summary['completed_commands'] == 23727, summary['completed_commands']
raw = (root / summary['raw']).resolve(strict=True)
assert raw.parent == root / '.work' and raw.name.startswith('interpreter-validation-'), raw
records_path = raw / 'records.json'
records = json.loads(records_path.read_text())
assert isinstance(records, list) and len(records) == summary['completed_commands'] == 23727
archive_path = raw / 'commands.jsonl'
if archive_path.exists():
    with archive_path.open() as stream:
        archived = [json.loads(line) for line in stream]
    assert archived == records, 'raw JSONL and final records differ'
assert {n: d for n, d in summary['inputs_sha256'].items() if n.startswith(('tests/', 'scripts/'))} == expected['inputs_sha256']
for name, digest in summary['inputs_sha256'].items(): assert sha(root / name) == digest, name
build = json.loads((b / 'local-export-tools.json').read_text())
baseline = json.loads((b / 'owned-analysis-tools.json').read_text())
assert baseline['tool_key'] == 'eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d'
assert build['tool_key'] == source['tool_key']
for group in [build, baseline]:
    for name, digest in group['binaries'].items(): assert sha(Path(group['directory']) / name) == digest, name
for name in ['rust-interp-vm', 'rust-interp-rustc-wrapper']: assert build['binaries'][name] == baseline['binaries'][name]
capabilities = json.loads((b / 'local-export-capabilities.json').read_text())
completed(capabilities, [str(Path(build['directory']) / 'rust-interp-mir-export'), '--rust-interp-capabilities'], executions['local-export-tools-install']['started_at'])
assert capabilities['controller_pid'] == executions['local-export-tools-install']['child_pid']
assert capabilities['finished_at'] <= executions['local-export-tools-install']['finished_at']
proof_map = {str((b / name).relative_to(root)): sha(b / name) for name in dict.fromkeys(proofs)}
proof_map[str(records_path.relative_to(root))] = sha(records_path)
if archive_path.exists(): proof_map[str(archive_path.relative_to(root))] = sha(archive_path)
for name, digest in summary['inputs_sha256'].items(): proof_map[name] = digest
for group in [build, baseline]:
    for name, digest in group['binaries'].items():
        proof_map[str((Path(group['directory']) / name).relative_to(root))] = digest
q.update(full_validation=summary, baseline_tool_key=baseline['tool_key'],
         input_freeze_finished_at=freeze_finish, raw_validation_records=len(records),
         raw_validation_jsonl_bound=archive_path.exists(), proofs=proof_map,
         qualification_pass=True, diagnostic_or_performance_executed=False,
         free_bytes_after_qualification=shutil.disk_usage(root).free)
with (b / 'local-export-qualification.json').open('x') as f: json.dump(q, f, indent=2); f.write('\n')
print(json.dumps(dict(tests=q['tests'], full_validation_commands=summary['completed_commands'],
                     tool_key=build['tool_key'], qualification_pass=True), indent=2))
