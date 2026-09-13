"""Compare bounded allocation observation across two fresh parser histories."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'pgrust-parser-probe'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'pgrust-parser-edits'))
from compare_saved_runtime import acquire_lock, sha
from probe import PIN, fingerprint
from states import source_states
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import SourceEdit, capture, require_space, write_json as write
from interpreter import installed_tools


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 14)
        run = 'parser-allocation-history-01'
        proof_path = ROOT / 'results/pgrust-parser-edits-incremental-01-failure/summary.json'
        proof = json.loads(proof_path.read_text())
        assert proof['commands'] == 22 and proof['source_restored'] and proof['all_executed_outcomes_match_native']
        before = ROOT / proof['raw']
        assert sha(before / 'audited-prefix.json') == proof['audited_prefix_sha256']
        assert sha(before / 'plan.json') == proof['plan_sha256']
        prior = json.loads((before / 'audited-prefix.json').read_text())
        old_plan = json.loads((before / 'plan.json').read_text())
        source = ROOT / '.work/sources/pgrust'
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == PIN
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        marker = json.loads((source / '.rust-interp-owned.json').read_text())
        assert marker['owner'] == str(ROOT) and marker['revision'] == PIN
        changed = source / 'crates/backend/parser/gram_core/src/parse.rs'
        original = changed.read_bytes(); states = source_states(original)
        selected = [states[0], states[1], states[6], states[-1]]
        native = {r['state']: r for r in prior if r['mode'] == 'native' and r['cycle'] == 0}
        names = [name for name, _ in native[0]['outcomes']]
        assert names == sorted(names) and len(names) == 114
        for state in selected:
            import hashlib
            assert hashlib.sha256(state['source']).hexdigest() == native[state['state']]['source_sha256']
        tool, key = installed_tools(old_plan['tool_key'])
        assert json.loads((tool / 'ready.json').read_text()) == old_plan['binaries']
        frozen = {p: h for p, h in old_plan['frozen'].items() if p.startswith('.work/sources/pgrust/')}
        frozen.pop(str(changed.relative_to(ROOT)), None)
        assert all(fingerprint(ROOT / p) == h for p, h in frozen.items())
        paths = [Path(__file__), Path(__file__).with_name('PARSER-TRACE.md'), proof_path,
                 before / 'audited-prefix.json', before / 'plan.json', Path(__file__).parent.parent / 'pgrust-parser-edits/states.py']
        paths += list((ROOT / 'scripts').glob('*.py')) + [tool / n for n in old_plan['binaries']]
        frozen.update({str(p.relative_to(ROOT)): fingerprint(p) for p in paths})
        work = ROOT / '.work' / run; work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, tool_key=key, commands=8,
            source_states=[0, -1, 5, 0], cargo_incremental='1', function_cache='off',
            native_proof_reused=True, tests=114, cargo_jobs=2, prepared_workers=2, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                             'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1', CARGO_INCREMENTAL='1', RUST_INTERP_LAUNCH_STATS='1')
        records = []
        with SourceEdit(changed, original) as edit:
            for state_index, state in enumerate(selected):
                edit.replace(state['source']); group = []
                for mode in ['plain', 'traced']:
                    index = len(records); suite = work / f'{index}-suite.json'
                    command = old_plan['custom_command_template'].copy()
                    for option, value in [('--function-cache', 'off'), ('--suite-report', str(suite)),
                                          ('--cache-namespace', run + ':' + mode)]:
                        assert command.count(option) == 1; command[command.index(option) + 1] = value
                    if mode == 'traced': command.append('--allocation-trace')
                    require_space(ROOT, 8)
                    child, out, err = capture(command, cwd=source, env=env, receipt_path=work / 'active.json',
                                              receipt=dict(index=index, state=state_index, mode=mode))
                    (work / f'{index}.stdout').write_text(out); (work / f'{index}.stderr').write_text(err)
                    row = dict(index=index, state=state_index, source_state=state['state'], mode=mode, command=command,
                        pid=child.pid, returncode=child.returncode, source_sha256=sha(changed),
                        stdout_sha256=sha(work / f'{index}.stdout'), stderr_sha256=sha(work / f'{index}.stderr'))
                    records.append(row); write(work / 'records.json', records)
                    assert child.returncode == (1 if state['state'] == -1 else 0)
                    launch, = [json.loads(l.split(': ', 1)[1]) for l in err.splitlines() if l.startswith('rust-interp-launch: ')]
                    assert launch['tool_key'] == key and launch['borrowck_cache'] == launch['function_cache'] == 'off'
                    report, digest = read_report(suite, launch['suite_report_sha256'])
                    actual = validate_report(report, names, 'prepared', state['state'] != -1)
                    assert actual == [tuple(o) for o in native[state['state']]['outcomes']]
                    validate_runtime_limits(report, 100000000000, 150000, required=True)
                    assert report['workers'] == report['requested_workers'] == 2
                    row.update(suite_sha256=digest, tests=114)
                    for kind, suffix in [('artifact', 'rbc'), ('entry_catalog', 'json')]:
                        path = Path(launch[kind + '_path']); assert sha(path) == launch[kind + '_sha256']
                        saved = work / f'{index}-{kind}.{suffix}'; shutil.copy2(path, saved)
                        assert sha(saved) == launch[kind + '_sha256']
                        row[kind] = dict(path=str(saved.relative_to(ROOT)), sha256=sha(saved))
                    if mode == 'traced':
                        from allocation_trace import validate_trace
                        trace = launch['allocation_trace']; path = Path(trace['path'])
                        assert trace['artifact_sha256'] == row['artifact']['sha256'] and sha(path) == trace['sha256']
                        saved = work / f'{index}-allocations.jsonl'; shutil.copy2(path, saved)
                        assert sha(saved) == trace['sha256']
                        assert validate_trace(saved.read_bytes(), row['artifact']['sha256']) == trace['events']
                        row['allocation_trace'] = dict(trace, saved_path=str(saved.relative_to(ROOT)))
                    group.append(row); write(work / 'records.json', records)
                    print(index + 1, mode, state['label'], 'original outcomes verified', flush=True)
                for kind in ['artifact', 'entry_catalog']:
                    assert group[0][kind]['sha256'] == group[1][kind]['sha256'], 'allocation observer changed artifact'
        assert changed.read_bytes() == original
        assert all(fingerprint(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results' / run; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', commands=8, native_commands=0, original_tests=114,
            source_restored=True, original_outcomes_match_native=True, observer_byte_identity=True,
            original_restored_identical=records[0]['artifact']['sha256'] == records[6]['artifact']['sha256'],
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'),
            performance_measurement=False))
        print('PASS: eight diagnostic commands; observer byte identity and original outcomes', flush=True)


if __name__ == '__main__':
    main()
