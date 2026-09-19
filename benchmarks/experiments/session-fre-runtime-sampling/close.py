"""Close retained native-PC evidence without another guest execution."""
import hashlib
import subprocess
import sys
from common import ROOT, KEY, VM, read, verify, terminal, run_name, acquire_lock, sha, require_space, write


def main():
    run, preparation, analysis = sys.argv[1:4]
    run_name(run)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        raw, out = ROOT / '.work' / run, ROOT / 'results' / run
        plan, summary = read(raw / 'plan.json'), read(out / 'summary.json')
        assert summary['status'] == 'passed' and summary['tool_key'] == KEY and summary['vm_sha256'] == VM
        assert summary['guest_commands'] == 2 and summary['new_guests_during_analysis'] == 0
        assert summary['reused_controls'] == 9 and summary['all_frozen_inputs_verified']
        assert sha(raw / 'plan.json') == summary['plan_sha256']
        assert sha(raw / 'analysis-records.json') == summary['records_sha256']
        assert sha(raw / 'sample-evidence.json') == summary['sample_evidence_sha256']
        verify(plan)
        bindings, evidence = {}, dict(read(raw / 'sample-evidence.json'))
        for path, digest in plan['frozen'].items():
            if path.startswith(('.work/', 'results/')):
                evidence[path] = digest
            else:
                blob = subprocess.check_output(['git', 'show', plan['source_revision'] + ':' + path], cwd=ROOT)
                assert hashlib.sha256(blob).hexdigest() == digest
                bindings[path] = dict(revision=plan['source_revision'], sha256=digest)
        archived = ROOT / plan['archived_vm_sources']
        assert sha(archived) == plan['archived_vm_sources_sha256'] == summary['archived_vm_sources_sha256']
        for path, row in read(archived).items():
            assert hashlib.sha256(subprocess.check_output(['git', 'show', row['revision'] + ':' + path], cwd=ROOT)).hexdigest() == row['sha256']
        evidence[str(archived.relative_to(ROOT))] = sha(archived)
        for name in [preparation, analysis]:
            outer, _ = terminal(name)
            for file in ['status.json', 'plan.json', 'command.log']:
                p = outer / file
                evidence[str(p.relative_to(ROOT))] = sha(p)
        rows = read(raw / 'analysis-records.json')
        assert len(rows) == 2 and [r['label'] for r in rows] == ['block', 'exhaustive']
        for row in rows:
            assert row['returncode'] == 0
            for stream in ['stdout', 'stderr']:
                p = raw / (row['label'] + '.' + stream)
                assert sha(p) == row[stream + '_sha256']
                evidence[str(p.relative_to(ROOT))] = sha(p)
        for case in summary['cases']:
            p = ROOT / case['report']
            assert sha(p) == case['report_sha256']
            report = read(p)
            assert report['status'] == 'passed' and report['reconstructed_same_process_code']
            assert report['profile_used_for_static_identity_only'] and not report['performance_measurement']
            evidence[str(p.relative_to(ROOT))] = sha(p)
            evidence.update(report['evidence'])
        assert all(sha(ROOT / path) == digest for path, digest in evidence.items())
        assert not (out / 'closure.json').exists()
        write(raw / 'closed-bindings.json', bindings)
        write(raw / 'closed-evidence.json', evidence)
        (out / 'terminal.json').write_bytes((ROOT / '.work/experiments' / analysis / 'status.json').read_bytes())
        write(out / 'closure.json', dict(status='closed', source_revision=plan['source_revision'],
            all_hashes_verified=True, frozen_inputs=len(plan['frozen']), archived_vm_sources=len(read(archived)),
            source_bindings=str((raw / 'closed-bindings.json').relative_to(ROOT)),
            source_bindings_sha256=sha(raw / 'closed-bindings.json'),
            evidence=str((raw / 'closed-evidence.json').relative_to(ROOT)),
            evidence_sha256=sha(raw / 'closed-evidence.json'),
            summary_sha256=sha(out / 'summary.json'), terminal_sha256=sha(out / 'terminal.json'),
            new_guest_commands=0, performance_measurement=False))
        print('Closed two candidate-runtime diagnostic windows;', len(evidence), 'evidence files', flush=True)


if __name__ == '__main__':
    main()
