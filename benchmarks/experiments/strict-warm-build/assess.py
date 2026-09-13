#!/usr/bin/env python3
"""Validate and summarize a completed compiler diagnostic without compiling."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from cargo_timing_data import units_from_html, timeline
from suite_reports import read_report, validate_report, validate_runtime_limits


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def options(args, flag):
    values = []
    for index, arg in enumerate(args):
        if arg == flag and index + 1 < len(args):
            values.append(args[index + 1])
        elif arg.startswith(flag + '='):
            values.append(arg[len(flag) + 1:])
    return values


def phase_totals(events):
    grouped = defaultdict(list)
    for event in events:
        value = event['time']
        require(isinstance(event['pass'], str) and isinstance(value, (float, int)) and
                math.isfinite(value) and value >= 0, 'invalid phase duration')
        grouped[event['pass']].append(value)
    return {name: dict(count=len(values), summed_reported_seconds=math.fsum(values),
                       minimum_reported_seconds=min(values), maximum_reported_seconds=max(values))
            for name, values in sorted(grouped.items())}


def compiler_role(compiler, selected, raw):
    args = compiler['original_args']
    environment = compiler['environment']
    crate_names = options(args, '--crate-name')
    targets = options(args, '--target')
    emissions = [v for value in options(args, '--emit') for v in value.split(',')]
    crate_types = [v for value in options(args, '--crate-type') for v in value.split(',')]
    features = sorted(value[9:-1] for value in options(args, '--cfg')
                      if value.startswith('feature="') and value.endswith('"'))
    capture_path = Path(compiler['record_path']).with_name('exporter-args.json')
    capture = None
    if capture_path.exists():
        require(capture_path.resolve().is_relative_to(raw), 'exporter capture escapes diagnostic')
        capture_payload = capture_path.read_bytes()
        capture = json.loads(capture_payload)
        require(crate_names == [selected['target']['name']] and selected['profile']['test'] is True and
                environment.get('CARGO_MANIFEST_DIR') == str(Path(selected['manifest_path']).parent),
                'exporter capture does not match selected Cargo test artifact')
        require('--test' in capture['args'] or 'test' in options(capture['args'], '--cfg'),
                'selected exporter is missing its test compilation configuration')
        role, cargo_target = 'selected library test check', ' (check-test)'
        capture = dict(path=str(capture_path), sha256=sha(capture_payload), record=capture)
    elif not compiler['compilation']:
        role, cargo_target = 'compiler information probe', None
    elif environment.get('CARGO_CRATE_NAME') == 'build_script_build' and 'bin' in crate_types:
        role, cargo_target = 'host build-script compilation', ' build-script'
    elif 'proc-macro' in crate_types:
        role, cargo_target = 'host procedural macro compilation', ''
    elif 'metadata' in emissions and 'link' not in emissions:
        role, cargo_target = 'ordinary library check', ' (check)'
    elif not targets and any(t in crate_types for t in ['lib', 'rlib']):
        role, cargo_target = 'host library build', ''
    else:
        role, cargo_target = 'other compiler unit', None
    return dict(role=role, package=environment.get('CARGO_PKG_NAME'),
                crate_name=crate_names[0] if len(crate_names) == 1 else crate_names,
                target_context='explicit target' if targets else 'host context',
                explicit_targets=targets, crate_types=crate_types, emissions=emissions,
                features=features, cargo_target_description=cargo_target,
                selected_exporter_capture=capture)


def verify_state(row, raw, tests):
    directory = raw / row['state']
    for name in ['cargo', 'vm']:
        require(row[name]['returncode'] == 0, 'recorded command failed')
        for stream in ['stdout', 'stderr']:
            require(sha((directory / (name + '.' + stream)).read_bytes()) == row[name][stream + '_sha256'],
                    'command output hash differs')
    payload = (directory / 'program.rbc').read_bytes()
    require(sha(payload) == row['artifact_sha256'] and len(payload) == row['artifact_bytes'],
            'retained selected artifact differs')
    catalog = json.loads((directory / 'program.rbc.entries.json').read_text())
    require([entry['name'] for entry in catalog['entries']] == tests and
            catalog['artifact_sha256'] == row['artifact_sha256'], 'artifact-bound test catalog differs')
    calls = json.loads((directory / 'program.rbc.calls.json').read_text())
    require(calls['strict_frontend'] is True and calls['artifact_sha256'] == row['artifact_sha256'],
            'strict checking call report differs')
    suite, suite_hash = read_report(directory / 'suite.json', row['suite_sha256'])
    outcomes = validate_report(suite, tests, 'prepared', True)
    validate_runtime_limits(suite, 100000000000, 150000, required=True)
    timing = (directory / 'cargo-timing.html').read_bytes()
    require(sha(timing) == row['cargo_timing_sha256'] and units_from_html(timing) == row['cargo_units'],
            'Cargo timing snapshot differs')
    require(timeline(row['cargo_units']) == row['cargo_timeline'], 'Cargo timeline differs')
    compilers = []
    for compiler in row['compiler_invocations']:
        record_path = Path(compiler['record_path']).resolve(strict=True)
        require(record_path.is_relative_to(directory / 'units'), 'compiler receipt escapes state')
        disk = json.loads(record_path.read_text())
        require(all(compiler.get(key) == value for key, value in disk.items()) and
                disk['status'] == 'finished' and disk['returncode'] == 0, 'compiler receipt differs')
        stderr = record_path.with_name('stderr.log').read_bytes()
        require(sha(stderr) == compiler['stderr_sha256'], 'compiler stderr hash differs')
        actual_phases = [json.loads(line[6:]) for line in stderr.decode(errors='replace').splitlines()
                         if line.startswith('time: {')]
        require(actual_phases == compiler['phases'], 'compiler phases differ from raw output')
        role = compiler_role(compiler, row['selected_cargo_event'], raw)
        matching = [u for u in row['cargo_units'] if u['name'] == role['package'] and
                    u['target'] == role['cargo_target_description'] and sorted(u['features']) == role['features']]
        phases = phase_totals(actual_phases)
        residual = None
        persist = phases.get('incr_comp_persist_result_cache')
        serialize = phases.get('incr_comp_serialize_result_cache')
        if persist and serialize and persist['count'] == serialize['count'] == 1:
            residual = persist['summed_reported_seconds'] - serialize['summed_reported_seconds']
            require(residual >= 0, 'nested cache persistence time exceeds its outer scope')
        compilers.append(dict(**role, wrapper_pid=compiler['wrapper_pid'], child_pid=compiler['child_pid'],
            wrapper_child_elapsed_seconds=compiler['elapsed_seconds'], compilation=compiler['compilation'],
            cargo_unit_ids=[u['i'] for u in matching], phases=phases, phase_event_count=len(actual_phases),
            persist_outside_serialize_seconds=residual,
            receipt_sha256=sha(record_path.read_bytes()), stderr_sha256=sha(stderr),
            source_receipt_path=str(record_path)))
    build_scripts = [u for u in row['cargo_units'] if u['mode'] == 'run-custom-build']
    return dict(state=row['state'], source_sha256=row['source_sha256'],
        rustc_phase_logging=row['instrumented'], cargo_seconds=row['cargo']['seconds'],
        vm_seconds=row['vm']['seconds'],
        direct_cargo_to_validated_artifact_seconds=row['direct_cargo_to_validated_artifact_seconds'],
        selected_exporter_stages=row['exporter_stages'], cargo_unit_count=len(row['cargo_units']),
        compiler_unit_count=sum(c['compilation'] for c in compilers),
        information_probe_count=sum(not c['compilation'] for c in compilers),
        build_script_run_count=len(build_scripts), build_script_runs=build_scripts,
        cargo_timeline=row['cargo_timeline'], cargo_units=row['cargo_units'],
        artifact_sha256=row['artifact_sha256'], artifact_bytes=row['artifact_bytes'],
        suite_sha256=suite_hash, test_outcomes=outcomes,
        selected_cargo_event=row['selected_cargo_event'], compiler_invocations=compilers)


def value(unit, phase):
    row = unit['phases'].get(phase)
    return row['summed_reported_seconds'] if row else None


def seconds(number):
    return 'not reported' if number is None else f'{number:.6f}'


def assessment(summary):
    rows = summary['states']
    edited = next(r for r in rows if r['state'] == 'edited')
    compilers = [c for c in edited['compiler_invocations'] if c['compilation']]
    by_id = {u['i']: u for u in edited['cargo_units']}
    text = ['# Strict warm-build compiler diagnosis', '',
        'One real production edit in the pinned ' + summary['project'] + ' `' + summary['workflow'] +
        '` workflow, with all ' + str(len(summary['tests'])) + ' original tests preserved. '
        'The empty-target prime, edited source and restored original each passed the selected suite. '
        'These are diagnostic observations, not a performance comparison or evidence that the 0.5 s target passed.', '',
        '| State | Cargo wall seconds | VM seconds | rustc phase logging |',
        '| --- | ---: | ---: | --- |']
    for row in rows:
        text.append(f"| {row['state']} | {row['cargo_seconds']:.6f} | {row['vm_seconds']:.6f} | " +
                    ('enabled' if row['rustc_phase_logging'] else 'disabled') + ' |')
    text += ['', 'All states include the diagnostic Python wrapper, verbose Cargo output, Cargo HTML timings '
        'and exporter timers. Only the edited state adds rustc phase logging. The edited and restoration '
        'commands have different source/cache histories, so their difference does not estimate instrumentation '
        'overhead. Tool/bootstrap and prebuilt standard-library setup are outside these observations. '
        'The direct Cargo-to-artifact metric excludes launcher startup and VM preflight; it is not strict readiness.', '',
        f"The edited command has {edited['compiler_unit_count']} compiler units, "
        f"{edited['build_script_run_count']} build-script execution and {edited['information_probe_count']} "
        f"compiler information probes. Cargo reports {edited['cargo_unit_count']} timed units. "
        f"The selected exporter reports {edited['selected_exporter_stages']['frontend']:.6f} s frontend "
        f"and {edited['selected_exporter_stages']['lowering']:.6f} s lowering; other required units remain outside those scopes.", '',
        '## Every edited compiler unit', '',
        'Host/target context, Cargo feature sets and actual emissions remain distinct. The selected test is '
        'identified through its captured exporter arguments and the selected Cargo artifact, including its '
        '`cfg(test)` configuration; checking only the incoming argv for `--test` would mislabel it.', '',
        '| Package | Actual role | Context | Features | Child wall s | Cargo IDs |',
        '| --- | --- | --- | --- | ---: | --- |']
    for unit in sorted(compilers, key=lambda c: min((by_id[i]['start'] for i in c['cargo_unit_ids']), default=math.inf)):
        text.append(f"| {unit['package']} | {unit['role']} | {unit['target_context']} | " +
            ', '.join(unit['features']) + f" | {unit['wrapper_child_elapsed_seconds']:.6f} | " +
            ', '.join(map(str, unit['cargo_unit_ids'])) + ' |')
    for unit in edited['build_script_runs']:
        text.append(f"| {unit['name']} | build-script execution | Cargo run-custom-build | " +
                    ', '.join(unit['features']) + f" | {unit['duration']:.6f} (Cargo interval) | {unit['i']} |")
    text += ['', 'Compiler child wall intervals and Cargo intervals have different boundaries and can overlap. '
        'They do not sum to CPU or complete-command time. The preserved Cargo timeline includes every '
        'reported interval and unblocking edge; it does not expose a complete causal critical path.', '',
        '## Phases in the four longest compiler invocations', '',
        'Each cell aggregates events with that exact label within one invocation. Nested phase labels '
        'overlap and must not be added into a total. Missing selected-exporter `total` output is left missing.', '',
        '| Package / role | Macro expansion s | Type checking s | Misc checking 3 s | Metadata s | Borrow checking s |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    largest = sorted(compilers, key=lambda c: -c['wrapper_child_elapsed_seconds'])[:4]
    for unit in largest:
        text.append('| ' + unit['package'] + ' / ' + unit['role'] + ' | ' + ' | '.join(
            seconds(value(unit, name)) for name in ['macro_expand_crate', 'type_check_crate',
                'misc_checking_3', 'generate_crate_metadata', 'MIR_borrow_checking']) + ' |')
    text += ['', '## Incremental-cache scope bounds and repeated events', '',
        '| Package / role | Persist s | Serialize s | Outside serialize s | drop_ast events | drop_ast sum s |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for unit in largest:
        drops = unit['phases'].get('drop_ast', {})
        text.append('| ' + unit['package'] + ' / ' + unit['role'] + ' | ' + ' | '.join([
            seconds(value(unit, 'incr_comp_persist_result_cache')),
            seconds(value(unit, 'incr_comp_serialize_result_cache')),
            seconds(unit['persist_outside_serialize_seconds']), str(drops.get('count', 0)),
            seconds(drops.get('summed_reported_seconds'))]) + ' |')
    text += ['', 'On the pinned compiler, the outer result-cache persistence scope includes cache promotions, '
        'closing the old memory map, file setup/finalization and the nested serialization scope. '
        'The difference is an observed upper envelope for promotion inside that invocation, including other '
        'work and timing effects. It is not pure promotion time or a predicted removable speedup. '
        'The JSON retains count, sum, minimum and maximum for every repeated phase label. '
        'The table keeps every occurrence instead of overwriting repeated labels. These counts make the logging '
        'cost relevant, but they do not measure that overhead.', '',
        '## Evidence and scope', '',
        f"Source revision: `{summary['revision']}`. Tool key: `{summary['tool']['tool_key']}`. "
        f"Cargo workers: {summary['jobs']}; suite workers: {summary['suite_workers']}; "
        f"borrow-check reuse: `{summary['borrowck_cache']}`; function reuse: `{summary['function_cache']}`.", '',
        'The summary preserves tool binary/capability/source hashes, compiler identity, source-state hashes, '
        'all metadata-sysroot hashes, measured harness hashes, selected-artifact hashes, test outcomes and '
        'verified restoration/input-integrity receipts. [summary.json](summary.json) contains the complete '
        'aggregates and roles. [report.json.gz](report.json.gz) preserves the exact original report bytes, '
        'including every original compiler argument and phase event, with deterministic gzip metadata. '
        'No project target artifacts are copied into results.', '']
    return '\n'.join(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id) is not None, 'invalid output run ID')
    path = args.report.resolve(strict=True)
    require(path.is_relative_to(ROOT / '.work') and path.stat().st_size <= 128*1024*1024,
            'expected bounded task-owned diagnostic report')
    payload = path.read_bytes()
    report = json.loads(payload)
    require(report['schema_version'] == 1 and report['status'] == 'passed' and
            report['owner'] == str(ROOT) and report['performance_measurement'] is False,
            'diagnostic was not completed successfully by this checkout')
    checks = ['source_restored', 'assertions_unchanged', 'tool_inputs_unchanged',
              'scripts_unchanged', 'std_mir_unchanged']
    require(all(report[key] is True for key in checks), 'diagnostic integrity check failed')
    require([r['state'] for r in report['records']] == ['prime', 'edited', 'restored'],
            'unexpected source-state sequence')
    require([r['source_sha256'] for r in report['records']] ==
            [report['original_sha256'], report['edited_sha256'], report['original_sha256']] and
            report['original_sha256'] != report['edited_sha256'], 'source state hashes differ')
    states = [verify_state(row, path.parent, report['tests']) for row in report['records']]
    edited = states[1]
    require(all(len(c['cargo_unit_ids']) == 1 for c in edited['compiler_invocations'] if c['compilation']),
            'an edited compiler unit lacks an unambiguous Cargo role match')
    require(edited['compiler_unit_count'] + edited['build_script_run_count'] == edited['cargo_unit_count'],
            'edited Cargo unit inventory is incomplete')
    compressed_stream = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=compressed_stream, mtime=0, compresslevel=9) as archive:
        archive.write(payload)
    compressed = compressed_stream.getvalue()
    require(gzip.decompress(compressed) == payload, 'gzip report does not round-trip exactly')
    provenance_keys = ['source', 'revision', 'project', 'workflow', 'tests', 'edits',
        'original_sha256', 'edited_sha256', 'compiler', 'compiler_sysroot', 'rustc_path',
        'std_mir_sysroot', 'std_mir_artifacts', 'target', 'tool', 'jobs', 'suite_workers',
        'borrowck_cache', 'function_cache', 'frozen_scripts']
    summary = dict(schema_version=1, status='completed diagnostic validated and summarized',
        performance_measurement=False, **{k: report[k] for k in provenance_keys},
        integrity={k: report[k] for k in checks}, states=states,
        source_report=dict(path=str(path.relative_to(ROOT)), sha256=sha(payload), bytes=len(payload)),
        compressed_report=dict(path='report.json.gz', sha256=sha(compressed), bytes=len(compressed),
                               gzip_mtime=0, exact_decompression=True),
        assessor_sha256=sha(Path(__file__).read_bytes()),
        phase_interpretation='Repeated labels retain counts and summed reported wall intervals; nested labels and concurrent units do not sum to elapsed or CPU time.',
        persistence_interpretation='Persist minus nested serialize includes promotion plus mmap closure and file setup/finalization; it is not pure promotion time or an estimated speedup.')
    output = ROOT / 'results' / args.run_id
    output.mkdir(exist_ok=False)
    (output / 'report.json.gz').write_bytes(compressed)
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (output / 'assessment.md').write_text(assessment(summary))
    print(output / 'assessment.md')


if __name__ == '__main__':
    main()
