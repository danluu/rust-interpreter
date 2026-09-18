"""Close the two completed results under one bounded benchmark-lock acquisition."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/runtime-composition-retirement'))
from compare_saved_runtime import acquire_lock
from workflow_io import require_space
from close_parser import main as close_parser
from close_current_nushell_custom import main as close_retirement

if __name__=='__main__':
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        assert not (ROOT/'results/runtime-composition-parser-01/closure.json').exists()
        assert not (ROOT/'results/closed-runtime-composition-nushell-custom-retirement-01/closure.json').exists()
        close_parser('840eee0c','runtime-composition-parser-admission-02')
        close_retirement('ac3618f3')
