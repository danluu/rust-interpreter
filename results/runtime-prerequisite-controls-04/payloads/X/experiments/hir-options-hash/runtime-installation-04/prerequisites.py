"""Read-only adapter for an ACTUALLY completed, independently audited hash stage.

No constructor, execute method, discovery, process or write is performed.
Only authenticated, actually qualified pure file-table and plan-reference helpers are loaded. The enclosing preparer supplies the exact frozen stage module
and its already isolated dependencies. Missing actual evidence rejects.
"""
import copy
import json
import os
from pathlib import Path


def require(value, message):
    if not value:
        raise RuntimeError(message)


def same(left, right):
    """Typed JSON equality: booleans cannot relabel integers in frozen proof."""
    encode = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True, allow_nan=False)
    return encode(left) == encode(right)


class Reader:
    def __init__(self, stage, modules, *, combined_freeze, references, read_json, sha, copy_partition):
        require(set(references) == {'beta', 'native', 'run_make', 'hash'},
                'four explicit completed qualification audits required')
        require('snapshot_bindings' in modules
                and Path(modules['snapshot_bindings'].__file__) == stage.HERE/'snapshot_bindings.py',
                'exact hash v2 snapshot binding module required')
        self.stage, self.modules = stage, modules
        self.references, self.read_json, self.sha = copy.deepcopy(references), read_json, sha
        self._partition = copy_partition
        self.copy_state = None
        self._checked = self._checked_owner = None
        source = stage.HERE/'inputs.json'
        self.compact = read_json(source)
        self.inputs_sha256 = sha(source)
        require(str(source) in combined_freeze['files']
                and combined_freeze['files'][str(source)]['sha256'] == self.inputs_sha256,
                'actual compact hash inputs missing from frozen union')
        terminal = read_json(stage.WORK/'receipt.json')
        require(terminal['status'] == 'passed-awaiting-independent-audit'
                and terminal['inputs_sha256'] == self.inputs_sha256,
                'actual completed compact hash input binding required')
        # Authenticate the actual completed owner before any file-table import.
        self.audit('hash', stage.WORK/'receipt.json')
        self.plan_wire_sha256 = sha(stage.HERE/'plan.json')
        require(self.plan_wire_sha256 == self.compact['plan_sha256'], 'actual hash plan differs')
        reader = stage.Stage.__new__(stage.Stage)
        reader.modules, reader.core = modules, modules['core']
        reader.monitor, reader.owned = modules['monitor'], modules['monitor'].owned
        reader.comp, reader.require = modules['comp'], require
        reader.freeze, reader.plan = copy.deepcopy(combined_freeze), None
        reader.inputs_sha256 = self.inputs_sha256
        reader.environment = dict(os.environ)
        self.reader = reader
        # The already complete enclosing union supplies the actual29 proof.
        # Its current helper row is checked again immediately before import.
        self.file_table_proof = reader.file_table_qualification()
        helper = str(stage.FILE_TABLE_SOURCE)
        require(helper in self.compact['files'] and helper in combined_freeze['files']
                and same(self.compact['files'][helper], combined_freeze['files'][helper]),
                'file-table helper differs from qualified frozen union')
        table = stage.load_file_table(self.compact, reader.comp)
        self.original = stage.expand_file_table(self.compact, table,
            guard=lambda: reader.owned.disk(stage.ROOT, 9))
        for name, row in self.original['links'].items():
            require(name in combined_freeze['links'] and same(combined_freeze['links'][name], row),
                    'historical hash freeze omitted or changed')
        require(set(self.original['absent_paths']) <= set(combined_freeze['absent_paths']),
                'historical absence omitted')
        # New plan-envelope helper is qualified before import. The raw wire
        # digest remains the completed packet identity after reconstruction.
        self.continuation_proof = self.continuation_qualification()
        helper = str(stage.PLAN_REFERENCE_SOURCE)
        require(helper in self.original['files'] and helper in combined_freeze['files']
                and same(self.original['files'][helper], combined_freeze['files'][helper]),
                'plan-reference helper differs from qualified frozen union')
        self.plan_reference = stage.load_plan_reference(self.original, reader.comp)
        self.plan = self.read_hash_plan()
        reader.plan = self.plan
        require(same(self.plan['continuation_controls'], self.continuation_proof)
                and same(self.plan['failed_driver'], stage.failed_owner()),
                'actual continuation and failed-owner plan association differs')
        # Preserve the complete historical selection, separate from the new
        # runtime selection; the physical compact SHA remains the input identity.
        names = self.original['snapshot_inputs']
        require(type(names) is list and names == sorted(set(names))
                and set(names) <= set(self.original['files']), 'historical hash snapshot selection differs')
        reader.freeze['snapshot_inputs'] = copy.deepcopy(names)
        reader.snapshot_qualification()
        self.partition()
        require(set(names) <= set(reader.freeze['files']), 'selected logical snapshot must remain current')
        for path in [stage.HERE/'snapshot-plan.json', stage.WORK/'snapshot-plan.json',
                     stage.WORK/'source-snapshots.json']:
            reader.frozen(path)
        reader.bind_snapshot_plan(terminal['snapshot_plan_sha256'])
        reader.retained_snapshot_proof(stage.HERE, stage.WORK, terminal)
        # Complete physical catalog and gzip EOF validation is a separate
        # caller step, after check(full=True), using snapshot_owner below.

    def partition(self):
        """Rebuild references before trusting any saved historical-copy table.

        The authenticated callback reads the fixed predecessor catalog directly;
        it must never call this Reader's check or successful-owner callback.
        """
        before = copy.deepcopy(self.original)
        state = self._partition(self)
        require(same(before, self.original), 'partition changed original completed input table')
        require(state['bootstrap_policy'] == 'continued-catalog-before-reader'
                and state['runtime_admitted'] is False and state['retirement_authorized'] is False,
                'historical-copy validation cannot grant admission')
        historical = state['historical_files']; physical = self.reader.freeze['files']
        require(set(historical).isdisjoint(physical)
                and set(historical) <= set(self.original['files'])
                and set(historical).isdisjoint(self.original['snapshot_inputs']),
                'historical copy overlaps current or selected input')
        for name, row in self.original['files'].items():
            current = historical if name in historical else physical
            require(name in current and same(current[name], row), 'historical hash freeze omitted or changed')
        require(type(state['current_context_files']) is int
                and state['current_context_files'] == len(self.original['files']) - len(historical),
                'historical partition counts differ')
        if self.copy_state is not None:
            require(same(state, self.copy_state), 'historical-copy bootstrap changed')
        self.copy_state = copy.deepcopy(state)
        return state

    def continuation_qualification(self):
        s = self.reader
        return self.stage.continuation_qualification(read_json=s.read_json, read_bytes=s.read_bytes,
            sha=lambda path: s.owned.sha(s.frozen(path)),
            file_record=lambda path: dict(path=str(s.frozen(path)), **s.freeze['files'][str(path)]))

    def read_hash_plan(self):
        """Return the current full plan without changing its raw file identity."""
        source = self.stage.HERE/'plan.json'
        self.reader.frozen(source)
        require(self.sha(source) == self.plan_wire_sha256 == self.compact['plan_sha256'],
                'completed raw hash plan changed')
        self.reader.frozen(self.stage.PLAN_REFERENCE_SOURCE)
        return self.stage.expand_plan(self.read_json(source), self.plan_reference, self.reader.read_bytes)

    def audit(self, role, terminal):
        ref = self.references[role]
        require(set(ref) == {'path', 'sha256'}, 'explicit actual audit reference required')
        proof = self.read_json(ref['path'])
        require(self.sha(ref['path']) == ref['sha256'] and proof['status'] == 'verified'
                and proof['receipt_sha256'] == self.sha(terminal), 'actual independent audit differs: '+role)
        if role != 'hash':
            require(ref == self.plan['independent_audits'][role], 'hash predecessor audit association differs')
        return proof

    def check(self, *, full=True):
        self._checked = self._checked_owner = None
        s, p, r = self.stage, self.plan, self.reader
        r.guard(full)
        self.partition()
        require(same(self.read_hash_plan(), p), 'completed expanded hash plan changed')
        continuation = self.continuation_qualification()
        require(same(continuation, self.continuation_proof)
                and same(p['continuation_controls'], continuation)
                and same(p['failed_driver'], s.failed_owner()), 'current continuation proof changed')
        for role, work in [('beta', s.BETA_WORK), ('native', s.NATIVE_QUALIFICATION_WORK), ('run_make', s.RECIPE_WORK)]:
            require(self.read_json(work/'receipt.json')['status'] == 'passed', 'unfinished prerequisite')
            self.audit(role, work/'receipt.json')
        receipt = self.read_json(s.WORK/'receipt.json')
        result = self.read_json(s.WORK/'result.json')
        require(receipt['status'] == 'passed-awaiting-independent-audit'
                and receipt['inputs_sha256'] == r.inputs_sha256
                and receipt['result_sha256'] == self.sha(s.WORK/'result.json'), 'actual hash terminal/result required')
        hash_audit = self.audit('hash', s.WORK/'receipt.json')
        failed = dict(owner=s.failed_owner(), receipt_sha256=self.sha(s.FAILED_WORK/'receipt.json'),
                      actual_children=1, qualified_children=0)
        require(hash_audit['result_sha256'] == self.sha(s.WORK/'result.json')
                and hash_audit['inputs_sha256'] == self.inputs_sha256
                and hash_audit['snapshot_plan_sha256'] == receipt['snapshot_plan_sha256']
                and hash_audit['launch_sha256'] == self.sha(s.HERE/'launch.json')
                and same(hash_audit['metadata_plan_reference'], s.METADATA_PLAN_REFERENCE)
                and same(hash_audit['continuation_controls'], continuation)
                and same(hash_audit['failed_predecessor'], failed)
                and all(same(item['continuation_controls'], continuation)
                        and same(item['failed_driver'], failed['owner']) for item in [receipt, result])
                and all(type(hash_audit[key]) is int and hash_audit[key] == value for key, value in
                        dict(actual_children=3, compilation_count=1, driver_process_count=2, contexts_per_process=8,
                             historical_failed_compiler_children=1, total_actual_hash_children=4).items())
                and hash_audit['hash_driver_qualified'] is True
                and all(hash_audit[key] is False for key in ['application_qualified', 'performance_measurement', 'runtime_installation']),
                'actual successful continuation audit and retained failed owner required')
        r.retained_snapshot_proof(s.HERE, s.WORK, receipt)
        require(result['status'] == 'hash-driver-observations-passed-awaiting-independent-audit'
                and result['candidate_revision'] == s.REVISION
                and result['source_identity'] == p['source_identity']
                and [result[k] for k in ['compilation_count', 'driver_process_count', 'contexts_per_process']] == [1, 2, 8]
                and result['application_qualified'] is False and result['performance_measurement'] is False,
                'hash result scope differs')
        rows = p['children']
        require(rows == r.core.desired_commands(p) and len(rows) == 3, 'actual hash recipe differs')
        # Re-read the two completed process observations using the unchanged
        # parser; the independent audit also binds the enclosing actual history.
        closure = self.read_json(s.WORK/'driver-loader-closure.json')
        require(self.sha(s.WORK/'driver-loader-closure.json') == result['closure_sha256'], 'hash closure digest differs')
        for declaration, process in zip(rows[1:], result['processes'], strict=True):
            mode = declaration['argv'][-1]
            work = s.WORK/mode
            child = self.read_json(work/'receipt.json')
            require(process['mode'] == mode and process['pid'] == child['pid']
                    and self.sha(work/'receipt.json') == process['receipt_sha256']
                    and self.sha(work/'validated-readback.json') == process['readback_sha256'],
                    'hash mode/process association differs')
            observed = self.modules['trace'].process(child, r.read_bytes(work/'stdout'), r.read_bytes(work/'stderr'),
                command=declaration['argv'], cwd=str(r.core.S), environment=declaration['environment'],
                allowed_private=set(closure['files']))
            require(observed == self.read_json(work/'validated-readback.json'), 'actual hash observation differs')
        binary = r.core.ARTIFACTS/'hash-control-driver'
        require(self.sha(binary) == result['binary_sha256'] and r.closure(binary) == closure,
                'qualified hash binary/provider closure changed')
        summary = r.prerequisites()
        answer = dict(candidate_revision=s.REVISION, source_identity=p['source_identity'],
            hash_result_sha256=self.sha(s.WORK/'result.json'), hash_receipt_sha256=self.sha(s.WORK/'receipt.json'),
            independent_audits=copy.deepcopy(self.references),
            file_table_qualification=copy.deepcopy(self.file_table_proof),
            continuation_controls=copy.deepcopy(continuation), failed_hash_predecessor=copy.deepcopy(failed),
            historical_copy_references=copy.deepcopy(self.copy_state['references']),
            earlier_qualifications=summary)
        if full is True:
            self._checked = copy.deepcopy(answer)
            self._checked_owner = dict(terminal=copy.deepcopy(receipt), result=copy.deepcopy(result),
                audit=copy.deepcopy(hash_audit), digests={
                    str(s.HERE/'inputs.json'):self.inputs_sha256,
                    str(s.HERE/'plan.json'):self.plan_wire_sha256,
                    str(s.WORK/'receipt.json'):answer['hash_receipt_sha256'],
                    str(s.WORK/'result.json'):answer['hash_result_sha256'],
                    self.references['hash']['path']:self.references['hash']['sha256']})
        return answer

    def snapshot_owner(self, owner, terminal, result, audit):
        """Nonrecursive recipe callback; catalog/EOF checks remain caller-owned."""
        require(self._checked is not None and self._checked_owner is not None,
                'complete hash recipe check must precede snapshot catalog')
        expected = dict(role='hash', source=str(self.stage.HERE), evidence=str(self.stage.WORK),
                        audit=self.references['hash'], result_path=str(self.stage.WORK/'result.json'),
                        result_digest_field='result_sha256')
        require(same(owner, expected), 'completed hash snapshot owner differs')
        saved = self._checked_owner
        require(same(terminal, saved['terminal']) and same(result, saved['result'])
                and same(audit, saved['audit']), 'completed hash owner readback differs')
        for path, digest in saved['digests'].items():
            require(self.sha(path) == digest, 'completed hash owner changed after recipe validation')
        return True
