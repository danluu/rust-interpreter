#!/usr/bin/env python3
"""Check persistent-register CLI controls and historical receipt verification."""
import argparse
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from interpreter import installed_tools
from verify_repeated_workflow import verify, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--tool-key', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ('.', '..'), 'invalid run ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    directory, _ = installed_tools(args.tool_key)
    vm = directory / 'rust-interp-vm'
    artifact = ROOT / '.work/runs/paired-scalar-packed-cache-folded-literal-trie-01/artifacts/candidate/0-0.rbc'
    scripts = {
        'scripts/interpreter.py': '--jit-persistent-registers',
        'scripts/bench_e2e_workflow.py': '--candidate-jit-persistent-registers',
        'scripts/bench_workflow_corpus.py': '--candidate-jit-persistent-registers',
        'scripts/sample_owned_vm.py': '--jit-persistent-registers',
        'benchmarks/experiments/bounded-native-calls/run_saved.py': '--candidate-persistent-registers',
    }
    paths = [Path(__file__), vm, artifact, *[ROOT / p for p in scripts],
             ROOT / 'scripts/verify_repeated_workflow.py']
    frozen = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    for p in paths:
        if p.suffix == '.py':
            compile(p.read_text(), str(p), 'exec')
    checks = []

    def check(command, code, message):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
        checks.append(dict(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
        require(result.returncode == code and message in result.stdout + result.stderr, 'CLI expectation failed')

    for script, flag in scripts.items():
        check([sys.executable, script, '--help'], 0, flag)
    check([sys.executable, 'scripts/interpreter.py', '--package', 'unused', '--entry', 'unused',
           '--jit-persistent-registers'], 2, '--jit-persistent-registers requires --engine=jit')
    check([sys.executable, 'scripts/bench_e2e_workflow.py', '--candidate-jit-persistent-registers'],
          2, '--candidate-jit-persistent-registers requires a paired JIT comparison')
    check([sys.executable, 'scripts/bench_e2e_workflow.py', '--candidate-jit-persistent-registers',
           '--candidate-jit-native-call-stubs'], 2, '--candidate-jit-native-call-stubs requires --candidate-jit-native-calls')
    check([str(vm), '--jit-persistent-registers', str(artifact)], 1, 'persistent registers require the JIT engine')
    check([str(vm), '--engine', 'jit', '--jit-persistent-registers', '--instruction-limit', '0', str(artifact)],
          1, 'interpreter instruction limit exceeded')
    historical = []
    for label in ['folded-literal-trie', 'token-phrase']:
        path = ROOT / 'results' / ('native-region-e2e-01-' + label) / 'summary.json'
        report = json.loads(path.read_text())
        require(verify(report) == json.loads(path.with_name('verification.json').read_text()), 'historical receipt changed')
        wrong = copy.deepcopy(report)
        wrong['tool_builds']['candidate']['jit_persistent_registers'] = True
        try:
            verify(wrong)
        except RuntimeError as error:
            require(str(error) == 'recorded runtime option differs', 'unexpected rejection')
        else:
            raise RuntimeError('verifier accepted a false runtime-option claim')
        historical.append(dict(report=str(path.relative_to(ROOT)), receipt_unchanged=True, false_flag_rejected=True))
    require(all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest for p, digest in frozen.items()), 'frozen input changed')
    out = ROOT / 'results' / args.run_id
    out.mkdir(exist_ok=False)
    (out / 'summary.json').write_text(json.dumps(dict(status='passed', tool_key=args.tool_key,
        checks=checks, historical=historical, frozen=frozen, performance_measurement=False), indent=2) + '\n')
    print(json.dumps(dict(status='passed', cli_checks=len(checks), historical_checks=len(historical))))


if __name__ == '__main__':
    main()
