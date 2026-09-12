#!/usr/bin/env python3
"""Bind fresh profiles to completed original-test artifacts and actual processes."""
from collections import Counter
import fcntl
import json
from pathlib import Path
import runpy
import sys

from build_relocation import ROOT, HERE, read, write, sha, require
from check_comparison import expected_tools
import summarize_owned_sample as summary
import attribute_generated_sample as generated


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        qualification = ROOT/'results/aggregate-relocation-heldout-recovery-01/summary.json'
        q = read(qualification)
        require(q['status'] == 'all seven histories verified' and q['heldout_gates_passed'] and
                len(q['cases']) == 7 and all(sha(ROOT/p) == h for p, h in q['evidence'].items()),
                'complete held-out qualification changed')
        tool = expected_tools()['candidate']
        for label, workflow, seconds in [('folded', 'folded-literal-trie', 1), ('token', 'token-phrase', 3)]:
            run = 'aggregate-relocation-'+label+'-sample-01'
            work, out = ROOT/'.work'/run, ROOT/'results'/run
            experiment = ROOT/'.work/experiments'/run
            launch, supervisor = (read(experiment/n) for n in ['plan.json', 'status.json'])
            plan, execution = (read(work/n) for n in ['plan.json', 'summary.json'])
            primary = ROOT/'.work/runs'/('aggregate-relocation-e2e-01-'+workflow)/'records.json'
            originals = [r for r in read(primary) if r['cycle'] == 0 and r['state'] == 0 and r['mode'] == 'candidate']
            require(len(originals) == 1 and len(originals[0]['artifacts']) == 1, 'ambiguous original artifact')
            artifact = originals[0]['artifacts'][0]
            expected = ['scripts/sample_owned_vm.py', '--run-id', run, '--tool-key', tool['tool_key'],
                '--artifact', artifact['path'], '--artifact-sha256', artifact['sha256'], '--duration', str(seconds),
                '--jit-resumable-calls', '--jit-persistent-registers', '--dump-code']
            require(supervisor['status'] == 'finished' and supervisor['returncode'] == 0 and
                    supervisor['owner'] == supervisor['cwd'] == launch['owner'] == str(ROOT) and
                    supervisor['command'] == launch['command'] and supervisor['command'][1:] == expected and
                    supervisor['plan_sha256'] == sha(experiment/'plan.json') and
                    supervisor['log_sha256'] == sha(experiment/'command.log'), 'sample supervisor differs')
            require(plan['artifact'] == str(ROOT/artifact['path']) and
                    plan['artifact_sha256'] == execution['artifact_sha256'] == sha(ROOT/artifact['path']) == artifact['sha256'] and
                    plan['tool_key'] == execution['tool_key'] == tool['tool_key'] and
                    plan['vm_sha256'] == execution['vm_sha256'] == tool['vm_sha256'] and
                    plan['repetitions'] == 3 and plan['sample_seconds'] == seconds and plan['dump_code'] and
                    len(execution['records']) == 3 and execution['source_unchanged'] and
                    not execution['performance_measurement'], 'profile inputs differ')
            # Existing public analyzers remain unchanged; a previously analyzed
            # profile is independently recomputed below, never overwritten.
            saved_argv = sys.argv
            try:
                for script, destination in [('summarize_owned_sample.py', out/'summary.json'),
                                             ('attribute_generated_sample.py', out/'generated-attribution.json')]:
                    if not destination.exists():
                        sys.argv = [script, '--run-id', run]
                        runpy.run_path(str(ROOT/'scripts'/script), run_name='__main__')
            finally:
                sys.argv = saved_argv
            report, attribution = read(out/'summary.json'), read(out/'generated-attribution.json')
            counts, classes = Counter(), Counter()
            evidence = {str(qualification.relative_to(ROOT)): sha(qualification), str(primary.relative_to(ROOT)): sha(primary),
                        artifact['path']: artifact['sha256']}
            for index, row in enumerate(execution['records']):
                identity = row['identity']
                require(row['index'] == index and identity['parent_pid'] == supervisor['child_pid'] and
                        identity['cwd'] == str(ROOT) and
                        supervisor['started_at'] <= identity['started_at'] <= identity['finished_at'] <= supervisor['finished_at'],
                        'VM process identity or timestamps differ')
                command = identity['command']
                require(command == [str(ROOT/'.work/interpreter-tools'/tool['tool_key']/'rust-interp-vm'),
                    '--engine', 'jit', '--instruction-limit', '100000000000', '--allocation-limit', '150000',
                    '--jit-persistent-registers', '--jit-resumable-calls', '--jit-code-dump',
                    str(work/str(index)/'jit-code'), str(ROOT/artifact['path'])], 'actual VM command differs')
                recomputed = summary.summarize(work/str(index))
                require(json.loads(json.dumps(recomputed)) == report['samples'][index], 'recorded sample summary differs')
                recomputed_code = generated.attribute(work/str(index), recomputed)
                require(json.loads(json.dumps(recomputed_code)) == attribution['samples'][index], 'recorded code attribution differs')
                counts.update(recomputed['disjoint_counts'])
                classes.update(recomputed_code['by_instruction_class'])
                for path, digest in recomputed['evidence'].items():
                    evidence[path] = digest
            require(dict(counts) == report['disjoint_counts'] and sum(counts.values()) == report['total_samples'] and
                    dict(classes) == attribution['by_instruction_class'] and
                    sum(classes.values()) == attribution['attributed_generated_samples'] == counts['generated_code'],
                    'aggregate sample totals differ')
            for directory, names in [(experiment, ['plan.json', 'status.json', 'command.log']),
                    (work, ['plan.json', 'summary.json']), (out, ['summary.json', 'generated-attribution.json'])]:
                for name in names:
                    path = directory/name
                    evidence[str(path.relative_to(ROOT))] = sha(path)
            for path in [Path(__file__), HERE/'PROFILE-NEXT.md', ROOT/'scripts/summarize_owned_sample.py',
                         ROOT/'scripts/attribute_generated_sample.py']:
                evidence[str(path.relative_to(ROOT))] = sha(path)
            provenance = out/'execution-provenance.json'
            require(not provenance.exists(), 'profile assessment already exists')
            write(provenance, dict(status='verified', profiled_executions=3, original_artifact=artifact,
                original_run='aggregate-relocation-e2e-01-'+workflow, exact_code_attribution=True,
                signals_sent=False, performance_measurement=False, evidence=evidence))
            zero = sum(classes.get(k, 0) for k in ['native_zero_bulk', 'native_zero_range'])
            (out/'assessment.md').write_text(f'# Aggregate relocation: {label} execution profile\n\n'
                f'Three original-test executions verify with immutable VM {tool["vm_sha256"][:8]} and '
                f'tool {tool["tool_key"][:8]}. All {counts["generated_code"]:,} generated-code self samples '
                f'bind to their own emitted instructions; {sum(counts.values()):,} thread samples were captured. '
                f'Generated clearing accounts for {100*zero/sum(counts.values()):.2f}% of captured self samples.\n\n'
                'The artifact is the exact original-source candidate from the completed primary comparison. '
                'Original assertions, RNG, instruction/allocation limits and runtime options remain unchanged. '
                'Every VM and diagnostic child finished naturally. Captures are partial and perturbed; '
                'sample shares are not latency measurements or predictions of savings. Unclassified generated '
                'instructions remain grouped, and source integration remains a separate task.\n')
            print(dict(case=label, samples=sum(counts.values()), clearing_percent=100*zero/sum(counts.values())))


if __name__ == '__main__':
    main()
