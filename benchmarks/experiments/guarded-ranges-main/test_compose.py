import copy
import unittest

import compose


class CompositionProofTests(unittest.TestCase):
    def setUp(self):
        self.current = {'Cargo.toml': 'workspace', 'Cargo.lock': 'lock', 'rust-toolchain.toml': 'compiler',
                        'crates/bytecode/src/jit.rs': 'guarded', 'crates/bytecode/Cargo.toml': 'vm-package',
                        'crates/function-cache/src/lib.rs': 'shared', 'crates/mir-export/src/main.rs': 'exporter',
                        'crates/rustc-dispatch/src/main.rs': 'dispatch'}
        self.runtime = dict(self.current, **{'old-plan.md': 'historical plan'})
        self.frontend = dict(self.current, **{'crates/bytecode/src/jit.rs': 'old-vm', 'old-controller.py': 'historical'})
        self.proof = dict(status='passed', all_five_gates_passed=True, commands=726, previous_commands=594,
                          new_commands=132, completed_cases=['token','folded','pgrust','rg-aot','nushell'],
                          unstarted_cases=[], no_completed_case_repeated=True, final_source_and_input_audit_passed=True)
        self.vm = {'rust-interp-vm': compose.VM_SHA, 'rust-interp-mir-export': 'old-exporter',
                   'rust-interp-rustc-wrapper': 'old-wrapper'}
        self.front = {'rust-interp-vm': 'old-vm',
                      'rust-interp-mir-export': 'cccdc9092c63bad8f0a8c8bd7bb8ca88e21bf7c83895749ed21ac1cfdf9e4783',
                      'rust-interp-rustc-wrapper': '10fb76569f0e1b13c10090a84f47be539cc27d1c6546f9e1f29d1029adfa57fa'}

    def test_reuses_complete_source_proofs_without_requiring_old_vm_in_frontend(self):
        self.assertTrue(compose.verify_sources(self.current, self.runtime, self.frontend))

    def test_added_removed_and_changed_current_source_rejects_reuse(self):
        extra = dict(self.current, **{'crates/bytecode/src/new.rs': 'unqualified'})
        missing = dict(self.current); missing.pop('Cargo.lock')
        changed = dict(self.current, **{'crates/bytecode/src/jit.rs': 'changed'})
        for current in [extra, missing, changed]:
            with self.subTest(current=current), self.assertRaises(AssertionError):
                compose.verify_sources(current, self.runtime, self.frontend)

    def test_changed_or_missing_frontend_shared_source_rejects_reuse(self):
        for name in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'crates/function-cache/src/lib.rs',
                     'crates/rustc-dispatch/src/main.rs', 'crates/mir-export/src/main.rs']:
            for remove in [False, True]:
                prior = dict(self.frontend)
                if remove: prior.pop(name)
                else: prior[name] = 'different'
                with self.subTest(name=name, remove=remove), self.assertRaises(AssertionError):
                    compose.verify_sources(self.current, self.runtime, prior)

    def test_added_rust_source_and_package_manifests_are_not_hidden_by_old_file_list(self):
        for name in ['crates/new/src/lib.rs', 'crates/new/Cargo.toml']:
            self.assertTrue(compose.rust_input(name))
            changed = dict(self.current, **{name: 'new'})
            with self.assertRaises(AssertionError):
                compose.verify_sources(changed, self.runtime, self.frontend)

    def test_completed_campaign_is_required(self):
        self.assertTrue(compose.verify_completed(self.proof))

    def test_failed_incomplete_repeated_or_unaudited_campaign_rejects_integration(self):
        changes = [dict(status='rejected'), dict(all_five_gates_passed=False), dict(commands=594),
                   dict(previous_commands=0), dict(new_commands=726), dict(unstarted_cases=['nushell']),
                   dict(no_completed_case_repeated=False), dict(final_source_and_input_audit_passed=False),
                   dict(completed_cases=['nushell','token','folded','pgrust','rg-aot'])]
        for change in changes:
            bad = dict(self.proof, **change)
            with self.subTest(change=change), self.assertRaises(AssertionError):
                compose.verify_completed(bad)

    def test_composition_preserves_exact_selected_components_without_mutating_inputs(self):
        originals = copy.deepcopy((self.vm, self.front))
        result = compose.component_binaries(self.vm, self.front)
        self.assertEqual(result, dict(self.front, **{'rust-interp-vm': compose.VM_SHA}))
        self.assertEqual((self.vm, self.front), originals)

    def test_wrong_or_extra_component_rejects_assembly(self):
        for side, key in [('vm','rust-interp-vm'), ('front','rust-interp-mir-export'),
                          ('front','rust-interp-rustc-wrapper'), ('vm','unexpected'), ('front','unexpected')]:
            vm, front = dict(self.vm), dict(self.front)
            (vm if side == 'vm' else front)[key] = 'different'
            with self.subTest(side=side, key=key), self.assertRaises(AssertionError):
                compose.component_binaries(vm, front)


if __name__ == '__main__':
    unittest.main()
