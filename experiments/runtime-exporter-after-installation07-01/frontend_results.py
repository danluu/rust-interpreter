"""Corrected continuation predicates applied to fresh full18 frontend observations."""
import json
from pathlib import Path

def validate(c, t, recipe, work, plan, rows, actual):
    require, read = c.require, c.read
    observations, results = [], {}
    original = {name: (c.PREFIX / 'tests/fixtures/borrowck-cache' / name).read_bytes()
                for name in ('basic.rs', 'test_export.rs')}
    states = {'original': original['basic.rs']} | {name: original['basic.rs'] + extra for name, _, extra in recipe.errors}
    for row, outcome in zip(rows, actual, strict=True):
        name = row['name']; path = Path(outcome['path'])
        stdout, stderr = [(path.parent / stream).read_bytes() for stream in ('stdout', 'stderr')]
        require(b'internal compiler error' not in stderr, 'retained compiler panic')
        retained = work / (name + '.source.rs')
        require(retained.read_bytes() == (original['test_export.rs'] if name.startswith('test-') else states[row['state']]),
                'saved frontend source state differs')
        argv_record = recipe.argv_record(row, (work/'outputs') / (name + '-argv'))
        artifact = (work/'outputs') / (name + ('.json' if row['profile'] == 'list' else '.rbc'))
        allow = row['profile'] in ('basic', 'test') and row['error'] is None
        split = None
        if row['error'] == 'wrong-role':
            require(stderr == b"compiler executable does not match the exporter's runtime toolchain\n"
                    and not stdout and not artifact.exists(), 'wrong-role refusal differs')
        else:
            split = t.split_stderr(stderr, allow_telemetry=allow)
            diagnostics = [item['diagnostic'] for item in split['segments'] if item['channel'] == 'compiler']
            if row['error']:
                require(not artifact.exists() and any(item['level'] == 'error' for item in diagnostics),
                        'failed control lacks diagnostic or published bytecode')
                if row['error'] != 'metadata':
                    require(any((item.get('code') or {}).get('code') == row['error'] for item in diagnostics),
                            'required uncalled error is missing')
            elif name == 'exporter-capabilities':
                caps = json.loads(stdout)
                require(not stderr and caps['schema_version'] == 1 and caps['bytecode_version'] == 5
                        and caps['compiler_sysroot'] == str(c.RUNTIME) and caps['compiler_roles'] == plan['binding'],
                        'retained exporter capabilities differ')
            elif name == 'wrapper-roles':
                require(not stderr and json.loads(stdout) == plan['binding'], 'retained wrapper roles differ')
            elif row['profile'] == 'list':
                report = read(artifact); tests = report.get('tests')
                require(report.get('kind') == 'test-discovery' and report.get('schema_version') == 1
                        and report.get('strict_frontend') is True and report.get('executed') is False
                        and report.get('harness') == 'libtest' and report.get('target') == c.HOST and report.get('count') == 1
                        and isinstance(tests, list) and len(tests) == 1 and tests[0]['name'] == 'selected'
                        and tests[0]['status'] == 'classified' and tests[0]['ordinary_test'] is True,
                        'retained test discovery differs')
                require(Path(row['argv'][-1] + '.tests.json').read_bytes() == artifact.read_bytes(), 'test sidecar differs')
            elif row['profile'] != 'native':
                require(artifact.is_file() and artifact.stat().st_size > 0
                        and Path(row['argv'][-1] + '.rbc').read_bytes() == artifact.read_bytes(), 'RBC sidecar differs')
                telemetry = [item for item in split['segments'] if item['channel'] == 'telemetry']
                kinds = [item['kind'] for item in telemetry]
                base = ['aggregate-frames', 'scalar-frames', 'scalar-promotion']
                require(kinds in (base + ['cfg', 'export'], base + ['forwarding', 'cfg', 'export'])
                        and all(item['values']['stage'] == 'final' for item in telemetry if item['kind'] == 'forwarding')
                        and telemetry[-1]['values']['bytes'] == artifact.stat().st_size,
                        'fixed export telemetry sequence or bytecode size differs')
        results[name] = dict(stdout=stdout, stderr=stderr, artifact=artifact, split=split)
        observations.append(dict(name=name, receipt=str(path), receipt_sha256=c.file(path)['sha256'],
            source=c.file(retained), compiler_argv=argv_record, stderr_separation=split,
            artifact=c.file(artifact) if artifact.is_file() else None))
    pairs = [('basic-native', 'basic-export-explicit-R'), ('test-native', 'test-export'),
        ('uncalled-type-native', 'uncalled-type-export'), ('uncalled-borrow-native', 'uncalled-borrow-export'),
        ('restored-native', 'restored-export'), ('reject-build-sysroot-native', 'reject-build-sysroot-export'),
        ('basic-native', 'basic-export-default-R'), ('basic-native', 'wrapper-export-R'), ('test-native', 'test-discovery')]
    for left, right in pairs:
        require(results[left]['stdout'] == results[right]['stdout'], 'raw compiler stdout differs')
        t.compare_compiler_stderr(results[left]['split'], results[right]['split'])
    for name in ('basic-export-default-R', 'wrapper-export-R', 'restored-export'):
        require(results[name]['artifact'].read_bytes() == results['basic-export-explicit-R']['artifact'].read_bytes(),
                'explicit/default/wrapper/restored RBC differs')
    require((results['basic-native']['stdout'], results['basic-native']['stderr']) ==
            (results['restored-native']['stdout'], results['restored-native']['stderr']), 'restored native diagnostics differ')
    return c.write(work / 'frontend-results.json', dict(children=observations, comparison_pairs=pairs,
        raw_compiler_diagnostic_parity=True, whole_stderr_parity=False, telemetry_losslessly_retained=True,
        bytecode_parity=True, source_restored=True, guest_executions=0))
