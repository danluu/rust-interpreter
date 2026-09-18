"""A failed parser guard terminates qualification without requiring another run."""

PROFILES = ['incremental', 'repository']


def parser_decision(results):
    assert 1 <= len(results) <= len(PROFILES)
    for index, result in enumerate(results):
        assert result['profile'] == PROFILES[index]
        assert result['commands'] == 88 and result['tests'] == 114
        assert isinstance(result['gate_passed'], bool)
        if not result['gate_passed']:
            assert index == len(results) - 1, 'parser run started after a failed guard'
            return dict(passed=False, unstarted=PROFILES[len(results):])
    assert len(results) == len(PROFILES), 'passing parser prefix is not terminal'
    return dict(passed=True, unstarted=[])
