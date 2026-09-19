"""Preflight-only admission successor; original installation controller is unchanged.

Construction requires the reviewed isolated modules, an exact prepared plan and
the complete union freeze. The eventual small launcher/preparer must bind this
source and every imported module before invoking it. No generic subprocess path
or old owned.run fallback is present.
"""
import copy
import os
from pathlib import Path
import time

R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
PREFIX = 'hir-options-hash-runtime-'
ATTEMPT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05')
ROUTES = ATTEMPT/'routes.json'
ROUTES_SHA256 = '893d6102741b5206a829e2f5e130614667140b1eacc09d0c55616f7311f82e6a'
CAPACITY = dict(entry_gib=16, stop_gib=9, floor_gib=8,
    combined_namespace_bytes=14*2**30, evidence_bytes=256*2**20)


def require(value, message):
    if not value:
        raise RuntimeError(message)


def configure_monitor(private_monitor, *, installation_directory):
    """Adapt a NEW private module instance, never the predecessor's monitor.

    The original complete-identity stop/drain/run code remains unchanged. The
    same 14 GiB allocation cap now counts N plus the one new runtime prefix;
    the 256 MiB evidence cap includes the two new R evidence roots. The caller
    must create this module instance through the existing isolated loader.
    """
    require(not getattr(private_monitor, '_runtime_configured', False), 'monitor already adapted')
    private_monitor._runtime_configured = True
    private_monitor.EVIDENCE_OWNERS = tuple(dict.fromkeys((*private_monitor.EVIDENCE_OWNERS, R)))
    private_monitor.EVIDENCE_PREFIXES = (*private_monitor.EVIDENCE_PREFIXES, PREFIX)
    original_sample = private_monitor.sample
    if installation_directory is not None:
        directory = Path(installation_directory)
        require(directory.parent == R/'.work/runtime-compilers'
                and len(directory.name) == 64 and all(c in '0123456789abcdef' for c in directory.name),
                'only exact new keyed runtime allocation may be added')
    else:
        directory = None
    def sample(*, evidence_root, evidence_roots):
        row = original_sample(evidence_root=evidence_root, evidence_roots=evidence_roots)
        row['compiler_namespace_allocated_bytes'] = row['namespace_allocated_bytes']
        extra = dict(bytes=0, absent=True)
        if directory is not None and (directory.exists() or directory.is_symlink()):
            try:
                extra = private_monitor.allocated(directory, (directory,))
            except (OSError, AssertionError) as error:
                extra = dict(bytes=0, unavailable=True)
                row['allocation_errors'].append(dict(root=str(directory), error=repr(error)))
        row['runtime_installation_allocation_sample'] = extra
        row['namespace_allocated_bytes'] += extra['bytes']
        row['allocation_scope'] = 'N plus exact new runtime prefix; shared 14 GiB cap, no old R payload scan'
        # A final free sample covers the extra owned allocation traversal.
        row['free_bytes'] = min(row['free_bytes'], private_monitor.shutil.disk_usage(R).free)
        return row
    private_monitor.sample = sample
    return private_monitor


