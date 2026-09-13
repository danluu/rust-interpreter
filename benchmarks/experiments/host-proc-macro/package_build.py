#!/usr/bin/env python3
"""Package existing macro qualification evidence; no compiler, test or inspector runs."""
import argparse
import gzip
import io
import json
from pathlib import Path
import re
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from custom_compiler import require
from qualified_public_tools import sha, validate_input_guard, validate_public_tool


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assessor-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assessor = args.assessor_root.resolve(strict=True)
    output = args.output.absolute()
    require(not output.exists() and not output.is_symlink(), 'evidence destination already exists')
    work = ROOT / '.work/host-proc-macro-build-05'
    result = json.loads((work / 'result.json').read_bytes())
    require(result['status'] == 'qualified-and-published' and result['commands'] == 8
            and result['screen_executed'] is False and result['performance_claim'] is False,
            'build did not qualify for this evidence package')
    key = result['tool_key']
    data, records, blobs = {}, {}, {}

    def add(name, path):
        path = Path(path)
        require(path.is_file() and not path.is_symlink(), 'evidence is not a regular file: ' + str(path))
        payload = path.read_bytes(); digest = sha(payload)
        require(name not in records, 'duplicate logical evidence name')
        member = blobs.setdefault(digest, name)
        data[name] = payload
        records[name] = dict(archive_member=member, source=str(path), sha256=digest, bytes=len(payload))

    def tree(prefix, directory):
        for path in sorted(directory.rglob('*')):
            require(not path.is_symlink(), 'evidence tree contains a symlink')
            if path.is_file():add(prefix + '/' + str(path.relative_to(directory)), path)

    installations = result['publication']['installations']
    require(len(installations) == 2 and installations[0]['owner'] == str(ROOT), 'wrong publication owners')
    primary_tool = Path(installations[0]['directory'])
    composition = json.loads((primary_tool / 'source.json').read_bytes())['composition']
    for name, expected in composition['payloads'].items():
        add('publication/' + name, primary_tool / name)
        require(records['publication/' + name]['sha256'] == expected, 'published payload differs')
        require((Path(installations[1]['directory']) / name).read_bytes() == data['publication/' + name],
                'published owner payloads differ')
    roles = dict(zip(('macro', 'primary'), (Path(row['directory']) for row in installations)))
    for role, tool in roles.items():
        for name in ('source.json', 'ready.json', 'capabilities.json', 'publication.json', 'publication-guard.json'):
            add('installations/' + role + '/' + name, tool / name)

    def public_reader(contents, path):
        for role, tool in roles.items():
            if path.is_relative_to(tool):
                name = str(path.relative_to(tool))
                return contents[('publication/' if name.startswith('provenance/') else 'installations/' + role + '/') + name]
        raise RuntimeError('unexpected archived input path: ' + str(path))

    def check_public(contents):
        validated = None
        for role, tool in roles.items():
            current = validate_public_tool(tool, key, lambda p: public_reader(contents, p))
            guard = json.loads(contents['installations/' + role + '/publication-guard.json'])
            validate_input_guard(current, guard)
            require(guard['validation'] == 'sha256', 'publication lacks full input hashing')
            if validated:require(current['composition'] == validated['composition'], 'owner compositions differ')
            validated = current
        return validated

    validated = check_public(data)
    for path in sorted(work.iterdir()):
        if path.is_file():add('build-05/' + path.name, path)
    for index in (1, 2, 3, 4, 5):
        add(f'plans/planned-build-{index:02}.json', Path(__file__).with_name(f'planned-build-{index:02}.json'))
    failures = []
    for index in (3, 4):
        previous = ROOT / f'.work/host-proc-macro-build-{index:02}'
        supervisor = json.loads((previous / 'supervisor.json').read_bytes())
        require(supervisor['status'] == 'failed' and not list(previous.glob('*-process.json')),
                'failed attempt unexpectedly started qualification commands')
        tree(f'failures/build-{index:02}', previous)
        failures.append(dict(plan=index, supervisor_pid=supervisor['pid'], error=supervisor['error'],
                             qualification_commands_started=0, metadata_commands=len(list((previous / 'metadata').glob('*-process.json')))))
    add('failures/admission-03.json', ROOT / '.work/host-proc-macro-admission-03-failed.json')
    replay = json.loads(data['publication/provenance/prior-attempt/.work/host-proc-macro-closure-replay-01/summary.json'])
    require(replay['status'] == 'passed' and len(replay['calls']) == 8 and replay['inspector_children_started'] == 0,
            'retained inspector replay did not pass')
    tests = []
    for label in ('macro-publication-inventory-tests-01', 'macro-publication-loader-tests-01'):
        directory = assessor / '.work' / label
        summary = json.loads((directory / 'summary.json').read_bytes())
        process = json.loads((directory / 'process.json').read_bytes())
        stderr = (directory / 'stderr').read_text()
        require(summary['status'] == 'passed' and summary['expected_tests'] == 5
                and process['returncode'] == 0 and process['status'] == 'finished'
                and re.search(r'^Ran 5 tests in [\d.]+s$', stderr, re.M) and '\nOK\n' in stderr
                and 'skipped' not in stderr, 'root publication controls did not pass')
        for name, expected in summary['source_hashes'].items():
            snapshot = directory / 'sources' / Path(name).relative_to(assessor)
            require(sha(snapshot.read_bytes()) == expected, 'root test source snapshot differs')
        tree('root-tests/' + label, directory)
        tests.append(dict(name=label, tests=5, revision=summary['revision'], supervisor_pid=summary['supervisor_pid'],
                          child_pid=process['pid'], source_files=len(summary['source_hashes'])))
    prior = assessor / 'results/macro-screen-assessment-tests-03'
    prior_summary = json.loads((prior / 'summary.json').read_bytes())
    archive = prior / prior_summary['archive']['path']
    require(sha(archive.read_bytes()) == prior_summary['archive']['sha256'], 'prior21 archive differs')
    with tarfile.open(archive, 'r:gz') as stream:
        expected = {row['name']: row for row in prior_summary['members']}
        require(set(stream.getnames()) == set(expected), 'prior21 archive member set differs')
        for member in stream:
            require(member.isfile() and sha(stream.extractfile(member).read()) == expected[member.name]['sha256'],
                    'prior21 archive member differs')
    require(prior_summary['status'] == 'passed' and prior_summary['test_count'] == 21, 'prior21 did not pass')
    add('references/root-21-summary.json', prior / 'summary.json')
    add('references/root-21-README.md', prior / 'README.md')
    add('packager/package_build.py', Path(__file__))

    correctness = validated['correctness']; counts = correctness['results']
    require(counts['rust-workspace-tests']['passed'] == 479 and counts['real-histories']['passed'] == 3,
            'unexpected macro qualification count')
    ignored = re.findall(r'^test (.+) \.\.\. ignored, (.+)$', data['build-05/rust-workspace-tests.stdout'].decode(), re.M)
    require(len(ignored) == 1 and sum(s['ignored'] for s in counts['rust-workspace-tests']['suites']) == 1,
            'ignored Rust test inventory differs')
    supervisor = json.loads(data['build-05/supervisor.json'])
    require(supervisor['status'] == 'supervisor-exited', 'build supervisor did not finish')
    command_rows = []
    for command in validated['commands']:
        receipt = json.loads(data['publication/' + command['receipt']])
        command_rows.append(dict(label=command['label'], pid=receipt['pid'], returncode=receipt['returncode'],
            elapsed_seconds=receipt['finished_at'] - receipt['started_at'], argv=receipt['command']))
    manifest = dict(schema_version=1, logical_files=records,
        storage='Identical byte strings share an archive member; every logical name retains its source path, hash and size.')
    output.mkdir(parents=True)
    archive_path = output / 'evidence.tar.gz'
    with archive_path.open('xb') as destination, gzip.GzipFile(fileobj=destination, mode='wb', filename='', mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w', format=tarfile.PAX_FORMAT) as stream:
            for name, payload in sorted([('manifest.json', encoded(manifest)), *[(name, data[name]) for name in blobs.values()]]):
                member = tarfile.TarInfo(name); member.size = len(payload); member.mode = 0o444; member.mtime = 0
                stream.addfile(member, io.BytesIO(payload))
    with tarfile.open(archive_path, 'r:gz') as stream:
        archived = {m.name:stream.extractfile(m).read() for m in stream if m.isfile()}
    require(json.loads(archived.pop('manifest.json')) == manifest, 'archive manifest changed')
    reconstructed = {}
    for name, record in records.items():
        payload = archived[record['archive_member']]
        require(sha(payload) == record['sha256'] and len(payload) == record['bytes'], 'archive bytes differ')
        reconstructed[name] = payload
    check_public(reconstructed)
    summary = dict(schema_version=1, status='qualified-and-published', performance_claim=False, screen_executed=False,
        production_source_revision=composition['source']['revision'], build_harness_revision='71c7feac',
        source_input_key=composition['source']['source_input_key'], tool_key=key, binaries=composition['binaries'],
        installations=installations, public_compiler=composition['public_compiler'], public_cargo=composition['public_cargo'],
        shared_std=dict(key=correctness['shared_std']['key'], ready_sha256=correctness['shared_std']['ready_sha256'],
                        sysroot=correctness['shared_std']['sysroot'], artifacts=len(correctness['shared_std']['files'])),
        build=dict(supervisor_pid=supervisor['pid'], elapsed_seconds=supervisor['finished_at'] - supervisor['started_at'],
                   profile=composition['build']['profile'], environment_overrides=composition['build']['environment_overrides'], commands=command_rows),
        tests=dict(rust_passed=479, rust_ignored=[dict(name=n, reason=r) for n,r in ignored], launcher=3, screen_contracts=24, real_histories=3, python_skips=0),
        failed_attempts=failures, admission_failure='Before any child; failed supervisor PID unavailable in the tool result; exact limitation retained.',
        retained_replay=dict(commands=8, inspector_children_started=0), root_followup_tests=tests,
        prior21_reference=dict(path='results/macro-screen-assessment-tests-03/evidence.tar.gz', **{k:v for k,v in prior_summary['archive'].items() if k!='path'}, verified_again=True),
        archive=dict(path=archive_path.name, sha256=sha(archive_path.read_bytes()), bytes=archive_path.stat().st_size,
                     members=len(archived)+1, logical_files=len(records), all_logical_hashes_verified=True, both_archived_publications_validated=True),
        limitations=['Setup elapsed time includes compilation, tests, inventories and publication; it is not a warm benchmark.',
            'Compiled artifacts, registry/compiler libraries and std metadata stay in owned caches; their exact identities and publication-time full-hash guards are retained.',
            'Plans01/02 were not executed; plans03/04 failed before their eight qualification commands.',
            'No holdout or performance screen is included; no speed or 0.5-second claim.'])
    (output / 'summary.json').write_bytes(encoded(summary))
    text = f'''# Macro tool build and publication qualification

The same public-compiler toolset `{key}` passed all eight required commands and
was published into both recorded owners. There is no performance result here.

Rust: **479 passed, one existing ignored test** (`{ignored[0][0]}`), whose retained
reason is “{ignored[0][1]}”. Python: **3 launcher contracts, 24 screen contracts,
and all 3 real compiler histories passed**, with zero skips. The histories cover
uncalled errors, macro cfg/debug/overflow behavior, Cargo host macros and declared
file inputs, generated errors, fresh edits/restoration, and selected guest
bytecode parity. Source, actual commands/output, native/VM execution records and
the shared std receipt are retained; assertions are the frozen fixture's.

Plan03 failed on a registry layout assumption; plan04 passed that inventory and
failed on a logical loader-path validation mismatch. Both stopped before any of
their eight qualification commands. The initial missing `.work` admission failure
is also retained, including its unavailable-PID limitation. Plans01/02 remain
unexecuted. The fixes were qualified by five inventory tests, five loader tests,
and replay of all eight saved rustc inspection records without new inspector
processes. The prior 21-test archive is referenced by exact hash and was fully
reverified; it has not been overwritten or silently replaced.

Plan05's supervisor16668 completed in {summary['build']['elapsed_seconds']:.3f}s,
including the build, tests, inventories and publication. This is setup duration,
not a warm build or an improvement estimate. Release debug level1 and the pinned
public compiler/Cargo identities are recorded. No custom compiler/Cargo or other
optimization policy was combined with the macro qualification.

`evidence.tar.gz` contains {len(records)} logical files in {len(archived)+1} physical
members. `manifest.json` maps every logical name to an exact archive member,
source path, size and SHA-256; identical bytes are stored once. Both owner
publications are revalidated using only reconstructed archive bytes with the
shared pure validator, including full publication input guards. Every archived
hash was checked after compression. Binaries/caches are not copied into Git.
The publication-time identities cover the actual three binaries, compiler and
Cargo, resolved non-system loader closures, platform assumption, dependency
archives/source files, effective configuration and prepared std artifacts.

Reproduce into a new output directory with `python3 -B
benchmarks/experiments/host-proc-macro/package_build.py --assessor-root
{assessor} --output <new-directory>` while the retained evidence remains available.
This packager executes no compiler, test, inspector or benchmark.
'''
    (output / 'assessment.md').write_text(text)
    print(json.dumps(dict(output=str(output), archive=summary['archive'], tool_key=key)))


if __name__ == '__main__':
    main()
