"""Read-only adapter for an ACTUALLY completed, independently audited hash stage.

No constructor, execute method, discovery, process or write is performed.
Only the authenticated, actually qualified pure file-table helper is loaded. The enclosing preparer supplies the exact frozen stage module
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
    def __init__(self, stage, modules, *, combined_freeze, references, read_json, sha):
        require(set(references) == {'beta', 'native', 'run_make', 'hash'},
                'four explicit completed qualification audits required')
        require('snapshot_bindings' in modules
                and Path(modules['snapshot_bindings'].__file__) == stage.HERE/'snapshot_bindings.py',
                'exact hash v2 snapshot binding module required')
        self.stage, self.modules = stage, modules
        self.references, self.read_json, self.sha = copy.deepcopy(references), read_json, sha
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
        self.plan = read_json(stage.HERE/'plan.json')
        require(sha(stage.HERE/'plan.json') == self.compact['plan_sha256'], 'actual hash plan differs')
        reader = stage.Stage.__new__(stage.Stage)
        reader.modules, reader.core = modules, modules['core']
        reader.monitor, reader.owned = modules['monitor'], modules['monitor'].owned
        reader.comp, reader.require = modules['comp'], require
        reader.freeze, reader.plan = copy.deepcopy(combined_freeze), self.plan
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
        for group in ['files', 'links']:
            for name, row in self.original[group].items():
                require(name in combined_freeze[group] and same(combined_freeze[group][name], row),
                        'historical hash freeze omitted or changed')
        require(set(self.original['absent_paths']) <= set(combined_freeze['absent_paths']),
                'historical absence omitted')
        # Preserve the complete historical selection, separate from the new
        # runtime selection; the physical compact SHA remains the input identity.
        names = self.original['snapshot_inputs']
        require(type(names) is list and names == sorted(set(names))
                and set(names) <= set(self.original['files']), 'historical hash snapshot selection differs')
        reader.freeze['snapshot_inputs'] = copy.deepcopy(names)
        reader.snapshot_qualification()
        for path in [stage.HERE/'snapshot-plan.json', stage.WORK/'snapshot-plan.json',
                     stage.WORK/'source-snapshots.json']:
            reader.frozen(path)
        reader.bind_snapshot_plan(terminal['snapshot_plan_sha256'])
        reader.retained_snapshot_proof(stage.HERE, stage.WORK, terminal)
        # Complete physical catalog and gzip EOF validation is a separate
        # caller step, after check(full=True), using snapshot_owner below.

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
        for role, work in [('beta', s.BETA_WORK), ('native', s.NATIVE_QUALIFICATION_WORK), ('run_make', s.RECIPE_WORK)]:
            require(self.read_json(work/'receipt.json')['status'] == 'passed', 'unfinished prerequisite')
            self.audit(role, work/'receipt.json')
        receipt = self.read_json(s.WORK/'receipt.json')
        result = self.read_json(s.WORK/'result.json')
        require(receipt['status'] == 'passed-awaiting-independent-audit'
                and receipt['inputs_sha256'] == r.inputs_sha256
                and receipt['result_sha256'] == self.sha(s.WORK/'result.json'), 'actual hash terminal/result required')
        hash_audit = self.audit('hash', s.WORK/'receipt.json')
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
            earlier_qualifications=summary)
        if full is True:
            self._checked = copy.deepcopy(answer)
            self._checked_owner = dict(terminal=copy.deepcopy(receipt), result=copy.deepcopy(result),
                audit=copy.deepcopy(hash_audit), digests={
                    str(s.HERE/'inputs.json'):self.inputs_sha256,
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
