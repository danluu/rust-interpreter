#!/usr/bin/env python3
"""Run the ordinary source-branch launcher against shared qualified local tools."""
import importlib.util
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
SOURCE = ROOT / '.work/test-targets-source/scripts/interpreter.py'
spec = importlib.util.spec_from_file_location('test_target_source', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.ROOT = ROOT
if __name__ == '__main__':
    raise SystemExit(module.main())
