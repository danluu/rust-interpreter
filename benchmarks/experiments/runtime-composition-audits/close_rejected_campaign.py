"""Close the failed parser guard and terminal campaign without repeating any guest."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock
from workflow_io import require_space
from close_parser_edits import main as close_parser
from close_campaign import main as close_campaign

if __name__=='__main__':
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        out=ROOT/'results/runtime-composition-parser-edits-incremental-01'
        summary=json.loads((out/'summary.json').read_text())
        assert summary['commands']==88 and not summary['measurement']['gate_passed']
        assert not (out/'closure.json').exists()
        assert not (ROOT/'results/runtime-composition-full-02/closure.json').exists()
        assert not (ROOT/'.work/runtime-composition-parser-edits-repository-01').exists()
        close_parser('incremental')
        close_campaign('runtime-composition-full-nushell-02','840eee0c')
