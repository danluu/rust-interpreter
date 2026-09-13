"""Source-derived diagnostic views for preliminary compiler mechanism checks.

This does not repair compiler diagnostics. Raw records remain authoritative and
missing snippets remain explicit presentation gaps. Only inventoried std files
with identical public, installed, and prepared-source bytes are admissible.
"""
import copy
import json
import os
from pathlib import Path

from custom_compiler import file_digest, require
from std_mir import source_digest


SOURCE_PREFIX = 'lib/rustlib/src/rust/library/'


def source_span_text(span, payload):
    # rustc_errors/json.rs uses original byte offsets and 1-based character
    # columns. Fail closed on source normalization cases not implemented here.
    require(not payload.startswith(b'\xef\xbb\xbf') and b'\r' not in payload,
            'unsupported standard-source normalization')
    text = payload.decode('utf-8', errors='strict')
    lines = text.split('\n')
    fields = ['byte_start', 'byte_end', 'line_start', 'line_end', 'column_start', 'column_end']
    require(all(type(span.get(k)) is int for k in fields), 'invalid standard span coordinates')
    require(1 <= span['line_start'] <= span['line_end'] <= len(lines), 'standard span line out of bounds')
    for end in ['start', 'end']:
        line, column = span['line_' + end], span['column_' + end]
        require(1 <= column <= len(lines[line - 1]) + 1, 'standard span column out of bounds')
        offset = sum(len(s.encode('utf-8')) + 1 for s in lines[:line - 1])
        offset += len(lines[line - 1][:column - 1].encode('utf-8'))
        require(span['byte_' + end] == offset, 'standard span byte/character coordinates disagree')
    require(span['byte_start'] <= span['byte_end'], 'reversed standard span')
    # SourceMap::span_to_lines includes every line through line_end, including
    # a zero-width final line. Interior highlights cover the full line.
    return [dict(text=lines[line - 1],
                 highlight_start=span['column_start'] if line == span['line_start'] else 1,
                 highlight_end=span['column_end'] if line == span['line_end'] else len(lines[line - 1]) + 1)
            for line in range(span['line_start'], span['line_end'] + 1)]


class VerifiedStandardSources:
    def __init__(self, compiler, public_library, prepared):
        self.compiler = compiler
        self.roots = {'public': public_library, 'installed': compiler.sysroot / SOURCE_PREFIX}
        self.files = {name[len(SOURCE_PREFIX):]: sha for name, sha in compiler.identity['files'].items()
                      if name.startswith(SOURCE_PREFIX)}
        require(self.files, 'compiler lacks an inventoried standard source tree')
        self.snapshots = {}
        for mode, ready_path in prepared.items():
            ready = json.loads(ready_path.read_text())
            source_path = ready_path.parent / 'source.json'
            source = json.loads(source_path.read_text())
            require(ready['identity']['compiler_key'] == compiler.key
                    and ready['identity']['source_sha256'] == compiler.identity['source_sha256']
                    and ready['identity']['namespace'] == 'stable-cgu:' + mode,
                    'standard source compiler/namespace differs')
            require(ready['source_sha256'] == source['sha256'], 'standard snapshot manifests disagree')
            name = 'prepared-' + mode
            self.roots[name] = ready_path.parent / 'library'
            self.snapshots[name] = dict(sha256=source['sha256'], ready_path=str(ready_path),
                ready_sha256=file_digest(ready_path), source_path=str(source_path),
                source_manifest_sha256=file_digest(source_path))
        require(set(prepared) == {'off', 'on'}, 'both prepared standard sources are required')
        self.proofs, self.gaps, self.aliases = {}, [], []
        self.recheck()

    def recheck(self):
        for name, proof in self.snapshots.items():
            require(source_digest(self.roots[name]) == proof['sha256']
                    and file_digest(Path(proof['ready_path'])) == proof['ready_sha256']
                    and file_digest(Path(proof['source_path'])) == proof['source_manifest_sha256'],
                    'prepared standard source snapshot changed')
        for relative in self.proofs:
            self.verify_file(relative)

    def verify_file(self, relative):
        paths = {}
        for name, root in self.roots.items():
            path = root / relative
            require(path.resolve(strict=True) == path and path.is_file(),
                    'standard source is missing or indirect: ' + str(path))
            require(file_digest(path) == self.files[relative], 'standard source bytes differ: ' + str(path))
            paths[name] = str(path)
        payload = (self.roots['installed'] / relative).read_bytes()
        # Keep the actual source text in compact evidence; derived snippets are
        # independently reproducible without the live compiler installation.
        self.proofs[relative] = dict(sha256=self.files[relative], paths=paths,
                                    source_text=payload.decode('utf-8', errors='strict'))
        return payload

    def resolve(self, filename, application_roots):
        path = Path(filename)
        if path.is_absolute():
            for root in self.roots.values():
                if path.is_relative_to(root):
                    relative = str(path.relative_to(root))
                    require(relative in self.files and '..' not in path.parts,
                            'unrecognized standard source path')
                    return relative
            return None
        # Exact, whole relative names only; never basename/suffix matching.
        relative = filename.removeprefix('library/')
        if relative not in self.files:
            require(not filename.startswith('library/') and not any(
                filename.startswith(crate + '/src/') for crate in ['core', 'std', 'alloc', 'proc_macro']),
                'unrecognized relative standard source alias')
            return None
        require(filename in (relative, 'library/' + relative) and '..' not in path.parts,
                'noncanonical standard source alias')
        for root in application_roots:
            # Cargo may run rustc from any package directory. Check all fixture
            # directories, including both original and copied workspaces.
            for directory, dirs, _ in os.walk(root):
                dirs[:] = [d for d in dirs if d not in ('target', '.git', '.work')]
                candidate = Path(directory) / path
                require(not candidate.exists() and not candidate.is_symlink(),
                        'ambiguous standard source alias can resolve to an application file')
        return relative

    def comparison(self, records, label, application_roots):
        def visit(value, position):
            if isinstance(value, list):
                return [visit(v, position + [i]) for i, v in enumerate(value)]
            if not isinstance(value, dict):
                return value
            result = {k: visit(v, position + [k]) for k, v in value.items()}
            if 'file_name' not in value:
                return result
            relative = self.resolve(value['file_name'], application_roots)
            if relative is None:
                return result
            expected = source_span_text(value, self.verify_file(relative))
            require(isinstance(value.get('text'), list), 'invalid standard source snippet')
            require(value['text'] == expected or value['text'] == [], 'standard source snippet differs')
            proof = dict(label=label, position=position, raw_file_name=value['file_name'],
                         source=relative, sha256=self.files[relative])
            self.aliases.append(proof)
            if not value['text']:
                self.gaps.append(proof | dict(kind='missing-standard-source-snippet',
                    raw_text=copy.deepcopy(value['text']), source_derived_text=expected))
            result['file_name'] = '<verified-stdlib>/' + relative + '@' + self.files[relative]
            result['text'] = expected
            return result
        # Sorting happens after alias substitution; duplicate units stay intact.
        return sorted(visit(records, []), key=lambda value: json.dumps(value, sort_keys=True))

    def evidence(self):
        return dict(kind='source-identity-diagnostic-comparison', preliminary_only=True,
            compiler_key=self.compiler.key, snapshots=self.snapshots, files=self.proofs,
            aliases=self.aliases, presentation_gaps=self.gaps,
            source_derived_text_is_compiler_output=False, full_presentation_qualified=False,
            final_target_eligible=False, adoption_eligible=False)
