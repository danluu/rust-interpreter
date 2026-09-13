#!/usr/bin/env python3
"""Validate and archive retention screen 02; its written assessment is specific to this record."""
import argparse
import gzip
import json
from pathlib import Path
import re
import statistics

from analyzer import ROOT, compressed, identity, member
from assess import require, sha
from screen import assessment as assess_rows, protocol_states, frozen_input_hash
from suite_reports import read_report, validate_report, validate_runtime_limits


def retention(rows):
    seen = set()
    prior_pids = set()
    result = []
    prefix = 'rust-interp-query-cache-retention: '
    for row in rows:
        if row['mode'] != 'candidate':
            require(not any(l.startswith(prefix) for l in row['stderr'].splitlines()),
                    'baseline unexpectedly reports candidate mechanism')
            continue
        events = [json.loads(l[len(prefix):]) for l in row['stderr'].splitlines() if l.startswith(prefix)]
        require(events and all(e['strict_checking'] is True and e['mode'] == 'demand' for e in events),
                'missing or incompatible retention report')
        new, replay, duplicate = [], 0, 0
        current = set()
        for event in events:
            signature = json.dumps(event, sort_keys=True, separators=(',', ':'))
            if signature in current:
                duplicate += 1
            elif signature in seen:
                replay += 1
            else:
                new.append(event)
            current.add(signature)
        collisions = sorted({e['process_id'] for e in new} & prior_pids)
        seen.update(current)
        prior_pids.update(e['process_id'] for e in events)
        enabled = [e for e in new if e['provider_installed']]
        fields = ['promotion_passes_omitted', 'serialization_attempts', 'serialized_bytes',
                  'serializer_query_jobs', 'retained_side_effects']
        result.append(dict(index=row['index'], phase=row['phase'], emitted_lines=len(events),
            exact_previously_seen_records=replay, duplicate_records_within_command=duplicate,
            newly_observed_records=len(new), newly_observed_process_ids=sorted({e['process_id'] for e in new}),
            new_record_with_previously_seen_pid=collisions, newly_observed_provider_installed=len(enabled),
            newly_observed_counter_sums={k: sum(e[k] for e in new) for k in fields},
            selected_test_records=[e for e in new if e['test']],
            interpretation='Exact earlier process-ID/counter records are replay, not new compiler work. '
                'First-seen records identify newly observed reports; no independent compiler parentage/start-time '
                'receipts exist, so these are not an independently verified process census.'))
    return result


