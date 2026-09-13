"""Equal compiler-side std diagnostic remaps for correctness qualification only.

No compiler subprocesses and no diagnostic rewriting. The caller first loads
authoritatively checked compiler/std identities and retains actual compiler argv.
This helper verifies sources, writes a new fixture Cargo configuration, and
checks the real JSON spans emitted under that configuration.
"""
import copy
import json
from pathlib import Path
import re
import stat

from custom_compiler import digest, file_digest, require, tree_stamps
from std_mir_source_paths import SOURCE, compiler_sources, configuration, validate_environment
from toolchain_lookup import _stamp
from verified_std_diagnostics import source_span_text

POLICY = 'standard-diagnostic-mapping-v1'


def _commit(version):
    matches = re.findall(r'^commit-hash: ([0-9a-f]{40})$', version, flags=re.MULTILINE)
    require(len(matches) == 1, 'diagnostic mapping requires a truthful compiler commit')
    return matches[0]


def _ordinary(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path,
            'diagnostic mapping requires ordinary absolute paths: ' + str(path))
    require(not any(c in str(path) for c in ['=', '\n', '\r', '\x00']),
            'diagnostic mapping path cannot be represented in compiler flags')
    return path


class StandardDiagnosticMapping:
    def __init__(self, fixture_root, compiler, public_library, prepared_sysroots, environment,
                 *, public_compiler):
        self.fixture_root = _ordinary(fixture_root)
        require(self.fixture_root.is_dir(), 'diagnostic fixture must exist')
        require(set(prepared_sysroots) == {'off', 'on'}, 'both prepared standard sysroots are required')
        validate_environment(environment)
        require('RUSTC' not in environment, 'equal diagnostic qualification requires no ambient RUSTC')
        self.environment = environment
        self.environment_sha256 = digest(environment)
        self.compiler = compiler
        self.compiler_identity_sha256 = digest(compiler.identity)
        commit, self.files = compiler_sources(compiler)
        self.files = dict(sorted(self.files.items()))
        self.public_compiler = copy.deepcopy(public_compiler)
        public_commit = _commit(public_compiler['compiler'])
        self.public_rustc = _ordinary(public_compiler['rustc'])
        require(file_digest(self.public_rustc) == public_compiler['sha256'],
                'public compiler bytes differ from its retained identity')
        require([s[6:] for s in public_compiler['compiler'].splitlines() if s.startswith('host: ')]
                == [compiler.host], 'diagnostic compiler hosts differ')
        self.custom_rustc = _ordinary(compiler.rustc)
        require(file_digest(self.custom_rustc) == compiler.identity['files']['bin/rustc'],
                'custom compiler bytes differ from its identity')
        self.compiler_stamps = {'public': _stamp(self.public_rustc), 'custom': _stamp(self.custom_rustc)}
        self.roots = {'public': _ordinary(public_library),
                      'installed': _ordinary(compiler.sysroot / SOURCE)}
        require(self.roots['public'] == self.public_rustc.parent.parent / SOURCE,
                'public standard sources do not belong to the retained compiler prefix')
        for mode in ['off', 'on']:
            self.roots['prepared-' + mode] = _ordinary(Path(prepared_sysroots[mode]) / SOURCE)
        self.source_stamps = {}
        for name, root in self.roots.items():
            stamps = tree_stamps(root)
            files = {p: file_digest(root / p) for p, s in stamps.items() if stat.S_ISREG(s[2])}
            require(files == self.files, 'full standard source inventories differ: ' + name)
            require(tree_stamps(root) == stamps, 'standard sources changed while hashing: ' + name)
            self.source_stamps[name] = stamps
        self.source_sha256 = digest(self.files)
        self.namespace = '/rust-interp-std-source/' + self.source_sha256 + '/library'
        # The same ordered list reaches public/native/prepared compilers. Real
        # roots let the metadata decoder keep local source access. Truthful
        # virtual roots cover diagnostics which retain an encoded source name.
        prefixes = [str(root) for root in self.roots.values()]
        prefixes += ['/rustc/' + c + '/library' for c in [public_commit, commit]]
        self.prefixes = list(dict.fromkeys(prefixes))
        self.rustc_flags = ['--remap-path-scope=diagnostics'] + [
            '--remap-path-prefix=' + prefix + '=' + self.namespace for prefix in self.prefixes]
        self._flags = list(self.rustc_flags)
        self.configuration = configuration(self.fixture_root, environment)
        self.config_path = self.fixture_root / '.cargo/config.toml'
        require(self.configuration[str(self.config_path)] is None
                and self.configuration[str(self.config_path.with_name('config'))] is None,
                'diagnostic helper will not replace fixture Cargo configuration')
        parent = self.config_path.parent
        if parent.exists():
            _ordinary(parent)
        else:
            parent.mkdir()
        flags = json.dumps(self.rustc_flags, ensure_ascii=True)
        host = json.dumps(compiler.host)
        self.config_bytes = ('target-applies-to-host = false\n'
            '[unstable]\nhost-config = true\ntarget-applies-to-host = true\n'
            '[host]\nrustflags = ' + flags + '\n'
            '[host.' + host + ']\nrustflags = ' + flags + '\n'
            '[target.' + host + ']\nrustflags = ' + flags + '\n').encode()
        with self.config_path.open('xb') as output:
            output.write(self.config_bytes)
        self.config_stamp = _stamp(self.config_path)
        self.configuration[str(self.config_path)] = {
            'sha256': file_digest(self.config_path), 'stamp': self.config_stamp}
        self.checked_spans = []
        self.recheck()

    def recheck(self):
        require(digest(self.environment) == self.environment_sha256, 'diagnostic base environment changed')
        require(digest(self.compiler.identity) == self.compiler_identity_sha256,
                'diagnostic compiler identity changed')
        require(self.rustc_flags == self._flags, 'diagnostic compiler flags changed')
        require(_stamp(self.public_rustc) == self.compiler_stamps['public']
                and _stamp(self.custom_rustc) == self.compiler_stamps['custom'],
                'diagnostic compiler changed')
        for name, root in self.roots.items():
            require(tree_stamps(root) == self.source_stamps[name], 'diagnostic source tree changed: ' + name)
        for name, expected in self.configuration.items():
            path = Path(name)
            require(not path.is_symlink(), 'diagnostic Cargo configuration became indirect')
            current = {'sha256': file_digest(path), 'stamp': _stamp(path)} if path.exists() else None
            require(current == expected, 'diagnostic Cargo configuration changed: ' + name)

    def validate_diagnostics(self, records, *, require_std):
        """Verify actual nested JSON spans; do not return a transformed view."""
        require(type(require_std) is bool and isinstance(records, list), 'invalid diagnostic validation input')
        self.recheck()
        seen = set()
        checked = []
        def visit(value):
            if isinstance(value, list):
                for child in value:
                    visit(child)
            elif isinstance(value, dict):
                if 'file_name' in value:
                    filename = value['file_name']
                    require(isinstance(filename, str), 'invalid diagnostic filename')
                    prefix = self.namespace + '/'
                    if filename.startswith(prefix):
                        relative = filename[len(prefix):]
                        require(relative in self.files and Path(relative).as_posix() == relative
                                and all(p not in ['.', '..'] for p in relative.split('/')),
                                'unknown mapped standard source')
                        path = self.roots['installed'] / relative
                        require(file_digest(path) == self.files[relative], 'standard span source bytes changed')
                        expected = source_span_text(value, path.read_bytes())
                        require(bool(value.get('text')) and value['text'] == expected,
                                'actual standard diagnostic snippet is missing or differs')
                        seen.add(relative)
                        checked.append({'source': relative, 'sha256': self.files[relative],
                            'file_name': filename, 'byte_start': value['byte_start'], 'byte_end': value['byte_end']})
                    else:
                        require(filename != self.namespace and not any(
                            filename == p or filename.startswith(p + '/') for p in self.prefixes),
                            'standard diagnostic did not use the configured compiler mapping')
                        # A relative standard alias is unsupported; actual fixture
                        # files with std-looking names remain ordinary diagnostics.
                        relative = filename.removeprefix('library/')
                        if not Path(filename).is_absolute() and relative in self.files:
                            local = self.fixture_root / filename
                            require(local.is_file() and local.resolve().is_relative_to(self.fixture_root),
                                    'unmapped relative standard diagnostic alias')
                for child in value.values():
                    visit(child)
        visit(records)
        if require_std:
            require({'core/src/panic.rs', 'std/src/macros.rs'} <= seen,
                    'E0080 lacks complete mapped core and std diagnostic spans')
        self.checked_spans.extend(checked)
        self.recheck()

    def evidence(self):
        self.recheck()
        return copy.deepcopy(dict(schema_version=1, policy=POLICY, compiler_key=self.compiler.key,
            public_compiler=self.public_compiler, source_files=self.files, source_sha256=self.source_sha256,
            roots={name: str(path) for name, path in self.roots.items()}, source_stamps=self.source_stamps,
            compiler_stamps=self.compiler_stamps, environment_sha256=self.environment_sha256,
            prefixes=self.prefixes, namespace=self.namespace, rustc_flags=self.rustc_flags,
            configuration=self.configuration, generated_configuration=str(self.config_path),
            generated_configuration_text=self.config_bytes.decode(), checked_spans=self.checked_spans,
            diagnostic_records_rewritten=False, source_derived_snippets_substituted=False,
            correctness_qualification_only=True, actual_compiler_argv_required=True))


def prepare_standard_diagnostic_mapping(fixture_root, compiler, public_library, prepared_sysroots,
                                        environment, *, public_compiler):
    return StandardDiagnosticMapping(fixture_root, compiler, public_library, prepared_sysroots,
                                     environment, public_compiler=public_compiler)
