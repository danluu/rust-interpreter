"""Close the rejected screen without starting any held-out or full timing case."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import screen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 8)
        names = ['native-boundary-memory-build-01', 'native-boundary-memory-qualification-01',
                 'native-boundary-memory-profile-01', 'native-boundary-memory-protocol-01',
                 'native-boundary-memory-screen-token-01']
        frozen = {}; proofs = []; evidence = {}
        for name in names:
            path = ROOT / 'results' / name / 'summary.json'
            proof = json.loads(path.read_text()); assert proof['status'] == 'passed'; proofs.append(proof)
            raw = ROOT / proof['raw']; evidence[str(path.relative_to(ROOT))] = sha(path)
            terminal = ROOT / '.work/experiments' / name / 'status.json'
            final = json.loads(terminal.read_text()); assert final['status'] == 'finished' and final['returncode'] == 0
            assert sha(terminal.with_name('plan.json')) == final['plan_sha256']
            assert sha(terminal.with_name('command.log')) == final['log_sha256']
            evidence[str(terminal.relative_to(ROOT))] = sha(terminal)
            if name.endswith('build-01'):
                plan_path = ROOT / proof['source_manifest']; assert sha(plan_path) == proof['source_manifest_sha256']
                inputs = json.loads(plan_path.read_text())['frozen']
            elif name.endswith('protocol-01'):
                plan_path = raw / 'inputs.json'; assert sha(plan_path) == proof['inputs_sha256']
                inputs = json.loads(plan_path.read_text())
            else:
                plan_path = raw / 'plan.json'; assert sha(plan_path) == proof['plan_sha256']
                assert sha(raw / 'records.json') == proof['records_sha256']
                inputs = json.loads(plan_path.read_text())['frozen']
            evidence[str(plan_path.relative_to(ROOT))] = sha(plan_path)
            for p, h in inputs.items():
                assert p not in frozen or frozen[p] == h, p
                frozen[p] = h
        build, strict, profile, harness, result = proofs
        assert build['tests'] == {'test-debug':519, 'test-release':519}
        assert strict['commands'] == 119 and harness['tests'] == 12 and profile['commands'] == 3
        assert result['commands'] == 40 and not result['gate_passed']
        assert result['source_restored'] and result['test_source_unchanged']
        assert result['native_assertion_outcomes_match'] and result['candidate_control_bytecode_matches']
        raw = ROOT / result['raw']; plan = json.loads((raw / 'plan.json').read_text())
        rows = json.loads((raw / 'records.json').read_text())
        recalculated = screen.assessment(rows)
        assert all(result[k] == v for k, v in recalculated.items())
        for name in ['transitions', 'space']: assert sha(raw / (name + '.json')) == result[name + '_sha256']
        source = ROOT / '.work/sources/fre'
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == plan['revision']
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        assert sha(source / plan['case']['file']) == plan['original_source_sha256']
        retained = {}
        for row in rows:
            for kind in ['artifact', 'catalog', 'entry_catalog', 'selection', 'native_executable', 'cargo_timing']:
                if kind in row:
                    item = row[kind]; assert item['path'] not in retained or retained[item['path']] == item['sha256']
                    retained[item['path']] = item['sha256']
        assert retained and all(sha(ROOT / p) == h for p, h in retained.items())
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        bindings = []
        for p, h in sorted(frozen.items()):
            if p.startswith(('crates/', 'scripts/', 'benchmarks/')) or p in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml']:
                spec = revision + ':' + p
                assert hashlib.sha256(subprocess.check_output(['git', 'show', spec])).hexdigest() == h
                bindings.append(dict(path=p, sha256=h, git_source=spec))
        for name in ['native-boundary-memory-real-controls-01', 'native-boundary-memory-full-01']:
            assert not (ROOT / '.work' / name).exists()
        out = ROOT / 'results/native-boundary-memory-screen-token-01'
        write(out / 'source-bindings.json', dict(source_revision=revision, files=bindings))
        write(out / 'closure.json', dict(status='passed', performance_gate_passed=False,
            parked=True, full_comparison_commands=0, held_out_commands=0, repeated_screen_commands=0,
            unique_frozen_inputs=len(frozen), retained_artifacts_verified=len(retained), source_bindings=len(bindings),
            source_bindings_sha256=sha(out / 'source-bindings.json'), evidence=evidence,
            auditor_sha256=sha(Path(__file__))))
        print('closed rejected screen:',len(frozen),'inputs,',len(retained),'artifacts,',len(bindings),'Git bindings')


if __name__ == '__main__': main()
