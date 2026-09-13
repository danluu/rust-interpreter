"""Close the saved diagnostic without repeating successful reconstructions or tests."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        evidence = {}
        frozen = {}
        bindings = {}
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()

        def read(path):
            evidence[path] = sha(ROOT / path)
            return json.loads((ROOT / path).read_text())

        def terminal(name, saved, expected):
            raw = '.work/experiments/' + name + '/'
            t = read(saved)
            assert t == read(raw + 'status.json')
            assert t['status'] == 'finished' and t['returncode'] == expected
            assert t['owner'] == t['cwd'] == str(ROOT)
            assert sha(ROOT / raw / 'plan.json') == t['plan_sha256']
            assert sha(ROOT / raw / 'command.log') == t['log_sha256']
            read(raw + 'plan.json')
            evidence[raw + 'command.log'] = t['log_sha256']

        def inputs(plan, historical=False):
            for path, digest in plan['frozen'].items():
                source = plan.get('source_revision', revision)
                if historical:
                    content = subprocess.check_output(['git', 'show', source + ':' + path])
                    assert hashlib.sha256(content).hexdigest() == digest, path
                    bindings[source + ':' + path] = digest
                else:
                    assert sha(ROOT / path) == digest, path
                    assert frozen.setdefault(path, digest) == digest, path

        failed = read('results/native-continuation-build-01/summary.json')
        assert failed['status'] == 'failed' and not failed['release_started']
        for name in ['plan', 'records']:
            assert sha(ROOT / failed['raw'] / (name + '.json')) == failed[name + '_sha256']
        inputs(read(failed['raw'] + '/plan.json'), historical=True)
        records = read(failed['raw'] + '/records.json')
        assert len(records) == 1 and records[0]['returncode'] != 0
        assert '271 passed; 1 failed; 8 ignored' in records[0]['stdout']
        terminal('native-continuation-build-01', 'results/native-continuation-build-01/terminal.json', 1)

        build = read('results/native-continuation-build-02/summary.json')
        assert build['status'] == 'passed' and build['tests'] == dict(debug=414, release=414)
        assert build['commands'] == 2 and build['guest_benchmark_commands'] == 0
        for name in ['plan', 'records']:
            assert sha(ROOT / build['raw'] / (name + '.json')) == build[name + '_sha256']
        inputs(read(build['raw'] + '/plan.json'))
        records = read(build['raw'] + '/records.json')
        assert [(r['label'], r['returncode'], r['tests_passed']) for r in records] == [('debug', 0, 414), ('release', 0, 414)]
        terminal('native-continuation-build-02', 'results/native-continuation-build-02/terminal.json', 0)

        summary = read('results/native-continuation-census-01/summary.json')
        assert summary['status'] == 'passed' and not summary['performance_measurement']
        assert summary['retained_reconstruction_commands'] == 2
        assert summary['new_reconstruction_commands'] == summary['guest_commands'] == 0
        assert summary['failed_attribution_attempts'] == summary['successful_attribution_commands'] == 1
        for prefix, raw in [('', summary['raw']), ('attribution_', summary['attribution_raw'])]:
            for name in ['plan', 'records']:
                assert sha(ROOT / raw / (name + '.json')) == summary[prefix + name + '_sha256']
            inputs(read(raw + '/plan.json'))
        prior = read(summary['raw'] + '/records.json')
        assert [(r['label'], r['returncode']) for r in prior] == [('block', 0), ('exhaustive', 0), ('attribute', 1)]
        assert 'FileNotFoundError' in prior[-1]['stderr']
        assert '/results/native-continuation-census-01/.attribution.json-' in prior[-1]['stderr']
        recovered = read(summary['attribution_raw'] + '/records.json')
        assert len(recovered) == 1 and recovered[0]['returncode'] == 0
        assert recovered[0]['command'] == prior[-1]['command']
        terminal('native-continuation-census-01', 'results/native-continuation-census-01/failed-terminal.json', 1)
        terminal('native-continuation-attribution-02', 'results/native-continuation-census-01/terminal.json', 0)

        path = 'results/native-continuation-census-01/attribution.json'
        assert sha(ROOT / path) == summary['attribution_sha256']
        attribution = read(path)
        assert attribution['status'] == 'passed' and attribution['guest_commands'] == 0
        for path, digest in attribution['evidence'].items():
            assert sha(ROOT / path) == digest, path
            assert frozen.setdefault(path, digest) == digest, path
        for index, label in enumerate(['block', 'exhaustive']):
            report = read(summary['raw'] + '/' + label + '.json')
            assert report['status'] == 'passed' and report['exact_baseline_reconstruction']
            assert report['guest_commands'] == report['executable_code_publications'] == 0
            case = attribution['cases'][index]
            assert case['case'] == label and case['functions'] == [1101, 1305][index]
            assert len(report['functions']) == case['functions']
            assert not case['ambiguous_samples'] and not case['omitted_executed_functions']
            assert case['weighted_continuations']['eligible'] == case['native_calls']
            assert case['counter_updates'] == dict(Call=case['native_calls'], Return=case['native_returns'])
            assert sum(case['samples'].values()) == case['generated_samples'] == [1651, 1439][index]

        for path, digest in frozen.items():
            if path.startswith('.work/'):
                continue
            content = subprocess.check_output(['git', 'show', revision + ':' + path])
            assert hashlib.sha256(content).hexdigest() == digest, path
            bindings[revision + ':' + path] = digest
        output = ROOT / 'results/native-continuation-census-01'
        write(output / 'source-bindings.json', bindings)
        write(output / 'closure.json', dict(status='passed', unique_frozen_inputs=len(frozen),
            git_bound_files=len(bindings), source_bindings_sha256=sha(output / 'source-bindings.json'),
            frozen=frozen, evidence=evidence, auditor_sha256=sha(Path(__file__)),
            all_frozen_inputs_verified=True, retained_reconstruction_commands=2,
            new_reconstruction_commands=0, guest_commands=0, executable_code_publications=0,
            performance_measurement=False))
        print('Closed diagnostic:', len(frozen), 'frozen inputs;', len(bindings), 'Git bindings', flush=True)


if __name__ == '__main__':
    main()
