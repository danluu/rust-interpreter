"""Compose two exact qualified components; no compilation or guest execution."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from workflow_io import require_space, write_json as write

VM_KEY = '02bd8087e8a973bfb721760da591bfe6417a93ddab2bb85a47afffe4ea73bc6e'
FRONT_KEY = '923ad6d94c365365f15322ee65d32dca6ba9ccc4fd07a8147111329ea1955c86'
VM_SHA = '4e9c9af6d32e3998e6308b8cc5142526f60631a05fa7fa01c93e50f52daff2d6'


def rust_input(name):
    return name in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'] or (
        name.startswith('crates/') and (name.endswith('.rs') or name.endswith('/Cargo.toml')))


def verify_sources(current, runtime, frontend):
    expected = {p: h for p, h in runtime.items() if rust_input(p)}
    assert current == expected, 'current Rust/Cargo source differs from the qualified runtime build'
    selected = {p: h for p, h in current.items() if not p.startswith('crates/bytecode/')}
    prior = {p: h for p, h in frontend.items() if rust_input(p) and not p.startswith('crates/bytecode/')}
    assert selected == prior, 'compiler/shared source differs from the qualified main compiler build'
    return True


def verify_completed(proof):
    assert proof['status'] == 'passed' and proof['all_five_gates_passed']
    assert proof['commands'] == 726 and proof['previous_commands'] == 594 and proof['new_commands'] == 132
    assert proof['completed_cases'] == ['token', 'folded', 'pgrust', 'rg-aot', 'nushell']
    assert proof['unstarted_cases'] == [] and proof['no_completed_case_repeated']
    assert proof['final_source_and_input_audit_passed']
    return True


def component_binaries(vm, front):
    names = {'rust-interp-vm', 'rust-interp-mir-export', 'rust-interp-rustc-wrapper'}
    assert set(vm) == set(front) == names
    assert vm['rust-interp-vm'] == VM_SHA
    assert front['rust-interp-mir-export'] == 'cccdc9092c63bad8f0a8c8bd7bb8ca88e21bf7c83895749ed21ac1cfdf9e4783'
    assert front['rust-interp-rustc-wrapper'] == '10fb76569f0e1b13c10090a84f47be539cc27d1c6546f9e1f29d1029adfa57fa'
    return dict(front, **{'rust-interp-vm': VM_SHA})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'guarded-ranges-main-compose-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT).strip()
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        proof_path = ROOT / 'results/guarded-ranges-admission-resume-01/summary.json'
        proof = json.loads(proof_path.read_text())
        verify_completed(proof)
        old = ROOT / proof['raw']
        for name in ['plan', 'records', 'final-audit']:
            assert sha(old / (name + '.json')) == proof[name.replace('-', '_') + '_sha256']
        terminal = ROOT / '.work/experiments/guarded-ranges-admission-resume-01/status.json'
        status = json.loads(terminal.read_text())
        assert status['owner'] == str(ROOT) and status['status'] == 'finished' and status['returncode'] == 0
        assert sha(terminal.with_name('plan.json')) == status['plan_sha256']
        assert sha(terminal.with_name('command.log')) == status['log_sha256']
        paths = [proof_path, terminal, terminal.with_name('plan.json'), terminal.with_name('command.log')]
        paths += [old / (name + '.json') for name in ['plan', 'records', 'final-audit']]
        for row in json.loads((old / 'records.json').read_text()):
            case_path = ROOT / 'results' / ('guarded-ranges-edit-' + row['case'] + '-01') / 'summary.json'
            assert sha(case_path) == row['summary_sha256']
            assert json.loads(case_path.read_text())['gate_passed']
            paths.append(case_path)
        builds, folders, manifests = {}, {}, {}
        for name, run, key in [('vm', 'guarded-ranges-build-01', VM_KEY),
                               ('frontend', 'reuse-misses-main-build-01', FRONT_KEY)]:
            report_path = ROOT / 'results' / run / 'summary.json'
            build = json.loads(report_path.read_text())
            assert build['status'] == 'passed' and build['tool_key'] == key
            plan_path = ROOT / build['raw'] / 'plan.json'
            assert sha(plan_path) == build['source_manifest_sha256']
            builds[name] = build
            manifests[name] = json.loads(plan_path.read_text())['frozen']
            folder, _ = installed_tools(key)
            folders[name] = folder
            assert json.loads((folder / 'ready.json').read_text()) == build['binaries']
            for binary, digest in build['binaries'].items():
                assert sha(folder / binary) == digest
            paths += [report_path, plan_path, folder / 'ready.json', folder / 'capabilities.json', folder / 'source.json']
            paths += [folder / binary for binary in build['binaries']]
        assert builds['vm']['tests'] == {label: dict(passed=478, ignored=1) for label in ['test-debug', 'test-release']}
        assert builds['frontend']['tests'] == {'test-debug': 88, 'test-release': 88}
        rust = [ROOT / name for name in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml']]
        rust += [p for p in (ROOT / 'crates').rglob('*') if p.is_file() and rust_input(str(p.relative_to(ROOT)))]
        current = {str(p.relative_to(ROOT)): sha(p) for p in rust}
        verify_sources(current, manifests['vm'], manifests['frontend'])
        paths += rust + [p for p in Path(__file__).parent.rglob('*') if p.is_file()]
        for run, expected in [('guarded-ranges-validation-repair-01', 222), ('reuse-misses-main-qualification-01', None)]:
            path = ROOT / 'results' / run / 'summary.json'
            receipt = json.loads(path.read_text())
            assert receipt['status'] == 'passed'
            if expected is not None:
                assert receipt['commands'] == expected
                for stage in receipt['stages'].values():
                    part = ROOT / stage['path']
                    assert sha(part) == stage['sha256']
                    paths.append(part)
            else:
                assert receipt['tool_key'] == FRONT_KEY and receipt['compiler_fixture_commands'] == 196
                for name in ['plan', 'records']:
                    part = ROOT / receipt['raw'] / (name + '.json')
                    assert sha(part) == receipt[name + '_sha256']
                    paths.append(part)
                for name, digest in receipt['compiler_command_files'].items():
                    assert sha(ROOT / name) == digest
                    paths.append(ROOT / name)
            paths.append(path)
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        binaries = component_binaries(builds['vm']['binaries'], builds['frontend']['binaries'])
        composition = dict(kind='guarded-ranges-main-integration', schema_version=1, source_commit=source,
                           runtime_key=VM_KEY, exporter_and_wrapper_key=FRONT_KEY, binaries=binaries)
        key = hashlib.sha256(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_commit=source, frozen=frozen,
                                     composition=composition, performance_measurement=False, new_builds=0, new_guest_commands=0))
        with (ROOT / '.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication, 45)
            installed = ROOT / '.work/interpreter-tools' / key
            installed.mkdir(exist_ok=False)
            for name, digest in binaries.items():
                shutil.copy2(folders['vm' if name == 'rust-interp-vm' else 'frontend'] / name, installed / name)
                assert sha(installed / name) == digest
            caps = json.loads((folders['frontend'] / 'capabilities.json').read_text())
            assert caps['schema_version'] == 1 and caps['tool_key'] == FRONT_KEY
            assert caps['exporter_sha256'] == binaries['rust-interp-mir-export']
            caps.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
            write(installed / 'capabilities.json', caps)
            write(installed / 'source.json', dict(tool_key=key, composition=composition, files=current,
                                                source_commit=source, source=str(ROOT),
                                                key_algorithm='SHA256 of canonical composition JSON'))
            assert all(sha(ROOT / p) == digest for p, digest in frozen.items())
            write(installed / 'ready.json', binaries)
        result = ROOT / 'results' / args.run_id
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', tool_key=key, binaries=binaries, composition=composition,
              source_commit=source, tests=builds['vm']['tests'], tests_reused_from='guarded-ranges-build-01',
              frontend_tests_reused_from='reuse-misses-main-build-01', performance_measurement=False,
              new_builds=0, new_guest_commands=0, raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json')))
        print(key, flush=True)


if __name__ == '__main__':
    main()
