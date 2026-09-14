"""Close the scalar Call primary and derive stage observations from its records."""
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import screen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write
from suite_reports import validate_report

RUN = 'scalar-store-log-screen-token-01'


def read(path):
    return json.loads(path.read_text())


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 10)
        out = ROOT / 'results' / RUN
        assert not (out / 'closure.json').exists()
        result = read(out / 'summary.json')
        work = ROOT / result['raw']
        evidence, bindings, artifacts = {}, {}, {}

        def retain(path, expected=None):
            digest = sha(path)
            if expected is not None:
                assert digest == expected, path
            evidence[str(path.relative_to(ROOT))] = digest
            return digest

        for key in ['plan', 'records', 'transitions', 'space']:
            retain(work / (key + '.json'), result[key + '_sha256'])
        plan, rows = read(work / 'plan.json'), read(work / 'records.json')
        assert plan['owner'] == str(ROOT)
        revision=plan['source_revision']
        assert result['commands'] == len(rows) == 40
        assert all(result[k] is True for k in ['source_restored', 'test_source_unchanged',
            'native_assertion_outcomes_match', 'candidate_control_bytecode_matches'])
        assert all(result[k] == v for k, v in screen.assessment(rows).items())
        assert type(result['gate_passed']) is bool
        for path, digest in plan['frozen'].items():
            retain(ROOT / path, digest)
            if not path.startswith(('.work/', 'results/')):
                spec = revision + ':' + path
                assert hashlib.sha256(subprocess.check_output(['git', 'show', spec], cwd=ROOT)).hexdigest() == digest
                bindings[path] = dict(sha256=digest, git_source=spec)
        build = read(ROOT / 'results/scalar-store-log-build-01/summary.json')
        profile = read(ROOT / 'results/scalar-store-log-profile-01/summary.json')
        assert screen.validate_matched_profile(build, profile)
        assert result['tool_keys']['candidate'] == build['tool_key']
        assert result['tool_keys']['baseline'] == result['tool_keys']['duplicate'] == build['matched_control']['tool_key']
        suites = {}
        for index, state in enumerate(plan['schedule']):
            group = rows[index * 5:index * 5 + 5]
            assert [r['mode'] for r in group] == state['modes']
            assert all((r['cycle'], r['state'], r['source_sha256']) ==
                (state['cycle'], state['state'], state['source_sha256']) for r in group)
            assert len({json.dumps(r['outcomes']) for r in group}) == 1
            for kind in ['artifact', 'catalog']:
                assert len({r[kind]['sha256'] for r in group if r['mode'] in screen.CACHED}) == 1
        for row in rows:
            success = row['state'] != -1
            assert (row['returncode'] == 0) == success
            if row['mode'] == 'native':
                assert row['outcomes'] == [list(x) for x in screen.native_outcomes(row['stdout'], plan['names'], success)]
            else:
                command = row['command']
                path = Path(command[command.index('--suite-report') + 1])
                retain(path, row['suite_sha256'])
                suite = read(path)
                suites[row['cycle'], row['state'], row['mode']] = suite
                assert row['outcomes'] == [list(x) for x in sorted(validate_report(suite, plan['names'], 'prepared', success))]
                assert row['launch']['tool_key'] == result['tool_keys'][row['mode']]
                assert row['launch'].get('jit_scalar_calls', False) == (row['mode'] in screen.CACHED)
                assert ('--jit-scalar-calls' in command) == (row['mode'] in screen.CACHED)
            for kind in ['artifact', 'catalog', 'entry_catalog', 'selection', 'native_executable', 'cargo_timing']:
                if kind in row:
                    item = row[kind]
                    artifacts[item['path']] = retain(ROOT / item['path'], item['sha256'])
        source = ROOT / '.work/sources/fre'
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == plan['revision']
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        retain(source / plan['case']['file'], plan['original_source_sha256'])
        outer = ROOT / '.work/experiments' / RUN
        terminal = read(outer / 'status.json')
        assert terminal['owner'] == terminal['cwd'] == str(ROOT)
        assert terminal['status'] == 'finished' and terminal['returncode'] == 0
        retain(outer / 'plan.json', terminal['plan_sha256'])
        retain(outer / 'command.log', terminal['log_sha256'])
        (out / 'terminal.json').write_bytes((outer / 'status.json').read_bytes())
        retain(out / 'terminal.json')
        for name in ['scalar-store-log-full-01', 'scalar-store-log-real-controls-01']:
            assert not (ROOT / '.work' / name).exists()
            assert not (ROOT / '.work/experiments' / name).exists()
        stages = {}
        for field in ['cargo_seconds', 'build_to_ready_seconds', 'execution_seconds']:
            pairs = []
            for state in range(1, 6):
                mode = {r['mode']: r for r in rows if r['cycle'] == 0 and r['state'] == state}
                a, b = mode['baseline']['launch'][field], mode['candidate']['launch'][field]
                pairs.append(dict(state=state, baseline=a, candidate=b, delta=b-a, ratio=b/a))
            stages[field] = dict(pairs=pairs, median_delta=statistics.median(p['delta'] for p in pairs),
                median_ratio=statistics.median(p['ratio'] for p in pairs))
        bodies = {}
        for name in plan['names']:
            pairs = []
            for state in range(1, 6):
                times = {}
                for mode in ['baseline', 'candidate']:
                    test, = [t for t in suites[0, state, mode]['tests'] if t['name'] == name]
                    times[mode] = test['seconds']
                pairs.append(dict(state=state, **times, delta=times['candidate']-times['baseline']))
            bodies[name] = dict(pairs=pairs, median_delta=statistics.median(p['delta'] for p in pairs))
        write(out / 'stage-observations.json', dict(source_records_sha256=result['records_sha256'],
            stages=stages, tests=bodies, new_commands=0,
            scope='Descriptive paired observations only. Nested stages and overlapping test durations are not additive; no causal attribution or new performance gate.'))
        write(work / 'source-bindings.json', dict(files=bindings, historical_revision=revision))
        retain(out / 'summary.json')
        retain(out / 'stage-observations.json')
        write(work / 'closure-evidence.json',evidence)
        write(out / 'closure.json', dict(status='passed', performance_gate_passed=result['gate_passed'], parked=not result['gate_passed'],
            repeated_screen_commands=0, full_comparison_commands=0, held_out_commands=0,
            frozen_input_references=len(plan['frozen']), source_bindings=len(bindings),
            retained_artifacts_verified=len(artifacts), source_bindings_path=str((work/'source-bindings.json').relative_to(ROOT)),source_bindings_sha256=sha(work / 'source-bindings.json'),
            evidence_path=str((work/'closure-evidence.json').relative_to(ROOT)),evidence_sha256=sha(work/'closure-evidence.json'),evidence_files=len(evidence), auditor_sha256=sha(Path(__file__))))
        print('Closed scalar primary:', len(evidence), 'evidence files;', len(artifacts), 'artifacts')
        print(json.dumps({k: {n: v for n, v in row.items() if n != 'pairs'} for k, row in stages.items()}))


if __name__ == '__main__':
    main()
