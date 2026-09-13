#!/usr/bin/env python3
"""Package saved measureme summaries; never invoke a compiler, VM, or profile reader."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re

from assess import ROOT, require, sha, verify_state


def identity(path):
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
            size += len(block)
    return dict(path=str(path), bytes=size, sha256=digest.hexdigest())


def member(path):
    payload = path.read_bytes()
    return dict(path=str(path), bytes=len(payload), sha256=sha(payload),
                utf8=payload.decode('utf-8'))


def compressed(payload):
    stream = io.BytesIO()
    with gzip.GzipFile(filename='', fileobj=stream, mode='wb', mtime=0, compresslevel=9) as archive:
        archive.write(payload)
    result = stream.getvalue()
    require(gzip.decompress(result) == payload, 'archive does not round-trip exactly')
    return result


def duration(value):
    require(type(value['secs']) is int and value['secs'] >= 0 and
            type(value['nanos']) is int and 0 <= value['nanos'] < 1000000000,
            'invalid saved duration')
    return value['secs'] + value['nanos'] / 1000000000


def query(row):
    result = dict(label=row['label'])
    for old, new in [('self_time', 'self_seconds'), ('time', 'inclusive_seconds'),
                     ('incremental_load_time', 'incremental_load_seconds'),
                     ('incremental_hashing_time', 'incremental_hashing_seconds'),
                     ('blocked_time', 'blocked_seconds')]:
        result[new] = duration(row[old])
    for key in ['invocation_count', 'number_of_cache_misses', 'number_of_cache_hits']:
        require(type(row[key]) is int and row[key] >= 0, 'invalid saved event count')
        result[key] = row[key]
    return result


def assessment(summary):
    edited, restored = summary['states']
    selected = next(u for u in summary['units'] if u['role'] == 'selected library test check')
    hosts = [u for u in summary['units'] if u['role'] == 'host library build' and
             u['package'] == selected['package']]
    lines = ['# Strict warm-build self-profile diagnosis', '',
        f"Edit {summary['edit_index']} in `{summary['project']}` / `{summary['workflow']}` passed all "
        f"{len(summary['tests'])} original tests, as did restoration. This is a warm continuation of "
        '[profile 01](../strict-warm-profile-01/assessment.md), with its existing target directory. '
        'The source hash was fresh relative to the recorded edit history; the cold prime was skipped. '
        'This is not an independent cold history, a speedup comparison, or acceptance of the 0.5 s target.', '',
        '| State | Cargo wall s | VM wall s | rustc self-profile | Tests |',
        '| --- | ---: | ---: | --- | --- |']
    for row in [edited, restored]:
        lines.append(f"| {row['state']} | {row['cargo_seconds']:.6f} | {row['vm_seconds']:.6f} | "
                     f"{row['profiling']} | {len(row['test_outcomes'])} passed |")
    lines += ['', 'The edited and restored commands have different source and cache states. Their wall-time '
        'difference does not estimate profiling overhead. Both use the diagnostic wrapper, Cargo timings '
        'and exporter timers; only the edited command records rustc self-profiles. These direct Cargo and '
        'VM intervals exclude launcher startup, preflight and tool/bootstrap setup.', '',
        f"The edited build has {edited['compiler_unit_count']} compiler invocations, "
        f"{edited['build_script_run_count']} build-script execution and {edited['information_probe_count']} "
        f"compiler information probes: {edited['cargo_unit_count']} timed Cargo units. Every real compiler "
        'invocation has a retained raw profile and a successful saved reader result.', '',
        '## How to read the query data', '',
        'Self time subtracts directly nested events on the same thread; inclusive time includes those '
        'nested events. Incremental-load and hashing times are already represented in self time, so they '
        'are not additional costs to add. The reader’s `total_time` is the sum of each recorded thread’s '
        'end-minus-start span. These are elapsed-event counters, not measured process CPU time. Concurrent '
        'threads and compiler invocations overlap; neither their spans nor inclusive query rows sum to '
        'complete-command wall time.', '',
        '`Invocations` counts actual query/provider or activity executions without cache hits. Loads and '
        'blocked hits do not increment that counter; zero invocations can coexist with substantial load '
        'time. Cache misses and cache hits remain separate counters in the JSON; activity rows need not '
        'have query-cache semantics.', '',
        '## All edited compiler units', '',
        'Roles preserve host/target context and features in the JSON. The selected test is identified '
        'through its captured exporter arguments and selected Cargo artifact, including its test '
        'configuration; the initial wrapper argv alone does not contain `--test`.', '',
        '| Package | Role | Child wall s | Sum of thread spans s | Raw profile bytes |',
        '| --- | --- | ---: | ---: | ---: |']
    for unit in summary['units']:
        lines.append(f"| {unit['package']} | {unit['role']} | {unit['wrapper_child_elapsed_seconds']:.6f} | "
                     f"{unit['reader_thread_span_sum_seconds']:.6f} | {unit['raw_profile']['bytes']} |")
    lines += ['', '## Four longest compiler invocations', '',
        'Rows below are the ten largest self-time labels within each invocation. A row can aggregate '
        'many events. The full query table, including exact nanosecond durations and all counts, is '
        'preserved in the compressed query archive.']
    for unit in sorted(summary['units'], key=lambda u: -u['wrapper_child_elapsed_seconds'])[:4]:
        lines += ['', f"### {unit['package']} — {unit['role']}", '',
            f"Compiler child wall: {unit['wrapper_child_elapsed_seconds']:.6f} s; "
            f"sum of recorded thread spans: {unit['reader_thread_span_sum_seconds']:.6f} s.", '',
            '| Label | Self s | Inclusive s | Incremental load s | Invocations | Cache misses | Cache hits |',
            '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
        for q in unit['top_queries_by_self_time']:
            lines.append(f"| `{q['label']}` | {q['self_seconds']:.6f} | {q['inclusive_seconds']:.6f} | "
                         f"{q['incremental_load_seconds']:.6f} | {q['invocation_count']} | "
                         f"{q['number_of_cache_misses']} | {q['number_of_cache_hits']} |")
    focused = {q['label']: q for q in selected['top_queries_by_self_time']}
    if all(k in focused for k in ['expand_proc_macro', 'lower_to_hir', 'typeck_root']):
        lines += ['', f"In the selected test compilation, procedural macros account for "
            f"{focused['expand_proc_macro']['self_seconds']:.6f} s self time; HIR lowering accounts for "
            f"{focused['lower_to_hir']['self_seconds']:.6f} s self time. The `typeck_root` row includes "
            f"{focused['typeck_root']['incremental_load_seconds']:.6f} s of incremental-result loading. "
            'These are distinct required frontend activities, not a demonstrated removable budget.']
    for host in hosts:
        counts = host['codegen_activity_counts']
        if 'LLVM_module_codegen_emit_obj' in counts:
            lines += ['', f"The changed production edit also reaches the host `{host['package']}` build: "
                f"{counts['LLVM_module_codegen_emit_obj']} LLVM object-emission events and "
                f"{counts.get('codegen_module', 0)} `codegen_module` events show work on that many "
                'codegen units. This generic-code change therefore includes substantial host code '
                'generation and LLVM work; the table is not solely a selected-test frontend profile. '
                'The counters identify work observed here, not the causal cost of each source change.']
    lines += ['', '## Evidence and reproduction', '',
        f"Source revision: `{summary['revision']}`. Tool key: `{summary['tool']['tool_key']}`. "
        f"Reader: measureme {summary['reader']['version']}, recorded source commit "
        f"`{summary['reader']['source_commit']}`. The compiler is the pinned nightly-2026-09-08 build; "
        'its full version and sysroot identity are retained in the JSON.', '',
        '[summary.json](summary.json) preserves both source states, all test outcomes, exact source/tool/'
        'sysroot/harness identities, all 18 compiler roles, raw-profile paths/sizes/hashes and archive hashes. '
        '[query-summaries.json.gz](query-summaries.json.gz) preserves the exact UTF-8 bytes of all saved '
        'reader JSON files, successful reader commands, supervisor/build receipts and the reader analysis '
        'source used to interpret counters. [report.json.gz](report.json.gz) preserves the exact original '
        'diagnostic report, including compiler arguments. All archived member hashes and gzip round trips '
        'were verified; selected artifacts and both suites were validated against their recorded hashes. '
        'Raw `.mm_profdata` files stay in `.work` and are not copied into results.', '',
        'Repackage the retained evidence into a fresh result directory without executing any workload:', '',
        '```sh', 'python3 benchmarks/experiments/strict-warm-build/analyzer.py \\',
        f"  {summary['source_report']['path']} \\",
        f"  --reader-build {summary['reader']['build_report']['path']} \\",
        '  --run-id strict-warm-self-profile-02-reproduced', '```', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--reader-build', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid output run ID')
    path, build_path = args.report.resolve(strict=True), args.reader_build.resolve(strict=True)
    require(all(p.is_relative_to(ROOT / '.work') for p in [path, build_path]), 'input escapes owned work')
    raw = path.parent
    payload = path.read_bytes()
    report, build = json.loads(payload), json.loads(build_path.read_bytes())
    require(report['schema_version'] == 1 and report['owner'] == str(ROOT) and
            report['status'] == 'passed' and report['profiling'] == 'self' and
            report['performance_measurement'] is False, 'expected passed owned self-profile diagnostic')
    checks = ['source_restored', 'assertions_unchanged', 'tool_inputs_unchanged', 'scripts_unchanged',
              'std_mir_unchanged', 'previous_reports_unchanged']
    require(all(report[k] is True for k in checks), 'diagnostic integrity check failed')
    require([r['state'] for r in report['records']] == ['edited', 'restored'] and
            [r['source_sha256'] for r in report['records']] ==
            [report['edited_sha256'], report['original_sha256']], 'unexpected source state sequence')
    continuation = report['continuation']
    prior_path = Path(continuation['prior_report']).resolve(strict=True)
    require(prior_path.is_relative_to(ROOT / '.work') and
            identity(prior_path)['sha256'] == continuation['prior_report_sha256'] and
            continuation['prime_skipped'] is True and
            report['edit_index'] > max(continuation['previously_compiled_edit_indices']) and
            report['edited_sha256'] not in continuation['previously_compiled_source_hashes'] and
            report['edited_sha256'] != report['original_sha256'], 'continuation identity/freshness differs')
    states = [verify_state(r, raw, report['tests']) for r in report['records']]
    edited = states[0]
    require(edited['compiler_unit_count'] + edited['build_script_run_count'] == edited['cargo_unit_count'],
            'Cargo unit inventory is incomplete')
    directory = raw / 'query-summaries'
    commands_member, supervisor_member = member(directory / 'commands.json'), member(directory / 'supervisor.json')
    commands, supervisor = json.loads(commands_member['utf8']), json.loads(supervisor_member['utf8'])
    build_command_member = member(build_path.with_name('command-1.json'))
    build_command = json.loads(build_command_member['utf8'])
    reader_source = Path(build_command['cwd']).resolve(strict=True)
    reader_binary = Path(build['binary']).resolve(strict=True)
    require(reader_source.is_relative_to(ROOT / '.work') and reader_binary.is_relative_to(ROOT / '.work'),
            'reader source or binary escapes owned work')
    require(build['status'] == supervisor['status'] == 'passed' and build_command['returncode'] == 0 and
            build['sha256'] == supervisor['reader_sha256'] == identity(reader_binary)['sha256'] and
            identity(reader_source / 'Cargo.lock')['sha256'] == build['lock_sha256'],
            'reader build/supervisor identity differs')
    manifest_member = member(reader_source / 'Cargo.toml')
    version = re.search(r'\[workspace\.package\]\s+version = "([^"]+)"', manifest_member['utf8']).group(1)
    require(version == '12.0.3', 'unexpected reader data-format version')
    files = [commands_member, supervisor_member, member(build_path), build_command_member,
             member(build_path.with_name('command-0.json')), manifest_member,
             member(reader_source / 'analyzeme/src/analysis.rs')]
    units = []
    expected_summaries, raw_paths = set(), set()
    original_compilers = {c['wrapper_pid']: c for c in report['records'][0]['compiler_invocations']}
    largest = {c['wrapper_pid'] for c in sorted(
        (c for c in edited['compiler_invocations'] if c['compilation']),
        key=lambda c: -c['wrapper_child_elapsed_seconds'])[:4]}
    for role in edited['compiler_invocations']:
        compiler = original_compilers[role['wrapper_pid']]
        if not role['compilation']:
            require(not compiler['self_profiles'], 'information probe unexpectedly profiled')
            continue
        require(len(role['cargo_unit_ids']) == len(compiler['self_profiles']) == 1,
                'compiler lacks unambiguous Cargo role or raw profile')
        require(compiler['profiling'] == 'self' and not compiler['phases'] and
                '-Zself-profile-events=default' in compiler['diagnostic_flags'] and
                not any(a.startswith('-Ztime-passes') for a in compiler['forwarded_command']),
                'unexpected edited compiler instrumentation')
        recorded_profile = compiler['self_profiles'][0]
        profile_path = Path(recorded_profile['path']).resolve(strict=True)
        require(profile_path.is_relative_to(raw / 'edited/units' / str(role['wrapper_pid'])) and
                profile_path.suffix == '.mm_profdata' and identity(profile_path) == recorded_profile,
                'raw profile identity differs')
        require(profile_path not in raw_paths, 'duplicate raw profile')
        raw_paths.add(profile_path)
        matches = [c for c in commands if c['command'] ==
                   [str(reader_binary), 'summarize', str(profile_path), '--json']]
        require(len(matches) == 1 and matches[0]['returncode'] == 0 and
                matches[0]['parent_pid'] == supervisor['supervisor_pid'], 'missing successful reader command')
        summary_path = directory / f"{compiler['child_pid']}.json"
        expected_summaries.add(summary_path)
        saved = member(summary_path)
        files.append(saved)
        queries = json.loads(saved['utf8'])
        rows = [query(q) for q in queries['query_data']]
        require(len({q['label'] for q in rows}) == len(rows), 'duplicate reader query label')
        unit = {k: role[k] for k in ['package', 'role', 'crate_name', 'target_context', 'explicit_targets',
            'crate_types', 'emissions', 'features', 'wrapper_pid', 'child_pid', 'cargo_unit_ids',
            'wrapper_child_elapsed_seconds', 'receipt_sha256', 'source_receipt_path']}
        capture = role['selected_exporter_capture']
        if capture:
            unit['selected_exporter_capture'] = {k: capture[k] for k in ['path', 'sha256']}
        unit.update(raw_profile=recorded_profile,
            query_summary={k: saved[k] for k in ['path', 'bytes', 'sha256']}, query_label_count=len(rows),
            reader_thread_span_sum_seconds=duration(queries['total_time']),
            codegen_activity_counts={q['label']: q['invocation_count'] for q in rows if q['label'] in
                ['codegen_module', 'LLVM_module_codegen_emit_obj', 'codegen_copy_artifacts_from_incr_cache']})
        if role['wrapper_pid'] in largest:
            unit['top_queries_by_self_time'] = sorted(rows, key=lambda q: (-q['self_seconds'], q['label']))[:10]
        units.append(unit)
    require(set(directory.glob('[0-9]*.json')) == expected_summaries and
            len(commands) == supervisor['profiles'] == len(units), 'reader inventory differs')
    require(all(not c['self_profiles'] and c['profiling'] == 'off'
                for c in report['records'][1]['compiler_invocations']), 'restoration unexpectedly profiled')
    bundle = dict(schema_version=1, encoding='utf8 members preserve exact original bytes', files=files)
    query_payload = (json.dumps(bundle, separators=(',', ':'), ensure_ascii=False) + '\n').encode()
    archives = {'report.json.gz': compressed(payload), 'query-summaries.json.gz': compressed(query_payload)}
    # Verify every original member after decompressing the actual archive representation.
    for item in json.loads(gzip.decompress(archives['query-summaries.json.gz']))['files']:
        content = item['utf8'].encode('utf-8')
        require(len(content) == item['bytes'] and sha(content) == item['sha256'], 'archived member differs')
    compact_states = []
    for saved, state in zip(report['records'], states):
        compact = {k: state[k] for k in ['state', 'source_sha256', 'cargo_seconds', 'vm_seconds',
            'direct_cargo_to_validated_artifact_seconds', 'selected_exporter_stages', 'cargo_unit_count',
            'compiler_unit_count', 'information_probe_count', 'build_script_run_count', 'build_script_runs',
            'artifact_sha256', 'artifact_bytes', 'suite_sha256', 'test_outcomes']}
        compact['profiling'] = saved['profiling']
        compact_states.append(compact)
    keys = ['source', 'revision', 'project', 'workflow', 'tests', 'edits', 'edit_index', 'original_sha256',
        'edited_sha256', 'compiler', 'compiler_sysroot', 'rustc_path', 'std_mir_sysroot', 'std_mir_artifacts',
        'target', 'target_directory', 'tool', 'jobs', 'suite_workers', 'borrowck_cache', 'function_cache',
        'frozen_scripts', 'history_kind', 'continuation']
    summary = dict(schema_version=1, status='saved diagnostic evidence validated and packaged',
        performance_measurement=False, **{k: report[k] for k in keys},
        integrity={k: report[k] for k in checks}, states=compact_states, units=units,
        source_report=dict(path=str(path.relative_to(ROOT)), bytes=len(payload), sha256=sha(payload)),
        reader=dict(version=version, source_commit=build['source_commit'], binary_sha256=build['sha256'],
            lock_sha256=build['lock_sha256'], build_report=dict(path=str(build_path.relative_to(ROOT)),
                sha256=sha(build_path.read_bytes())),
            analysis_source=identity(reader_source / 'analyzeme/src/analysis.rs'),
            successful_reader_commands=len(commands)),
        archives={name: dict(bytes=len(data), sha256=sha(data), gzip_mtime=0, exact_decompression=True)
                  for name, data in archives.items()},
        archive_member_hashes_verified=True, raw_profile_hashes_verified=True,
        raw_profile_total_bytes=sum(u['raw_profile']['bytes'] for u in units),
        packaging_script_sha256=sha(Path(__file__).read_bytes()),
        role_and_state_validator_sha256=sha(Path(__file__).with_name('assess.py').read_bytes()),
        timing_semantics='Query self time excludes nested child events per thread; inclusive time overlaps. '
            'Incremental load/hash counters are included in self time. Reader total_time is a sum of thread '
            'spans, not process CPU time. Overlapping compiler units do not sum to command wall time.',
        qualification='Continuation edit is fresh only relative to recorded target history; different '
            'edited/restored states cannot estimate profiling overhead. No speedup or 0.5 s acceptance claim.')
    output = ROOT / 'results' / args.run_id
    output.mkdir(exist_ok=False)
    for name, data in archives.items():
        (output / name).write_bytes(data)
        require(identity(output / name)['sha256'] == summary['archives'][name]['sha256'],
                'published archive hash differs')
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (output / 'assessment.md').write_text(assessment(summary))
    print(json.dumps(dict(output=str(output), units=len(units),
                         raw_profile_total_bytes=summary['raw_profile_total_bytes'], archives=summary['archives'])))


if __name__ == '__main__':
    main()