class Controller:
    def __init__(self, *, plan, inputs_sha256, q, recipe, reader, monitor,
                 check_frozen, read_json, read_bytes, sha, canonical_fd):
        self.plan, self.inputs_sha256 = copy.deepcopy(plan), inputs_sha256
        self.q, self.recipe, self.reader, self.monitor = q, recipe, reader, monitor
        self.owned, self.check_frozen = monitor.owned, check_frozen
        self.read_json, self.read_bytes, self.sha = read_json, read_bytes, sha
        require(type(canonical_fd) is int and canonical_fd >= 0, 'explicit inherited canonical descriptor required')
        with self.owned.workload_lock(self.owned.CANONICAL_LOCK, 600, inherited_fd=canonical_fd):
            pass  # The entry owns this open description through constructor and execute.
        self.fd = canonical_fd
        require(plan.get('attempt') == dict(path=str(ROUTES), sha256=ROUTES_SHA256)
            and sha(ROUTES) == ROUTES_SHA256, 'exact reviewed retry routes required')
        routes = read_json(ROUTES)
        require(routes['phase'] == plan['phase'] == 'preflight'
            and routes['work'] == plan['work'] and routes['supervisor'] == plan['supervisor_work']
            and routes['capacity'] == CAPACITY and routes['installation_entry_gib'] == 24,
            'preflight-only retry routing or phase policy differs')
        self.work = Path(plan['work']); self.phase = plan['phase']
        require(self.phase == 'preflight' and Path(plan['owner']) == R
                and self.work.parent == R/'.work' and self.work.name.startswith(PREFIX), 'exact runtime stage scope')
        require(plan['capacity'] == CAPACITY, 'preflight retry bounds changed')
        require(monitor is not reader.reader.monitor, 'do not mutate historical shared monitor')
        require(Path.cwd() == R and dict(os.environ) == plan['launch_environment'], 'exact runtime launch context required')
        self.spec = read_json(plan['specification']['path'])
        require(sha(plan['specification']['path']) == plan['specification']['sha256'], 'runtime specification differs')
        self.identity = q.runtime.identity_for(self.spec)
        self.key = q.runtime.digest(self.identity)
        self.environment = dict(plan['environment'])
        q.std.validate_environment(self.environment)
        if self.phase == 'preflight':
            require('std_source_paths' not in self.identity['provenance'], 'preflight capability added prematurely')
            desired = recipe.preflight_commands(q, self.spec, R, self.work/'source-probe', self.environment)
            directory = None
        else:
            require(q.runtime.qualification_policy(self.spec) == q.FINAL, 'final validator declaration required')
            key, sysroot, desired = recipe.installation_commands(q, self.spec, R, self.work, self.environment)
            require(key == plan['runtime_key'] and str(sysroot) == plan['sysroot'], 'final keyed runtime differs')
            directory = sysroot.parent
            require(not directory.exists() and not directory.is_symlink(), 'runtime prefix already exists')
        require(desired == plan['children'], 'runtime exact ordered recipe differs')
        require(not monitor.ALLOWED_CWDS, 'runtime monitor already has a cwd policy')
        monitor.ALLOWED_CWDS = frozenset(Path(row['cwd']) for row in desired)
        require(monitor.ALLOWED_CWDS <= {R, self.work/'source-probe'}, 'unexpected monitored cwd')
        configure_monitor(monitor, installation_directory=directory)
        self.last_allocation_sample = None
        self.last_allocation_time = 0.0
        self.snapshots = [q.runtime.inspect_component(c) for c in self.spec['components']]
        self.check_frozen(True)
        require(not self.work.exists() and not self.work.is_symlink(), 'runtime evidence must be fresh')
        self.work.mkdir()
        self.record = dict(status='waiting', phase=self.phase, pid=os.getpid(), parent_pid=os.getppid(),
            started_at=time.time(), inputs_sha256=inputs_sha256, children=[], runtime_key=self.key,
            application_qualified=False, performance_measurement=False, exporter_qualified=False, std_mir_prepared=False)
        self.save()

    def save(self):
        self.owned.write(self.work/'receipt.json', self.record)

    def capacity(self, *, force=False):
        # Every copy/read chunk checks current free space. Allocation walks are
        # sampled at most once per second, avoiding a full N walk per MiB.
        self.owned.disk(R, 9)
        now = time.monotonic()
        if not force and self.last_allocation_sample is not None and now-self.last_allocation_time < 1.0:
            return self.last_allocation_sample
        row = self.monitor.sample(evidence_root=self.work, evidence_roots=list(map(Path, self.plan['evidence_roots'])))
        require(self.monitor.rejection(row) is None, str(self.monitor.rejection(row)))
        self.last_allocation_sample, self.last_allocation_time = row, now
        return row

    def full_guard(self):
        self.check_frozen(True)
        qualified = self.reader.check(full=True)
        require(qualified == self.plan['qualified_prerequisites'], 'actual qualification summary changed')
        for component, snapshot in zip(self.spec['components'], self.snapshots, strict=True):
            require(self.q.runtime.inspect_component(component) == snapshot, 'current runtime provider membership changed')
            for name, row in component['files'].items():
                self.q.runtime.transfer(Path(component['root'])/name, row, snapshot['files'][name], self.capacity)
            require(self.q.runtime.inspect_component(component) == snapshot, 'provider changed during rehash')
        self.capacity(force=True)

    def run(self, argv, *, cwd, env, out, capacity_root, expected):
        self.check_frozen(False); self.capacity()
        index = len(self.record['children'])
        require(index < len(self.plan['children']) and capacity_root == R, 'unexpected runtime child')
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), environment=env,
                   expected=list(expected), output=str(out))
        require(row == self.plan['children'][index], 'runtime command/order/environment differs')
        out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
        try:
            return self.monitor.run(row['argv'], cwd=Path(cwd), environment=env, output=out,
                canonical_fd=self.fd, evidence_root=self.work,
                evidence_roots=list(map(Path, self.plan['evidence_roots'])), expected=tuple(expected))
        finally:
            path = out/'receipt.json'
            if path.exists():
                child = self.read_json(path, frozen=False)
                self.record['children'].append(dict(path=str(path), sha256=self.sha(path, frozen=False),
                    pid=child.get('pid'), returncode=child.get('returncode')))
                self.save()
            self.check_frozen(False); self.capacity()

    def simple_run(self, argv, env):
        row = self.plan['children'][len(self.record['children'])]
        out = Path(row['output'])
        child = self.run(argv, cwd=R, env=env, out=out, capacity_root=R, expected=(0,))
        stdout, stderr = [self.read_bytes(out/name, frozen=False) for name in ['stdout', 'stderr']]
        require(not stderr, 'final runtime identity/loader probe emitted stderr')
        require(self.sha(out/'stdout', frozen=False) == child['stdout_sha256']
                and self.sha(out/'stderr', frozen=False) == child['stderr_sha256'], 'runtime raw output differs')
        return dict(returncode=child['returncode'], stdout=stdout.decode(), stderr=stderr.decode())

    def execute(self):
        try:
            with self.owned.workload_lock(self.owned.CANONICAL_LOCK, 600, inherited_fd=self.fd):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(R, 16))
                self.save(); self.full_guard()
                if self.phase == 'preflight':
                    result = self.recipe.execute_preflight(self.q, self.spec, owner=R, work=self.work/'source-probe',
                        environment=self.environment, run=self.run, capacity=self.capacity, full_guard=self.full_guard)
                    self.record['source_preflight_sha256'] = self.sha(self.work/'source-probe/result.json', frozen=False)
                else:
                    compiler = self.recipe.execute_installation(self.q, self.spec, owner=R, work=self.work,
                        environment=self.environment, preflight_reference=self.plan['source_preflight'],
                        run=self.run, simple_run=self.simple_run, capacity=self.capacity, full_guard=self.full_guard,
                        all_commands_completed=lambda: len(self.record['children']) == len(self.plan['children']))
                    self.record.update(installed_runtime_key=compiler.key, sysroot=str(compiler.sysroot))
                require(len(self.record['children']) == len(self.plan['children']), 'runtime command recipe incomplete')
                self.full_guard()
                self.record.update(status='passed', finished_at=time.time(), free_bytes_after=self.owned.disk(R, 9))
                self.save()
        except BaseException as error:
            self.record.update(status='failed', finished_at=time.time(), error=repr(error)); self.save(); raise
