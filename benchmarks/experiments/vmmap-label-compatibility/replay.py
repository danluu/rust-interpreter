"""Check both observed labels against retained emitted arenas, without execution."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import sha
from vmmap_ranges import anonymous_executable_ranges


def replay():
    checked, evidence = [], {}
    names = ['adopted-current-sample-block-01', 'scratch-scalar-runtime-sample-block-01',
             'scratch-scalar-runtime-sample-exhaustive-01']
    for name in names:
        raw = ROOT / '.work' / name / '0'
        native = json.loads((raw / 'jit-code/map.json').read_text())
        record = json.loads((raw / 'record.json').read_text())
        assert record['identity']['status'] == 'finished' and record['identity']['returncode'] == 0
        assert native['pid'] == record['identity']['pid'] and native['profiled'] is False
        assert all(sha(raw / p) == h for p, h in record['files'].items())
        maps = [raw / ('vmmap-' + str(i) + '.stdout') for i in range(12)] if name == names[0] else [raw / 'vmmap.stdout']
        for report in maps:
            ranges = anonymous_executable_ranges(report.read_text(), native['pid'])
            begin, end = native['arena_base'], native['arena_base'] + native['code_bytes']
            assert any(lo <= begin < end <= hi for lo, hi in ranges)
            checked.append(dict(report=str(report.relative_to(ROOT)), sha256=sha(report),
                pid=native['pid'], arena_base=begin, code_bytes=native['code_bytes'], parsed_ranges=ranges))
            evidence[str(report.relative_to(ROOT))] = sha(report)
        for file in ['record.json', 'jit-code/map.json']:
            p = raw / file
            evidence[str(p.relative_to(ROOT))] = sha(p)
    assert len(checked) == 14
    return dict(status='passed', reports=14, every_original_emitted_arena_contained=True,
                cases=checked, evidence=evidence, guest_commands=0)


if __name__ == '__main__':
    print(json.dumps(replay(), sort_keys=True))
