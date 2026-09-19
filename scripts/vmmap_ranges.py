"""Read anonymous executable mapping candidates from one owned VM's vmmap report.

These ranges establish inspection readiness. Attribution must additionally bind
the captured process, emitted-code map and exact arena addresses.
"""
import re


def anonymous_executable_ranges(report, expected_pid):
    if type(expected_pid) is not int or expected_pid <= 0:
        raise ValueError('invalid expected VM pid')
    headers = re.findall(r'^Process:[ \t]+rust-interp-vm[ \t]+\[([0-9]+)\][ \t]*$', report, re.M)
    if len(headers) != 1 or int(headers[0]) != expected_pid:
        raise ValueError('vmmap report does not identify the owned VM pid')
    rows = re.findall(
        r'^(?:VM_ALLOCATE|Untagged)[ \t]+([0-9a-fA-F]+)-([0-9a-fA-F]+)'
        r'[ \t]+\[[^\r\n\]]+\][ \t]+rwx/rwx(?:[ \t]|$)', report, re.M)
    ranges = sorted((int(lo, 16), int(hi, 16)) for lo, hi in rows)
    if any(not 0 < lo < hi <= 2**64 for lo, hi in ranges):
        raise ValueError('invalid anonymous executable mapping bounds')
    if any(left[1] > right[0] for left, right in zip(ranges, ranges[1:])):
        raise ValueError('overlapping anonymous executable mapping bounds')
    return ranges
