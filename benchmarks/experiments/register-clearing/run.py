#!/usr/bin/env python3
"""Qualify and run storage attribution over six already captured public processes."""
import copy
import fcntl
import json
from pathlib import Path
import struct
import subprocess
import sys

from attribute import ROOT, ZERO_BULK, ZERO_RANGE, analyze, call_spans, require, sha, zero_spans

HERE = Path(__file__).resolve().parent
RUN = 'register-clearing-attribution-01'
ARTIFACTS = [
    ('folded', 'folded-literal-trie', '0b266be5fc28def9af2f43a4f2de3b5c543484a79a73479c674cdb7aec19669e'),
    ('token', 'token-phrase', 'c263d8924ec053275d9e807c4b5dce5d1a4c7082c9019e75b5c0532242008334'),
]


def qualify():
    positive = negative = 0
    pack = lambda words: struct.pack('<' + 'I' * len(words), *words)
    for memory in [0, 1, 63, 64, 128]:
        for registers, clears in [(0, False), (3, True), (4, True), (100, False)]:
            functions = [dict(id=0, name='caller', code_len=1, calls=[dict(pc=0, callee=1)]),
                dict(id=1, frame_size=memory, registers=registers, needs_initial_zeroes=clears)]
            row = dict(function=0, name='caller', pc=0, pc_end=1)
            first = ZERO_BULK if memory >= 64 else ZERO_RANGE
            second = (ZERO_BULK if registers >= 4 else ZERO_RANGE) if clears else ()
            data = pack(first + (0xd503201f,) + second)
            result = call_spans(data, row, functions)
            require([r[2] for r in result] == ['guest_memory'] + (['register_array'] if clears else []), 'fixture arenas differ')
            positive += 1
            for field, value in [('name', 'different'), ('pc', 1), ('pc_end', 2)]:
                altered = dict(row, **{field: value})
                try: call_spans(data, altered, functions)
                except RuntimeError: negative += 1
                else: raise RuntimeError('invalid caller was accepted')
            altered = copy.deepcopy(functions)
            altered[1]['needs_initial_zeroes'] = not clears
            try: call_spans(data, row, altered)
            except RuntimeError: negative += 1
            else: raise RuntimeError('invalid zero requirement was accepted')
    for pattern in [ZERO_RANGE, ZERO_BULK]:
        for i in range(len(pattern)):
            changed = list(pattern); changed[i] ^= 1
            require(not any(lo == 0 and hi == len(pattern) * 4 for lo, hi, _ in zero_spans(pack(changed))), 'mutated full sequence accepted')
            negative += 1
        for n in range(len(pattern)):
            require(not any(lo == 0 and hi == len(pattern) * 4 for lo, hi, _ in zero_spans(pack(pattern[:n]))), 'truncated full sequence accepted')
            negative += 1
    return dict(positive_cases=positive, rejected_mutants=negative)


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        work = ROOT / '.work' / RUN
        work.mkdir(exist_ok=False)
        tests = qualify()
        target = ROOT / '.work/register-clearing-target'
        command = ['cargo', '+nightly-2026-09-08', 'build', '--offline', '--release', '--jobs', '4',
                   '--manifest-path', str(HERE / 'Cargo.toml'), '--target-dir', str(target)]
        subprocess.run(command, cwd=ROOT, check=True)
        binary = target / 'release/register-clearing-census'
        results = []
        for label, workflow, digest in ARTIFACTS:
            artifact = ROOT / '.work/runs' / f'resumable-copy-original-e2e-01-{workflow}' / 'artifacts/candidate/cycle-0/0-0.rbc'
            require(sha(artifact) == digest, 'original artifact changed')
            metadata = work / f'{label}.json'
            with metadata.open('x') as out:
                subprocess.run([str(binary), str(artifact)], stdout=out, check=True)
            results.append(analyze(f'resumable-copy-{label}-sample-01', artifact, metadata))
        paths = [HERE / name for name in ['Cargo.toml', 'Cargo.lock', 'census.rs', 'attribute.py', 'run.py']]
        paths += [ROOT / p for p in ['crates/bytecode/src/registers.rs', 'crates/bytecode/src/jit/resumable.rs',
                                    'scripts/attribute_generated_sample.py', 'scripts/summarize_owned_sample.py']]
        result = dict(run_id=RUN, qualification=tests, build_command=command, diagnostic_binary_sha256=sha(binary),
            performance_measurement=False, production_change=False, samples=results,
            evidence={str(p.relative_to(ROOT)): sha(p) for p in paths},
            limitation='Reanalysis of six perturbed sample windows. Exact sequences classify current clearing cost; no speedup is predicted and no guest-memory initialization is removed.')
        out = ROOT / 'results' / RUN
        out.mkdir(exist_ok=False)
        (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
        lines = ['# Register versus guest-memory clearing', '',
                 'Typed direct calls and complete emitted sequences account for every previously attributed zeroing sample. The original six process captures and analyzers are unchanged.', '',
                 '| Workload | Thread samples | Guest memory | Register array |', '| --- | ---: | ---: | ---: |']
        for row in results:
            lines.append(f"| {row['run_id']} | {row['total_thread_samples']} | {row['percentages'].get('guest_memory', 0):.2f}% | {row['percentages'].get('register_array', 0):.2f}% |")
        lines += ['', result['limitation'], '']
        (out / 'assessment.md').write_text('\n'.join(lines))
        print(json.dumps(dict(qualification=tests, results=[dict(run=r['run_id'], counts=r['counts'], percentages=r['percentages'], top=r['hot_callees'][:5]) for r in results])))


if __name__ == '__main__':
    main()
