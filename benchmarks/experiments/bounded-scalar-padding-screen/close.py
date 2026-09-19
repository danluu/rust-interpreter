"""Close successful histories or preserve failed prefixes; never rerun guests."""
import hashlib
import subprocess
import sys
from pathlib import Path
from common import ROOT, RUN, SOURCE, CHANGED, read, sha, write, acquire_lock, require_space
from model import KEY, CANDIDATE, NAMES, MODES, FLAGS, schedule, command, accounting, native_executable
from benchmark import PROBES
from evidence import validate_row, validate_group


def close():
    raw, out = ROOT/'.work'/RUN, ROOT/'results'/RUN
    outer = ROOT/'.work/experiments'/RUN
    plan, records, terminal = read(raw/'plan.json'), read(raw/'records.json'), read(outer/'status.json')
    assert terminal['status'] == 'finished' and terminal['owner'] == terminal['cwd'] == plan['owner'] == str(ROOT)
    assert terminal['command'][1:] == plan['controller_command'][1:]
    assert Path(terminal['command'][0]).resolve() == Path(plan['controller_command'][0]).resolve()
    assert sha(outer/'plan.json') == terminal['plan_sha256'] and sha(outer/'command.log') == terminal['log_sha256']
    assert not (out/'closure.json').exists()
    original = (raw/'original.rs').read_bytes()
    assert hashlib.sha256(original).hexdigest() == sha(CHANGED) == plan['original_source_sha256']
    assert plan['schedule'] == schedule(original)
    assert plan['tool_key'] == KEY and plan['candidate_tool_key'] == CANDIDATE and plan['names'] == NAMES
    assert plan['cargo_jobs'] == plan['native_threads'] == plan['prepared_workers'] == 2
    assert plan['guest_rustflags'] == FLAGS and plan['build_tool_opt_level'] == 0
    assert plan['initial_minimum_gib'] == 16 and plan['minimum_child_gib'] == 8
    assert plan['expected_commands'] == 40 and plan['strict_controls'] == 2
    assert plan['source'] == str(SOURCE.relative_to(ROOT))
    assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=SOURCE).strip()
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip() == plan['revision']
    owner = read(SOURCE/'.rust-interp-owned.json')
    assert owner['owner'] == str(ROOT) and owner['revision'] == plan['revision']
    bindings, evidence = {}, {}
    for p,h in plan['frozen'].items():
        assert sha(ROOT/p) == h, p
        if p.startswith(('.work/', 'results/')):
            bindings[p] = dict(kind='retained', sha256=h)
        else:
            data = subprocess.check_output(['git', 'show', plan['source_revision']+':'+p], cwd=ROOT)
            assert hashlib.sha256(data).hexdigest() == h, p
            bindings[p] = dict(kind='git', revision=plan['source_revision'], sha256=h)

    def child_receipt(row, prefix):
        path = raw/(prefix+'-child.json')
        assert sha(path) == row['child_sha256']
        child = read(path)
        assert child['status'] == 'finished' and child['pid'] == row['pid']
        assert child['parent_pid'] == terminal['child_pid'] and child['cwd'] == str(SOURCE)
        assert child['command'] == row['command'] and child['returncode'] == row['returncode']
        assert terminal['child_started_at'] <= child['started_at'] <= child['finished_at'] <= terminal['finished_at']
        for stream in ['stdout', 'stderr']:
            assert sha(raw/(prefix+'.'+stream)) == row[stream+'_sha256']

    previous = dict.fromkeys(MODES)
    for i,row in enumerate(records):
        scheduled = plan['schedule'][i]
        assert row['index'] == i and {k:row[k] for k in scheduled} == scheduled
        mode = row['mode']
        assert row['command'] == command(SOURCE, raw, i, mode)
        assert row['previous_source_sha256'] == previous[mode] != row['source_sha256']
        previous[mode] = row['source_sha256']
        assert row['wall_seconds'] > 0 and row['cpu_seconds'] == row['cpu']['total_seconds'] > 0
        assert row['cpu_seconds'] == row['cpu']['user_seconds']+row['cpu']['system_seconds']
        child_receipt(row, str(i))
        if terminal['returncode'] == 0:
            validate_row(row, raw)
            if mode == 'native':
                # Cargo's path is mutable across edits; retained bytes carry
                # the per-edit identity, and the final file checks restoration.
                exe = native_executable((raw/(str(i)+'.stdout')).read_text(), SOURCE, raw/mode)
                if row['state'] == 'restored':
                    assert sha(exe) == row['executable']['sha256']
    strict = read(raw/'strict.json')
    assert len(strict) <= len(PROBES)
    for row,(label,code,diagnostic) in zip(strict, PROBES):
        assert row['label'] == label
        assert row['source_sha256'] == hashlib.sha256(original+code).hexdigest()
        assert row['command'] == command(SOURCE, raw, 'strict-'+label, 'candidate', raw.name+':strict')
        child_receipt(row, 'strict-'+label)
        if terminal['returncode'] == 0:
            err = (raw/('strict-'+label+'.stderr')).read_text()
            assert row['returncode'] == 101 and diagnostic in err
            assert 'rust-interp-launch: ' not in err and 'rust-interp-export: ' not in err
            assert not (raw/('strict-'+label+'-suite.json')).exists()
    fields = ['plan', 'records', 'strict', 'space']
    out.mkdir(exist_ok=True)
    if terminal['returncode'] == 0:
        summary = read(out/'summary.json')
        assert summary['status'] == 'passed' and summary['commands'] == len(records) == 40
        assert summary['strict_controls'] == len(strict) == 2 and summary['original_tests'] == 2
        assert summary['tool_key'] == KEY and summary['candidate_tool_key'] == CANDIDATE and summary['source_revision'] == plan['source_revision']
        assert summary['source_restored'] and summary['original_assertions_unchanged']
        assert summary['exact_native_test_outcomes'] and summary['matching_custom_artifacts']
        assert summary['performance_measurement'] and summary['candidate'] and not summary['adoption']
        assert summary['measurement'] == accounting(records)
        assert all(h == plan['original_source_sha256'] for h in previous.values())
        for start in range(0,40,5):
            validate_group(records[start:start+5])
        spaces = read(raw/'space.json')
        assert [(s['index'],s['phase']) for s in spaces] == [(i,p) for i in range(40) for p in ['before','after']]
        assert all(s['free_bytes'] >= 8*1024**3 for s in spaces if s['phase'] == 'before')
        for field in fields:
            assert sha(raw/(field+'.json')) == summary[field+'_sha256']
    else:
        assert not (out/'summary.json').exists()
        write(out/'summary.json', dict(status='failed-prefix-preserved', source_revision=plan['source_revision'],
            raw=str(raw.relative_to(ROOT)), commands=len(records), strict_controls=len(strict),
            source_restored=True, returncodes=[r['returncode'] for r in records],
            **{field+'_sha256':sha(raw/(field+'.json')) for field in fields},
            performance_measurement=False, candidate=True, adoption=False))
    for path in raw.rglob('*'):
        if path.is_file() and path.relative_to(raw).parts[0] not in ['native', 'check']:
            assert not path.is_symlink()
            evidence[str(path.relative_to(ROOT))] = sha(path)
    for path in [outer/'status.json', outer/'plan.json', outer/'command.log']:
        evidence[str(path.relative_to(ROOT))] = sha(path)
    write(raw/'closed-bindings.json', bindings)
    write(raw/'closed-evidence.json', evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json', dict(status='closed', all_hashes_verified=True, source_revision=plan['source_revision'],
        complete=terminal['returncode'] == 0, source_restored=True, adoption=False,
        frozen_inputs=len(bindings), evidence_files=len(evidence),
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)), bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)), evidence_sha256=sha(raw/'closed-evidence.json'),
        summary_sha256=sha(out/'summary.json'), terminal_sha256=sha(out/'terminal.json')))
    print('Closed ES8 history; terminal', terminal['returncode'], flush=True)


if __name__ == '__main__':
    assert len(sys.argv) == 1
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        require_space(ROOT,8)
        close()
