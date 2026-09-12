"""Strict libtest summaries; rounded suite time is not process execution time."""
import re

SUMMARY = re.compile(
    r'^test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; '
    r'(\d+) ignored; (\d+) measured; (\d+) filtered out; '
    r'finished in (\d+\.\d{2})s$', re.M)
GROUPED_SUMMARY = re.compile(
    r'^test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; '
    r'(\d+) ignored; (\d+) filtered out; across (\d+) groups, '
    r'finished in (\d+\.\d{2})s$', re.M)


def libtest_summary(stdout, *, selected=None, success=True):
    matches = [(m, 'libtest') for m in SUMMARY.finditer(stdout)]
    matches += [(m, 'grouped') for m in GROUPED_SUMMARY.finditer(stdout)]
    if len(matches) != 1:
        raise ValueError('expected exactly one libtest summary')
    match, harness = matches[0]
    outcome, *fields = match.groups()
    passed, failed, ignored = map(int, fields[:3])
    if harness == 'libtest':
        measured, filtered = map(int, fields[3:5])
        groups = None
    else:
        measured = None
        filtered, groups = map(int, fields[3:5])
    seconds = float(fields[5])
    if success:
        if outcome != 'ok' or failed or (selected is not None and passed != selected):
            raise ValueError('original selected tests did not all pass')
    elif outcome != 'FAILED' or not failed:
        raise ValueError('negative edit did not fail its original tests')
    return dict(harness=harness, groups=groups,
                passed=passed, failed=failed, ignored=ignored, measured=measured,
                filtered=filtered, rounded_seconds=seconds,
                lower_seconds=max(0, seconds - .005), upper_seconds=seconds + .005)


def residual_seconds(command_seconds, suite):
    if command_seconds < suite['lower_seconds']:
        raise ValueError('suite time exceeds complete command')
    return dict(lower=max(0, command_seconds - suite['upper_seconds']),
                upper=command_seconds - suite['lower_seconds'])
