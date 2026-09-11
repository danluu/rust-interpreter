#!/usr/bin/env python3
"""Qualify worker controls separately from actual workflow integration."""
import argparse
from contextlib import redirect_stderr
from copy import deepcopy
import fcntl
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_repeated_workflow import require
from workflow_io import write_json
from workflow_jobs import UniqueJobCount, recorded_build_jobs, resolve_build_jobs, verify_command_jobs


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify():
    configurations = [
        ({}, dict(native=4, interpreter=4, jit=4)),
        (dict(native=18), dict(native=18, interpreter=4, jit=4)),
        (dict(paired=True), dict(native=4, baseline=4, candidate=4)),
        (dict(paired=True, candidate=18), dict(native=4, baseline=4, candidate=18)),
        (dict(paired=True, baseline=1), dict(native=4, baseline=1, candidate=4)),
        (dict(paired=True, native=18, baseline=1, candidate=256), dict(native=18, baseline=1, candidate=256)),
    ]
    for arguments, expected in configurations:
        require(resolve_build_jobs(4, **arguments) == dict(expected, **{'check-floor': expected['native']}),
                'worker override changed another mode or default')
    rejected = []

    def reject(label, function, *args, **kwargs):
        try:
            function(*args, **kwargs)
        except ValueError:
            rejected.append(label)
        else:
            raise RuntimeError('accepted invalid worker control: ' + label)

    for value in [0, -1, 257, True, 4.0, '4']:
        reject('shared ' + repr(value), resolve_build_jobs, value)
        for field in ['native', 'baseline', 'candidate']:
            reject(field + ' ' + repr(value), resolve_build_jobs, 4, paired=True, **{field: value})
    reject('missing shared count', resolve_build_jobs, None)
    reject('nonboolean comparison', resolve_build_jobs, 4, paired='yes')
    for mode in ['baseline', 'candidate']:
        reject('unpaired ' + mode, resolve_build_jobs, 4, **{mode: 4})

    parser = argparse.ArgumentParser()
    for flag in ['jobs', 'native-jobs', 'baseline-jobs', 'candidate-jobs']:
        parser.add_argument('--' + flag, type=int, action=UniqueJobCount, default=4 if flag == 'jobs' else None)
    parsed = parser.parse_args(['--jobs=4', '--native-jobs', '18', '--candidate-jobs=18'])
    require((parsed.jobs, parsed.native_jobs, parsed.baseline_jobs, parsed.candidate_jobs) == (4, 18, None, 18),
            'job options parsed incorrectly')
    require(json.loads(json.dumps(vars(parsed)))['candidate_jobs'] == 18,
            'job parser namespace cannot be serialized in a corpus plan')
    require(parser.parse_args([]).jobs == 4, 'parser retains previous invocation state')
    cli_rejections = 0
    for flag in ['jobs', 'native-jobs', 'baseline-jobs', 'candidate-jobs']:
        for arguments in [[f'--{flag}', '0'], [f'--{flag}', '257'],
                          [f'--{flag}', '4', f'--{flag}=4'], [f'--{flag}=4', f'--{flag}', '18']]:
            with redirect_stderr(io.StringIO()):
                try:
                    parser.parse_args(arguments)
                except SystemExit as error:
                    require(error.code == 2, 'wrong argument rejection status')
                else:
                    raise RuntimeError('invalid or repeated job option accepted')
            cli_rejections += 1

    for command in [[], ['cargo', '--jobs'], ['cargo', '--jobs=4'], ['cargo', '-j4'],
                    ['cargo', '--jobs', '4', '--jobs', '4'], ['cargo', '--jobs', '4', '-j18'],
                    ['cargo', '--jobs', '4', '--jobs=18'], ['cargo', '--jobs', '18'],
                    ['cargo', '--jobs', '04'], ['cargo', '--jobs', '--', '4'], 'cargo --jobs 4']:
        reject('command ' + repr(command), verify_command_jobs, command, 4)
    verify_command_jobs(['cargo', 'test', '--jobs', '4', '--', '--exact', 'jobs'], 4)
    verify_command_jobs(['launcher', '--jobs', '18', '--entry', 'tests::jobs'], 18)

    report = dict(build_jobs=4, native_control=dict(jobs=18), comparison={})
    for custom in [None, [], {}, dict(baseline=4), dict(baseline=4, candidate=18, native=18),
                   dict(interpreter=4, jit=18), dict(baseline=True, candidate=18)]:
        reject('receipt ' + repr(custom), recorded_build_jobs, dict(report, custom_build_jobs=custom))
    new = dict(report, custom_build_jobs=dict(baseline=4, candidate=18))
    require(recorded_build_jobs(new) == {'native': 18, 'check-floor': 18, 'baseline': 4, 'candidate': 18},
            'new receipt loses separate worker counts')
    reject('false candidate receipt', verify_command_jobs, ['launcher', '--jobs', '4'],
           recorded_build_jobs(new)['candidate'])
    altered = deepcopy(new)
    altered['native_control']['jobs'] = False
    reject('false native count', recorded_build_jobs, altered)
    require(recorded_build_jobs(dict(build_jobs=1, native_control=dict(jobs=256))) ==
            {'native': 256, 'check-floor': 256, 'interpreter': 1, 'jit': 1}, 'legacy nonpaired receipt differs')

    histories = []
    for name in ['interface-pgrust-repeated-01', 'interface-nushell-repeated-01',
                 'lightweight-wrapper-pgrust-repeated-01', 'lightweight-wrapper-nushell-repeated-01',
                 *[f'lightweight-wrapper-nushell-cold-{i:02d}' for i in range(1, 4)]]:
        path = ROOT / 'results' / name / 'summary.json'
        report = json.loads(path.read_text())
        jobs = recorded_build_jobs(report)
        count = 0
        records = ROOT / report['raw'] / 'records.json'
        checks = records.with_name('check-records.json')
        for row in json.loads(records.read_text()):
            for call in row['calls']:
                verify_command_jobs(call['command'], jobs[row['mode']])
                count += 1
        for row in json.loads(checks.read_text()):
            verify_command_jobs(row['command'], jobs['check-floor'])
            count += 1
        histories.append(dict(run=name, commands=count, report_sha256=sha(path),
                              records_sha256=sha(records), check_records_sha256=sha(checks)))
    return dict(status='passed', resolver_configurations=len(configurations), rejections=rejected,
                parser_namespace_json_serializable=True,
                cli_rejections=cli_rejections, historical_command_checks=histories,
                note='Standalone helper checks; actual workflow integration and project execution are qualified separately.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid ID')
    out = ROOT / 'results' / args.run_id
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not out.exists(), 'qualification already exists')
        result = qualify()
        paths = [Path(__file__), ROOT / 'scripts/workflow_jobs.py']
        result['sources'] = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        out.mkdir()
        write_json(out / 'summary.json', result)
        print(json.dumps(dict(status=result['status'], configurations=result['resolver_configurations'],
                              rejected=len(result['rejections']), cli_rejections=result['cli_rejections'],
                              historical_commands=sum(h['commands'] for h in result['historical_command_checks']))))


if __name__ == '__main__':
    main()
