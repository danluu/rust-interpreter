"""Explicit adapter to shared whole-history candidate budget supervision."""
import importlib.util
from pathlib import Path
import sys

A = Path(__file__).resolve().parents[2]
SOURCE = A/'experiments/hir-options-hash-stage-monitor/monitor.py'
spec = importlib.util.spec_from_file_location('b3_whole_history_monitor', SOURCE)
shared = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = shared
spec.loader.exec_module(shared)
OWNER, NAMESPACE, owned = shared.OWNER, shared.NAMESPACE, shared.owned
EVIDENCE = A/'.work/hir-options-hash-beta-composition-04'

def sample(prior_evidence):
    return shared.sample(evidence_root=EVIDENCE, evidence_roots=prior_evidence)

def rejection(row):
    return shared.rejection(row)

def run(command, *, cwd, environment, output, canonical_fd, prior_evidence, expected=(0,)):
    return shared.run(command, cwd=cwd, environment=environment, output=output,
        canonical_fd=canonical_fd, evidence_root=EVIDENCE, evidence_roots=prior_evidence, expected=expected)
