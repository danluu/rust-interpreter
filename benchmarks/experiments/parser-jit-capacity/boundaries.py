"""Check CLI boundaries and all original parser tests at both code capacities."""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import capture, require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        build_path = ROOT / 'results/parser-jit-capacity-build-01/summary.json'
        strict_path = ROOT / 'results/parser-jit-capacity-qualification-01/summary.json'
        parser_path = ROOT / 'results/environment-main-parser-01/summary.json'
        build, strict, parser = [json.loads(p.read_text()) for p in [build_path, strict_path, parser_path]]
        assert build['status'] == strict['status'] == parser['status'] == 'passed'
        assert build['tool_key'] == strict['tool_key'] and strict['commands'] == 119
        assert parser['custom_tests_passed'] == parser['native_tests_reused'] == 114
        tool, key = installed_tools(build['tool_key']); vm = tool / 'rust-interp-vm'
        assert all(sha(tool / n) == h for n, h in build['binaries'].items())
        old = ROOT / parser['raw']
        prior, _ = read_report(old / 'suite.json', parser['suite_sha256'])
        names = [r['name'] for r in prior['tests']]
        artifact, catalog = [ROOT / parser['artifacts'][k]['path'] for k in ['artifact', 'entry_catalog']]
        for p, k in [(artifact, 'artifact'), (catalog, 'entry_catalog')]:
            assert sha(p) == parser['artifacts'][k]['sha256']
        raw = ROOT / strict['raw']
        assert sha(raw / 'records.json') == strict['records_sha256']
        strict_rows = json.loads((raw / 'records.json').read_text())
        small = raw / 'environment-off.rbc'
        fixture, = [r for r in strict['fixtures'] if r['fixture'] == 'environment']
        assert sha(small) == fixture['artifact_sha256']
        expected_row, = [r for r in strict_rows if r['label'] == 'environment-native-0']
        expected_path = ROOT / expected_row['stdout']
        assert sha(expected_path) == expected_row['stdout_sha256']
        expected = expected_path.read_text()
        paths = [Path(__file__), Path(__file__).with_name('QUALIFICATION.md'), build_path, strict_path,
                 parser_path, old / 'suite.json', artifact, catalog, small, expected_path, raw / 'records.json']
        paths += [tool / n for n in build['binaries']]
        paths += [ROOT / 'scripts' / n for n in ['interpreter.py', 'suite_reports.py', 'workflow_io.py', 'compare_saved_runtime.py']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work/parser-jit-capacity-boundaries-01'; work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, expected_commands=16,
            invalid_vm_commands=8, old_vm_rejection_commands=1, small_fixture_commands=4,
            original_parser_commands=3, original_parser_tests=114, code_limits=[None, 16777216, 33554432],
            suite_workers=2, instruction_limit=100000000000, allocation_limit=150000,
            performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env['RUST_INTERP_VM_STATS'] = '1'
        fixture_env = dict(env, RI_ENV_TEXT='hello=λ', RI_ENV_EMPTY='', RI_ENV_RAW=os.fsdecode(bytes([0x80, 61, 0xfe])))
        fixture_env[os.fsdecode(b'RI_ENV_\xff')] = 'raw-name'; fixture_env.pop('RI_ENV_MISSING', None)
        rows = []

        def invoke(label, command, success=True, selected=env):
            require_space(ROOT, 8)
            command = list(map(str, command))
            child, out, err = capture(command, cwd=ROOT, env=selected,
                                     receipt_path=work / 'active.json', receipt=dict(label=label))
            (work / (label + '.stdout')).write_text(out); (work / (label + '.stderr')).write_text(err)
            rows.append(dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
                stdout_sha256=sha(work / (label + '.stdout')), stderr_sha256=sha(work / (label + '.stderr'))))
            write(work / 'records.json', rows)
            assert (child.returncode == 0) == success, (label, err[-2000:])
            return out, err

        missing = work / 'must-not-be-opened.rbc'
        invalid = [(['--engine', 'jit', '--jit-code-limit', n, missing], message) for n, message in
                   [('33554433', 'exceeds supported maximum'), ('-1', 'invalid digit'),
                    ('9999999999999999999999999999', 'too large'), ('1.5', 'invalid digit')]]
        invalid += [(['--engine', 'jit', '--jit-code-limit', '0', '--jit-code-limit', '1', missing], 'duplicate JIT code limit'),
                    (['--engine', 'jit', '--jit-code-limit'], 'missing JIT code limit'),
                    (['--jit-code-limit', '0', missing], 'requires --engine=jit'),
                    (['--rust-interp-capabilities', missing], 'capabilities take no arguments')]
        for index, (args, message) in enumerate(invalid):
            out, err = invoke('invalid-' + str(index), [vm, *args], False)
            assert out == '' and message in err and not re.search(r'\binstructions=\d+', err)
        out, err = invoke('old-vm', [sys.executable, ROOT / 'scripts/interpreter.py',
            '--manifest-path', work / 'absent.toml', '--package', 'fixture', '--entry', 'rust_interp_entry',
            '--engine', 'jit', '--jit-code-limit', '33554432', '--tool-key', build['composition']['compiler_source_key']], False)
        assert out == '' and 'selected VM does not support the requested --jit-code-limit' in err
        assert 'Checking ' not in err and 'Compiling ' not in err and 'rust-interp-launch: ' not in err
        small_results = []
        for label, limit in [('default', None), ('zero', 0), ('16', 16777216), ('32', 33554432)]:
            flags = [] if limit is None else ['--jit-code-limit', str(limit)]
            out, err = invoke('small-' + label, [vm, '--engine', 'jit', '--jit-resumable-calls',
                '--jit-persistent-registers', *flags, small, '0'], selected=fixture_env)
            assert out == expected
            stats = {k: int(v) for k, v in re.findall(r'\b([a-z_]+)=(\d+)\b', err)}
            effective = 16777216 if limit is None else limit
            assert stats['jit_bytes'] <= effective and (stats['jit_bytes'] == 0) == (limit == 0)
            small_results.append(dict(mode=label, code_limit_bytes=effective, statistics=stats))
        suites = []
        for label, limit in [('default', None), ('16', 16777216), ('32', 33554432)]:
            path = work / ('parser-' + label + '-suite.json')
            flags = [] if limit is None else ['--jit-code-limit', str(limit)]
            invoke('parser-' + label, [vm, '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                *flags, '--instruction-limit', '100000000000', '--allocation-limit', '150000',
                '--isolated-batch', 'prepared', '--suite-report', path, '--suite-catalog', catalog,
                '--suite-workers', '2', artifact])
            report, digest = read_report(path)
            assert len(validate_report(report, names, 'prepared', True)) == 114
            validate_runtime_limits(report, 100000000000, 150000, jit_code_limit=limit, required=True)
            assert report['workers'] == report['requested_workers'] == 2
            effective = 16777216 if limit is None else limit
            peak = max(t['jit_bytes'] for t in report['tests'])
            declines = max(t['jit_declined_functions'] for t in report['tests'])
            assert peak <= effective
            suites.append(dict(mode=label, tests=114, code_limit_bytes=effective,
                maximum_owner_code_bytes=peak, maximum_owner_declines=declines, suite_sha256=digest))
            print('parser', label, '114 passed', peak, 'bytes', declines, 'declines', flush=True)
        assert suites[2]['maximum_owner_code_bytes'] > 16777216
        assert all(sha(ROOT / p) == h for p, h in frozen.items()) and len(rows) == 16
        result = ROOT / 'results/parser-jit-capacity-boundaries-01'; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', commands=16, tool_key=key,
            invalid_vm_rejections=8, old_vm_rejected_before_cargo=True, small_fixture=small_results,
            parser=suites, all_original_parser_assertions_preserved=True,
            larger_configuration_exceeds_prior_code_bound=True, source_edits=0,
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            records_sha256=sha(work / 'records.json'), performance_measurement=False))


if __name__ == '__main__':
    main()
