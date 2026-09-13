"""Close the primary screen without starting any held-out or full timing case."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import re
import sys
import screen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-run',default='native-indirect-flush-build-01')
    args=parser.parse_args();assert re.fullmatch(r'native-indirect-flush-build-\d{2}',args.build_run)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 12)
        names = [args.build_run, 'native-indirect-flush-qualification-01',
                 'native-indirect-flush-emission-02', 'native-indirect-flush-profile-01', 'native-indirect-flush-protocol-01',
                 'native-indirect-flush-screen-token-01']
        frozen = {}; proofs = []; evidence = {}
        for name in names:
            path = ROOT / 'results' / name / 'summary.json'
            proof = json.loads(path.read_text()); assert proof['status'] == 'passed'; proofs.append(proof)
            raw = ROOT / proof['raw']; evidence[str(path.relative_to(ROOT))] = sha(path)
            terminal = ROOT / 'results' / name / 'terminal.json'
            final = json.loads(terminal.read_text()); assert final['status'] == 'finished' and final['returncode'] == 0
            assert final['owner'] == final['cwd'] == str(ROOT)
            matches = re.findall(r'--supervise (\S+/plan\.json)', final['supervisor_identity'])
            assert len(matches) == 1
            supervisor_plan = Path(matches[0]); supervisor = supervisor_plan.parent
            assert supervisor.parent == ROOT / '.work/experiments'
            assert supervisor.name.startswith(name.rsplit('-',1)[0])
            assert sha(supervisor/'status.json') == sha(terminal)
            assert sha(supervisor_plan) == final['plan_sha256']
            assert sha(supervisor/'command.log') == final['log_sha256']
            evidence[str(terminal.relative_to(ROOT))] = sha(terminal)
            if 'source_manifest' in proof:
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
        build, strict, emission, profile, harness, result = proofs
        assert build['tests'] == {'test-debug':544, 'test-release':544}
        setup_path=ROOT/'results'/args.build_run/'setup-accounting.json'
        setup=json.loads(setup_path.read_text())
        assert setup['status']=='passed' and setup['tool_key']==build['tool_key']
        assert setup['qualification_summary_sha256']==sha(ROOT/'results'/args.build_run/'summary.json')
        evidence[str(setup_path.relative_to(ROOT))]=sha(setup_path)
        build_raw=ROOT/build['raw']
        assert json.loads((build_raw/'commands.json').read_text())==build['commands']
        for record in build['commands']:
            assert record['returncode']==0
            for suffix in ['stdout','stderr']:
                p=build_raw/(record['label']+'.'+suffix)
                assert sha(p)==record[suffix+'_sha256']
                evidence[str(p.relative_to(ROOT))]=sha(p)
        assert strict['commands'] == 119 and harness['tests'] == 13 and profile['commands'] == 3
        assert strict['jit_indirect_calls'] and harness['launcher_tests']==384 and harness['launcher_skipped']==16
        assert profile['exact_per_pc_counts'] and profile['exact_logical_counts_memory_and_entropy']
        assert emission['commands']==3 and emission['guest_commands']==0
        assert emission['exact_indirect_baseline_reconstruction'] and emission['only_dead_flush_words_removed']
        assert emission['tool_key']==strict['tool_key']==profile['tool_key']==build['tool_key']
        for c in emission['cases']:
            report_path=ROOT/emission['raw']/f"{c['index']}.json"
            assert sha(report_path)==c['report_sha256'];evidence[str(report_path.relative_to(ROOT))]=sha(report_path)
            report=json.loads(report_path.read_text())
            assert c['baseline_bytes']-c['candidate_bytes']==c['removed_flush_bytes']
            assert sum(f['removed_flush_bytes'] for f in report['functions'])==c['removed_flush_bytes']
            current,=[r for r in profile['comparisons'] if r['index']==c['index']]
            assert current['statistics']['jit_bytes']==c['candidate_bytes']
        for c in profile['comparisons']:
            index=c['index'];base=ROOT/profile['raw']
            for suffix,key in [('profile.json','profile_sha256'),('code/map.json','code_map_sha256'),
                               ('code/operations.json','operation_map_sha256'),('code/code.bin','code_sha256')]:
                p=base/(str(index)+'-'+suffix);assert sha(p)==c[key];evidence[str(p.relative_to(ROOT))]=c[key]
        protocol_raw=ROOT/harness['raw']
        for name in ['stdout','stderr','active.json']:
            p=protocol_raw/name;evidence[str(p.relative_to(ROOT))]=sha(p)
        assert 'Ran 13 tests' in (protocol_raw/'stderr').read_text()
        assert harness['launcher_source_hashes_match'] and harness['launcher_commands_reused']==1
        prior=json.loads((ROOT/harness['launcher_proof']).read_text());prior_raw=ROOT/prior['raw']
        prior_inputs=json.loads((prior_raw/'inputs.json').read_text())
        assert sha(prior_raw/'inputs.json')==prior['inputs_sha256']
        assert prior['launcher_tests']==384 and prior['launcher_skipped']==16
        for folder in ['scripts','tests']:
            for p in (ROOT/folder).glob('*.py'):assert sha(p)==prior_inputs[str(p.relative_to(ROOT))]
        old_closure_path=ROOT/'results/native-indirect-screen-token-01/closure.json'
        old_closure=json.loads(old_closure_path.read_text());assert old_closure['status']=='passed'
        for name in ['launcher-stdout','launcher-stderr','launcher-active.json']:
            p=prior_raw/name;assert sha(p)==old_closure['evidence'][str(p.relative_to(ROOT))]
        assert 'Ran 384 tests' in (prior_raw/'launcher-stderr').read_text()
        # The first emission attempt was an admission timeout, with no work to splice.
        rejected='native-indirect-flush-emission-01';out=ROOT/'results'/rejected;outer=ROOT/'.work/experiments'/rejected
        failure=json.loads((out/'summary.json').read_text());terminal=json.loads((out/'terminal.json').read_text())
        assert failure['status']=='not-admitted' and failure['emission_commands']==failure['guest_commands']==0
        assert not (ROOT/'.work'/rejected).exists()
        assert terminal['status']=='finished' and terminal['returncode']==1
        assert sha(outer/'status.json')==sha(out/'terminal.json')
        assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
        assert 'TimeoutError' in (outer/'command.log').read_text()
        for p in [out/'summary.json',out/'terminal.json',outer/'plan.json',outer/'command.log',old_closure_path]:
            evidence[str(p.relative_to(ROOT))]=sha(p)
        assert result['commands'] == 40
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
            if p.startswith(('crates/', 'scripts/', 'benchmarks/', 'tests/')) or p in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml']:
                spec = revision + ':' + p
                assert hashlib.sha256(subprocess.check_output(['git', 'show', spec])).hexdigest() == h
                bindings.append(dict(path=p, sha256=h, git_source=spec))
        for row in rows:
            if row['mode'] in screen.CUSTOM:
                assert row['launch']['jit_indirect_calls'] is (row['mode']=='candidate')
        for name in ['native-indirect-flush-real-controls-01', 'native-indirect-flush-full-01']:
            assert not (ROOT / '.work' / name).exists()
        out = ROOT / 'results/native-indirect-flush-screen-token-01'
        assert not (out/'closure.json').exists(), 'screen closure already exists'
        write(out / 'source-bindings.json', dict(source_revision=revision, files=bindings))
        write(out / 'closure.json', dict(status='passed', performance_gate_passed=result['gate_passed'],
            parked=not result['gate_passed'], full_comparison_commands=0, held_out_commands=0, repeated_screen_commands=0,
            unique_frozen_inputs=len(frozen), retained_artifacts_verified=len(retained), source_bindings=len(bindings),
            source_bindings_sha256=sha(out / 'source-bindings.json'), evidence=evidence,
            auditor_sha256=sha(Path(__file__))))
        print('closed primary screen:',len(frozen),'inputs,',len(retained),'artifacts,',len(bindings),'Git bindings')


if __name__ == '__main__': main()
