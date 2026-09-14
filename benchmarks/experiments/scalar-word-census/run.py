"""Read-only census on three closed original scalar native profiles."""
from pathlib import Path
import json
import os
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/scalar-call-guards'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write
import native_observation
from words import analyze

NAME = 'scalar-word-census-03'


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 10)
        result_path = ROOT / 'results/scalar-call-guards-profile-01/summary.json'
        summary = json.loads(result_path.read_text())
        assert summary['status'] == 'passed' and summary['commands'] == 6
        terminal_path = result_path.with_name('terminal.json')
        terminal = json.loads(terminal_path.read_text())
        assert terminal['owner'] == terminal['cwd'] == str(ROOT)
        assert terminal['status'] == 'finished' and terminal['returncode'] == 0
        outer = ROOT / '.work/experiments/scalar-call-guards-profile-01'
        assert sha(outer/'plan.json') == terminal['plan_sha256']
        assert sha(outer/'command.log') == terminal['log_sha256']
        assert sha(outer/'status.json') == sha(terminal_path)
        directory = Path(__file__).parent
        paths = [*directory.glob('*.py'), directory/'PLAN.md', result_path, terminal_path,
                 outer/'plan.json', outer/'command.log', outer/'status.json',
                 ROOT/'scripts/compare_saved_runtime.py', ROOT/'scripts/workflow_io.py',
                 ROOT/'scripts/supervise_experiment.py', Path(native_observation.__file__)]
        # Root emitter sources must still match the source-qualified build.
        build_plan = ROOT / '.work/scalar-call-guards-build-01/plan.json'
        plan = json.loads(build_plan.read_text()); paths.append(build_plan)
        for p in (ROOT/'crates/bytecode').rglob('*.rs'):
            assert sha(p) == plan['frozen'][str(p.relative_to(ROOT))], p
            paths.append(p)
        comparisons = [r for r in summary['comparisons'] if r['mode'] == 'candidate']
        assert [r['index'] for r in comparisons] == [0, 1, 2]
        for row in comparisons:
            for key in ['profile', 'code', 'operations']:
                p = ROOT/row[key+'_path']; assert sha(p) == row[key+'_sha256']; paths.append(p)
            p = (ROOT/row['code_path']).with_name('map.json')
            assert sha(p) == row['map_sha256']; paths.append(p)
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD']).strip()
        work = ROOT/'.work'/NAME; work.mkdir(exist_ok=False)
        write(work/'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
                                    guest_commands=0, host_builds=0, admission_gib=10,
                                    minimum_child_gib=8, source_tool=summary['tool_key']))
        records = []
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', str(directory), '-p', 'test_words.py', '-v']
        require_space(ROOT, 8); started = time.time()
        child, out, err = capture(command, cwd=ROOT, env=env, receipt_path=work/'active.json',
                                  receipt=dict(label='census-controls'))
        (work/'controls.stdout').write_text(out); (work/'controls.stderr').write_text(err)
        records.append(dict(command=command, pid=child.pid, returncode=child.returncode,
                            started_at=started, finished_at=time.time(),
                            stdout_sha256=sha(work/'controls.stdout'), stderr_sha256=sha(work/'controls.stderr')))
        write(work/'records.json', records)
        assert child.returncode == 0, out+err
        observations = []
        for row in comparisons:
            require_space(ROOT, 8)
            profile = json.loads((ROOT/row['profile_path']).read_text())
            code = (ROOT/row['code_path']).read_bytes()
            regions = json.loads((ROOT/row['code_path']).with_name('map.json').read_text())
            operations = json.loads((ROOT/row['operations_path']).read_text())
            # The source-qualified profiler independently re-emitted all bytes.
            native_observation.validate(operations, regions, code, profile, regions['pid'])
            _, totals = native_observation.logical_counts(profile)
            assert totals == row['logical_counts']
            bodies = []
            for span in regions['ranges']:
                if span['kind'] != 'scalar_leaf': continue
                function = profile['functions'][span['function']]
                hits = function['jit_scalar_hits']; assert len(hits) == len(function['operations'])
                calls = hits[0]; assert all(0 <= n <= calls for n in hits)
                words = [w for (w,) in struct.iter_unpack('<I', code[span['offset']:span['end']])]
                observed = analyze(words)
                bounds = observed['successful_path_bounds']
                assert not calls or bounds is not None
                bodies.append(dict(function=span['function'], name=span['name'], successful_calls=calls,
                                   word_sha256=sha_bytes(code[span['offset']:span['end']]), **observed,
                                   weighted_lower=(bounds[0]*calls if bounds else 0),
                                   weighted_upper=(bounds[1]*calls if bounds else 0)))
            assert len(bodies) == row['scalar_bodies']
            assert sum(b['successful_calls'] for b in bodies) == row['scalar_calls']
            observation = dict(index=row['index'], name=row['name'], bodies=bodies,
                scalar_calls=row['scalar_calls'], static_words=sum(b['words'] for b in bodies),
                static_dead_words=sum(b['dead_words'] for b in bodies),
                weighted_lower=sum(b['weighted_lower'] for b in bodies),
                weighted_upper=sum(b['weighted_upper'] for b in bodies))
            write(work/f'observation-{row["index"]}.json', observation)
            observations.append({k:v for k,v in observation.items() if k != 'bodies'})
            print(json.dumps(observations[-1]), flush=True)
            del profile, operations, regions, code
        assert all(sha(ROOT/p) == h for p,h in frozen.items())
        result = ROOT/'results'/NAME; result.mkdir(exist_ok=False)
        write(result/'summary.json', dict(status='passed', source_revision=revision, raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'), records_sha256=sha(work/'records.json'), controls=9,
            observations=observations, observation_sha256=[sha(work/f'observation-{i}.json') for i in range(3)],
            all_frozen_inputs_verified=True, host_builds=0, guest_commands=0, executable_code_publications=0,
            production_changes=0, performance_measurement=False,
            limitation='Pure register liveness only; preserves memory and stack effects. Successful-path bounds include infeasible branches and exclude failed private attempts. Not hardware instruction measurements or a speedup.'))


def sha_bytes(value):
    import hashlib
    return hashlib.sha256(value).hexdigest()


if __name__ == '__main__': main()
