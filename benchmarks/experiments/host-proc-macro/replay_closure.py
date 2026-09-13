#!/usr/bin/env python3
"""Caller-serialized retained otool replay; never execute an inspected command."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import public_tool_publication as publication
from custom_compiler import file_digest, require
from workflow_io import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    metadata = args.metadata.resolve(strict=True)
    require(metadata.is_relative_to(ROOT / '.work'), 'replay input is not owned')
    output = args.output.absolute()
    require(output.is_relative_to(ROOT / '.work') and not output.exists() and not output.is_symlink(),
            'replay output must be fresh and owned')
    expected_inputs = json.loads((metadata.parent / 'payload/provenance/compiler-inputs.json').read_bytes())
    hashes = {r['resolved']: r['sha256'] for r in expected_inputs['files']}
    subjects, retained, calls = {}, {}, []
    for name in ('rustc', 'cargo'):
        paths = sorted(metadata.glob('closure-' + name + '-*-process.json'))
        if not paths:continue
        commands = {}
        for path in paths:
            record = json.loads(path.read_bytes())
            require(record['status'] == 'finished' and record['returncode'] == 0,
                    'retained inspector did not succeed')
            argv = tuple(record['command'])
            require(argv[:3] == ('/usr/bin/otool', '-arch', 'arm64') and argv[3] in ('-L', '-l')
                    and len(argv) == 5 and argv not in commands, 'unexpected retained inspector')
            prefix = path.name.removesuffix('-process.json')
            stdout, stderr = [metadata / (prefix + suffix) for suffix in ('.stdout', '.stderr')]
            commands[argv] = (stdout.read_text(), stderr.read_text())
            for source in (path, stdout, stderr):retained[str(source)] = file_digest(source)
        first = json.loads(paths[0].read_bytes())['command']
        require(first[3] == '-L', 'closure lacks initial executable inspection')
        used = set()

        def replay(command, **kwargs):
            argv = tuple(command)
            require(argv in commands and argv not in used, 'inspector replay differs from retained commands')
            used.add(argv); calls.append(list(argv))
            return commands[argv]

        with patch.object(publication, 'retained_command', replay):
            closure = publication.capture_library_closure(Path(first[4]), 'aarch64-apple-darwin',
                receipt_directory=metadata, env={}, label='replay-' + name)
        require(used == set(commands), 'retained inspector commands were not all replayed')
        for record in [closure['executable'], *closure['identity']['libraries']]:
            require(hashes[record['resolved']] == record['sha256'], 'current inspected input differs from failed attempt')
        subjects[name] = closure
    require(subjects, 'no retained closures')
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, dict(status='passed', subjects=subjects, retained=retained, calls=calls,
        source_sha256=file_digest(Path(__file__)), inspector_children_started=0,
        scope='retained command output replay with current input hashes checked against original inventory'))
    print(json.dumps(dict(status='passed', subjects=list(subjects), replayed_commands=len(calls),
                          inspector_children_started=0, output=str(output))))


if __name__ == '__main__':
    main()
