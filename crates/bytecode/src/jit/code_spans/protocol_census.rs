//! Test-only refinement of already captured native transitions. Never publish code.
use super::*;
use serde_json::{Value, json};

fn number(value: &Value, key: &str) -> usize {
    usize::try_from(value[key].as_u64().unwrap()).unwrap()
}

pub(in crate::jit) fn validate_partition(a: &Assembler<'_>) -> Result<(), &'static str> {
    let mut cursor = 0;
    for span in &a.protocol_spans {
        if span.offset != cursor || span.end <= span.offset || span.end > a.words.len() * 4
            || span.offset % 4 != 0 || span.end % 4 != 0 {
            return Err("invalid protocol partition");
        }
        if span.kind.starts_with("argument_") != span.argument.is_some() {
            return Err("invalid protocol argument identity");
        }
        cursor = span.end;
    }
    if cursor != a.words.len() * 4 { return Err("incomplete protocol partition"); }
    Ok(())
}

#[test]
fn protocol_partitions_cover_copy_sizes_profiles_and_register_clearing() {
    for size in [0, 1, 8, 16, 17, 128, 256, 513] {
        for profiled in [false, true] {
            for zeroes in [false, true] {
                let extent = (size.max(1) + 15) / 16 * 16;
                let f = Function { name: "protocol partition fixture".into(), frame_size: extent,
                    frame_align: 16, registers: 8, args: vec![],
                    result: crate::Slot { offset: 0, size }, code: vec![Op::Return] };
                let mut caller = f.clone();
                caller.registers = if zeroes { 4096 } else { 8 };
                caller.code = vec![Op::Local { dst: 0, offset: 0 }, Op::Local { dst: 1, offset: 0 },
                    Op::Call { function: 1, args: vec![0], destination: 1 }, Op::Return];
                let mut callee = f;
                callee.args.push(crate::Slot { offset: 0, size });
                let program = Program { version: crate::VERSION, target: "aarch64-apple-darwin".into(),
                    entry: 0, functions: vec![caller, callee], data: vec![], statics: vec![], thread_locals: vec![] };
                crate::validate(&program).unwrap();
                let mut jit = Jit::new_resumable(&program, profiled, MAX_CODE_BYTES, true).unwrap();
                jit.resumable.as_mut().unwrap().zeroes[1] = zeroes;
                for (fid, pc) in [(0, 2), (1, 0)] {
                    let f = &program.functions[fid];
                    let reads = read_registers(f);
                    let allocation = values::analyze(f);
                    let slots = call_slots::collect(f, &program);
                    let (a, _, _) = jit.emit_resumable_transition(f, pc, &reads,
                        allocation.as_ref(), slots.get(&pc).map(Vec::as_slice), 0).unwrap();
                    validate_partition(&a).unwrap();
                    let kinds: BTreeSet<_> = a.protocol_spans.iter().map(|s| s.kind).collect();
                    assert!(kinds.contains("entry") && kinds.contains("entry_budget")
                        && kinds.contains("charge_budget") && kinds.contains("admission_fallback"));
                    assert_eq!(kinds.contains("charge_profile"), profiled);
                    assert_eq!(kinds.contains("profile_switch"), profiled);
                    if fid == 0 {
                        assert!(kinds.contains("call_publish_frame") && kinds.contains("argument_source"));
                        assert_eq!(kinds.contains("call_register_clear"), zeroes);
                        assert!(a.protocol_spans.iter().filter_map(|s| s.argument).all(|i| i == 0));
                    } else {
                        assert!(kinds.contains("return_restore_frame") && kinds.contains("return_dispatch")
                            && kinds.contains("return_dispatch_fallback"));
                        assert!(a.protocol_spans.iter().all(|s| s.argument.is_none()));
                    }
                    assert!(jit.code.is_none());
                    assert_eq!(jit.bytes, 0);
                }
            }
        }
    }
}

#[test]
fn protocol_partition_rejects_gaps_overlaps_missing_tail_and_argument_aliases() {
    use resumable::ProtocolSpan;
    let mut a = Assembler { words: vec![0; 3], ..Assembler::default() };
    a.protocol_spans = vec![ProtocolSpan { offset: 0, end: 4, kind: "entry", argument: None },
        ProtocolSpan { offset: 4, end: 12, kind: "argument_copy", argument: Some(0) }];
    validate_partition(&a).unwrap();
    for offset in [0, 3, 8] {
        a.protocol_spans[1].offset = offset;
        assert!(validate_partition(&a).is_err());
    }
    a.protocol_spans[1].offset = 4;
    for end in [4, 8, 13, 16] {
        a.protocol_spans[1].end = end;
        assert!(validate_partition(&a).is_err());
    }
    a.protocol_spans[1].end = 12;
    a.protocol_spans[1].argument = None;
    assert!(validate_partition(&a).is_err());
    a.protocol_spans[1].argument = Some(0);
    a.protocol_spans[0].argument = Some(0);
    assert!(validate_partition(&a).is_err());
}

#[test]
#[ignore = "Requires exact saved unprofiled machine words and operation map"]
fn observe_saved_protocol() {
    let artifact = std::fs::read(std::env::var("PROTOCOL_ARTIFACT").unwrap()).unwrap();
    assert!(artifact.len() <= 128 * 1024 * 1024);
    let program: Program = bincode::deserialize(&artifact).unwrap();
    crate::validate(&program).unwrap();
    let mapping = std::fs::read(std::env::var("PROTOCOL_MAP").unwrap()).unwrap();
    assert!(mapping.len() <= MAX_OUTPUT_BYTES);
    let mapping: Value = serde_json::from_slice(&mapping).unwrap();
    let bytes = std::fs::read(std::env::var("PROTOCOL_CODE").unwrap()).unwrap();
    assert!(bytes.len() <= MAX_CODE_BYTES);
    assert_eq!(number(&mapping, "schema_version"), 1);
    assert_eq!(mapping["profiled"], false);
    for flag in ["persistent_registers", "resumable_calls", "complete", "reconstructed_bytes_match"] {
        assert_eq!(mapping[flag], true, "{flag}");
    }
    assert_eq!(number(&mapping, "code_bytes"), bytes.len());
    assert_eq!(mapping["code_sha256"], format!("{:x}", Sha256::digest(&bytes)));
    let jit = Jit::new_resumable(&program, false, MAX_CODE_BYTES, true).unwrap();
    let (mut cursor, mut assertions, mut count) = (0, 0, 0);
    let mut seen = BTreeSet::new();
    let mut output = vec![];
    for function in mapping["functions"].as_array().unwrap() {
        let id = number(function, "function");
        assert!(seen.insert(id));
        let f = &program.functions[id];
        assert_eq!(function["name"], f.name);
        let offset = number(function, "offset");
        let end = number(function, "end");
        assert_eq!(offset, cursor);
        assert!(offset < end && end <= bytes.len());
        assert_eq!(number(function, "assertion_base"), assertions);
        let mut collector = Collector { rows: vec![], limit: MAX_SPANS };
        let staged = jit.emit_function_inner(f, (end-offset)/4, assertions, Some(&mut collector))
            .unwrap().expect("saved complete function must reconstruct");
        verify_words(&staged.words, &bytes[offset..end]).unwrap();
        collector.validate(f, &staged).unwrap();
        assert_eq!(staged.assertions.len(), number(function, "assertion_count"));
        for row in &mut collector.rows { row.offset += offset; row.end += offset; }
        assert_eq!(serde_json::to_value(&collector.rows).unwrap(), function["spans"]);
        let reads = read_registers(f);
        let allocation = values::analyze(f);
        let slots = call_slots::collect(f, &program);
        for row in collector.rows.iter().filter(|row| row.kind == Kind::Transition) {
            let pc = row.pc.unwrap();
            let (a, resume, _) = jit.emit_resumable_transition(f, pc, &reads,
                allocation.as_ref(), slots.get(&pc).map(Vec::as_slice), 0).unwrap();
            verify_words(&a.words, &bytes[row.offset..row.end]).unwrap();
            assert_eq!(staged.resumes[pc], Some((row.offset-offset)/4 + resume));
            validate_partition(&a).unwrap();
            let kind = match f.code[pc] { Op::Call { .. } => "Call", Op::Return => "Return", _ => unreachable!() };
            for span in a.protocol_spans {
                output.push(json!({"function":id,"pc":pc,"operation":kind,
                    "offset":row.offset+span.offset,"end":row.offset+span.end,
                    "kind":span.kind,"argument":span.argument}));
                assert!(output.len() <= MAX_SPANS);
            }
            count += 1;
        }
        assertions += staged.assertions.len(); cursor = end;
    }
    assert_eq!(cursor, bytes.len());
    assert!(jit.code.is_none());
    assert_eq!(jit.bytes, 0);
    let file = std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("PROTOCOL_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file, &json!({"status":"passed","code_bytes":bytes.len(),
        "code_sha256":mapping["code_sha256"],"functions":seen.len(),"transitions":count,
        "exact_full_function_reconstruction":true,"exact_transition_reconstruction":true,
        "complete_partition":true,"guest_commands":0,"executable_code_publications":0,
        "spans":output})).unwrap();
}