def markdown(s):
    lines = ['# Demand-retention mechanism screen', '',
        '**No material improvement; do not adopt this candidate from this screen.** '
        f"The median of five edited complete commands is {s['complete_command_median_seconds']['candidate']:.6f} s "
        f"for candidate, {s['complete_command_median_seconds']['baseline']:.6f} s for baseline and "
        f"{s['complete_command_median_seconds']['duplicate']:.6f} s for the independent baseline duplicate. "
        'None of the five candidate commands reached 0.5 s. This is a mechanism screen, with no final '
        'latency qualification or holdout/generalization claim.', '',
        f"The median paired wall change is {(s['median_paired_wall_ratio']-1)*100:+.3f}%; "
        f"median paired CPU change is {(s['median_paired_cpu_ratio']-1)*100:+.3f}%. "
        f"The largest absolute A/A wall deviation is {s['maximum_aa_wall_deviation']*100:.3f}%; "
        f"the largest A/A CPU deviation is {s['maximum_aa_cpu_deviation']*100:.3f}%. "
        'These five comparisons and descriptive A/A deviations are not confidence intervals. '
        'A median of paired ratios differs from a ratio of separate arm medians.', '',
        '| Edit | Baseline wall s | Candidate wall s | Duplicate wall s | B/A wall | A′/A wall | B/A CPU | A′/A CPU |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for p in s['pairs']:
        lines.append(f"| {p['index']-2}: {p['label']} | {p['baseline_seconds']:.6f} | "
            f"{p['candidate_seconds']:.6f} | {p['duplicate_seconds']:.6f} | {p['wall_ratio']:.6f} | "
            f"{p['aa_wall_ratio']:.6f} | {p['cpu_ratio']:.6f} | {p['aa_cpu_ratio']:.6f} |")
    lines += ['', '| Edit | Baseline CPU s | Candidate CPU s | Duplicate CPU s |',
              '| --- | ---: | ---: | ---: |']
    for p in s['pairs']:
        lines.append(f"| {p['index']-2} | {p['baseline_cpu_seconds']:.6f} | "
                     f"{p['candidate_cpu_seconds']:.6f} | {p['duplicate_cpu_seconds']:.6f} |")
    lines += ['', 'Complete wall time surrounds the launcher, Cargo, VM, original selected tests and '
        'process-receipt I/O. CPU is waited-for child user plus system time and can exceed elapsed time '
        'because compiler processes run concurrently. Nested launcher/Cargo stages are preserved in '
        'the JSON; they are not added to complete-command time.', '',
        '## Cold observations and controls', '',
        '| Arm | Initial empty-target wall s | CPU s | All nine commands wall s |',
        '| --- | ---: | ---: | ---: |']
    for r in s['cold']:
        lines.append(f"| {r['mode']} | {r['seconds']:.6f} | {r['cpu']['total_seconds']:.6f} | "
                     f"{s['whole_session_command_seconds'][r['mode']]:.6f} |")
    lines += ['', 'Each arm starts with a separate empty target/cache history; installed compiler and '
        'standard-library setup are outside these commands. The single cold command per arm was run '
        'in the planned order (baseline, candidate, duplicate). Its slower candidate observation is '
        'retained, not a repeatable cold-build regression estimate.', '',
        'All 27 commands were validated. Each arm ran the original 14 tests, the deliberate wrong '
        'production edit, compiled recovery, five fresh cumulative production edits and compiled final '
        'restoration. The wrong edit produced matching guest-test failures in all arms; every other '
        'state passed all 14 tests. Bytecode and entry catalogs matched across all three arms for every '
        'state. The original source was restored. Every valid edited hash was new in each arm’s history; '
        'these exposed Nushell edits are not fresh-project holdouts.', '',
        '## Retention reports and Cargo replay', '',
        '| State index | Phase | Report lines | Exact earlier reports | First-seen reports | First-seen installed providers |',
        '| --- | --- | ---: | ---: | ---: | ---: |']
    for r in s['retention_reports']:
        lines.append(f"| {r['index']} | {r['phase']} | {r['emitted_lines']} | "
            f"{r['exact_previously_seen_records']} | {r['newly_observed_records']} | "
            f"{r['newly_observed_provider_installed']} |")
    lines += ['', 'Cargo replays stored compiler stderr for fresh units. Reports are compared by their '
        'complete JSON, including actual `process_id`, crate/test identity, incremental directories and '
        'counters. Exact records from earlier commands are excluded from newly observed counter sums. '
        'The JSON retains all first-seen process IDs, PID-reuse ambiguities, and selected-test reports. '
        'These logs lack independent compiler start-time/parentage receipts, so first-seen reports are '
        'not asserted to be an independently verified census of newly started compiler processes. '
        'Omitted promotion passes and serialized-byte counters describe mechanism activity; they do '
        'not measure time saved or establish a speedup.', '',
        '## Identity and retained evidence', '',
        f"Baseline and duplicate tool key: `{s['tools']['baseline']}`. Candidate key: "
        f"`{s['tools']['candidate']}`. VM bytes are identical; exporter and wrapper identities differ. "
        f"The pinned Nushell revision is `{s['revision']}`. Cargo jobs: {s['cargo_jobs']}; "
        f"suite workers: {s['suite_workers']}. Compiler profile and flags were not reduced, and all "
        'required Cargo units and strict checking were retained.', '',
        '[summary.json](summary.json) contains all five pairs, all 27 command summaries, cold costs, '
        'source-state hashes, artifact hashes, tool/compiler/sysroot identities and replay-aware counters. '
        '[evidence.json.gz](evidence.json.gz) preserves exact UTF-8 plan, records, original summary, '
        'receipts, suites, source transitions, small artifact sidecars, frozen harness/protocol and tool '
        'source-provenance files. Every member hash and the deterministic gzip round trip was verified. '
        'Bytecode hashes were checked against retained snapshots; caches, bytecode and executable '
        'binaries remain in `.work`.', '',
        'Screen 01 failed before any workload because the inventory reader encountered a tracked '
        'directory symlink. Its [failure evidence](../strict-warm-retention-screen-01-failure/assessment.md) '
        'is preserved. Screen 02 starts fresh after that inventory fix; no timed sample was replaced.', '',
        'Repackage saved evidence into a fresh result directory:', '', '```sh',
        'python3 benchmarks/experiments/strict-warm-build/assess_screen.py \\',
        f"  {s['raw']} --run-id strict-warm-retention-screen-02-reproduced", '```', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid run ID')
    raw = args.raw.resolve(strict=True)
    require(raw.is_relative_to(ROOT / '.work'), 'input escapes owned workspace')
    files = {str(raw / name): member(raw / name) for name in
             ['plan.json', 'records.json', 'summary.json', 'transitions.json']}
    plan, rows, original_summary, transitions = [json.loads(files[str(raw / n)]['utf8'])
        for n in ['plan.json', 'records.json', 'summary.json', 'transitions.json']]
    require(original_summary['records_sha256'] ==
            '9734f40544d395add1247e1d7305aee36f5c3ef7143384ddd669cf46a8f69ece',
            'written assessment applies only to retained screen 02; assess a new experiment separately')
    require(plan['owner'] == str(ROOT) and plan['kind'] == 'mechanism-screen' and
            plan['final_qualification'] is False and original_summary['source_restored'] is True,
            'expected completed owned mechanism screen')
    for name in ['plan', 'records']:
        require(files[str(raw / (name + '.json'))]['sha256'] == original_summary[name + '_sha256'],
                'screen source hash differs')
    calculated = assess_rows(rows)
    require(all(original_summary[k] == v for k, v in calculated.items()), 'saved screen assessment differs')
    source_file = Path(plan['source']) / plan['case']['file']
    source_bytes = source_file.read_bytes()
    require(sha(source_bytes) == plan['original_source_sha256'], 'source is not restored')
    expected_states = protocol_states(source_bytes, plan['case'])
    expected_plan = [{k: v for k, v in state.items() if k != 'source'} |
                     dict(source_sha256=sha(state['source'])) for state in expected_states]
    require(expected_plan == plan['states'], 'saved source sequence differs from original edits')
    require([(r['index'], r['mode']) for r in rows] ==
            [(s['index'], m) for s in plan['states'] for m in s['modes']], 'command order differs')
    require(len(transitions) == len(plan['states']), 'source transition count differs')
    for index, transition in enumerate(transitions):
        require(transition['index'] == index and transition['after'] == plan['states'][index]['source_sha256'],
                'source transition differs')
        if index < len(transitions) - 1:
            expected_before = plan['states'][max(0, index - 1)]['source_sha256']
            require(transition['before'] == expected_before, 'source transition input differs')
    artifacts, compact = {}, []
    previous = dict.fromkeys(plan['tools'])
    for row in rows:
        index, mode = row['index'], row['mode']
        expected = plan['states'][index]
        require(row['phase'] == expected['phase'] and row['source_sha256'] == expected['source_sha256'] and
                row['previous_source_sha256'] == previous[mode], 'command source history differs')
        previous[mode] = row['source_sha256']
        receipt_path, suite_path = [raw / folder / f'{index}-{mode}.json' for folder in ['receipts', 'suites']]
        for p in [receipt_path, suite_path]:
            files[str(p)] = member(p)
        receipt = json.loads(files[str(receipt_path)]['utf8'])
        require(all(receipt[k] == row[k] for k in ['index', 'phase', 'mode', 'source_sha256', 'pid',
                'command', 'returncode']) and receipt['status'] == 'finished' and
                receipt['tool_key'] == plan['tools'][mode], 'command receipt differs')
        success = row['phase'] != 'wrong-edit'
        require((row['returncode'] == 0) == success, 'command status differs')
        suite, suite_sha = read_report(suite_path, row['suite_sha256'])
        outcomes = validate_report(suite, plan['case']['tests'], 'prepared', success)
        validate_runtime_limits(suite, plan['instruction_limit'], plan['allocation_limit'], required=True)
        require([list(x) for x in outcomes] == row['outcomes'] and
                suite['workers'] == suite['requested_workers'] == plan['suite_workers'], 'suite differs')
        launches = [json.loads(l.split(': ', 1)[1]) for l in row['stderr'].splitlines()
                    if l.startswith('rust-interp-launch: ')]
        require(launches == [row['launch']] and row['launch']['suite_report_sha256'] == suite_sha and
                row['launch']['tool_key'] == plan['tools'][mode] and
                row['launch']['query_cache_retention'] == ('demand' if mode == 'candidate' else 'off'),
                'launcher evidence differs')
        for item in row['artifacts']:
            p = (ROOT / item['path']).resolve(strict=True)
            require(p.is_relative_to(raw / 'artifacts'), 'artifact snapshot escapes screen')
            actual = identity(p)
            require(actual['sha256'] == item['sha256'] and actual['bytes'] == item['bytes'],
                    'retained artifact differs')
            artifacts[item['path']] = item
            if p.suffix == '.json':
                files[str(p)] = member(p)
        bytecode, catalog_item, calls_item = row['artifacts']
        catalog, calls = [json.loads(files[str((ROOT / i['path']).resolve())]['utf8'])
                          for i in [catalog_item, calls_item]]
        require(bytecode['sha256'] == row['launch']['artifact_sha256'] == catalog['artifact_sha256'] ==
                calls['artifact_sha256'] and calls['strict_frontend'] is True and
                [e['name'] for e in catalog['entries']] == plan['case']['tests'] and
                [e['function'] for e in catalog['entries']] == [t['function'] for t in suite['tests']],
                'artifact-bound catalog/checking evidence differs')
        compact.append({k: row[k] for k in ['index', 'phase', 'label', 'mode', 'pid', 'seconds', 'cpu',
            'returncode', 'source_sha256', 'previous_source_sha256', 'suite_sha256', 'artifacts']} |
            dict(test_passed=suite['passed'], test_failed=suite['failed'],
                 stdout_sha256=sha(row['stdout'].encode()), stderr_sha256=sha(row['stderr'].encode()),
                 stages={k: row['launch'][k] for k in ['tools_seconds', 'std_mir_seconds', 'cargo_seconds',
                     'cargo_cpu', 'execution_seconds', 'build_to_ready_seconds', 'build_to_ready_cpu']},
                 failed_tests=[name for name, status in outcomes if status == 'failed']))
    for index in range(len(plan['states'])):
        group = [r for r in rows if r['index'] == index]
        require(len({json.dumps(r['outcomes']) for r in group}) == 1 and
                len({r['stdout'] for r in group}) == 1 and all(
                    len({r['artifacts'][slot]['sha256'] for r in group}) == 1 for slot in [0, 1]),
                'cross-arm suite, bytecode, catalog or output differs')
    provenance = []
    for key in sorted(set(plan['tools'].values())):
        tool = ROOT / '.work/interpreter-tools' / key
        for name in ['ready.json', 'capabilities.json', 'source.json']:
            p = tool / name
            require(frozen_input_hash(p) == plan['frozen'][str(p)], 'frozen tool provenance differs')
            files[str(p)] = member(p)
            provenance.append({k: files[str(p)][k] for k in ['path', 'bytes', 'sha256']})
    for p in [Path(__file__).with_name('screen.py'), Path(__file__).with_name('PROTOCOL.md'),
              Path(plan['source']) / '.rust-interp-owned.json', Path(plan['std_mir']['path'])]:
        require(frozen_input_hash(p) == plan['frozen'][str(p)], 'frozen evidence file differs')
        files[str(p)] = member(p)
    for name in ['installed-retention-composition.json', 'merged-retention-source-check.json']:
        p = ROOT / '.work/strict-warm-build' / name
        files[str(p)] = member(p)
    bundle = dict(schema_version=1, encoding='exact UTF-8 members', files=list(files.values()))
    payload = (json.dumps(bundle, separators=(',', ':'), ensure_ascii=False) + '\n').encode()
    archive = compressed(payload)
    for item in json.loads(gzip.decompress(archive))['files']:
        data = item['utf8'].encode()
        require(len(data) == item['bytes'] and sha(data) == item['sha256'], 'archived member differs')
    summary = dict(original_summary)
    summary.update(project=plan['project'], workflow=plan['workflow'], revision=plan['revision'],
        tools=plan['tools'], binaries=plan['binaries'], cargo_jobs=plan['cargo_jobs'],
        suite_workers=plan['suite_workers'], tests=plan['case']['tests'], states=plan['states'],
        original_source_sha256=plan['original_source_sha256'], compiler=plan['std_mir']['compiler'],
        std_mir=plan['std_mir'], environment_sha256=plan['environment_sha256'],
        command_summaries=compact, cold=[r for r in compact if r['phase'] == 'cold'],
        maximum_aa_cpu_deviation=max(abs(p['aa_cpu_ratio'] - 1) for p in summary['pairs']),
        retention_reports=retention(rows), artifact_inventory=list(artifacts.values()),
        tool_provenance=provenance, source_inventory_entries=len(plan['frozen']),
        archive=dict(path='evidence.json.gz', bytes=len(archive), sha256=sha(archive), gzip_mtime=0,
                     uncompressed_sha256=sha(payload), members=len(files), all_member_hashes_verified=True),
        packager_sha256=sha(Path(__file__).read_bytes()), source_restoration_rechecked=True,
        adoption='not supported; no material complete-command improvement and target not met')
    for pair in summary['pairs']:
        for mode in plan['tools']:
            row = next(r for r in rows if r['index'] == pair['index'] and r['mode'] == mode)
            pair[mode + '_cpu_seconds'] = row['cpu']['total_seconds']
    output = ROOT / 'results' / args.run_id
    output.mkdir(exist_ok=False)
    (output / 'evidence.json.gz').write_bytes(archive)
    require(identity(output / 'evidence.json.gz')['sha256'] == summary['archive']['sha256'],
            'published archive differs')
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (output / 'assessment.md').write_text(markdown(summary))
    print(json.dumps(dict(output=str(output), archive=summary['archive'], commands=len(rows))))


if __name__ == '__main__':
    main()
