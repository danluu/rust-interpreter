import copy
import unittest
from inputs import CASES, VM_KEY, COMPILER_CONTROLS, require_complete, require_vm_sources


class PublicationBoundaries(unittest.TestCase):
    def setUp(self):
        self.proof = dict(status='passed', all_five_gates_passed=True,
            completed_cases=CASES, unstarted_cases=[], commands=726,
            retained_commands=594, new_commands=132, repeated_commands=0,
            final_source_and_input_audit_passed=True, complete_parser_tests=114)
        self.cases = [dict(case=name, status='passed', gate_passed=True, source_restored=True,
            commands=154 if i < 3 else 132, candidate_control_bytecode_matches=True,
            test_source_unchanged=True, tool_keys=dict(candidate=VM_KEY)) for i, name in enumerate(CASES)]

    def test_failed_final_guard_cannot_publish_despite_correctness(self):
        self.cases[-1]['gate_passed'] = False
        with self.assertRaises(AssertionError):
            require_complete(self.proof, self.cases)

    def test_correct_total_cannot_hide_a_repeated_prefix(self):
        self.proof.update(retained_commands=440, new_commands=286, repeated_commands=154)
        with self.assertRaises(AssertionError):
            require_complete(self.proof, self.cases)

    def test_case_identity_and_component_must_match(self):
        require_complete(self.proof, self.cases)
        for change in ['order', 'tool', 'source']:
            cases = copy.deepcopy(self.cases)
            if change == 'order': cases[0], cases[1] = cases[1], cases[0]
            if change == 'tool': cases[-1]['tool_keys']['candidate'] = '0' * 64
            if change == 'source': cases[-1]['source_restored'] = False
            with self.subTest(change=change), self.assertRaises(AssertionError):
                require_complete(self.proof, cases)

    def test_new_frontend_does_not_license_a_different_vm(self):
        old = {'Cargo.lock': 'lock', 'rust-toolchain.toml': 'pin',
            'crates/bytecode/Cargo.toml': 'manifest', 'crates/bytecode/src/jit.rs': 'jit',
            'crates/mir-export/src/main.rs': 'old compiler'}
        new = dict(old, **{'crates/mir-export/src/main.rs': 'new compiler'})
        require_vm_sources(new, old)
        for name in ['Cargo.lock', 'rust-toolchain.toml', 'crates/bytecode/src/jit.rs']:
            changed = dict(new, **{name: 'different'})
            with self.subTest(name=name), self.assertRaises(AssertionError):
                require_vm_sources(changed, old)

    def test_added_or_missing_runtime_file_refuses_binary_reuse(self):
        old = {'Cargo.toml': 'workspace', 'crates/bytecode/src/jit.rs': 'jit'}
        for changed in [dict(old, **{'crates/bytecode/build.rs': 'new'}), {'Cargo.toml': 'workspace'}]:
            with self.assertRaises(AssertionError): require_vm_sources(changed, old)

    def test_only_exact_declared_compiler_controls_can_be_added(self):
        old = {'Cargo.toml': 'workspace', 'crates/bytecode/src/jit.rs': 'jit'}
        added = dict(old, **COMPILER_CONTROLS)
        with self.assertRaises(AssertionError): require_vm_sources(added, old)
        require_vm_sources(added, old, compiler_controls=True)
        bad = [dict(added, **{path: 'changed'}) for path in COMPILER_CONTROLS]
        bad += [dict(added, **{'crates/bytecode/tests/other.rs': 'unknown'}),
                dict(added, **{'crates/bytecode/src/jit.rs': 'changed'}),
                {p: h for p, h in added.items() if p != 'Cargo.toml'}, old]
        for current in bad:
            with self.subTest(current=current), self.assertRaises(AssertionError):
                require_vm_sources(current, old, compiler_controls=True)
        with self.assertRaises(AssertionError):
            require_vm_sources(added, added, compiler_controls=True)


if __name__ == '__main__': unittest.main()
