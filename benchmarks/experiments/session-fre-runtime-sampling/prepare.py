"""Freeze diagnostic commands, archived VM sources and current-host profiles."""
import hashlib
import argparse
import subprocess
import sys
from pathlib import Path
from common import ROOT, KEY, VM, read, verify, run_name, acquire_lock, sha, require_space, write
from interpreter import installed_tools


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True, type=run_name)
    args = parser.parse_args()
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        paths = []

        def closed(name):
            out = ROOT / 'results' / name
            summary, receipt = read(out / 'summary.json'), read(out / 'closure.json')
            assert receipt['status'] == 'closed'
            assert sha(out / 'summary.json') == receipt['summary_sha256']
            assert sha(out / 'terminal.json') == receipt['terminal_sha256']
            paths.extend(out / n for n in ['summary.json', 'closure.json', 'terminal.json'])
            return summary, receipt

        guard, _ = closed('session-project-edit-token-01')
        assert guard['commands']==176 and guard['measurement']['verdict']=='failed'
        phases, _ = closed('session-duration-order-phases-token-02')
        assert phases['status']=='passed' and phases['test_invocations']==192
        build, _ = closed('session-duration-order-install-01')
        qualified, _ = closed('session-duration-order-qualification-02')
        profiles, _ = closed('runtime-composition-profile-02')
        assert build['status']==qualified['status']==profiles['status']=='passed'
        assert build['tool_key']==KEY and qualified['duration_order'] and not qualified['diagnostic_feature']
        assert profiles['matched_control_key']=='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
        assert profiles['control_vm_matches_adopted'] and profiles['fresh_control_profiles']==3
        assert profiles['exact_per_pc_counts'] and profiles['exact_operation_map_reconstruction']
        tool,key=installed_tools(KEY)
        assert key==KEY and sha(tool/'rust-interp-vm')==VM==build['binaries']['rust-interp-vm']
        for path,digest in build['outputs'].items():
            assert sha(ROOT/path)==digest;paths.append(ROOT/path)
        source=ROOT/qualified['raw']/'plan.json'
        assert sha(source)==qualified['plan_sha256'];manifest=read(source);paths.append(source)
        archived={}
        for path,digest in manifest['frozen'].items():
            if path.startswith(('crates/','.cargo/')) or path in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:
                blob=subprocess.check_output(['git','show',qualified['source_revision']+':'+path],cwd=ROOT)
                assert hashlib.sha256(blob).hexdigest()==digest==sha(ROOT/path)
                archived[path]=dict(revision=qualified['source_revision'],sha256=digest)
        assert archived
        retained=ROOT/qualified['raw']/'release-rust-interp-vm'
        assert sha(retained)==qualified['outputs'][str(retained.relative_to(ROOT))]==VM
        paths.append(retained)
        history=ROOT/guard['raw']/'records.json';assert sha(history)==guard['records_sha256'];paths.append(history)
        current=next(r for r in read(history) if r['mode']=='candidate' and r['cycle']==0 and r['state']==0)
        compatibility, _ = closed('vmmap-label-compatibility-01')
        assert compatibility['status'] == 'passed' and compatibility['guest_commands'] == 0
        assert compatibility['attribution_tests'] == 9 and compatibility['retained_reports'] == 14
        controls = ROOT / compatibility['raw']
        prior = read(controls / 'plan.json')
        assert sha(controls / 'plan.json') == compatibility['plan_sha256']
        assert sha(controls / 'records.json') == compatibility['records_sha256']
        control, = [r for r in read(controls / 'records.json') if r['label'] == 'attribution']
        assert control['returncode'] == 0 and sha(controls / 'attribution.stderr') == control['stderr_sha256']
        assert 'Ran 9 tests' in (controls / 'attribution.stderr').read_text()
        dependencies = ['scripts/compare_saved_runtime.py', 'scripts/summarize_owned_sample.py',
            'scripts/sample_owned_vm.py', 'scripts/vmmap_ranges.py',
            'benchmarks/experiments/scalar-runtime-sampling/attribute.py',
            'benchmarks/experiments/scalar-runtime-sampling/test_attribution.py',
            'benchmarks/experiments/scalar-private-transfers/native_observation.py',
            'benchmarks/experiments/scalar-private-transfers/test_native_observation.py',
            'benchmarks/experiments/operation-map/attribute.py',
            'benchmarks/experiments/operation-map/maps.py',
            'benchmarks/experiments/operation-map/test_attribute.py']
        for path in dependencies:
            assert sha(ROOT / path) == prior['frozen'][path], path
            paths.append(ROOT / path)
        paths += [controls / n for n in ['plan.json', 'records.json', 'attribution.stdout', 'attribution.stderr']]
        reference_path = ROOT / 'results/current-runtime-boundaries-02/summary.json'
        reference = read(reference_path)
        assert reference['status'] == 'passed'
        paths.append(reference_path)
        cases = []
        for index, label in enumerate(['block', 'exhaustive']):
            item, = [r for r in reference['profiles'] if r['index'] == index]
            profile, = [r for r in profiles['comparisons'] if r['index'] == index and r['mode'] == 'control']
            assert profile['tool_key'] == profiles['matched_control_key'] and not profile['reused'] and profile['name'] == item['name']
            assert item['artifact_sha256']==current['artifact']['sha256']
            assert dict(current['outcomes'])[item['name']]=='passed'
            assert profile['native_indirect_calls'] == 0
            for field in ['artifact', 'catalog']:
                assert sha(ROOT / item[field]) == item[field + '_sha256']
                paths.append(ROOT / item[field])
            assert sha(ROOT / profile['profile_path']) == profile['profile_sha256']
            paths.append(ROOT / profile['profile_path'])
            name = 'session-fre-sample-' + label + '-' + args.run_id.rsplit('-', 1)[1]
            assert not (ROOT / '.work' / name).exists() and not (ROOT / 'results' / name).exists()
            command = [sys.executable, 'scripts/sample_owned_vm.py', '--tool-key', KEY,
                '--artifact', str(ROOT / item['artifact']), '--artifact-sha256', item['artifact_sha256'],
                '--run-id', name, '--repetitions', '1', '--duration', '3',
                '--instruction-limit', str(item['limits']['instructions']),
                '--allocation-limit', str(item['limits']['allocations']),
                '--jit-persistent-registers', '--jit-resumable-calls', '--jit-scalar-calls',
                '--dump-code', '--jit-operation-map', '--select-test', item['name'],
                '--suite-catalog', str(ROOT / item['catalog']), '--lock-wait-seconds', '45',
                '--minimum-free-bytes', str(8 * 1024**3), '--expected-jit-declines', '0']
            summary_command = [sys.executable, 'scripts/summarize_owned_sample.py', '--run-id', name]
            cases.append(dict(label=label, run_id=name, command=command, summary_command=summary_command, profile=profile['profile_path'],
                              profile_sha256=profile['profile_sha256'], test=item['name']))
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py', '.md']]
        paths += [ROOT / 'scripts' / n for n in ['interpreter.py', 'sample_owned_vm.py', 'compare_saved_runtime.py', 'workflow_io.py', 'supervise_experiment.py']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        for path, digest in frozen.items():
            if not path.startswith(('.work/', 'results/')):
                assert hashlib.sha256(subprocess.check_output(['git', 'show', revision + ':' + path], cwd=ROOT)).hexdigest() == digest
        raw = ROOT / '.work' / args.run_id
        raw.mkdir(exist_ok=False)
        write(raw / 'vm-source-bindings.json', archived)
        plan = dict(owner=str(ROOT), source_revision=revision, tool_key=KEY, vm_sha256=VM,
            frozen=frozen, cases=cases, guest_commands=2, reused_controls=9,
            archived_vm_sources=str((raw / 'vm-source-bindings.json').relative_to(ROOT)),
            archived_vm_sources_sha256=sha(raw / 'vm-source-bindings.json'),
            attribution_controls_from='vmmap-label-compatibility-01',
            sampler_compatibility_replay_reports=14,
            sampler_workspace_snapshot_is_not_vm_build_source=False,
            initial_gib=12, minimum_child_gib=8, ordinary_entropy=True,
            profile_used_for_static_identity_only=True, performance_measurement=False)
        verify(plan)
        write(raw / 'plan.json', plan)
        print('Prepared two fresh owned sample commands;', len(archived), 'archived VM sources;', len(frozen), 'frozen inputs', flush=True)


if __name__ == '__main__':
    main()
