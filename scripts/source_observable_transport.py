"""Exact fixture bytes and integer-result transport; no compiler or filesystem work."""
import copy
import hashlib

POLICY = 'std-source-observables-v2'
TRANSPORT = 'native-rows-exact-guest-bitmask-v1'
PHASES = ('unmapped', 'std-only', 'application-map', 'restored')
NEGATIVES = ('wrong-file', 'wrong-line')
EXPORTED_PHASES = (*PHASES[:3], *NEGATIVES, PHASES[3])
LABELS = ('main', 'std-looking')
FIELDS = ('file', 'span_file', 'local_file', 'line', 'column')
FULL_MASK = (1 << (len(LABELS) * len(FIELDS))) - 1
COMMANDS = 61


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def native_phase(phase):
    require(phase in EXPORTED_PHASES, 'unknown observable transport phase')
    return 'application-map' if phase in NEGATIVES else phase


def expected_mask(phase):
    native_phase(phase)
    return FULL_MASK ^ (1 if phase == 'wrong-file' else 1 << 8 if phase == 'wrong-line' else 0)


def expectation(mode, phase, command_index, stdout, values):
    require(mode in ['off', 'on'] and type(command_index) is int and command_index >= 0,
            'invalid native expectation association')
    table = copy.deepcopy(values)
    require(isinstance(table, dict) and set(table) == set(LABELS), 'expectation requires both native source locations')
    for value in table.values():
        require(isinstance(value, dict) and set(value) == set(FIELDS) | {'relative'}
                and all(isinstance(value[f], str) and value[f] for f in FIELDS[:3])
                and all(type(value[f]) is int and 0 < value[f] <= 0xffffffff for f in FIELDS[3:]),
                'invalid native expectation fields')
    if phase == 'wrong-file':
        # A guaranteed different, valid UTF-8 first byte; no digest comparison.
        table['main']['file'] = ('?' if table['main']['file'][0] != '?' else '!') + table['main']['file'][1:]
    elif phase == 'wrong-line':
        require(table['std-looking']['line'] < 0xffffffff, 'negative coordinate would overflow')
        table['std-looking']['line'] += 1
    return dict(schema_version=1, policy=TRANSPORT, mode=mode, phase=phase,
        native_phase=native_phase(phase), native_command_index=command_index,
        native_stdout_sha256=hashlib.sha256(stdout.encode()).hexdigest(), labels=list(LABELS),
        fields=list(FIELDS), values=table, expected_mask=expected_mask(phase))


def expectation_source(record):
    rows = []
    for label in LABELS:
        value = record['values'][label]
        fields = ['&[' + ','.join(str(b) for b in value[f].encode('utf-8')) + ']' for f in FIELDS[:3]]
        fields += [str(value[f]) + 'u32' for f in FIELDS[3:]]
        rows.append('    (' + ', '.join(fields) + '),')
    return ('// ' + TRANSPORT + '\n'
        'pub const EXPECTED: [(&[u8], &[u8], &[u8], u32, u32); 2] = [\n' +
        '\n'.join(rows) + '\n];\n').encode()


def validate_transport(record, source, values, command_index, native_stdout, mode, phase, stdout):
    correct = expectation(mode, phase, command_index, native_stdout, values)
    require(record == correct, 'guest expectation differs from the exact native values/control')
    require(source == expectation_source(correct), 'generated guest expectation source differs')
    require(stdout == str(correct['expected_mask']) + '\n',
            'actual guest comparison mask differs from the exact field control')
    return correct


def validate_fixture(payloads):
    for name, text in fixture_sources().items():
        require(payloads.get('application/' + name) == text.encode(),
                'source observable fixture or final restoration differs: ' + name)


def fixture_sources():
    # The archived validator checks these exact bytes, including the comparison
    # implementation. A constant or fabricated successful entry is not a valid
    # fixture under this transport policy.
    return {
        'Cargo.toml': '[package]\nname="std-source-observables"\nversion="0.0.0"\nedition="2024"\nautobins=false\n'
            '[lib]\npath="src/main.rs"\n[workspace]\nmembers=["macros"]\nresolver="2"\n'
            '[dependencies]\npath-probe={path="macros"}\n'
            '[profile.dev]\ncodegen-units=2\nincremental=true\n[profile.dev.build-override]\ncodegen-units=2\n',
        'macros/Cargo.toml': '[package]\nname="path-probe"\nversion="0.0.0"\nedition="2024"\n[lib]\nproc-macro=true\n',
        'macros/src/lib.rs': 'extern crate proc_macro;\n'
            '#[proc_macro] pub fn observe(input: proc_macro::TokenStream) -> proc_macro::TokenStream {\n'
            ' let span = input.into_iter().next().expect("marker token").span();\n'
            ' let local = span.local_file().expect("actual source path");\n'
            ' format!("({:?}, {:?}, {}u32, {}u32)", span.file(), local.to_str().unwrap(), '
            'span.line(), span.column()).parse().unwrap()\n}\n',
        'src/expected.rs': '// Original unused native expectation; restored after every exported history.\n'
            'pub const EXPECTED: [(&[u8], &[u8], &[u8], u32, u32); 2] = [(b"", b"", b"", 0, 0); 2];\n',
        'src/main.rs': '// phase:000000000000000\n'
            '#[path="core/src/panic.rs"] mod std_looking;\nmod expected;\n'
            'pub type Observed = (&\'static str, &\'static str, &\'static str, u32, u32);\n'
            'pub fn observe_main() -> Observed { let span = path_probe::observe!(marker); (file!(), span.0, span.1, span.2, span.3) }\n'
            'fn equal_bytes(value: &str, expected: &[u8]) -> bool {\n'
            ' let actual = value.as_bytes(); if actual.len() != expected.len() { return false; }\n'
            ' let mut i = 0; while i < actual.len() { if actual[i] != expected[i] { return false; } i += 1; } true\n}\n'
            'fn compare(value: Observed, expected: (&[u8], &[u8], &[u8], u32, u32)) -> u32 {\n'
            ' (equal_bytes(value.0, expected.0) as u32) | ((equal_bytes(value.1, expected.1) as u32) << 1) |\n'
            ' ((equal_bytes(value.2, expected.2) as u32) << 2) | (((value.3 == expected.3) as u32) << 3) |\n'
            ' (((value.4 == expected.4) as u32) << 4)\n}\n'
            'pub fn entry() -> u32 { compare(observe_main(), expected::EXPECTED[0]) | (compare(std_looking::observe(), expected::EXPECTED[1]) << 5) }\n'
            'fn show(label: &str, value: Observed) { println!("{}|{}|{}|{}|{}|{}", label, value.0, value.1, value.2, value.3, value.4); }\n'
            'fn main() { show("main", observe_main()); show("std-looking", std_looking::observe()); }\n',
        'src/core/src/panic.rs': 'pub fn observe() -> crate::Observed { let span = path_probe::observe!(marker); (file!(), span.0, span.1, span.2, span.3) }\n',
    }
