#!/usr/bin/env python3
"""Package saved native-host-MIR screen evidence and immutable source snapshots."""
import argparse
import gzip
import os
import json
from pathlib import Path
import re
import statistics

from analyzer import ROOT, compressed, identity, member
from assess import require, sha
from screen import assessment as assess_rows, protocol_states, frozen_input_hash, launch_settings
from suite_reports import read_report, validate_report, validate_runtime_limits


def markdown(s):
    lines = ['# Native host MIR mechanism screen', '',
        '**No material improvement; keep this prototype unadopted.** '
        f"The five edited complete commands have medians of {s['complete_command_median_seconds']['baseline']:.6f} s "
        f"for baseline, {s['complete_command_median_seconds']['candidate']:.6f} s for candidate and "
        f"{s['complete_command_median_seconds']['duplicate']:.6f} s for the independent baseline duplicate. "
        'None of the five candidate commands reached 0.5 s. This is a mechanism screen, with no final '
        'latency qualification or holdout/generalization claim.', '',
        f"Median paired wall change: {(s['median_paired_wall_ratio'] - 1) * 100:+.3f}%; "
        f"median paired CPU change: {(s['median_paired_cpu_ratio'] - 1) * 100:+.3f}%. "
        f"Maximum absolute A/A wall deviation: {s['maximum_aa_wall_deviation'] * 100:.3f}%; "
        f"maximum absolute A/A CPU deviation: {s['maximum_aa_cpu_deviation'] * 100:.3f}%. "
        'These descriptive deviations are not confidence intervals; a median of paired ratios can '
        'differ from a ratio of separate arm medians.', '',
        '| Edit | Baseline wall s | Candidate wall s | Duplicate wall s | B/A wall | A′/A wall | B/A CPU | A′/A CPU |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for p in s['pairs']:
        lines.append(f"| {p['index'] - 2}: {p['label']} | {p['baseline_seconds']:.6f} | "
            f"{p['candidate_seconds']:.6f} | {p['duplicate_seconds']:.6f} | {p['wall_ratio']:.6f} | "
            f"{p['aa_wall_ratio']:.6f} | {p['cpu_ratio']:.6f} | {p['aa_cpu_ratio']:.6f} |")
    lines += ['', '| Edit | Baseline CPU s | Candidate CPU s | Duplicate CPU s |',
              '| --- | ---: | ---: | ---: |']
    for p in s['pairs']:
        lines.append(f"| {p['index'] - 2} | {p['baseline_cpu_seconds']:.6f} | "
                     f"{p['candidate_cpu_seconds']:.6f} | {p['duplicate_cpu_seconds']:.6f} |")
    lines += ['', 'Complete wall time surrounds the launcher, Cargo, VM, all original selected tests '
        'and process-receipt I/O. CPU is waited-for child user plus system time; concurrent compilers '
        'can make it exceed elapsed time. Nested launcher/Cargo stages are preserved separately and '
        'are not added to complete-command wall time.', '',
        '| Arm | Initial empty-target wall s | CPU s | All nine commands wall s |',
        '| --- | ---: | ---: | ---: |']
    for r in s['cold']:
        lines.append(f"| {r['mode']} | {r['seconds']:.6f} | {r['cpu']['total_seconds']:.6f} | "
                     f"{s['whole_session_command_seconds'][r['mode']]:.6f} |")
    lines += ['', 'Each arm starts with a separate empty target/cache history. Installed-tool and '
        'standard-library setup are outside these commands. The single cold observation per arm '
        'ran in baseline/candidate/duplicate order; it does not establish a repeatable cold-build '
        'speedup or regression.', '',
        'All 27 commands were validated. Each arm ran the same 14 original tests through the original '
        'source, a deliberate wrong production edit, compiled recovery, five fresh cumulative '
        'production edits and compiled final restoration. The wrong edit produced matching test '
        'failures in all arms; every other state passed all 14 tests. Executed bytecode, entry catalogs '
        'and program outputs matched across all three arms in every state. The original source was '
        'restored. All five valid edited source hashes were new within every arm’s cache history. '
        'These previously exposed Nushell edits are not fresh-project holdouts.', '',
        'The candidate omits wrapper-added full MIR encoding only for unselected native host libraries '
        'in complete standard-library MIR context with an unambiguous link emission and no target or '
        'response-file arguments. Explicit user flags, selected guest export and metadata-only policy '
        'are preserved. Query-cache retention is not enabled in this screen. The installed capability '
        'and distinct exporter/wrapper hashes identify the candidate; these launcher logs contain no '
        'per-compiler host-omission counters, so no count of omitted MIR bodies is inferred from them. '
        'Cargo can replay saved compiler stderr for fresh units.', '',
        'The separate [correctness qualification](../native-host-mir-build-01/assessment.md) records '
        '91 Rust tests and four real compiler/Cargo histories. Its scope preserves ordinary native '
        'checking: metadata-only calls remain forced because otherwise uncalled constant-panic '
        'diagnostics can differ. Internal `rustc_force_inline` diagnostics in otherwise uninstantiated '
        'bodies may be forced only by legacy full MIR. This screen does not establish universal '
        'diagnostic-byte identity or justify adopting the prototype.', '',
        f"Baseline/duplicate tool: `{s['tools']['baseline']}`. Candidate: `{s['tools']['candidate']}`. "
        f"The VM bytes are identical. Nushell revision: `{s['revision']}`; Cargo jobs: {s['cargo_jobs']}; "
        f"suite workers: {s['suite_workers']}. Compiler profiles and guest flags were not reduced. "
        'The candidate was built with release debug level 1, as recorded in its frozen composition.', '',
        '[summary.json](summary.json) contains all five pairs, all 27 command summaries, cold costs, '
        'source-state and artifact hashes, tool/compiler/sysroot identities and control outcomes. '
        '[evidence.json.gz](evidence.json.gz) retains exact plan, records, original summary, receipts, '
        'suites, transitions, small artifact sidecars, frozen harness/protocol/tool provenance, the '
        'original `ty.rs` with all assertions, and all nine reconstructed source states. The complete '
        'original project hash inventory and symlink identities are retained alongside the immutable '
        'Git revision; the other original Nushell files are not duplicated. All frozen inputs and '
        'retained artifact hashes were verified during initial packaging, and every archive member '
        'and deterministic gzip round trip was checked. Executable binaries, bytecode and caches '
        'remain in `.work`.', '',
        'Repackage from saved source/harness snapshots after the working checkout changes, without '
        'restoring or editing that checkout:', '', '```sh',
        'python3 benchmarks/experiments/strict-warm-build/assess_host_screen.py \\',
        f"  {s['raw']} --run-id strict-warm-host-mir-screen-01-reproduced \\",
        '  --snapshots-from results/strict-warm-host-mir-screen-01/summary.json', '```', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--snapshots-from', type=Path,
                        help='previous result summary with a verified exact source/harness archive')
    args = parser.parse_args()
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid run ID')
    raw = args.raw.resolve(strict=True)
    require(raw.is_relative_to(ROOT / '.work'), 'input escapes owned workspace')
    files = {str(raw / name): member(raw / name) for name in
             ['plan.json', 'records.json', 'summary.json', 'transitions.json']}
    plan, rows, original_summary, transitions = [json.loads(files[str(raw / n)]['utf8'])
        for n in ['plan.json', 'records.json', 'summary.json', 'transitions.json']]
    require(original_summary['records_sha256'] ==
            '298c1e43c7a2dbee8383dde4af000946320a1a078ed7c993126552810bec0e73',
            'assessment applies only to host-MIR screen 01; assess a new experiment separately')
    require(plan['owner'] == str(ROOT) and plan['kind'] == 'mechanism-screen' and
            plan['final_qualification'] is False and original_summary['source_restored'] is True and
            plan['candidate_policy'] == original_summary['candidate_policy'] == 'native-host-mir',
            'expected completed owned mechanism screen')
    prior_files, prior_summary = {}, None
    if args.snapshots_from:
        previous_result = args.snapshots_from.resolve(strict=True)
        prior_summary = json.loads(previous_result.read_bytes())
        prior_archive = previous_result.parent / prior_summary['archive']['path']
        require(identity(prior_archive)['sha256'] == prior_summary['archive']['sha256'] and
                prior_summary['frozen_inventory_verified'] is True and
                prior_summary['plan_sha256'] == original_summary['plan_sha256'] and
                prior_summary['records_sha256'] == original_summary['records_sha256'],
                'prior snapshots do not identify this verified screen')
        prior_bundle = json.loads(gzip.decompress(prior_archive.read_bytes()))
        for item in prior_bundle['files']:
            data = item['utf8'].encode()
            require(len(data) == item['bytes'] and sha(data) == item['sha256'], 'prior archive member differs')
            prior_files[item['path']] = item
        require(prior_files[str(raw / 'plan.json')]['sha256'] == original_summary['plan_sha256'] and
                prior_files[str(raw / 'records.json')]['sha256'] == original_summary['records_sha256'],
                'prior archived plan or records differ')

    def snapshot(path):
        path = str(path)
        return prior_files[path] if args.snapshots_from else member(Path(path))

    def frozen_snapshot(path):
        item = snapshot(path)
        require(sha(b'file\0' + item['utf8'].encode()) == plan['frozen'][str(path)],
                'frozen snapshot differs: ' + str(path))
        files[str(path)] = item
        return item

    if not args.snapshots_from:
        require(all(frozen_input_hash(p) == digest for p, digest in plan['frozen'].items()),
                'frozen source/tool/harness differs; use an existing verified snapshot for repackaging')
    for name in ['plan', 'records']:
        require(files[str(raw / (name + '.json'))]['sha256'] == original_summary[name + '_sha256'],
                'screen source hash differs')
    calculated = assess_rows(rows)
    require(all(original_summary[k] == v for k, v in calculated.items()), 'saved screen assessment differs')
    source_file = Path(plan['source']) / plan['case']['file']
    source_member = snapshot(source_file)
    source_bytes = source_member['utf8'].encode()
    require(sha(source_bytes) == plan['original_source_sha256'], 'source is not restored')
    files[str(source_file)] = source_member
    expected_states = protocol_states(source_bytes, plan['case'])
    expected_plan = [{k: v for k, v in state.items() if k != 'source'} |
                     dict(source_sha256=sha(state['source'])) for state in expected_states]
    require(expected_plan == plan['states'], 'saved source sequence differs from original edits')
    for state in expected_states:
        path = str(source_file) + '#state=' + str(state['index'])
        files[path] = dict(path=path, bytes=len(state['source']), sha256=sha(state['source']),
                           utf8=state['source'].decode(), reconstructed_from='original source and exact plan edits')
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
                'query_cache_retention' not in row['launch'],
                'launcher evidence differs')
        settings = launch_settings(mode, plan['tools'][mode], plan['candidate_policy'])
        require(all(row['launch'].get(k) == v for k, v in settings.items()) and
                '--query-cache-retention' not in row['command'] and
                row['launch']['compiler_wrapper']['sha256'] == plan['binaries'][mode]['rust-interp-rustc-wrapper']
                and 'Checking ' + plan['case']['package'] in row['stderr'] and
                sum(l.startswith('rust-interp-export: ') for l in row['stderr'].splitlines()) == 1,
                'compiler policy or selected fresh export evidence differs')
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
            frozen_snapshot(p)
            provenance.append({k: files[str(p)][k] for k in ['path', 'bytes', 'sha256']})
    for p in [Path(__file__).with_name('screen.py'), Path(__file__).with_name('PROTOCOL.md'),
              Path(plan['source']) / '.rust-interp-owned.json', Path(plan['std_mir']['path'])]:
        frozen_snapshot(p)
    for path in plan['frozen']:
        if Path(path).parent == ROOT / 'scripts' or path == str(ROOT / 'benchmarks/corpus.json'):
            frozen_snapshot(path)
    # Preserve the complete hash inventory in the exact plan, and spell out
    # symlink identity without copying or following directory/link fixtures.
    source_symlinks = prior_summary['source_symlinks'] if prior_summary else [
        dict(path=p, target=os.readlink(p), frozen_sha256=digest)
        for p, digest in plan['frozen'].items() if Path(p).is_symlink()]
    for link in source_symlinks:
        require(sha(b'symlink\0' + os.fsencode(link['target'])) ==
                plan['frozen'][link['path']] == link['frozen_sha256'], 'symlink inventory differs')
    for p in [Path(__file__).resolve(), Path(__file__).with_name('analyzer.py'),
              Path(__file__).with_name('assess.py')]:
        files[str(p)] = member(p)
    candidate_source = json.loads(files[str(ROOT / '.work/interpreter-tools' /
        plan['tools']['candidate'] / 'source.json')]['utf8'])
    composition = candidate_source['composition']
    require(sha(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()) ==
            plan['tools']['candidate'] and composition['binaries'] == plan['binaries']['candidate']
            and composition['build_environment']['CARGO_PROFILE_RELEASE_DEBUG'] == '1' and
            composition['compiler'] == plan['std_mir']['compiler'], 'candidate composition differs')
    bundle = dict(schema_version=1, encoding='exact UTF-8 members', files=list(files.values()),
                  source_symlinks=source_symlinks)
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
        artifact_inventory=list(artifacts.values()),
        tool_provenance=provenance, source_inventory_entries=len(plan['frozen']),
        archive=dict(path='evidence.json.gz', bytes=len(archive), sha256=sha(archive), gzip_mtime=0,
                     uncompressed_sha256=sha(payload), members=len(files), all_member_hashes_verified=True),
        packager_sha256=sha(Path(__file__).read_bytes()), source_restoration_rechecked=not bool(prior_summary),
        frozen_inventory_verified=True, frozen_inventory_verified_against_current_files=not bool(prior_summary),
        source_snapshot_fallback=identity(args.snapshots_from.resolve()) if prior_summary else None,
        source_symlinks=source_symlinks, archived_source_states=len(expected_states),
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
