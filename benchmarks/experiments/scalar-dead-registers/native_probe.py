"""Isolated std-only synthetic native qualification; no E2E timing claim."""
from pathlib import Path
import json, os, struct, subprocess, sys, time
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'benchmarks/experiments/scalar-word-census'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write
import words

NAME = 'scalar-dead-registers-native-probe-01'


def relocate(before, dead):
    dead = set(dead); offsets = []; count = 0
    for pc in range(len(before)):
        offsets.append(count); count += pc not in dead
    result = []
    for pc, word in enumerate(before):
        if pc in dead: continue
        op = words.decode(word, pc, len(before))
        if op.kind in ['branch', 'condition']:
            bits, shift = (26, 0) if op.kind == 'branch' else (19, 5)
            delta = offsets[op.successors[0]] - offsets[pc]
            assert -(1 << (bits-1)) <= delta < (1 << (bits-1))
            mask = (1 << bits) - 1
            word = (word & ~(mask << shift)) | ((delta & mask) << shift)
        result.append(word)
    return result


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 10)
        source = Path(__file__).with_name('native_probe.rs')
        scalar = ROOT/'crates/bytecode/src/scalar'
        tests = scalar/'native_dead_tests.rs'
        census_path = ROOT/'results/scalar-word-census-03/summary.json'
        census = json.loads(census_path.read_text()); assert census['status'] == 'passed'
        census_plan = ROOT/census['raw']/'plan.json'; assert sha(census_plan) == census['plan_sha256']
        assert sha(Path(words.__file__)) == json.loads(census_plan.read_text())['frozen'][str(Path(words.__file__).relative_to(ROOT))]
        qualified_path = ROOT/'results/scalar-call-guards-profile-01/summary.json'
        qualified = json.loads(qualified_path.read_text()); assert qualified['status'] == 'passed'
        paths = [source, tests, scalar/'native_dead.rs', scalar/'native_memory.rs', scalar/'native_leaf.rs', Path(__file__), Path(__file__).with_name('PLAN.md'),
                 Path(words.__file__), census_path, census_plan, qualified_path,
                 ROOT/'scripts/workflow_io.py', ROOT/'scripts/compare_saved_runtime.py', ROOT/'scripts/supervise_experiment.py']
        lines = []; bodies = []; total_before = total_after = 0
        for index, expected in enumerate(census['observation_sha256']):
            path = ROOT/census['raw']/f'observation-{index}.json'; assert sha(path) == expected; paths.append(path)
            observed = json.loads(path.read_text())
            q, = [r for r in qualified['comparisons'] if r['mode'] == 'candidate' and r['index'] == index]
            code_path = ROOT/q['code_path']; assert sha(code_path) == q['code_sha256']; paths.append(code_path)
            map_path = code_path.with_name('map.json'); assert sha(map_path) == q['map_sha256']; paths.append(map_path)
            code = code_path.read_bytes(); mapping = json.loads(map_path.read_text())
            spans = {r['function']: r for r in mapping['ranges'] if r['kind'] == 'scalar_leaf'}
            assert len(spans) == len(observed['bodies'])
            for body in observed['bodies']:
                span = spans[body['function']]
                before = [w for w, in struct.iter_unpack('<I', code[span['offset']:span['end']])]
                current = words.analyze(before)
                assert current['dead_word_offsets'] == body['dead_word_offsets']
                after = relocate(before, body['dead_word_offsets'])
                assert len(after) == len(before) - body['dead_words']
                lines.append(' '.join(f'{w:08x}' for w in before)+'\t'+' '.join(f'{w:08x}' for w in after))
                bodies.append(dict(index=index, function=body['function'], before=len(before), after=len(after)))
                total_before += len(before); total_after += len(after)
        assert len(lines) == 137
        work = ROOT/'.work'/NAME; work.mkdir(exist_ok=False)
        fixture = work/'fixtures.txt'; fixture.write_text('\n'.join(lines)+'\n'); paths.append(fixture)
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD']).strip()
        write(work/'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen, bodies=bodies,
            cargo_builds=0, shared_target_used=False, complete_original_project_guest_commands=0, host_compile_modules=3,
            admission_gib=10, minimum_child_gib=8, maximum_retained_output_bytes=512*1024**2))
        env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_', 'DYLD_'))
               and k not in ['RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUST_TEST_THREADS']}
        env.update(PYTHONDONTWRITEBYTECODE='1', SCALAR_DEAD_WORD_FIXTURES=str(fixture))
        records = []
        def invoke(label, command, build=False):
            require_space(ROOT, 10 if build else 8); started = time.time()
            child, out, err = capture(list(map(str,command)), cwd=ROOT, env=env,
                receipt_path=work/'active.json', receipt=dict(label=label))
            for stream, text in [('stdout',out), ('stderr',err)]: (work/(label+'.'+stream)).write_text(text)
            records.append(dict(label=label, command=list(map(str,command)), pid=child.pid,
                returncode=child.returncode, started_at=started, finished_at=time.time(),
                stdout_sha256=sha(work/(label+'.stdout')), stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json', records)
            assert child.returncode == 0, out+err
            assert all(sha(ROOT/p) == h for p,h in frozen.items())
            assert sum(p.stat().st_size for p in work.rglob('*') if p.is_file()) < 512*1024**2
            return out
        binaries = {}
        for profile, level in [('debug','0'), ('release','3')]:
            binary = work/('test-'+profile)
            invoke('compile-'+profile, ['rustc','+nightly-2026-09-08','--edition=2024','--test',source,
                '--crate-name','scalar_dead_native_probe','-C','opt-level='+level,'-C','debuginfo=0','-o',binary],True)
            binaries[str(binary.relative_to(ROOT))] = sha(binary)
            out = invoke('controls-'+profile, [binary, 'native_scalar_dead_registers', '--nocapture', '--test-threads=1'])
            assert '3 passed; 0 failed' in out and '35072 synthetic native body attempts' in out
            out = invoke('saved-'+profile, [binary,'--ignored','--exact','dead::tests::observe_saved_scalar_dead_register_words','--nocapture'])
            assert '137 exact saved bodies' in out and '1 passed; 0 failed' in out
        out = ROOT/'results'/NAME; out.mkdir(exist_ok=False)
        write(out/'summary.json', dict(status='passed', raw=str(work.relative_to(ROOT)), source_revision=revision,
            plan_sha256=sha(work/'plan.json'), records_sha256=sha(work/'records.json'), binaries=binaries,
            controls_per_profile=3, saved_bodies_per_profile=137, synthetic_native_attempts_per_profile=35072, commands=len(records),
            static_words_before=total_before, static_words_after=total_after,
            host_setup_seconds=sum(r['finished_at']-r['started_at'] for r in records),
            all_frozen_inputs_verified=True, cargo_builds=0, complete_original_project_guest_commands=0, synthetic_native_publications_per_profile=274,
            performance_measurement=False, full_workspace_qualification_pending=True))


if __name__ == '__main__': main()
