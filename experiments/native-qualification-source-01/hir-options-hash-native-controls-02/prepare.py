#!/usr/bin/env python3
"""Source-only native20 discovery. Actual passed B3/audit required before invocation.

No provider probes, compilation or fixture mutation. Future read-only preparation
uses canonical admission, and writes a fresh proposal for separate launch review.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import sys
import time

import run as n
from recipe import desired_commands

MAX_FILES=180000
MAX_BYTES=8*2**30
MAX_FILE_BYTES=2**30


def write(path, value):
    with path.open('xb') as stream:
        stream.write(n.comp.encoded(value)); stream.flush(); os.fsync(stream.fileno())


class Discovery:
    def __init__(self, audit, expected):
        self.files, self.links, self.routes, self.absent = {}, {}, {}, []
        self.snapshots = set()
        self.total = 0
        self.audit = Path(audit)
        n.require(self.audit.parent == n.A/'.work' and self.audit.suffix == '.json'
                  and n.owned.sha(self.audit) == expected, 'exact owned B3 audit required')
        self.add(self.audit, snapshot=True)
        self.audit_ref = dict(path=str(self.audit), sha256=expected)

    def add(self, path, *, snapshot=False):
        path = Path(path)
        n.require(path.stat().st_size <= MAX_FILE_BYTES, 'bounded native discovery file required')
        row = n.comp.check_file(dict(path=str(path), sha256=n.owned.sha(path)))
        value = {key:row[key] for key in ['identity','size','sha256']}
        n.require(str(path) not in self.files or self.files[str(path)] == value, 'discovery input changed')
        if str(path) not in self.files:
            self.total += value['size']
        self.files[str(path)] = value
        n.require(len(self.files) <= MAX_FILES and self.total <= MAX_BYTES, 'finite native discovery bound exceeded')
        if snapshot:
            n.require(value['size'] <= 64*2**20, 'bounded native source snapshot required')
            self.snapshots.add(str(path))
        n.owned.disk(n.A, 9)
        return path

    def inherited(self, path, value):
        self.add(path)
        n.require(self.files[str(path)] == value, 'qualified B3 input identity changed: '+str(path))

    def load(self, path, *, snapshot=True):
        return n.read(self.add(path, snapshot=snapshot))

    def discover(self):
        prior = self.load(n.COMPOSITION/'plan.json')
        frozen = self.load(n.COMPOSITION/'inputs.json')
        terminal = self.load(n.ASSEMBLY/'receipt.json')
        audit = self.load(self.audit)
        n.require(terminal['status'] == 'passed' and terminal['assembly_and_auxiliary_strip_qualified'] is True
                  and terminal['candidate_revision'] == n.REVISION and len(terminal['commands']) == 19,
                  'actual passed B3 assembly/strip required')
        n.require(audit['status'] == 'verified' and audit['receipt_sha256'] == n.owned.sha(n.ASSEMBLY/'receipt.json'),
                  'independent actual B3 audit does not bind this terminal')
        n.require(n.owned.sha(n.COMPOSITION/'inputs.json') == terminal['inputs_sha256']
                  and n.owned.sha(n.COMPOSITION/'plan.json') == frozen['plan_sha256'], 'B3 plan/freeze binding differs')
        self.load(n.COMPOSITION/'snapshot-plan.json')
        self.load(n.ASSEMBLY/'snapshot-plan.json')
        self.load(n.ASSEMBLY/'source-snapshots.json')
        n.require(n.owned.sha(n.COMPOSITION/'snapshot-plan.json') == n.owned.sha(n.ASSEMBLY/'snapshot-plan.json')
                  == terminal['snapshot_plan_sha256']
                  and n.owned.sha(n.ASSEMBLY/'source-snapshots.json') == terminal['source_snapshots_sha256'],
                  'B3 compressed proof projection/manifest association differs')
        for name, row in frozen['files'].items(): self.inherited(name, row)
        for name, row in frozen['links'].items():
            path = Path(name); info = path.lstat()
            stamp = [info.st_dev,info.st_ino,info.st_mode,info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_nlink]
            n.require(path.is_symlink() and stamp == row['stamp'] and os.readlink(path) == row['target']
                      and str(path.resolve(strict=True)) == row['resolved'], 'qualified B3 route changed')
            self.links[name] = row
        for name in frozen['absent_paths']:
            n.require(not Path(name).exists() and not Path(name).is_symlink(), 'qualified absence changed')
            self.absent.append(name)
        old_freeze = self.load(n.previous_attempt.SOURCE/'inputs.json')
        for name, row in old_freeze['files'].items(): self.inherited(name, row)
        n.require(all(self.links.get(name) == row for name,row in old_freeze['links'].items())
                  and set(old_freeze['absent_paths']) <= set(self.absent), 'original native route closure differs')
        prior_attempt = n.previous_attempt.validate(lambda p:self.add(p,snapshot=Path(p).suffix!='.gz' and Path(p).stat().st_size<=64*2**20), self.files)
        controls = n.stock_controls.validate(lambda p:self.add(p,snapshot=True),self.files)
        paths = n.recipe.paths(n.N)
        source = self.add(paths['source']/'compiler/rustc/src/main.rs',snapshot=True)
        _, derivation = n.stock_source.derive(source.read_bytes(),source,paths['stock_source'])
        n.require(not paths['root'].exists() and not paths['root'].is_symlink(), 'fresh native fixture namespace required')
        previous = terminal['admitted_at']; outputs = []
        for index, (ref, declaration) in enumerate(zip(terminal['commands'], prior['children'], strict=True)):
            path = n.ASSEMBLY/'commands'/f'{index:03}'/'receipt.json'
            child = self.load(path)
            n.require(ref['path'] == str(path) and ref['sha256'] == n.owned.sha(path)
                      and ref['pid'] == child['pid'] and ref['command'] == child['command'] == declaration['argv']
                      and child['environment'] == declaration['environment'] and child['cwd'] == declaration['cwd']
                      and child['status'] == 'finished' and child['returncode'] == 0
                      and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
                      and previous <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                      'B3 actual command association differs')
            previous = child['finished_at']
            for stream in ['stdout','stderr']:
                raw = self.add(path.parent/stream, snapshot=True)
                n.require(raw.stat().st_size <= 8*2**20 and n.owned.sha(raw) == child[stream+'_sha256'],
                          'B3 actual raw stream changed')
            outputs.append(path.parent/'stdout')
        inventory_path = n.ASSEMBLY/'assembly/output-inventory.json'
        inventory = self.load(inventory_path)
        n.require(n.owned.sha(inventory_path) == terminal['assembly']['output_inventory_sha256']
                  and n.comp.output_inventory(paths['beta']) == inventory, 'complete B3 payload differs')
        for name, row in inventory.items():
            path = paths['beta']/name
            self.add(path)
            n.require(self.files[str(path)]['sha256'] == row['sha256']
                      and self.files[str(path)]['size'] == row['size']
                      and self.files[str(path)]['identity'] == row['identity'],
                      'actual B3 output bytes/identity differ')
        self.add(n.ASSEMBLY/'strip-proof.json', snapshot=True)
        n.require(n.owned.sha(n.ASSEMBLY/'strip-proof.json') == terminal['strip_proof_sha256'], 'B3 strip proof changed')
        compiler = prior['actual_build']; build = Path(compiler['evidence'])
        compiled = self.load(build/'compiled.json')
        runtime = self.load(build/'stage1-inventory.json')['closure']['identity']
        n.require(compiled['candidate_revision'] == n.REVISION and compiled['source_identity'] == prior['source_identity'],
                  'native candidate/source differs from actual B3 producer')
        pair = terminal['producer_proof']['ordered_driver_destinations']
        n.require(len(pair) == 2 and pair[0].endswith('.dylib') and pair[1] == str(Path(pair[0]).with_suffix('.rmeta')),
                  'actual B3 driver pair differs')
        candidates = [row for row in runtime['libraries'] if row['sha256'] == inventory[pair[0]]['sha256']
                      and Path(row['resolved']).name == Path(pair[0]).name]
        n.require(len(candidates) == 1, 'unique actual E2 driver required')
        driver = self.add(candidates[0]['resolved'])
        driver_record = dict(path=str(driver), **self.files[str(driver)])
        for row in runtime['libraries']:
            self.add(row['resolved']); n.require(self.files[row['resolved']]['sha256'] == row['sha256'], 'actual E2 provider changed')
        # These are actual observations from the successful B3 prefix, not
        # assumed beta/nightly labels or paths borrowed from the old B2 recipe.
        for index, command in [(2,[str(paths['build']/'bin/rustc'),'-vV']),
                               (4,[str(paths['runtime']/'bin/rustc'),'-vV'])]:
            n.require(prior['children'][index]['argv'] == command, 'wrong actual compiler version source')
        build_version, runtime_version = outputs[2].read_text(), outputs[4].read_text()
        n.require(runtime_version == prior['runtime_version'], 'E2 version observations disagree')
        environment = dict(prior['environment'], TMPDIR=str(n.WORK/'tmp'))
        n.require(environment.get('RUSTUP_DIST_SERVER') == 'file:///dev/null'
                  and not any((key.startswith(('RUST','DYLD_','LD_')) and key != 'RUSTUP_DIST_SERVER')
                              or key == 'CARGO_ENCODED_RUSTFLAGS' for key in environment), 'ambient native compiler/loader override')
        clang = prior['metadata_plan']['build_environment']['CC']
        self.add(Path(clang).resolve(strict=True))
        roots = set()
        for owner in n.monitor.EVIDENCE_OWNERS:
            for path in (owner/'.work').iterdir():
                if path.name.startswith(n.monitor.EVIDENCE_PREFIXES) and (path.is_dir() or path.is_symlink()):
                    n.require(not path.is_symlink(), 'candidate evidence root is indirect'); roots.add(path)
        roots.update([n.WORK,n.ASSEMBLY])
        plan = dict(status='prepared-unrun', namespace=str(n.N), candidate_revision=n.REVISION,
            source_identity=compiled['source_identity'], compiler=compiler,
            assembly=dict(source=str(n.COMPOSITION), evidence=str(n.ASSEMBLY),
                receipt_sha256=n.owned.sha(n.ASSEMBLY/'receipt.json'),inputs_sha256=n.owned.sha(n.COMPOSITION/'inputs.json'),audit=self.audit_ref),
            runtime_closure=runtime, runtime_driver=driver_record, ordered_driver_destinations=pair,
            build_version=build_version, runtime_version=runtime_version, environment=environment,
            clang=clang,otool=prior['otool'],evidence_roots=sorted(map(str,roots)),executor_routes=self.routes,
            beta_std_paths=[str(paths['beta']/name) for name in sorted(inventory)
                if name.startswith('lib/rustlib/'+n.recipe.HOST+'/lib/lib')
                and n.re.fullmatch(r'lib(?:std|core)-[a-f0-9]+\.(?:rlib|rmeta|dylib)',Path(name).name)],
            capacity=dict(entry_gib=24,stop_gib=9,floor_gib=8,namespace_bytes=14*2**30,evidence_bytes=256*2**20),
            canonical_lock=str(n.owned.CANONICAL_LOCK),wait_seconds=600,
            monitor_source=str(n.A/'experiments/hir-options-hash-stage-monitor/monitor.py'),
            interpretation='Native20 only; no hash-driver, run-make or application execution.')
        plan['prior_failed_attempt']=prior_attempt
        plan['stock_source_derivation']=derivation
        plan['stock_source_controls']=controls
        plan['children']=desired_commands(plan)
        for row in plan['children']:
            path=Path(row['argv'][0])
            if path in [paths['stock'],paths['program']]:continue
            resolved=path.resolve(strict=True);self.add(resolved);self.routes[str(path)]=str(resolved)
        for directory in [n.HERE,n.ROOT/'experiments/hir-driver-observations']:
            for path in directory.iterdir():
                if path.is_file():
                    self.add(path,snapshot=True)
                    if path.suffix=='.py':ast.parse(path.read_bytes())
        for path in [n.A/'scripts/supervise_experiment.py',n.A/'experiments/hir-options-hash-stage-monitor/monitor.py',
                     n.A/'experiments/hir-options-hash-stage-monitor/test_monitor.py']:
            self.add(path,snapshot=True)
        for imported in list(sys.modules.values()):
            value=getattr(imported,'__file__',None)
            if value and value.startswith('/Users/danluu/dev/'):self.add(Path(value).resolve(strict=True),snapshot=True)
        python=Path(sys.executable).resolve(strict=True);self.add(python)
        for route in ['/opt/homebrew/bin/python3','/bin/ps','/usr/sbin/lsof']:
            resolved=Path(route).resolve(strict=True);self.add(resolved);self.routes[route]=str(resolved)
        freeze=dict(files=self.files,links=self.links,absent_paths=self.absent,snapshot_inputs=sorted(self.snapshots),
                    python=str(python),launch_environment=environment)
        return plan,freeze


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--assembly-audit',required=True);parser.add_argument('--assembly-audit-sha256',required=True);args=parser.parse_args()
    n.require(Path.cwd()==n.A and sys.dont_write_bytecode and not sys.flags.optimize,'native preparation owner/Python differs')
    n.require(not any((n.HERE/name).exists() for name in ['plan.json','inputs.json','snapshot-plan.json','launch.json']) and not n.WORK.exists(),'fresh native proposal required')
    with n.owned.workload_lock(n.owned.CANONICAL_LOCK,600):
        n.owned.disk(n.A,16)
        plan,freeze=Discovery(args.assembly_audit,args.assembly_audit_sha256).discover()
        write(n.HERE/'plan.json',plan)
        record=n.comp.check_file(dict(path=str(n.HERE/'plan.json'),sha256=n.owned.sha(n.HERE/'plan.json')))
        freeze['files'][str(n.HERE/'plan.json')]={key:record[key] for key in ['identity','size','sha256']}
        freeze['snapshot_inputs'].append(str(n.HERE/'plan.json'));freeze['plan_sha256']=record['sha256']
        write(n.HERE/'inputs.json',freeze)
        n.snapshot_qualification(freeze)
        helper=n.load_snapshots(freeze)
        records=n.snapshot_records(freeze,n.HERE/'inputs.json',n.owned.sha(n.HERE/'inputs.json'))
        projection=helper.measure(records,n.SNAPSHOT_LIMITS,lambda:n.owned.disk(n.A,9))
        current=n.monitor.sample(evidence_root=n.WORK,evidence_roots=tuple(map(Path,plan['evidence_roots'])))
        n.require(n.monitor.rejection(current) is None,'native aggregate evidence admission failed')
        reservation=n.snapshot_reservation(projection,records)
        n.require(current['evidence_allocated_bytes']+reservation<=256*2**20,
                  'native compressed proof and remaining stage exceed evidence cap')
        snapshot_plan=dict(inputs_sha256=n.owned.sha(n.HERE/'inputs.json'),limits=n.SNAPSHOT_LIMITS,
            helper=dict(path=str(n.SNAPSHOT_SOURCE),sha256=freeze['files'][str(n.SNAPSHOT_SOURCE)]['sha256']),
            projection=projection,remaining_evidence_reservation_bytes=n.REMAINING_EVIDENCE_RESERVATION,
            measured_existing_evidence_bytes=current['evidence_allocated_bytes'],projected_reservation_bytes=reservation,
            evidence_cap_bytes=256*2**20)
        encoded=helper.encoded(snapshot_plan)
        n.require(len(encoded)<=n.SNAPSHOT_LIMITS['maximum_manifest_bytes'],'bounded native projection required')
        with (n.HERE/'snapshot-plan.json').open('xb') as stream:
            stream.write(encoded);stream.flush();os.fsync(stream.fileno())
        n.require(n.owned.sha(n.HERE/'snapshot-plan.json')==n.comp.digest(encoded),'native projection publication differs')
        # Read the exact future controller schema without initialization,
        # fixture creation or any compiler/provider invocation.
        probe=n.Stage.__new__(n.Stage)
        probe.plan,probe.freeze=plan,freeze
        probe.inputs_sha256=n.owned.sha(n.HERE/'inputs.json')
        probe.snapshot_plan_file=n.comp.check_file(dict(path=str(n.HERE/'snapshot-plan.json'),sha256=n.owned.sha(n.HERE/'snapshot-plan.json')))
        probe.environment=plan['environment'];probe.stock=None;probe.stock_source=None
        probe.paths=n.recipe.paths(n.N)
        probe.evidence_roots=tuple(map(Path,plan['evidence_roots']))
        saved=dict(os.environ);os.environ.clear();os.environ.update(probe.environment)
        started=time.time()
        try:
            probe.guard(True);probe.predecessor();capacity=probe.budget()
        finally:
            os.environ.clear();os.environ.update(saved)
        write(n.HERE/'metadata-preflight.json',dict(status='passed',started_at=started,finished_at=time.time(),
            workload_children=0,work_created=False,capacity=capacity,inputs_sha256=probe.inputs_sha256))
        launch=dict(owner=str(n.A),environment=plan['environment'],expected_children=20,capacity=plan['capacity'],
            command=[freeze['python'],'-B',str(n.A/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-native-controls-supervisor-02',
                '--',freeze['python'],'-B',str(n.HERE/'run.py'),'--inputs-sha256',n.owned.sha(n.HERE/'inputs.json'),
                '--snapshot-plan-sha256',n.owned.sha(n.HERE/'snapshot-plan.json')],
            inputs_sha256=n.owned.sha(n.HERE/'inputs.json'),snapshot_plan_sha256=n.owned.sha(n.HERE/'snapshot-plan.json'),review_required_before_launch=True)
        write(n.HERE/'launch.json',launch)
        n.owned.disk(n.A,9)
        print(json.dumps(dict(status='prepared-unrun',launch_sha256=n.owned.sha(n.HERE/'launch.json'),inputs=len(freeze['files']))))


if __name__=='__main__':main()
