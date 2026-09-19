"""Bind saved nine-root inventory/selection and exact historical closures.

Review preparation only: no target imports, process probes, recursive target
walks or deletion. Current cache observation is lstat of the selected names;
installed copies are bound to saved SHA and current identity for future EOF
verification by the reviewed retirement controller.
"""
import ast
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
FIELDS = ('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
SELECTION = X/'.work/runtime-exporter07-closed-cache-preservation-selection-01.json'
SELECTION_SHA = 'e4832e773c3c4b33e77d99c1604b0eef51223d0a16f877a211d33939a1b612d7'
FROZEN = {}


def identity(path):
    s = Path(path).lstat(); return {k:getattr(s,'st_'+k) for k in FIELDS}


def bind(path, expected=None):
    path = Path(path); before = identity(path)
    assert path.resolve(strict=True) == path and stat.S_ISREG(before['mode']) and before['size'] <= 32*2**20
    data = path.read_bytes(); sha = hashlib.sha256(data).hexdigest()
    assert identity(path) == before and len(data) == before['size'] and (expected is None or sha == expected)
    row = dict(identity=before, sha256=sha); FROZEN[str(path)] = row
    return dict(path=str(path), file=row)


def read(path, expected=None):
    bind(path, expected); return json.loads(Path(path).read_bytes())


def main():
    assert not (HERE/'plan.json').exists()
    selection = read(SELECTION, SELECTION_SHA)
    triage = read(selection['triage']['path'], selection['triage']['sha256'])
    inv = read(selection['inventory_receipt']['path'], selection['inventory_receipt']['sha256'])
    execution = read(selection['inventory_execution']['path'], selection['inventory_execution']['sha256'])
    assert inv['status'] == 'inventoried-not-retired' and inv['files'] == 11408
    assert execution['status'] == 'finished' and execution['returncode'] == 0 and execution['child_may_be_live'] is False
    assert selection['selected_files'] == 1456 and selection['retained_files'] == 9952 and not selection['strict_cache_included']
    bind(selection['inventory_source']['path'], selection['inventory_source']['sha256'])
    scopes = selection['scopes']; roots = [s['root'] for s in scopes]
    candidates = {c['path']:c for c in triage['candidates'] if c['group'] != 'legacy-std-target-conditional'}
    assert set(roots) == set(candidates) and len(roots) == 9
    closures = []; pids = set(); copies = []; selected_allocated = 0
    for scope in scopes:
        ref = scope['inventory']; bind(ref['path'], ref['sha256'])
        packed = Path(ref['path']).read_bytes(); payload = gzip.decompress(packed)
        assert len(payload) == ref['expanded_bytes'] and hashlib.sha256(payload).hexdigest() == ref['expanded_sha256']
        saved = json.loads(payload); root = Path(scope['root']); row = candidates[str(root)]
        assert saved['root'] == str(root) and saved['outer_parent'] == scope['outer_parent'] and saved['rows']['.']['identity'] == scope['root_identity']
        selected = scope['selected_files']; retained = scope['retained_files']
        assert len(selected) == scope['selected_count'] and len(retained) == scope['retained_count']
        assert set(selected).isdisjoint(retained) and set(selected)|set(retained) == {n for n,r in saved['rows'].items() if r['kind']=='file'}
        allocated = 0
        for name in selected:
            path = root/name; assert name != '.' and not Path(name).is_absolute() and '..' not in Path(name).parts
            assert path.suffix in ['.rlib','.rmeta','.dylib','.o','.a']
            assert str(path) not in selection['selected_native_artifacts_retained_in_place']
            assert identity(path) == saved['rows'][name]['identity'] and saved['rows'][name]['identity']['nlink'] == 1
            allocated += path.lstat().st_blocks*512
        scope['selected_allocated_bytes_observation'] = allocated; selected_allocated += allocated
        if row['group'] == 'allocator-Cargo-cache':
            p = row['closed_execution']; d = read(p, triage['refs'][p]['sha256'])
            assert d['status'] == row['qualification_status'] and d['parent_lock_closed_at'] > d['admitted_at']
            assert d['signals'] == d['retries'] == 0
            if d['status'] == 'failed': assert not d['samples'] and not d['restorations']
            else: assert len(d['samples']) == 36 and d['decision'] == 'park-allocator-performance-path' and not d['unchanged_retry_allowed']
            proof = row['independent_readback']; bind(proof, triage['refs'][proof]['sha256']); pids.add(d['parent_pid'])
            closures.append(dict(root=str(root), path=p, status=d['status'], parent_pid=d['parent_pid'], closed_at=d['parent_lock_closed_at']))
        else:
            prior = row['closed_history']; pp = prior.get('process_path', prior.get('process')); rp = prior.get('result_path', prior.get('result'))
            process = read(pp, prior['process_sha256']); result = read(rp, prior['result_sha256'])
            assert process['status'] == 'finished' and process['returncode'] == 0
            assert process['pid'] == prior['pid'] and process['parent_pid'] == prior['parent_pid']
            assert process['started_at'] < process['finished_at'] == prior['finished_at']
            assert process['command'][process['command'].index('--target-dir')+1] == str(root)
            pids.update([process['pid'],process['parent_pid']])
            if root.name == 'target':
                owner = read(prior['owner_path'], prior['owner_sha256']); ready = read(prior['ready_path'], prior['ready_sha256'])
                assert owner['owner'] == ready['owner'] == str(ROOT) and ready['key'] == root.parent.name
                assert owner['identity'] == ready['identity'] and owner['run_id'] == ready['run_id']
                assert result['status'] == 'passed' and result['commands'] == 7 and result['key'] == ready['key'] and result['work'] == str(root.parent)
                assert len(row['retained_publication_copies']) == len(ready['metadata']) == 26
                commands = read(root.parent/'evidence/commands.json')
                assert [(v['label'],v['returncode']) for v in commands] == [('cargo-location',0),('cargo-version',0),('cargo-library-1',0),('cargo-library-2',0),('probe-native',1),('metadata',0),('probe-prepared',1)]
            else:
                assert process['compiler_key'] == result['compiler_key'] == root.name and process['phase'] == 'build-tools'
                assert len(row['retained_publication_copies']) == 3 and set(result['binaries']) == {'rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper'}
            for source, copy in row['retained_publication_copies'].items():
                src = Path(source); dst = Path(copy['preserved']); relative = str(src.relative_to(root))
                assert saved['rows'][relative]['sha256'] == copy['sha256']
                if root.name == 'target':
                    assert dst.parent == root.parent/'sysroot/lib/rustlib/aarch64-apple-darwin/lib' and src.name == dst.name
                    assert ready['metadata'][str(dst.relative_to(root.parent/'sysroot'))] == copy['sha256']
                else:
                    assert src.parent == root/'release' and dst == ROOT/'.work/interpreter-tools'/result['tool_key']/src.name
                    assert result['binaries'][src.name] == copy['sha256'] and relative in retained
                stamp = identity(dst); assert stat.S_ISREG(stamp['mode']) and dst.resolve(strict=True) == dst
                copies.append(dict(source=source, destination=str(dst), file=dict(identity=stamp,sha256=copy['sha256'])))
            closures.append(dict(root=str(root), path=pp, result=rp, status='finished', pid=process['pid'], parent_pid=process['parent_pid'], closed_at=process['finished_at']))
    original = read(ROOT/'experiments/hir-options-hash-intermediate-retirement/plan-02/plan.json')
    controls = {k:v['path'] for k,v in original['controls'].items()}
    for ref in original['controls'].values(): bind(ref['path'],ref['sha256'])
    freeze = read(controls['freeze']); receipt = read(controls['receipt']); audit = read(controls['audit'])
    assert receipt['status'] == 'passed' and receipt['controls_passed'] == audit['controls'] == 6 and audit['status'] == 'verified'
    qualified = O/'experiments/hir-options-hash-intermediate-retirement/fd_remove.py'; controls['qualified_remover_path'] = str(qualified)
    for name, row in freeze['files'].items(): bind(name,row['sha256'])
    for row in receipt['commands']:
        bind(row['path'],row['sha256']); p = Path(row['path']).parent
        for name in ['stdout','stderr']: bind(p/name)
    bind(Path(controls['receipt']).parent/'result.json',receipt['result_sha256'])
    remover = bind(ROOT/'experiments/hir-options-hash-intermediate-retirement/fd_remove.py',freeze['files'][str(qualified)]['sha256'])
    owned = bind(ROOT/'experiments/stable-cgu/owned_stage.py')
    for name in ['retire.py','prepare_plan.py']:
        ast.parse((HERE/name).read_text()); bind(HERE/name)
    for name, row in selection['selected_native_artifacts_retained_in_place'].items():
        for key in ['setup','raw']: bind(row[key]['path'],row[key]['sha256'])
    routes = {}
    for name in ['/opt/homebrew/bin/python3','/bin/ps','/usr/sbin/lsof']:
        p = Path(name); resolved = p.resolve(strict=True); bind(resolved)
        routes[name] = dict(identity=identity(p),resolved=str(resolved))
    environment = dict(HOME='/Users/danluu',LANG='C',LC_ALL='C',PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHON_COLORS='0')
    if '__CF_USER_TEXT_ENCODING' in os.environ: environment['__CF_USER_TEXT_ENCODING'] = os.environ['__CF_USER_TEXT_ENCODING']
    commands = [dict(label=f'open-handles-{i:02d}',argv=['/usr/sbin/lsof','-nP','+D',r]) for i,r in enumerate(roots)]
    commands.append(dict(label='closed-historical-pids',argv=['/bin/ps','-p',','.join(map(str,sorted(pids))),'-o','pid=,ppid=,pgid=,lstart=,tty=,command=']))
    plan = dict(status='concrete-unrun-partial-retirement-plan',observed_at=time.time(),owner='/root/workspace_capacity',source_owner='/root',
        work=str(X/'.work/runtime-exporter07-closed-cache-retirement-01'),remover=remover,owned_stage=owned,controls=controls,
        scopes=scopes,selected_files=1456,retained_files=9952,remove_directories=False,strict_cache_included=False,
        selected_allocated_bytes_observation=selected_allocated,selected_logical_bytes=selection['selected_logical_bytes'],
        environment=environment,python=routes['/opt/homebrew/bin/python3']['resolved'],platform=list(os.uname()),routes=routes,
        frozen_files=FROZEN,closed_histories=closures,published_copies=copies,commands=commands,historical_pids=sorted(pids),
        capacity=dict(entry_bytes=9*2**30+32*2**20,stop_bytes=9*2**30,running_floor_bytes=8*2**30,evidence_reserve_bytes=32*2**20),
        transition=dict(selection=dict(path=str(SELECTION),sha256=SELECTION_SHA),removed_files=1456,retained_files=9952,
            all_directories_retained=True,closed_histories_preserved=True,old_cache_snapshots_become_historical=True,
            preserved_outside_roots=selection['preserve_complete_outside_roots'],owner_acknowledgments=selection['owner_acknowledgments'],
            excluded_legacy=selection['excluded_legacy'],installed_providers_untouched=True,strict_cache_included=False),
        limitations=['Allocation observations are not APFS extent guarantees or a capacity reservation. Only current free bytes decide future23GiB admission.',
            'Exact ps/lsof observations are point-in-time only. Any returned historical PID refuses retirement; no PID-reuse inference or signals.',
            'A failed probe may still hold inherited canonical FD; preserve unclosed status, do not retry or proceed.',
            'No full outside-provider tree walk. Exact saved references and84 retained installed copies are checked; all9,952 in-scope retained files receive full EOF before/after.'])
    data = (json.dumps(plan,sort_keys=True,indent=2)+'\n').encode()
    with (HERE/'plan.json').open('xb') as out: out.write(data)
    assert (HERE/'plan.json').read_bytes() == data
    print(json.dumps(dict(path=str(HERE/'plan.json'),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),frozen_files=len(FROZEN),published_copies=len(copies),selected_allocated_bytes=selected_allocated),sort_keys=True))


if __name__ == '__main__': main()
