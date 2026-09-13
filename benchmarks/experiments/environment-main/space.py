"""Bound fresh compatibility caches from the exact completed matching histories."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        proof_path = ROOT / 'results/environment-read-projects-02/summary.json'
        proof = json.loads(proof_path.read_text())
        audit_path = proof_path.with_name('final-audit.json')
        audit = json.loads(audit_path.read_text())
        assert proof['status'] == audit['status'] == 'passed' and proof['commands'] == 40
        raw = ROOT / proof['raw']
        assert sha(raw / 'records.json') == proof['records_sha256']
        rows = json.loads((raw / 'records.json').read_text())
        retirement_path = ROOT / 'results/environment-publication-nushell-retirement-01/summary.json'
        retirement = json.loads(retirement_path.read_text())
        assert retirement['status'] == 'passed' and retirement['all_protected_hashes_unchanged']
        retired = ROOT / retirement['raw']
        assert sha(retired / 'inventory.json') == retirement['inventory_sha256']
        assert sha(retired / 'protected.json') == retirement['protected_manifest_sha256']
        deleted = json.loads((retired / 'inventory.json').read_text())
        protected = json.loads((retired / 'protected.json').read_text())
        work = ROOT / '.work/environment-main-space-estimate-01'; work.mkdir(exist_ok=False)
        inventories, cases = [], []
        for case in proof['cases']:
            name = case['case']
            chosen = [r for r in rows if r['case'] == name]
            assert len(chosen) == 8
            roots = set()
            for r in chosen:
                launch, = [json.loads(line.split(': ', 1)[1]) for line in r['stderr'].splitlines()
                           if line.startswith('rust-interp-launch: ')]
                roots.add(launch['workspace_path'])
            root, = [Path(p) for p in roots]
            assert root.resolve(strict=True) == root and root.parent == ROOT / '.work/interpreter-workspaces' / proof['tool_key']
            files = [dict(path=str(p.relative_to(ROOT)), bytes=p.stat().st_size)
                     for p in root.rglob('*') if p.is_file()]
            assert all(not (ROOT / f['path']).is_symlink() for f in files)
            if name == 'nushell':
                assert all(r['path'].startswith(str(root.relative_to(ROOT)) + '/') for r in deleted)
                present = {r['path'] for r in files}
                assert not present.intersection(r['path'] for r in deleted)
                assert all(p in present for p in protected if p.startswith(str(root.relative_to(ROOT)) + '/'))
                files += [dict(path=r['path'], bytes=r['size'], retired=True) for r in deleted]
            size = sum(r['bytes'] for r in files)
            inventories.append(dict(case=name, files=files))
            cases.append(dict(case=name, logical_bytes=size, files=len(files),
                minimum_free_gib=8 + (size * 1.2 + 512 * 1024**2) / 1024**3))
        write(work / 'inventories.json', inventories)
        estimate = 8 + (sum(c['logical_bytes'] for c in cases) * 1.2 + 512 * 1024**2) / 1024**3
        result = ROOT / 'results/environment-main-space-estimate-01'; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', cases=cases, initial_free_gib=estimate,
            guest_commands=0, deleted_files=0, private_details_redacted=True,
            policy='8 GiB floor plus120% complete matching cache bytes and512 MiB transient allowance; recheck per case and8 GiB before each command',
            proof_sha256=sha(proof_path), final_audit_sha256=sha(audit_path),
            retirement_sha256=sha(retirement_path), raw=str(work.relative_to(ROOT)),
            inventories_sha256=sha(work / 'inventories.json'), script_sha256=sha(Path(__file__)),
            performance_measurement=False))
        print(json.dumps(dict(cases=cases, initial_free_gib=estimate)), flush=True)


if __name__ == '__main__':
    main()
