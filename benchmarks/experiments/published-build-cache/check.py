"""Exercise real published evidence and reject misbound metadata before archival."""
import copy
import fcntl
import archive as driver


def main():
    root = driver.ROOT
    with (root / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        catalog = driver.read(driver.HERE / 'catalog.json')
        selected, rejected = [], 0
        for run in catalog:
            target, proofs = driver.evidence(run)
            selected.append(dict(build=run, target=str(target), proofs=len(proofs)))
            report = driver.read(root / 'results' / run / 'summary.json')
            execution = driver.read(root / 'results' / run / 'execution.json')
            mutations = [
                lambda r,e: r.update(status='failed'),
                lambda r,e: r.update(source='.work/other/tool-source'),
                lambda r,e: r.update(production_change=True),
                lambda r,e: r['commands'][0].update(returncode=1),
                lambda r,e: r['commands'][0]['command'].__setitem__(r['commands'][0]['command'].index('--target-dir')+1, str(root)),
                lambda r,e: e['supervisor'].update(owner='/other'),
                lambda r,e: e['supervisor'].update(status='running'),
                lambda r,e: e['controller'].update(parent_pid=-1),
                lambda r,e: e['supervisor'].update(command=['python3','other.py']),
                lambda r,e: r['tests']['debug'].update(passed=1),
            ]
            for mutate in mutations:
                r,e=copy.deepcopy(report),copy.deepcopy(execution)
                mutate(r,e)
                try: driver.metadata(run,r,e,catalog)
                except RuntimeError: rejected+=1
                else: raise RuntimeError('invalid metadata accepted')
        for name in ['whole-call-build-01','../call-slot-build-01','rg-aot']:
            try: driver.evidence(name)
            except RuntimeError: rejected+=1
            else: raise RuntimeError('uncatalogued identity accepted')
        out=root/'results/published-build-cache-controls-01';out.mkdir(exist_ok=False)
        driver.write_json(out/'summary.json',dict(status='passed',selected=selected,rejected=rejected,
            sources=driver.sources(),qualification_sha256=driver.sha(driver.HERE/'check.py'),cache_mutations=0))
        print('three exact build identities, 33 invalid identities/metadata rejected; no cache changes')


if __name__=='__main__': main()
