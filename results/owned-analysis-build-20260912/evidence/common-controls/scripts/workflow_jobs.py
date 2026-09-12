"""Explicit Cargo worker counts for paired workflow comparisons."""
import argparse


def checked_count(value, label):
    if type(value) is not int or not 1 <= value <= 256:
        raise ValueError(label + ' must be an integer in 1..256')
    return value


class UniqueJobCount(argparse.Action):
    """Reject repeated job options instead of silently keeping the last value."""

    def __call__(self, parser, namespace, values, option_string=None):
        supplied = getattr(namespace, '_specified_job_counts', [])
        if self.dest in supplied:
            raise argparse.ArgumentError(self, 'job option specified more than once')
        try:
            count = checked_count(values, option_string or self.dest)
        except ValueError as error:
            raise argparse.ArgumentError(self, str(error)) from error
        setattr(namespace, self.dest, count)
        # Corpus plans serialize vars(namespace); preserve duplicate detection
        # without leaving a non-JSON set in the argument receipt.
        setattr(namespace, '_specified_job_counts', [*supplied, self.dest])


def resolve_build_jobs(shared, *, native=None, baseline=None, candidate=None, paired=False):
    """Resolve independent overrides without changing the shared/native default."""
    shared = checked_count(shared, 'shared jobs')
    if type(paired) is not bool:
        raise ValueError('paired must be a boolean')
    if not paired and (baseline is not None or candidate is not None):
        raise ValueError('baseline/candidate jobs require a paired comparison')
    native = shared if native is None else checked_count(native, 'native jobs')
    if paired:
        custom = {
            'baseline': shared if baseline is None else checked_count(baseline, 'baseline jobs'),
            'candidate': shared if candidate is None else checked_count(candidate, 'candidate jobs'),
        }
    else:
        custom = dict(interpreter=shared, jit=shared)
    return dict(native=native, **{'check-floor': native}, **custom)


def recorded_build_jobs(report):
    """Read new per-mode counts or the historical single custom-job count.

    Historical reports lacking build/native controls must keep their previous
    verifier path. They cannot establish explicit worker-count provenance.
    """
    shared = checked_count(report['build_jobs'], 'recorded shared jobs')
    native = checked_count(report['native_control']['jobs'], 'recorded native jobs')
    modes = ['baseline', 'candidate'] if 'comparison' in report else ['interpreter', 'jit']
    if 'custom_build_jobs' in report:
        custom = report['custom_build_jobs']
        if type(custom) is not dict or set(custom) != set(modes):
            raise ValueError('recorded custom jobs must contain exactly the custom modes')
        custom = {mode: checked_count(custom[mode], 'recorded ' + mode + ' jobs') for mode in modes}
    else:
        custom = dict.fromkeys(modes, shared)
    return dict(native=native, **{'check-floor': native}, **custom)


def verify_command_jobs(command, expected):
    """Require the one canonical worker option emitted by our Cargo launchers."""
    expected = checked_count(expected, 'expected jobs')
    if not isinstance(command, list) or not all(isinstance(arg, str) for arg in command):
        raise ValueError('command must be a list of strings')
    # Native commands append libtest arguments after this separator.
    build = command[:command.index('--')] if '--' in command else command
    locations = [i for i, arg in enumerate(build) if arg == '--jobs']
    if len(locations) != 1 or any(arg.startswith(('--jobs=', '-j')) for arg in build):
        raise ValueError('command must contain exactly one canonical --jobs option')
    index = locations[0]
    if index + 1 >= len(build) or build[index + 1] != str(expected):
        raise ValueError('executed Cargo job count differs from the recorded mode')
