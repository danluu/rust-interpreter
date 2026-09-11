#!/usr/bin/env python3
"""Qualify resumable-call CLI flags and historical workflow receipts."""
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
        'scripts/interpreter.py': '--jit-resumable-calls',
        'scripts/bench_e2e_workflow.py': '--candidate-jit-resumable-calls',
        'scripts/bench_workflow_corpus.py': '--candidate-jit-resumable-calls',
        'benchmarks/experiments/bounded-native-calls/run_saved.py': '--candidate-resumable-calls',
    }
    paths = [Path(__file__), vm, artifact, *[ROOT / p for p in scripts],
             ROOT / 'scripts/verify_repeated_workflow.py',
             ROOT / 'benchmarks/experiments/bounded-native-calls/evaluate_gates.py']
    frozen = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    for p in paths:
        if p.suffix == '.py':
            compile(p.read_text(), str(p), 'exec')
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    (work / 'plan.json').write_text(json.dumps(dict(tool_key=args.tool_key, frozen=frozen), indent=2) + '\n')
    checks = []

    def check(command, code, message):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
        checks.append(dict(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
        (work / 'commands.json').write_text(json.dumps(checks, indent=2) + '\n')
        require(result.returncode == code and message in result.stdout + result.stderr, 'CLI expectation failed')

    for script, flag in scripts.items():
        check([sys.executable, script, '--help'], 0, flag)
    for script in ['scripts/bench_e2e_workflow.py', 'scripts/bench_workflow_corpus.py']:
        for flag in ['--baseline-jit-resumable-calls', '--baseline-jit-persistent-registers']:
            check([sys.executable, script, '--help'], 0, flag)
    for flag in ['--baseline-jit-resumable-calls', '--baseline-jit-persistent-registers']:
        for extra in [[], ['--baseline-tool-key', 'unused', '--comparison-engine', 'interpreter']]:
            check([sys.executable, 'scripts/bench_e2e_workflow.py', flag, *extra], 2,
                  flag + ' requires a paired JIT comparison')
    launcher = [sys.executable, 'scripts/interpreter.py', '--package', 'unused', '--entry', 'unused']
    check([*launcher, '--jit-resumable-calls'], 2, '--jit-resumable-calls requires --engine=jit')
    check([*launcher, '--engine', 'jit', '--jit-resumable-calls', '--jit-native-calls'], 2,
          '--jit-resumable-calls cannot be combined with native tree/stub calls')
    check([sys.executable, 'scripts/bench_e2e_workflow.py', '--candidate-jit-resumable-calls'], 2,
          '--candidate-jit-resumable-calls requires a paired JIT comparison')
    check([str(vm), '--jit-resumable-calls', str(artifact)], 1, 'resumable calls require the JIT engine')
    for extra in [[], ['--jit-persistent-registers']]:
        check([str(vm), '--engine', 'jit', '--jit-resumable-calls', *extra,
               '--instruction-limit', '0', str(artifact)], 1, 'interpreter instruction limit exceeded')
    for extra in [[], ['--jit-native-call-stubs']]:
        check([str(vm), '--engine', 'jit', '--jit-resumable-calls', '--jit-native-calls',
               *extra, str(artifact)], 1, 'resumable calls cannot be combined with native tree/stub calls')
    historical = []
    for run in ['native-region-e2e-01', 'persistent-e2e-01', 'resumable-bulk-e2e-02']:
        for label in ['folded-literal-trie', 'token-phrase']:
            path = ROOT / 'results' / (run + '-' + label) / 'summary.json'
            report = json.loads(path.read_text())
            require(verify(report) == json.loads(path.with_name('verification.json').read_text()), 'historical receipt changed')
            for mode in ['baseline', 'candidate']:
                for option in ['jit_resumable_calls', 'jit_persistent_registers']:
                    wrong = copy.deepcopy(report)
                    wrong['tool_builds'][mode][option] = not report['tool_builds'][mode].get(option, False)
                    try:
                        verify(wrong)
                    except RuntimeError as error:
                        require(str(error) == 'recorded runtime option differs', 'unexpected rejection')
                    else:
                        raise RuntimeError('verifier accepted a false runtime-option claim')
            historical.append(dict(report=str(path.relative_to(ROOT)), receipt_unchanged=True,
                                   false_flag_rejections=4))
    require(all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest for p, digest in frozen.items()), 'frozen input changed')
    out = ROOT / 'results' / args.run_id
    out.mkdir(exist_ok=False)
    (out / 'summary.json').write_text(json.dumps(dict(status='passed', tool_key=args.tool_key,
        checks=checks, historical=historical, frozen=frozen, performance_measurement=False), indent=2) + '\n')
    print(json.dumps(dict(status='passed', cli_checks=len(checks), historical_checks=len(historical))))


if __name__ == '__main__':
    main()
