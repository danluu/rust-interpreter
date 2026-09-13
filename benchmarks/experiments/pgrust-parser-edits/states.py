"""Production-only edits and exact full-target native outcome validation."""
import re

NEGATIVE = ('wrong-initial-lookahead', 'have_lookahead: mode_token != 0,',
            'have_lookahead: mode_token == 0,')
EDITS = [
    ('not-lookahead-pattern',
     '(next_tok == tokens::BETWEEN\n                    || next_tok == tokens::IN_P\n                    || next_tok == tokens::LIKE\n                    || next_tok == tokens::ILIKE\n                    || next_tok == tokens::SIMILAR)',
     'matches!(next_tok, tokens::BETWEEN | tokens::IN_P | tokens::LIKE | tokens::ILIKE | tokens::SIMILAR)'),
    ('nulls-lookahead-pattern',
     '(next_tok == tokens::FIRST_P || next_tok == tokens::LAST_P)',
     'matches!(next_tok, tokens::FIRST_P | tokens::LAST_P)'),
    ('with-lookahead-pattern',
     '(next_tok == tokens::TIME || next_tok == tokens::ORDINALITY)',
     'matches!(next_tok, tokens::TIME | tokens::ORDINALITY)'),
    ('table-index-range',
     'if idx < 0 || idx > YYLAST || YYCHECK[idx as usize] as i32 != yytoken {',
     'if !(0..=YYLAST).contains(&idx) || YYCHECK[idx as usize] as i32 != yytoken {'),
    ('goto-explicit-boundaries',
     'if (0..=YYLAST).contains(&g) && YYCHECK[g as usize] as i32 == top {',
     'if g >= 0 && g <= YYLAST && YYCHECK[g as usize] as i32 == top {'),
]


def custom_export_ran(stderr):
    # Pinned Cargo labels Check { test: true } as Compiling in this profile.
    # Require the selected target plus a newly emitted exporter completion.
    progress = re.findall(r'^\s+(?:Checking|Compiling) gram_core v[^\n]+$', stderr, re.M)
    exports = re.findall(r'^rust-interp-export: frontend_ms=[^\n]+$', stderr, re.M)
    return len(progress) == len(exports) == 1


def check_prefix_schedule(rows, schedule, profile):
    expected = {'repository': 2, 'incremental': 22}.get(profile)
    if len(rows) != expected or len(schedule) != 66:
        raise ValueError('only the two specifically audited prefixes may continue')
    for index, row in enumerate(rows):
        code = 0 if row['state'] != -1 else (101 if row['mode'] == 'native' else 1)
        if row['index'] != index or row['returncode'] != code:
            raise ValueError('prefix is reordered or has an unexpected command outcome')
        if {k: row[k] for k in schedule[index]} != schedule[index]:
            raise ValueError('prefix does not match the frozen schedule')


def artifact_state_key(cycle, state, kind, history):
    if history == 'cross-cycle': return state, kind
    if history == 'paired-cycle': return cycle, state, kind
    raise ValueError('unknown artifact-history comparison')


def source_states(original, cycles=3):
    if not isinstance(original, bytes) or cycles != 3:
        raise ValueError('this protocol requires bytes and exactly three cycles')
    text = original.decode()
    # Assertions live in separate unchanged files. Refuse a changed target
    # layout instead of applying edits through any newly embedded tests.
    if '#[test]' in text or '#[cfg(test)]' in text:
        raise ValueError('production target unexpectedly contains tests')
    versions = {0: ('original', original)}
    for state in [-1, 1, 2, 3, 4, 5]:
        changed = text
        for label, before, after in [NEGATIVE] if state == -1 else EDITS[:state]:
            if before == after or changed.count(before) != 1:
                raise ValueError('edit must change exactly one occurrence: ' + label)
            changed = changed.replace(before, after)
        versions[state] = label, changed.encode()
    if len({payload for _, payload in versions.values()}) != 7:
        raise ValueError('source states are not distinct')
    rows = [dict(cycle=cycle, state=state, label=versions[state][0], source=versions[state][1])
            for cycle in range(cycles) for state in [0, -1, 1, 2, 3, 4, 5]]
    rows.append(dict(cycle=cycles, state=0, label='restored-original', source=original))
    return rows


def native_outcomes(stdout, names, success):
    rows = re.findall(r'^test (\S+) \.\.\. (ok|FAILED|ignored)(?:,.*)?$', stdout, re.M)
    if len(rows) != len(names) or sorted(name for name, _ in rows) != names:
        raise ValueError('native target omitted, duplicated or added tests')
    if any(status == 'ignored' for _, status in rows):
        raise ValueError('native target ignored tests')
    passed = sum(status == 'ok' for _, status in rows)
    failed = len(rows) - passed
    expected = [('ok' if success else 'FAILED', str(passed), str(failed), '0', '0', '0')]
    summaries = re.findall(r'^test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;', stdout, re.M)
    if summaries != expected or (failed == 0) != success:
        raise ValueError('native original/wrong control did not have the expected outcome')
    if re.findall(r'^running (\d+) tests?$', stdout, re.M) != [str(len(names))]:
        raise ValueError('native target selection differs')
    return sorted((name, 'passed' if status == 'ok' else 'failed') for name, status in rows)
