import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
PUBLIC=ROOT/'benchmarks/experiments/session-runtime-composition-guards/admission.py'
def load(case):
    assert case=='pgrust'
    spec=importlib.util.spec_from_file_location('original_public_admission',PUBLIC)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    builds,paths=module.load(case);paths.append(PUBLIC)
    return builds,paths
