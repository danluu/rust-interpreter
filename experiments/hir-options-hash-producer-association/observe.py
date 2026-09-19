"""Bounded read-only observation of existing native005; no workload invocation."""
import hashlib
import json
from pathlib import Path
import re
import shlex
import tomllib

HERE = Path(__file__).resolve().parent
S = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01/source')
C = Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
RAW = Path('/Users/danluu/dev/rust-interp-hir-arena-native-20260913/.work/hir-arena-native-01/stages/native-01/commands/005')


def stamp(path):
    s = path.lstat()
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]


def main():
    assert not (HERE / 'observation.json').exists()
    inputs = {}
    def load(path):
        assert path.resolve(strict=True) == path and path.is_file() and path.stat().st_size <= 4 * 2**20
        before = stamp(path); raw = path.read_bytes(); assert stamp(path) == before
        inputs[str(path)] = dict(size=len(raw), sha256=hashlib.sha256(raw).hexdigest(), stamp=before)
        return raw
    source_names = ['src/bootstrap/src/core/session.rs', 'src/bootstrap/src/core/builder/mod.rs',
                    'src/bootstrap/src/core/builder/cargo.rs', 'src/bootstrap/src/core/build_steps/compile.rs',
                    'src/bootstrap/src/core/build_steps/test.rs', 'src/bootstrap/src/utils/exec.rs',
                    'src/bootstrap/bootstrap.py']
    for name in source_names:
        assert load(S / name) == load(C / name), 'historical/candidate bootstrap source differs: ' + name
    config = tomllib.loads(load(S / 'bootstrap.toml').decode())
    assert config['build']['print-step-timings'] is True
    receipt = json.loads(load(RAW / 'receipt.json'))
    stdout, stderr = load(RAW / 'stdout'), load(RAW / 'stderr')
    assert receipt['status'] == 'finished' and receipt['returncode'] == 0
    assert receipt['stdout_sha256'] == hashlib.sha256(stdout).hexdigest()
    assert receipt['stderr_sha256'] == hashlib.sha256(stderr).hexdigest()
    load(HERE / 'PROPOSAL.md'); load(Path(__file__).resolve())
    stack, timing, cargo = [], [], []
    for number, raw in enumerate(stdout.splitlines(keepends=True), 1):
        line = raw.decode().rstrip('\r\n')
        start = re.fullmatch(r'\[TIMING:start\] (.+)', line)
        end = re.fullmatch(r'\[TIMING:end\] (.+) -- ([0-9]+\.[0-9]{3})', line)
        if line.startswith('[TIMING:'):
            assert start or end, 'unparsed timing record'
        if start:
            stack.append(start[1]); timing.append(dict(line=number, kind='start', step=start[1], depth=len(stack)))
        elif end:
            assert stack and stack[-1] == end[1], 'mismatched timing stack'
            timing.append(dict(line=number, kind='end', step=end[1], depth=len(stack))); stack.pop()
        elif line.startswith('running: ') and '--message-format' in line:
            words = shlex.split(line.removeprefix('running: '))
            environment = {}
            for word in words:
                if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*=.*', word, re.S):
                    key, value = word.split('=', 1); assert key not in environment
                    environment[key] = value
            cargo.append(dict(line=number, line_sha256=hashlib.sha256(raw).hexdigest(),
                              timing_stack=list(stack), target_directory=environment['CARGO_TARGET_DIR'],
                              environment=environment))
    assert not stack and len(timing) == 30
    assert [row['line'] for row in cargo] == [32, 33, 57, 70]
    assert [len(row['timing_stack']) for row in cargo] == [0, 0, 2, 1]
    assert not any(b'compiler-artifact' in line or line.startswith(b'{') for line in stdout.splitlines())
    segments, begin = [], 1
    lines = stderr.decode().splitlines()
    for number, line in enumerate(lines, 1):
        match = re.fullmatch(r'    Finished `(dev|release|dist)` profile \[([^\n]+)\] target\(s\) in ([0-9a-z .]+)', line)
        if match:
            commands = [index for index, value in enumerate(lines[begin - 1:number], begin) if re.match(r'\s*Running `', value)]
            segments.append(dict(first_line=begin, finished_line=number, profile=match[1],
                                 finished_text=line, running_line_count=len(commands)))
            begin = number + 1
    assert [row['finished_line'] for row in segments] == [67, 983, 1109]
    assert [row['running_line_count'] for row in segments] == [0, 173, 42]
    first, real = cargo[0]['environment'], cargo[2]['environment']
    differences = {key: dict(self_check_print=first.get(key), real_timed_print=real.get(key))
                   for key in sorted(first.keys() | real.keys()) if first.get(key) != real.get(key)}
    for name, row in inputs.items():
        path = Path(name); assert stamp(path) == row['stamp']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'] and stamp(path) == row['stamp']
    report = dict(status='read-only-historical-observation-not-successor-qualification', inputs=inputs,
                  source_files_identical_between_historical_and_candidate=len(source_names),
                  stdout_lines=len(stdout.splitlines()), stderr_lines=len(lines), timing_events=timing,
                  printed_stream_cargo_commands=cargo, stderr_finished_segments=segments,
                  stderr_trailing_lines=len(lines) - begin + 1, native_environment_differences=differences,
                  compiler_artifact_json_forwarded=False, new_candidate_build_observed=False,
                  controls_executed=0, compiler_calls=0, caveat='Timing classification is a proposed source-backed relation. No new producer admission or Finished-boundary parser is qualified.')
    with (HERE / 'observation.json').open('x') as output:
        json.dump(report, output, sort_keys=True, indent=2); output.write('\n')
    print(json.dumps(dict(status=report['status'], inputs=len(inputs), timing_events=len(timing),
                         printed_stream_commands=len(cargo), compiler_calls=0), indent=2))


if __name__ == '__main__': main()
