#!/usr/bin/env python3
"""Validate and package saved Cargo traces; never start a compiler or workload."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
import re

from analyzer import compressed, identity, member
from assess import ROOT, require, sha, verify_state


def union_us(intervals):
    total, end = 0.0, float('-inf')
    for begin, finish in sorted(intervals):
        require(finish >= begin, 'negative interval')
        total += max(0.0, finish - max(begin, end))
        end = max(end, finish)
    return total


def parse_trace(events):
    """Match B/E on each synthetic trace thread, retaining exact event indices."""
    stacks, spans, phases = defaultdict(list), [], Counter()
    for index, event in enumerate(events):
        phase = event['ph']
        phases[phase] += 1
        if phase not in ['B', 'E']:
            require(phase in ['i', 'M'], 'unsupported trace phase')
            continue
        stack = stacks[event['pid'], event['tid']]
        if phase == 'B':
            stack.append(dict(begin=event, begin_index=index, children=[]))
            continue
        require(stack, 'unmatched trace end')
        node = stack.pop()
        begin = node.pop('begin')
        require(all(begin.get(k) == event.get(k) for k in ['cat', 'name', '.file', '.line']),
                'mismatched trace span')
        duration = event['ts'] - begin['ts']
        self_time = duration - sum(b - a for a, b in node['children'])
        require(duration >= 0 and self_time >= -0.001, 'invalid elapsed span')
        node.update(cat=begin['cat'], name=begin['name'], pid=begin['pid'], tid=begin['tid'],
                    start_us=begin['ts'], end_us=event['ts'], inclusive_us=duration,
                    self_us=max(0, self_time), end_index=index, source_file=begin.get('.file'),
                    source_line=begin.get('.line'))
        spans.append(node)
        if stack:
            stack[-1]['children'].append((begin['ts'], event['ts']))
    require(all(not stack for stack in stacks.values()) and phases['B'] == phases['E'] == len(spans),
            'incomplete trace spans')
    aggregate = {}
    for span in spans:
        key = span['cat'], span['name']
        row = aggregate.setdefault(key, dict(cat=key[0], name=key[1], count=0, inclusive_us=0.0, self_us=0.0))
        row['count'] += 1
        row['inclusive_us'] += span['inclusive_us']
        row['self_us'] += span['self_us']
    return spans, [aggregate[k] for k in sorted(aggregate)], dict(phases)


def trace_summary(events, saved):
    spans, aggregate, phases = parse_trace(events)
    require(saved['events'] == len(events) and saved['span_count'] == len(spans),
            'saved trace count differs')
    require(len(aggregate) == len(saved['aggregate']), 'saved aggregation cardinality differs')
    by_key = {(r['cat'], r['name']): r for r in saved['aggregate']}
    for row in aggregate:
        prior = by_key[row['cat'], row['name']]
        require(row['count'] == prior['count'] and all(math.isclose(row[k], prior[k], abs_tol=0.001)
                for k in ['inclusive_us', 'self_us']), 'saved elapsed aggregation differs')
    def matching(cat, name):
        return [s for s in spans if s['cat'] == cat and s['name'] == name]
    main, = matching('cargo::cli', 'main')
    queue, = matching('cargo::compiler::job_queue', 'execute')
    rustc = matching('cargo::compiler', 'rustc')
    workers = [s for s in rustc if s['tid'] != main['tid']]
    versions = sorted(matching('cargo::util::rustc', 'new'), key=lambda s: s['start_us'])
    target_info = matching('cargo::compiler::build_context::target_info', 'new')
    first_worker = min(s['start_us'] for s in workers)
    startup = defaultdict(float)
    for s in spans:
        if s['tid'] != main['tid']:
            continue
        overlap = lambda a, b: max(0, min(b, queue['start_us']) - max(a, main['start_us']))
        own = overlap(s['start_us'], s['end_us']) - sum(overlap(a, b) for a, b in s['children'])
        require(own >= -0.001, 'invalid clipped self interval')
        startup[s['cat'], s['name']] += max(0, own)
    selected = [s for s in spans if (s['cat'], s['name']) in {
        ('cargo::cli', 'main'), ('cargo::compiler::job_queue', 'execute'),
        ('cargo::ops::cargo_compile', 'create_bcx'), ('cargo::compiler::build_runner', 'compile'),
        ('cargo::util::rustc', 'new'), ('cargo::compiler::build_context::target_info', 'new'),
        ('cargo::resolver', 'resolve'), ('cargo::workspace::package', 'download_accessible')}]
    compact = lambda s: {k: v for k, v in s.items() if k != 'children'}
    compiler_scope_union = union_us([(s['start_us'], s['end_us']) for s in versions + target_info])
    return dict(event_count=len(events), span_count=len(spans), phase_counts=phases,
        trace_pid_values=sorted({s['pid'] for s in spans}), main_thread=main['tid'],
        thread_count=len({e['tid'] for e in events}), aggregate=aggregate,
        cargo_main_seconds=main['inclusive_us'] / 1e6,
        main_before_job_queue_seconds=(queue['start_us'] - main['start_us']) / 1e6,
        first_worker_trace_seconds=first_worker / 1e6,
        queue_elapsed_seconds=queue['inclusive_us'] / 1e6,
        rustc_span_count=len(rustc), rustc_main_thread_spans=len(rustc) - len(workers),
        rustc_worker_spans=len(workers), rustc_worker_span_union_seconds=union_us(
            [(s['start_us'], s['end_us']) for s in workers]) / 1e6,
        compiler_info_scope_union_seconds=compiler_scope_union / 1e6,
        rustc_new_seconds=sum(s['inclusive_us'] for s in versions) / 1e6,
        two_later_rustc_new_seconds=sum(s['inclusive_us'] for s in versions[1:]) / 1e6,
        startup_self_span_seconds=[dict(cat=c, name=n, seconds=t / 1e6)
            for (c, n), t in sorted(startup.items(), key=lambda row: -row[1]) if t > 0],
        selected_spans=[compact(s) for s in sorted(selected, key=lambda s: s['start_us'])])


def markdown(s):
    edited, restored = s['states']
    e, r = edited['trace'], restored['trace']
    lines = ['# Cargo setup diagnosis, continuation 03', '',
        'The trace identifies a concrete compiler-info cache failure, but setup memoization alone '
        'does not account for the gap to 0.5 s. Cargo reports that its compiler fingerprint fails '
        'on an empty workspace-wrapper path, disables its existing rustc-info cache, and executes '
        'all five information probes again. The normal launcher also exports an empty workspace '
        'wrapper, so this observation has production relevance beyond the diagnostic wrapper.', '',
        '| State | Cargo wall s | Cargo child CPU s | VM wall s | rustc phase logging | Original tests |',
        '| --- | ---: | ---: | ---: | --- | --- |']
    for row in s['states']:
        lines.append(f"| {row['state']} | {row['cargo_seconds']:.6f} | {row['cargo_child_cpu_seconds']:.6f} | "
                     f"{row['vm_seconds']:.6f} | {row['rustc_phase_logging']} | 14 passed |")
    lines += ['', 'Both commands include Cargo Chrome tracing, rustc-info debug logging, `-vv`, Cargo '
        'HTML timings, exporter timers and the Python diagnostic wrapper with process receipts. Only '
        'the edited command adds rustc phase logging. The source and cache states differ, so subtracting '
        'restoration from edited time does not estimate profiler overhead. These direct Cargo/VM '
        'observations exclude normal launcher startup and setup and do not establish a normal '
        'startup floor or a speedup.', '',
        f"This is fresh edit {s['edit_index']} relative to the recorded diagnostic target history, "
        'continuing [self-profile 02](../strict-warm-self-profile-02/assessment.md) and its existing '
        'profile-01 target. No new cold prime was run. This is not an independent cold history, '
        'a new-project holdout, or acceptance evidence.', '',
        '| Elapsed scope | Edited s | Restored s | Interpretation |',
        '| --- | ---: | ---: | --- |',
        f"| Cargo main before job queue | {e['main_before_job_queue_seconds']:.6f} | "
        f"{r['main_before_job_queue_seconds']:.6f} | Same-thread elapsed prefix; excludes later scheduling and replay |",
        f"| First compilation wrapper from parent Cargo start | {edited['first_compilation_wrapper_seconds']:.6f} | "
        f"{restored['first_compilation_wrapper_seconds']:.6f} | Process receipts; includes instrumentation/startup |",
        f"| Compiler-info setup interval union | {e['compiler_info_scope_union_seconds']:.6f} | "
        f"{r['compiler_info_scope_union_seconds']:.6f} | Three Rustc::new scopes plus nested target-info scopes, overlap removed |",
        f"| Three Rustc::new scopes | {e['rustc_new_seconds']:.6f} | {r['rustc_new_seconds']:.6f} | Includes -vV waits and wrapper overhead |",
        f"| Five probe child intervals | {edited['probe_child_seconds']:.6f} | {restored['probe_child_seconds']:.6f} | Wrapper waits for child, not CPU |",
        f"| Job queue execute | {e['queue_elapsed_seconds']:.6f} | {r['queue_elapsed_seconds']:.6f} | Includes waiting for concurrent compiler/build-script work |", '',
        'Rows overlap and must not be added. In particular, the job-queue span is not several seconds '
        'of Cargo CPU. Same-thread self elapsed time subtracts directly nested spans; it can still '
        'include blocking and waiting. Sums across threads can exceed command wall time. The '
        'separately recorded Cargo child CPU above includes descendants and is not a Cargo-only '
        'CPU measurement.', '',
        'Each trace has 30,451 matched spans and 213,171 events. Its 36 `rustc` spans consist of '
        '18 on the main thread and 18 on worker threads; these are span entries, not 36 compiler '
        'processes. Independent wrapper receipts identify 18 real compiler invocations and five '
        'information probes per state. Cargo HTML reports those 18 compiler units plus one '
        'build-script execution. Synthetic trace PID 1 and thread indices are not operating-system '
        'process identities. The selected test role is confirmed through exporter arguments and '
        'the selected Cargo artifact, since incoming wrapper arguments alone need not contain `--test`.', '',
        '## What can safely improve', '',
        'Both stderr logs contain three fingerprint failures naming the empty path, three cache-disabled '
        'messages, five cache misses and five actual query commands: three identical `-vV` calls, '
        'one host-information query and one explicit-target query. The captured environment has '
        '`RUSTC_WORKSPACE_WRAPPER=""`. The archived production launcher sets the same value.', '',
        'The concrete first candidate is Cargo-side normalization of the explicit empty workspace '
        'wrapper when constructing its compiler fingerprint, after configuration resolution, while '
        'preserving the meaning “disable the configured workspace wrapper.” Merely deleting the '
        'launcher environment value could activate a wrapper from Cargo configuration and change '
        'behavior. A fix should let Cargo’s existing cache retain its normal rustc/wrapper/target/flags '
        'invalidation. The trace identifies the failure path; this package contains no implementation '
        'or evidence that the proposed change restores hits.', '',
        f"The observed compiler-info interval union is {e['compiler_info_scope_union_seconds']:.3f}/"
        f"{r['compiler_info_scope_union_seconds']:.3f} s, or "
        f"{100 * r['compiler_info_scope_union_seconds'] / restored['cargo_seconds']:.1f}% of the restored "
        'instrumented command. Treat that entire scope as an optimistic removable-work budget, '
        'not a prediction: validation still costs time, and these scopes contain Python startup, '
        'receipt I/O and other diagnostic overhead absent from the production wrapper. Sharing '
        'duplicate in-process Rustc setup addresses only part of that budget. The two later '
        f"Rustc::new scopes total {e['two_later_rustc_new_seconds']:.3f}/"
        f"{r['two_later_rustc_new_seconds']:.3f} s here.", '',
        'Even eliminating the entire observed prefix before the first compilation wrapper, while '
        'holding subsequent work fixed, would leave '
        f"{edited['cargo_seconds'] - edited['first_compilation_wrapper_seconds']:.3f}/"
        f"{restored['cargo_seconds'] - restored['first_compilation_wrapper_seconds']:.3f} s of these "
        'commands. That arithmetic is an illustrative budget, not a latency forecast: a real change '
        'can alter scheduling and overlap. It shows why resolving this cache failure may give a '
        'useful small general improvement, while compiler and dependency work still needs much '
        'larger reductions for the target.', '',
        'Broader memoization of dependency resolution, manifest parsing and fingerprint planning '
        'would need to preserve Cargo configuration/environment changes, feature/target/profile '
        'selection, source and dependency freshness, build-script rerun rules and proc-macro '
        'recompilation. The trace does not establish those checks as safely removable. Recursively '
        'nested fingerprint spans especially must not be summed into an alleged saving.', '',
        '## Largest exclusive elapsed labels before the job queue', '',
        'These clipped same-thread values are descriptive elapsed attribution, not sampled CPU '
        'or a claim that a check can be omitted.', '',
        '| Category / span | Edited s | Restored s |', '| --- | ---: | ---: |']
    lookup = [{(x['cat'], x['name']): x['seconds'] for x in trace['startup_self_span_seconds']}
              for trace in [e, r]]
    keys = sorted(set(lookup[0]) | set(lookup[1]), key=lambda k: -max(d.get(k, 0) for d in lookup))[:10]
    for key in keys:
        lines.append(f"| `{key[0]}::{key[1]}` | {lookup[0].get(key, 0):.6f} | {lookup[1].get(key, 0):.6f} |")
    lines += ['', '## Evidence', '',
        '[summary.json](summary.json) contains exact identities, source/test validation, all actual '
        'compiler roles, probe receipts, recomputed trace aggregates and startup spans. '
        '[report.json.gz](report.json.gz) preserves the complete original diagnostic report. '
        '[evidence.json.gz](evidence.json.gz) preserves exact command/process receipts, stdout/stderr, '
        'suites, artifact sidecars, HTML timings, frozen harness/tool provenance and the original '
        'derived trace summaries. Both raw 60 MB Chrome traces are retained in separate deterministic '
        'gzip files named in the summary; each decompresses byte-for-byte to its recorded original '
        'SHA256. No raw trace events are sampled or discarded. The independent parser reconciles '
        'all B/E spans and aggregate counters with the saved summaries. Trace arguments were not '
        'captured; compiler argv is instead retained in the wrapper receipts.', '',
        f"Tool key: `{s['tool']['tool_key']}`. Pinned compiler: `{s['compiler']['version'].splitlines()[0]}`. "
        'Nushell and compiler/sysroot identities and the prior-report hash are in the JSON. Cargo '
        'has prior optimization exposure and is already excluded from fresh holdouts, as recorded '
        'in [CARGO_EXPOSURE.md](../../benchmarks/experiments/strict-warm-build/CARGO_EXPOSURE.md). '
        'No holdout workload was executed for this diagnosis.', '',
        'Repackage the saved evidence without executing a workload:', '', '```sh',
        'python3 benchmarks/experiments/strict-warm-build/assess_cargo_trace.py \\',
        f"  {s['source_report']['path']} \\",
        f"  --trace-run {s['trace_supervisor']['path']} \\",
        '  --run-id strict-warm-cargo-profile-03-reproduced', '```', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--trace-run', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid result run ID')
    report_path, supervisor_path = args.report.resolve(strict=True), args.trace_run.resolve(strict=True)
    require(all(p.is_relative_to(ROOT / '.work') for p in [report_path, supervisor_path]), 'unowned input')
    raw, trace_run = report_path.parent, supervisor_path.parent
    report, supervisor = [json.loads(p.read_bytes()) for p in [report_path, supervisor_path]]
    checks = ['source_restored', 'assertions_unchanged', 'tool_inputs_unchanged', 'scripts_unchanged',
              'std_mir_unchanged', 'previous_reports_unchanged']
    require(report['owner'] == supervisor['owner'] == str(ROOT) and
            report['status'] == supervisor['status'] == 'passed' and report['performance_measurement'] is False
            and all(report[k] is True for k in checks), 'expected passed owned diagnostic')
    require(report['profiling'] == 'passes' and report['edit_index'] == 3 and
            supervisor['trace_environment'] == {'CARGO_LOG_PROFILE': '1', 'CARGO_LOG': 'cargo::util::rustc=debug'},
            'unexpected instrumentation or edit')
    continuation = report['continuation']
    prior = Path(continuation['prior_report'])
    require(identity(prior)['sha256'] == continuation['prior_report_sha256'] and
            continuation['prime_skipped'] is True and
            report['edit_index'] > max(continuation['previously_compiled_edit_indices']) and
            report['edited_sha256'] not in continuation['previously_compiled_source_hashes'],
            'continuation freshness or prior report differs')
    receipt = json.loads((trace_run / 'profile-process.json').read_bytes())
    require(receipt['status'] == 'finished' and receipt['returncode'] == supervisor['returncode'] == 0 and
            receipt['command'] == supervisor['command'] and receipt['pid'] == supervisor['profile_pid'] ==
            report['supervisor_pid'] and receipt['parent_pid'] == supervisor['supervisor_pid'],
            'trace supervisor receipt differs')
    require([r['state'] for r in report['records']] == ['edited', 'restored'] and
            [r['source_sha256'] for r in report['records']] == [report['edited_sha256'], report['original_sha256']],
            'source history differs')
    files = [member(p) for p in sorted(trace_run.iterdir()) if p.is_file()]
    harness = []
    for path, digest in report['frozen_scripts'].items():
        item = member(ROOT / path)
        require(item['sha256'] == digest, 'frozen diagnostic harness differs: ' + path)
        files.append(item)
        harness.append({k: item[k] for k in ['path', 'bytes', 'sha256']})
    launcher = next(item for item in files if item['path'] == str(ROOT / 'scripts/interpreter.py'))
    require("RUSTC_WORKSPACE_WRAPPER=''" in launcher['utf8'], 'production empty-wrapper setting differs')
    tool_dir = Path(report['tool']['directory'])
    for name, key in [('capabilities.json', 'capabilities_sha256'), ('source.json', 'source_sha256')]:
        item = member(tool_dir / name)
        require(item['sha256'] == report['tool'][key], 'tool provenance differs')
        files.append(item)
    binary_identities = {n: identity(tool_dir / n) for n in report['tool']['binaries']}
    require(all(binary_identities[n]['sha256'] == h for n, h in report['tool']['binaries'].items()),
            'installed tool binary differs')
    source = Path(report['source']) / 'crates/nu-protocol/src/ty.rs'
    require(identity(source)['sha256'] == report['original_sha256'], 'original source is not restored')
    files += [member(source), member(Path(__file__).with_name('CARGO_EXPOSURE.md')),
              member(Path(__file__).resolve()), member(Path(__file__).with_name('assess.py')),
              member(Path(__file__).with_name('analyzer.py'))]
    states, compressed_traces = [], {}
    require(len(supervisor['traces']) == 2, 'trace inventory differs')
    for row in report['records']:
        verified = verify_state(row, raw, report['tests'])
        require(verified['compiler_unit_count'] == 18 and verified['information_probe_count'] == 5 and
                verified['build_script_run_count'] == 1 and verified['cargo_unit_count'] == 19,
                'compiler or Cargo unit inventory differs')
        selected_trace = []
        for candidate in supervisor['traces']:
            epoch_ns = int(Path(candidate['copy']).stem.split('-')[1]) * 1000
            if row['cargo']['started_unix_ns'] < epoch_ns < row['cargo']['finished_unix_ns']:
                selected_trace.append(candidate)
        require(len(selected_trace) == 1, 'trace creation does not unambiguously identify Cargo command')
        trace = selected_trace[0]
        trace_path = Path(trace['copy'])
        payload = trace_path.read_bytes()
        require(len(payload) == trace['bytes'] and sha(payload) == trace['sha256'], 'raw trace differs')
        events = json.loads(payload)
        saved_path = trace_path.with_name(trace_path.stem + '.summary.json')
        details = trace_summary(events, json.loads(saved_path.read_bytes()))
        packed = compressed(payload)
        archive_name = row['state'] + '-cargo-trace.json.gz'
        compressed_traces[archive_name] = packed
        details.update(raw=identity(trace_path), saved_summary=identity(saved_path), archive=dict(
            file=archive_name, bytes=len(packed), sha256=sha(packed), exact_round_trip_verified=True),
            actual_cargo_pid=row['cargo']['pid'], association='trace filename creation epoch is within unique Cargo process interval')
        files.append(member(saved_path))
        del events, payload
        directory = raw / row['state']
        files += [member(p) for p in sorted(directory.rglob('*')) if p.is_file() and p.suffix != '.rbc']
        probes = [c for c in row['compiler_invocations'] if not c['compilation']]
        require(all(c['environment']['RUSTC_WORKSPACE_WRAPPER'] == '' and not c['diagnostic_flags'] for c in probes),
                'information-probe instrumentation or wrapper setting differs')
        logs = [(i + 1, line) for i, line in enumerate((directory / 'cargo.stderr').read_text().splitlines())
                if 'cargo::util::rustc:' in line]
        counts = {name: sum(text in line for _, line in logs) for name, text in {
            'empty_path_fingerprint_failures': 'failed to load metadata for path ``',
            'cache_disabled': 'rustc info cache disabled', 'cache_misses': 'rustc info cache miss',
            'actual_probe_commands': 'cargo::util::rustc: running `',
            'cache_hits': 'rustc info cache hit'}.items()}
        require(counts == dict(empty_path_fingerprint_failures=3, cache_disabled=3,
                              cache_misses=5, actual_probe_commands=5, cache_hits=0), 'rustc-info log counts differ')
        require(sum(c['original_args'][1:] == ['-vV'] for c in probes) == 3, 'version probe count differs')
        compilers = [{k: c[k] for k in ['role', 'package', 'crate_name', 'target_context', 'explicit_targets',
            'crate_types', 'emissions', 'features', 'wrapper_pid', 'child_pid', 'compilation',
            'cargo_unit_ids', 'wrapper_child_elapsed_seconds', 'receipt_sha256', 'stderr_sha256']}
            for c in verified['compiler_invocations']]
        states.append(dict(state=row['state'], source_sha256=row['source_sha256'],
            cargo_seconds=row['cargo']['seconds'], vm_seconds=row['vm']['seconds'],
            cargo_child_cpu_seconds=row['cargo']['child_user_seconds'] + row['cargo']['child_system_seconds'],
            rustc_phase_logging=row['instrumented'], cargo_command=row['cargo'], vm_command=row['vm'],
            artifact=identity(directory / 'program.rbc'), test_outcomes=verified['test_outcomes'],
            suite_sha256=row['suite_sha256'], selected_cargo_event=row['selected_cargo_event'],
            compiler_units=compilers, cargo_timeline=row['cargo_timeline'],
            first_compilation_wrapper_seconds=(min(c['start_unix_ns'] for c in row['compiler_invocations']
                if c['compilation']) - row['cargo']['started_unix_ns']) / 1e9,
            probe_child_seconds=sum(c['elapsed_seconds'] for c in probes),
            probes=[{k: c[k] for k in ['wrapper_pid', 'child_pid', 'parent_pid', 'start_unix_ns',
                'finish_unix_ns', 'original_args', 'elapsed_seconds', 'record_path']} for c in probes],
            rustc_info_debug_counts=counts, rustc_info_debug_lines=[dict(line=i, text=t) for i, t in logs],
            trace=details))
    # Preserve original report separately, including every compiler phase event.
    report_archive = compressed(report_path.read_bytes())
    unique_files = {item['path']: item for item in files}
    evidence_payload = json.dumps(dict(schema_version=1, encoding='exact UTF-8 members',
        files=list(unique_files.values())), separators=(',', ':')).encode() + b'\n'
    evidence_archive = compressed(evidence_payload)
    for item in json.loads(gzip.decompress(evidence_archive))['files']:
        payload = item['utf8'].encode()
        require(len(payload) == item['bytes'] and sha(payload) == item['sha256'], 'archived evidence differs')
    summaries = dict(schema_version=1, status='passed', performance_measurement=False,
        adoption='no implementation or speed claim', source_report=identity(report_path),
        trace_supervisor=identity(supervisor_path), trace_environment=supervisor['trace_environment'],
        revision=report['revision'], edit_index=report['edit_index'], history_kind=report['history_kind'],
        continuation=continuation, source_restored=True, assertions_unchanged=True,
        tests=report['tests'], tool=report['tool'], tool_binary_identities=binary_identities,
        compiler=dict(version=report['compiler'], sysroot=report['compiler_sysroot'],
                      rustc=identity(Path(report['rustc_path'])),
                      cargo=identity(Path(report['rustc_path']).with_name('cargo'))),
        std_mir=dict(sysroot=report['std_mir_sysroot'], artifacts=report['std_mir_artifacts']),
        frozen_harness=harness, states=states,
        archives=[dict(file='report.json.gz', bytes=len(report_archive), sha256=sha(report_archive),
                       exact_round_trip_verified=True),
                  dict(file='evidence.json.gz', bytes=len(evidence_archive), sha256=sha(evidence_archive),
                       members=len(unique_files), all_member_hashes_verified=True, exact_round_trip_verified=True)])
    output = ROOT / 'results' / args.run_id
    output.mkdir(exist_ok=False)
    archives = dict(compressed_traces, **{'report.json.gz': report_archive, 'evidence.json.gz': evidence_archive})
    for name, archive in archives.items():
        (output / name).write_bytes(archive)
        require(identity(output / name)['sha256'] == sha(archive), 'written archive differs')
    (output / 'summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
    (output / 'assessment.md').write_text(markdown(summaries))
    print(json.dumps(dict(output=str(output), states=len(states), exact_members=len(unique_files),
                          archive_bytes={name: len(data) for name, data in archives.items()})))


if __name__ == '__main__':
    main()
