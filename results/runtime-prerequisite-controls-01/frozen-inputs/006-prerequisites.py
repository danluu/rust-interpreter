"""Read-only adapter for an ACTUALLY completed, independently audited hash stage.

No constructor, execute method, discovery, import, process or write is performed
by this module. The enclosing preparer supplies the exact frozen stage module
and its already isolated dependencies. Missing actual evidence rejects.
"""
import copy
import os
from pathlib import Path


def require(value, message):
    if not value:
        raise RuntimeError(message)


class Reader:
    def __init__(self, stage, modules, *, combined_freeze, references, read_json, sha):
        require(set(references) == {'beta', 'native', 'run_make', 'hash'},
                'four explicit completed qualification audits required')
        require('snapshot_bindings' in modules
                and Path(modules['snapshot_bindings'].__file__) == stage.HERE/'snapshot_bindings.py',
                'exact hash v2 snapshot binding module required')
        self.stage, self.modules = stage, modules
        self.references, self.read_json, self.sha = references, read_json, sha
        self.original = read_json(stage.HERE/'inputs.json')
        self.plan = read_json(stage.HERE/'plan.json')
        require(sha(stage.HERE/'plan.json') == self.original['plan_sha256'], 'actual hash plan differs')
        # Every historical file identity/route/absence remains exact. The union
        # additionally admits the installer sources and actual post-stage files.
        for group in ['files', 'links']:
            for name, row in self.original[group].items():
                require(combined_freeze[group].get(name) == row, 'historical hash freeze omitted or changed')
        require(set(self.original['absent_paths']) <= set(combined_freeze['absent_paths']),
                'historical absence omitted')
        reader = stage.Stage.__new__(stage.Stage)
        reader.modules, reader.core = modules, modules['core']
        reader.monitor, reader.owned = modules['monitor'], modules['monitor'].owned
        reader.comp, reader.require = modules['comp'], require
        reader.freeze, reader.plan = copy.deepcopy(combined_freeze), self.plan
        # This reader validates the historical hash projection. Its logical
        # selection is independent of the enclosing runtime's new selection.
        names = self.original['snapshot_inputs']
        require(type(names) is list and names == sorted(set(names))
                and set(names) <= set(self.original['files']), 'historical hash snapshot selection differs')
        reader.freeze['snapshot_inputs'] = copy.deepcopy(names)
        reader.inputs_sha256 = sha(stage.HERE/'inputs.json')
        # The live installer environment is distinct from the historical launch
        # environment. No os.environ mutation or historical-environment claim.
        reader.environment = dict(os.environ)
        self.reader = reader
        terminal = read_json(stage.WORK/'receipt.json')
        require(terminal['status'] == 'passed-awaiting-independent-audit'
                and terminal['inputs_sha256'] == reader.inputs_sha256, 'actual completed hash input binding required')
        for path in [stage.HERE/'snapshot-plan.json', stage.WORK/'snapshot-plan.json',
                     stage.WORK/'source-snapshots.json']:
            reader.frozen(path)
        # The public pure binding method only reads the reviewed projection.
        # No snapshot helper import, constructor, compression or write occurs.
        reader.bind_snapshot_plan(terminal['snapshot_plan_sha256'])
        reader.retained_snapshot_proof(stage.HERE, stage.WORK, terminal)

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
        self.audit('hash', s.WORK/'receipt.json')
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
        return dict(candidate_revision=s.REVISION, source_identity=p['source_identity'],
            hash_result_sha256=self.sha(s.WORK/'result.json'), hash_receipt_sha256=self.sha(s.WORK/'receipt.json'),
            independent_audits=copy.deepcopy(self.references),
            earlier_qualifications=summary)
