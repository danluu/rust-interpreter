"""Apply the bounded whole-call experiment to an isolated integrated source."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent


def replace(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError('injection anchor changed: ' + old[:100])
    path.write_text(text.replace(old, new))


def inject(source):
    crate = source/'crates/bytecode/src'
    for name in ['register_init.rs', 'register_init_tests.rs', 'inline_graph.rs', 'whole_call_inline_tests.rs']:
        shutil.copy2(HERE/name, crate/name)
    replace(crate/'lib.rs', 'mod registers;', 'mod registers;\nmod register_init;\nmod inline_graph;\n#[cfg(test)]\nmod whole_call_inline_tests;')
    replace(crate/'registers.rs', '    block_needs_initial_zeroes(function, &entry)\n}',
        '    block_needs_initial_zeroes(function, &entry)\n        && !crate::register_init::proves_initialized(function)\n}')
    # Keep the old block proof available as an independent test comparison.
    replace(crate/'register_init_tests.rs', 'crate::registers::needs_initial_zeroes(f) }',
        'crate::registers::needs_initial_zeroes_for_inlining(f) }')
    replace(crate/'register_init_tests.rs', 'assert!(crate::registers::needs_initial_zeroes(&f));',
        'assert!(crate::registers::needs_initial_zeroes_for_inlining(&f));')
    inline = crate/'inline.rs'
    replace(inline, '            Op::Copy { size, .. } => *size <= MAX_COPY_BYTES,',
        '            Op::Call { .. } | Op::CompareBytes { .. } => true,\n            Op::Copy { size, .. } => *size <= MAX_COPY_BYTES,')
    replace(inline, '        Op::Binary {\n            dst,', '''        Op::Call { function, args, destination } => Op::Call {
            function: *function, args: args.iter().map(|reg| r(*reg)).collect(), destination: r(*destination),
        },
        Op::CompareBytes { dst, left, right, size } => Op::CompareBytes {
            dst: r(*dst), left: r(*left), right: r(*right), size: r(*size),
        },
        Op::Binary {
            dst,''')
    replace(inline, '    let eligible: Vec<_> = original',
        '    let nonrecursive = crate::inline_graph::nonrecursive(original);\n    let eligible: Vec<_> = original')
    replace(inline, '        .map(|f| {\n            scalar_leaf(f)', '''        .enumerate()
        .map(|(id, f)| {
            let calls = f.code.iter().filter(|op| matches!(op, Op::Call { .. })).count();
            scalar_leaf(f) && calls <= 1 && (calls == 0 || nonrecursive[id])''')
    text = inline.read_text()
    if text.count('needs_initial_zeroes_for_inlining') != 5:
        raise RuntimeError('unexpected inliner initialization checks')
    inline.write_text(text.replace('needs_initial_zeroes_for_inlining', 'needs_initial_zeroes')
        .replace('selection excludes non-scalar leaf operations', 'selection excludes unsupported body operations'))
    # This old test asserted rejection solely due to the block-only proof. Its
    # replacement preserves the purpose and makes the carried value observable.
    tests = crate/'inline_tests.rs'
    replace(tests, 'fn expansion_cannot_introduce_whole_caller_register_clearing()',
        'fn expansion_with_proven_cross_block_values_avoids_whole_caller_clearing()')
    replace(tests, '''    assert!(!crate::registers::needs_initial_zeroes_for_inlining(&p.functions[0]));
    let (q, report) = inline::transform(&p, options()).unwrap();
    assert_eq!(report["selected_sites"], 0);
    assert_eq!(format!("{p:?}"), format!("{q:?}"));''', '''    p.functions[0].result.size = 8;
    assert!(!crate::registers::needs_initial_zeroes(&p.functions[0]));
    let (q, report) = inline::transform(&p, options()).unwrap();
    assert_eq!(report["selected_sites"], 1);
    assert!(!crate::registers::needs_initial_zeroes(&q.functions[0]));
    for engine in [Engine::Interpreter, Engine::Jit] {
        assert_eq!(execute_with_engine(&p, &[], Limits::default(), engine).unwrap().value, 43);
        assert_eq!(execute_with_engine(&q, &[], Limits::default(), engine).unwrap().value, 43);
    }''')
