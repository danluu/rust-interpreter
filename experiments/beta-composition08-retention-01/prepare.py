"""Read-only finite B308 retention discovery; no archive or payload copies."""
import ast
import json
import os
from pathlib import Path
import stat
import sys

import history
import retain as r

ROOT=history.ROOT
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')

def main():
    r.require(Path.cwd()==r.A and sys.dont_write_bytecode and not sys.flags.optimize,'explicit owner/Python')
    for path in [r.HERE/'inputs.json',r.HERE/'launch.json',r.WORK,r.OUT]:
        r.require(not path.exists() and not path.is_symlink(),'fresh retention proposal')
    files,routes,sources,directories={}, {},set(),{}
    def add(path,expected=None,archive=True):
        path=Path(path);before=r.stamp(path)
        r.require(path.resolve(strict=True)==path and stat.S_ISREG(before[2]) and before[3]<=r.BOUNDS['file_bytes'],'ordinary bounded evidence: '+str(path))
        row=dict(stamp=before,bytes=before[3],sha256=r.sha(path))
        r.require(r.stamp(path)==before,'evidence changed while hashed')
        if expected:
            r.require(row['sha256']==expected['sha256'],'historical evidence hash differs')
            if 'stamp' in expected:r.require(before==expected['stamp'],'historical evidence identity differs')
        r.require(str(path) not in files or files[str(path)]==row,'inconsistent evidence input')
        files[str(path)]=row
        if archive:
            # Only the complete exact B308 WORK may contain its tiny strip
            # fixture objects. No live B3, compiler, SDK or registry is selected.
            r.require(path.is_relative_to(history.WORK) or path.suffix not in ['.dylib','.rlib','.rmeta','.o','.xz'],'live payload excluded')
            sources.add(str(path))
        if path.suffix=='.py':ast.parse(path.read_bytes(),filename=str(path))
        r.require(len(files)<=r.BOUNDS['members']-1,'finite selected input count')
        return row
    def directory(path):
        names=r.members(path);directories[str(path)]=dict(members=names,excluded_future_outputs=[])
        for name in names:add(name)

    for path in [history.SOURCE,history.WORK,history.OUTER,history.LAUNCHER]:directory(path)
    rejected=r.A/'experiments/hir-options-hash-beta-composition-07'
    for name in ['plan.json','inputs.json','launch.json']:add(rejected/name)
    extras=[r.A/'.work/beta-composition-prelaunch-rejection-07.json',history.AUDIT,
        r.A/'.work/launch_beta_composition_08.py',r.A/'.work/wait_beta_composition_capacity_08.py',
        ROOT/'.work/root-beta-composition08-plan-verification-01.json',
        O/'.work/beta08-projection-source-review-01.json',r.OWNED,r.A/'scripts/supervise_experiment.py']
    for number in ['07','08']:
        extras += [r.A/f'.work/beta-composition-discovery-{number}.{stream}' for stream in ['stdout','stderr']]
    extras += [r.A/f'.work/beta-composition-capacity-wait-08.{suffix}' for suffix in ['json','stdout','stderr']]
    for suffix,source in [('', 'verify_beta_composition_08.py'),('-sdk-route-01','verify_beta_composition_08_sdk_route_01.py'),('-loader-projection-02','verify_beta_composition_08_loader_projection_02.py')]:
        extras.append(r.A/'.work'/source)
        if suffix:extras.append((r.A/'.work'/source).with_suffix('.diff'))
        extras += [r.A/f'.work/beta-composition-independent-verification-execution-08{suffix}.{ending}' for ending in ['json','stdout','stderr']]
    qualification=ROOT/'experiments/bounded-proof-snapshot-controls-01'
    for path in [qualification,ROOT/'experiments/bounded-proof-snapshots',
        ROOT/'.work/bounded-proof-snapshot-controls-01',
        ROOT/'.work/experiments/bounded-proof-snapshot-controls-supervisor-01',
        ROOT/'.work/proof-snapshot-controls-launch-execution-01']:directory(path)
    for path,row in r.read(qualification/'inputs.json')['files'].items():
        archive=path.startswith('/Users/danluu/dev/')
        if not archive:r.require(Path(path).name in ['python3.14','ps','lsof'],'only executor payload excluded')
        add(path,row,archive)
    routes.update(r.read(qualification/'inputs.json')['routes'])
    extras += [ROOT/'.work/launch_proof_snapshot_controls_01.py',
        r.A/'.work/proof-snapshot-controls-independent-verification-01.json',
        r.A/'.work/verify_proof_snapshot_controls_01.py',
        r.A/'.work/proof-snapshots-controls-source-review-01.json']
    extras += [r.A/f'.work/proof-snapshot-controls-verification-01.{stream}' for stream in ['stdout','stderr']]
    for path in extras:add(path)
    prior=r.A/'results/hir-options-hash-beta-producer-controls-02'
    for name in ['README.md','manifest.json','summary.json']:add(prior/name)
    directory(prior/'retention')
    prior_archive=add(prior/'evidence.tar.gz',archive=False)
    r.require(prior_archive['sha256']=='3fcc012772b6ff1da094fa0bad62bf01a653f388770efbf5423970b1180d8558','prior closed controls archive')
    for path in sorted(r.HERE.iterdir()):add(path)
    python=str(Path(sys.executable).resolve(strict=True));add(python,archive=False)
    for path in ['/opt/homebrew/bin/python3','/bin/ps','/usr/sbin/lsof']:
        target=str(Path(path).resolve(strict=True));add(target,archive=False);routes[path]=target
    observed=history.validate_all()
    original=r.read(qualification/'inputs.json')
    r.require(python==original['python'],'qualified Python executor')
    environment=dict(original['environment'],TMPDIR='/tmp')
    logical=sum(files[n]['bytes'] for n in sources)
    physical=sum(n for _,n in {(files[p]['sha256'],files[p]['bytes']) for p in sources})
    r.require(logical<r.BOUNDS['logical_bytes']-4*r.MIB and physical<r.BOUNDS['physical_bytes']-4*r.MIB,'finite proposed archive size')
    frozen=dict(status='prepared-unrun',owner=str(r.A),files=files,routes=routes,python=python,environment=environment,
        archive_sources=sorted(sources),directories=directories,history=observed,bounds=r.BOUNDS,
        absent_paths=[str(r.A/'.work/hir-options-hash-beta-composition-07'),str(r.A/'.work/experiments/hir-options-hash-beta-composition-supervisor-07')],
        input_bytes=sum(row['bytes'] for row in files.values()),archive_logical_bytes_before_freeze=logical,
        archive_physical_bytes_before_freeze=physical,
        prior_archives=[dict(path=str(prior/'evidence.tar.gz'),sha256=prior_archive['sha256'],bytes=prior_archive['bytes'],included=False)],
        payload_exclusions=dict(files={name:row for name,row in files.items() if name not in sources},
            explanation='Only executor bytes and the already retained producer-control archive are hash-bound references. No live B3/compiler/SDK/registry payload is selected. All completed B308 WORK, including its two strip fixture objects, and every compressed proof blob are retained.'),
        capacity=dict(entry_gib=9,stop_gib=9,floor_gib=8,reservation_bytes=r.BOUNDS['expanded_bytes']),
        canonical_lock='/Users/danluu/dev/rust-interp/.work/benchmark.lock',wait_seconds=600,workload_children=0)
    r.guard(frozen,history)
    def write(path,value):
        with path.open('x') as stream:
            json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    write(r.HERE/'inputs.json',frozen)
    launch=dict(status='prepared-unrun-awaiting-review',owner=str(r.A),environment=environment,
        command=[python,'-B',str(r.A/'scripts/supervise_experiment.py'),'--run-id','beta-composition08-retention-supervisor-01','--',
            python,'-B',str(r.HERE/'retain.py'),'--inputs-sha256',r.sha(r.HERE/'inputs.json')],
        inputs_sha256=r.sha(r.HERE/'inputs.json'),helper_sha256=r.sha(r.HERE/'retain.py'),
        expected_workload_children=0,bounds=r.BOUNDS,capacity=frozen['capacity'])
    write(r.HERE/'launch.json',launch)
    print(json.dumps(dict(status='prepared-unrun',files=len(files),archive_members=len(sources)+1,logical_bytes=logical,
        physical_bytes=physical,inputs_sha256=launch['inputs_sha256'],launch_sha256=r.sha(r.HERE/'launch.json')),indent=2))

if __name__=='__main__':main()
