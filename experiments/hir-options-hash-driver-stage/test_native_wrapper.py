"""Synthetic successor associations with immutable source and failed history.

These controls do not assert that native02 has executed or qualified.
"""
import copy
import json
from pathlib import Path
import unittest

import prerequisites as p

A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
N = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01')
INPUTS = [N/'source/compiler/rustc/src/main.rs', A/'.work/native-controls-failure-verification-01.json',
          A/'.work/hir-options-hash-native-controls-01/receipt.json']


class NativeWrapper(unittest.TestCase):
    def setUp(self):
        self.files = {path: path.read_bytes() for path in INPUTS}
        self.paths = dict(source=N/'source', stock_source=N/'native-controls-02/stock-main.rs')
        lines = self.files[INPUTS[0]].splitlines(keepends=True)
        derived = b''.join(lines[:3] + lines[4:])
        self.files[self.paths['stock_source']] = derived
        derivation = dict(source=str(INPUTS[0]), original_sha256=p.digest(self.files[INPUTS[0]]), original_size=2128,
            destination=str(self.paths['stock_source']), derived_sha256=p.digest(derived), derived_size=len(derived),
            removed_line=4, removed_bytes=lines[3].decode(), policy='remove-exact-cargo-unused-crate-expectation-v1')
        prior = dict(source=str(A/'experiments/hir-options-hash-native-controls-01'),
            evidence=str(INPUTS[2].parent), audit=dict(path=str(INPUTS[1]), sha256=p.digest(self.files[INPUTS[1]])),
            receipt_sha256=p.digest(self.files[INPUTS[2]]), actual_children=5, qualified_children=0, fixture_never_created=True)
        self.plan = dict(namespace=str(N), stock_source_derivation=copy.deepcopy(derivation), prior_failed_attempt=copy.deepcopy(prior))
        source = dict(path=str(self.paths['stock_source']), sha256=p.digest(derived), size=len(derived))
        self.terminal = dict(stock_source_derivation=copy.deepcopy(derivation), stock_source=copy.deepcopy(source))
        self.result = dict(stock_source_derivation=copy.deepcopy(derivation), stock_source=copy.deepcopy(source),
                           prior_failed_attempt=copy.deepcopy(prior), qualified_native_children=20, total_actual_native_children=25)

    def check(self):
        return p.native_wrapper(self.plan, self.terminal, self.result, paths=self.paths,
            read_json=lambda path: json.loads(self.files[Path(path)]), read_bytes=lambda path: self.files[Path(path)])

    def test_exact_private_copy_and_separate_failed_history(self):
        self.assertEqual(self.check(), dict(derived_sha256=p.digest(self.files[self.paths['stock_source']]),
            prior_failed_children=5, qualified_children=20, total_actual_children=25))

    def test_extra_private_source_edit_rejects(self):
        self.files[self.paths['stock_source']] += b'\n'
        with self.assertRaises(ValueError): self.check()

    def test_changed_original_source_rejects(self):
        self.files[INPUTS[0]] += b'\n'
        with self.assertRaises(ValueError): self.check()

    def test_old_artifact_namespace_rejects(self):
        self.paths['stock_source'] = N/'native-controls/stock-main.rs'
        with self.assertRaises(ValueError): self.check()

    def test_consistently_relabelled_derivation_rejects(self):
        for record in [self.plan, self.terminal, self.result]: record['stock_source_derivation']['removed_line'] = 5
        with self.assertRaises(ValueError): self.check()

    def test_consistently_relabelled_stock_digest_rejects(self):
        for record in [self.terminal, self.result]: record['stock_source']['sha256'] = '0'*64
        with self.assertRaises(ValueError): self.check()

    def test_failed_history_cannot_become_qualified(self):
        for record in [self.plan, self.result]: record['prior_failed_attempt']['qualified_children'] = 5
        with self.assertRaises(ValueError): self.check()

    def test_five_historical_children_cannot_be_omitted(self):
        self.result['total_actual_native_children'] = 20
        with self.assertRaises(ValueError): self.check()


if __name__ == '__main__': unittest.main()
