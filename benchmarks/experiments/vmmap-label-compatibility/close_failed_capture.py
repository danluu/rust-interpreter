"""Preserve the completed guest with no captured window before fixing vmmap parsing."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/adopted-current-runtime-sampling'))
from common import RUN, KEY, VM, read, verify, terminal, acquire_lock, sha, require_space, write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        raw = ROOT / '.work' / RUN
        plan = read(raw / 'plan.json')
        verify(plan)
        assert plan['tool_key'] == KEY and plan['vm_sha256'] == VM
        case, unstarted = plan['cases']
        assert case['label'] == 'block' and unstarted['label'] == 'exhaustive'
        assert not (ROOT / '.work' / unstarted['run_id']).exists()
        assert not (ROOT / '.work/experiments' / unstarted['run_id']).exists()
        sample = ROOT / '.work' / case['run_id']
        record, = read(sample / 'records.json')
        assert record['identity']['status'] == 'finished' and record['identity']['returncode'] == 0
        assert record['statistics']['jit_declined_functions'] == 0
        assert not record['mapped'] and record['sample_returncode'] is None
        assert not (sample / '0/sample.txt').exists()
        assert (sample / '0/vm.stdout').read_text() == '0\n'
        assert all(sha(sample / '0' / p) == h for p, h in record['files'].items())
        native = read(sample / '0/jit-code/map.json')
        assert native['pid'] == record['identity']['pid'] and native['profiled'] is False
        base, end = native['arena_base'], native['arena_base'] + native['code_bytes']
        diagnostics = read(sample / '0/commands.json')
        maps = [r for r in diagnostics if r['command'][0] == '/usr/bin/vmmap']
        assert len(maps) == 12 and all(r['returncode'] == 0 for r in maps)
        assert not any(r['command'][0] == '/usr/bin/sample' for r in diagnostics)
        for i in range(len(maps)):
            text = (sample / '0' / ('vmmap-' + str(i) + '.stdout')).read_text()
            assert re.search(r'^Process:\s+rust-interp-vm \[' + str(native['pid']) + r'\]$', text, re.M)
            assert not re.search(r'^VM_ALLOCATE\s+[0-9a-f]+-[0-9a-f]+.*?rwx/rwx', text, re.M)
            ranges = [(int(a, 16), int(b, 16)) for a, b in re.findall(
                r'^Untagged\s+([0-9a-f]+)-([0-9a-f]+).*?rwx/rwx', text, re.M)]
            assert any(lo <= base < end <= hi for lo, hi in ranges)
        evidence = dict(plan['frozen'])
        for path in sample.rglob('*'):
            if path.is_file():
                evidence[str(path.relative_to(ROOT))] = sha(path)
        for name, command in [('adopted-current-runtime-sampling-prepare-01', None), (case['run_id'], case['command'])]:
            outer, _ = terminal(name, command)
            for file in ['status.json', 'plan.json', 'command.log']:
                p = outer / file
                evidence[str(p.relative_to(ROOT))] = sha(p)
        for file in ['plan.json', 'vm-source-bindings.json']:
            p = raw / file
            evidence[str(p.relative_to(ROOT))] = sha(p)
        bindings = {}
        for path, digest in plan['frozen'].items():
            if not path.startswith(('.work/', 'results/')):
                blob = subprocess.check_output(['git', 'show', plan['source_revision'] + ':' + path], cwd=ROOT)
                assert hashlib.sha256(blob).hexdigest() == digest
                bindings[path] = dict(revision=plan['source_revision'], sha256=digest)
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        helper = str(Path(__file__).relative_to(ROOT))
        assert hashlib.sha256(subprocess.check_output(['git', 'show', revision + ':' + helper], cwd=ROOT)).hexdigest() == sha(Path(__file__))
        bindings[helper] = dict(revision=revision, sha256=sha(Path(__file__)))
        assert all(sha(ROOT / p) == h for p, h in evidence.items())
        write(raw / 'failed-capture-evidence.json', evidence)
        write(raw / 'failed-capture-sources.json', bindings)
        out = ROOT / 'results' / RUN
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='capture-failed', tool_key=KEY, vm_sha256=VM,
            guest_commands_completed=1, original_assertions_passed=True, usable_sample_windows=0,
            unstarted_cases=['exhaustive'], vmmap_commands=12, vmmap_commands_succeeded=12,
            reason='Owned emitted arena is reported as Untagged; sampler only recognizes VM_ALLOCATE',
            every_retained_vmmap_covers_actual_emitted_arena=True,
            raw=str(raw.relative_to(ROOT)), plan_sha256=sha(raw / 'plan.json'),
            evidence_sha256=sha(raw / 'failed-capture-evidence.json'),
            sources_sha256=sha(raw / 'failed-capture-sources.json'), performance_measurement=False))
        (out / 'terminal.json').write_bytes((ROOT / '.work/experiments' / case['run_id'] / 'status.json').read_bytes())
        write(out / 'closure.json', dict(status='closed', source_revision=revision,
            capture_passed=False, all_original_hashes_verified=True,
            summary_sha256=sha(out / 'summary.json'), terminal_sha256=sha(out / 'terminal.json'),
            evidence=str((raw / 'failed-capture-evidence.json').relative_to(ROOT)),
            evidence_sha256=sha(raw / 'failed-capture-evidence.json'),
            source_bindings=str((raw / 'failed-capture-sources.json').relative_to(ROOT)),
            source_bindings_sha256=sha(raw / 'failed-capture-sources.json'), new_guest_commands=0))
        print('Closed one passing guest with no sample; all12 maps show its Untagged arena; exhaustive unstarted', flush=True)


if __name__ == '__main__':
    main()
