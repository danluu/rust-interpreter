"""Production-body edit experiments. Adapters only expose integer test inputs.

These are mutations for compiler measurement, not proposed upstream bug fixes.
Full source and private diagnostics remain in the owned .work snapshots.
"""

CASES = {
    'pgrust-hash': dict(project='pgrust', package='hashfn', crate='hashfn',
        directory='crates/common/hashfn', file='src/lib.rs',
        old='h = h.wrapping_mul(0x85eb_ca6b);',
        replacements=[f'h = h.wrapping_mul({0x85ebca6b + 2*i});' for i in range(1,6)],
        expression='murmurhash32(seed.wrapping_add(i) as u32) as u64',
        profile='debug = "line-tables-only"\nsplit-debuginfo = "unpacked"\nincremental = false\n'),
    'pgrust-numeric': dict(project='pgrust',package='adt_numeric',crate='adt_numeric',
        directory='crates/backend/utils/adt/numeric',file='src/ops.rs', module='ops',
        old='((typmod - VARHDRSZ as i32) & 0x7ff) ^ 1024',
        replacements=[f'((typmod - VARHDRSZ as i32) & 0x7ff) ^ {1024+i}' for i in range(1,6)],
        expression='numeric_typmod_scale((seed.wrapping_add(i) % 65536 + 4) as i32) as u64',
        profile='debug = "line-tables-only"\nsplit-debuginfo = "unpacked"\nincremental = false\n'),
    'fre': dict(project='fre',package='fre',crate='fre',
        directory='crates/fre',file='src/guarded_ascii_word.rs',module='guarded_ascii_word',
        old="byte == b'_' || byte.is_ascii_alphanumeric()",
        replacements=[f'byte == {b} || byte.is_ascii_alphanumeric()' for b in [45,46,47,58,59]],
        expression='is_ascii_word(seed.wrapping_add(i) as u8) as u64',profile=''),
    'ruff': dict(project='ruff',package='ruff_linter',crate='ruff_linter',
        directory='crates/ruff_linter',file='src/noqa.rs',module='noqa',
        old="[b'n' | b'N', b'o' | b'O', b'q' | b'Q', b'a' | b'A', ..]",
        replacements=[f"[b'n' | b'N', b'o' | b'O', b'q' | b'Q', b'a' | {b}, ..]" for b in [66,67,68,69,70]],
        expression='is_noqa_uncased(match seed.wrapping_add(i) % 8 { 0 => "noqA", 1 => "noqB", 2 => "noqC", 3 => "noqD", 4 => "noqE", 5 => "noqF", 6 => "noqa", _ => "bad" }) as u64',
        profile='opt-level = 1\ndebug = "line-tables-only"\nlto = "off"\n'),
    'nushell': dict(project='nushell',package='nu-parser',crate='nu_parser',
        directory='crates/nu-parser',file='src/lex.rs',module='lex',
        old="b'|' | b'{' | b'(' | b'[' | b',' | b':' | b'+' | b'-' | b'*' | b'/' | b'=' | b'.'",
        replacements=["b'|' | b'{' | b'(' | b'[' | b',' | b':' | b'+' | b'-' | b'*' | b'/' | b'=' | " + str(b) for b in [59,60,62,63,64]],
        expression='continues_onto_next_line(seed.wrapping_add(i) as u8) as u64',profile=''),
    'rg-aot': dict(project='rg-aot',package='rg-aot',crate='rg_aot',
        directory='.',file='src/lib.rs',old='u64::try_from(duration.as_nanos()).unwrap_or(u64::MAX)',
        replacements=[f'u64::try_from(duration.as_nanos()).unwrap_or(u64::MAX - {i})' for i in range(1,6)],
        expression='duration_ns(std::time::Duration::new(seed.wrapping_add(i), 123))',
        profile='',seed=2**40),
}


def adapter(case):
    # Each invocation actually traverses the edited routine with varying input.
    # Position-weighted accumulation makes changed classifications observable.
    return '''
#[doc(hidden)]
pub fn rust_interp_entry(seed: u64, count: u64) -> u64 {
    let mut output = 0u64;
    let mut i = 0u64;
    while i < count {
        let value = EXPRESSION;
        output = output.wrapping_add(value.wrapping_mul(i.wrapping_add(1)));
        i += 1;
    }
    output
}
'''.replace('EXPRESSION',case['expression'])
