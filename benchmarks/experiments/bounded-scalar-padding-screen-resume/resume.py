"""Keep the qualified screen unchanged; retry only its empty lock admission."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/bounded-scalar-padding-screen'))
import common
import benchmark
import close as original_close

RUN = 'bounded-scalar-padding-screen-es8-02'
OLD = 'bounded-scalar-padding-screen-es8-01'


def inputs():
    frozen, original, owner = common.inputs()

    def bind(path, expected=None):
        digest = common.sha(path)
        assert expected is None or digest == expected, path
        key = str(path.relative_to(ROOT))
        assert frozen.setdefault(key, digest) == digest
        return common.read(path) if path.suffix == '.json' else digest

    result, raw = ROOT / 'results' / OLD, ROOT / '.work' / OLD
    closed = bind(result / 'closure.json')
    assert closed['status'] == 'closed' and closed['all_hashes_verified']
    assert not closed['complete'] and closed['source_restored']
    summary = bind(result / 'summary.json', closed['summary_sha256'])
    terminal = bind(result / 'terminal.json', closed['terminal_sha256'])
    assert terminal['status'] == 'finished' and terminal['returncode'] == 1
    assert terminal['owner'] == terminal['cwd'] == str(ROOT)
    assert summary['status'] == 'failed-prefix-preserved'
    assert summary['commands'] == summary['strict_controls'] == 0
    assert summary['returncodes'] == [] and not summary['performance_measurement']
    assert not list(raw.glob('*-child.json'))
    for name in ['records', 'strict', 'space']:
        assert bind(raw / (name + '.json'), summary[name + '_sha256']) == []
    plan = bind(raw / 'plan.json', summary['plan_sha256'])
    assert plan['owner'] == str(ROOT) and plan['expected_commands'] == 40
    assert plan['tool_key'] == benchmark.KEY and plan['candidate_tool_key'] == benchmark.CANDIDATE
    assert common.sha(common.CHANGED) == plan['original_source_sha256']
    assert (raw / 'original.rs').read_bytes() == original
    bind(raw / 'original.rs', plan['original_source_sha256'])
    log = ROOT / '.work/experiments' / OLD / 'command.log'
    bind(log, terminal['log_sha256'])
    assert 'TimeoutError: timed out after 45s waiting for benchmark lock' in log.read_text()
    for path in [*HERE.glob('*.py'), *HERE.glob('*.md')]:
        bind(path)
    return frozen, original, owner


if __name__ == '__main__':
    if sys.argv[1:] == ['--close']:
        original_close.RUN = RUN
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            common.acquire_lock(lock, 45)
            common.require_space(ROOT, 8)
            original_close.close()
    else:
        assert len(sys.argv) == 1
        benchmark.RUN = RUN
        benchmark.inputs = inputs
        benchmark.main()
