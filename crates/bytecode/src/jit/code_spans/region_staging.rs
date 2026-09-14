//! Offline fragment/link equivalence. No executable code is published here.
use super::*;
use serde_json::{Value, json};

fn verify_fragments<'a>(jit: &Jit<'a>, f: &'a Function, full: &CompiledFunction<'a>,
    full_map: &Collector, assertion_base: usize,
) -> (usize, usize) {
    let analysis = jit.analyze_function(f);
    let regions: Vec<_> = full.entries.iter().enumerate()
        .filter_map(|(pc, entry)| entry.map(|e| (pc, e))).collect();
    let mut assertions = 0;
    let mut edges = 0;
    let mut joined = vec![];
    for (index, &(pc, entry)) in regions.iter().enumerate() {
        let byte_end = regions.get(index + 1).map_or(full.words.len() * 4, |(_, e)| e.offset);
        let word_base = entry.offset / 4;
        let word_end = byte_end / 4;
        let mut mapping = Collector { rows: vec![], limit: MAX_SPANS };
        let mut fragment = jit.emit_analyzed_function(f, word_end - word_base,
            assertion_base + assertions, Some(&mut mapping), &analysis, Some(pc))
            .unwrap().expect("published region must stage independently");
        assert_eq!(fragment.words.len(), word_end - word_base);
        assert_eq!(fragment.entries.iter().flatten().count(), 1);
        assert_eq!(fragment.entries[pc].unwrap().offset, 0);
        assert_eq!(fragment.entries[pc].unwrap().end, entry.end);
        assert_eq!(fragment.operations, entry.end - pc);
        assert_eq!(fragment.register_pairs, full.register_pairs);
        assert_eq!(fragment.liveness_declined, full.liveness_declined);
        assert_eq!(fragment.resumes[pc].map(|v| v + word_base), full.resumes[pc]);
        assert_eq!(fragment.internal_entries[pc].map(|v| v + word_base), full.internal_entries[pc]);
        let next = assertions + fragment.assertions.len();
        assert_eq!(fragment.assertions, full.assertions[assertions..next]);
        assertions = next;
        mapping.validate(f, &fragment).unwrap();
        let expected: Vec<_> = full_map.rows.iter().filter(|s| s.region_pc == pc).collect();
        for span in &mut mapping.rows { span.offset += entry.offset; span.end += entry.offset; }
        assert_eq!(serde_json::to_value(&mapping.rows).unwrap(), serde_json::to_value(&expected).unwrap());
        let expected_links: Vec<_> = full.region_links.iter().copied()
            .filter(|&(at, _, _)| (word_base..word_end).contains(&at)).collect();
        assert_eq!(fragment.region_links.iter().map(|&(at, next, fallback)|
            (at + word_base, next, fallback + word_base)).collect::<Vec<_>>(), expected_links);
        // Before resolving any external edge, every fragment target is either
        // its own internal entry or the original local VM fallback tail.
        for &(at, successor, fallback) in &fragment.region_links {
            let local = fragment.internal_entries.get(successor).copied().flatten().unwrap_or(fallback);
            assert!(local < fragment.words.len());
            assert_eq!(fragment.words[at], 0x14000000 |
                branch_displacement(at, local, 26, CodegenLimit::Jump).unwrap());
            let target = full.internal_entries.get(successor).copied().flatten()
                .unwrap_or(word_base + fallback);
            // This only edits a private test Vec. Future executable patching
            // needs its own checked, all-or-nothing publication transaction.
            fragment.words[at] = 0x14000000 |
                branch_displacement(word_base + at, target, 26, CodegenLimit::Jump).unwrap();
            edges += 1;
        }
        assert_eq!(fragment.words, full.words[word_base..word_end], "fragment PC {pc}");
        assert_eq!(joined.len(), word_base);
        joined.extend(fragment.words);
    }
    assert_eq!(joined, full.words);
    assert_eq!(assertions, full.assertions.len());
    assert!(jit.code.is_none());
    assert_eq!(jit.bytes, 0);
    (regions.len(), edges)
}

fn input(code: Vec<Op>) -> Program {
    Program { version: crate::VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 16], statics: vec![], thread_locals: vec![],
        functions: vec![Function { name: "fragments".into(), frame_size: 64, frame_align: 16,
            registers: 8, args: vec![], result: crate::Slot { offset: 0, size: 8 }, code }] }
}

fn check(p: &Program) {
    crate::validate(p).unwrap();
    for profiled in [false, true] { for persistent in [false, true] { for heap in [false, true] {
        let mut jit = Jit::new_resumable(p, profiled, MAX_CODE_BYTES, persistent).unwrap();
        jit.uses_heap = heap;
        let f = &p.functions[0];
        let mut map = Collector { rows: vec![], limit: MAX_SPANS };
        let full = jit.emit_function_inner(f, MAX_CODE_BYTES / 4, 7, Some(&mut map)).unwrap().unwrap();
        map.validate(f, &full).unwrap();
        let (regions, _) = verify_fragments(&jit, f, &full, &map, 7);
        assert!(regions >= 3);
    } } }
}

#[test]
fn independent_regions_preserve_wide_branches_calls_faults_and_assertions() {
    let p = input(vec![Op::Local { dst: 0, offset: 0 }, Op::Load { dst: 1, address: 0, size: 16 },
        Op::Switch { value: 1, cases: vec![(1 << 100, 5), (1 << 100, 3)], otherwise: 3 },
        Op::Assert { value: 1, expected: true, message: "first fragment assertion".into() },
        Op::Jump { target: 5 }, Op::Load { dst: 2, address: 1, size: 8 },
        Op::Binary { dst: 3, overflow: 4, op: Binary::Div, a: 2, b: 1, bits: 64, signed: false },
        Op::Assert { value: 3, expected: false, message: "second fragment assertion".into() },
        Op::Call { function: 0, args: vec![], destination: 0 },
        Op::Switch { value: 3, cases: vec![(0, 5)], otherwise: 10 }, Op::Return]);
    check(&p);
}

#[test]
fn size_split_and_unsupported_successors_keep_exact_fragment_boundaries() {
    let mut code = vec![Op::Imm { dst: 1, value: 0 }; 1027];
    code.extend([Op::ResetThreadLocals, Op::Local { dst: 0, offset: 0 },
        Op::Load { dst: 2, address: 0, size: 8 }, Op::Jump { target: 1024 }, Op::Return]);
    check(&input(code));
}

#[test]
fn invalid_selection_and_fragment_capacity_never_publish_partial_state() {
    let p = input(vec![Op::Local { dst: 0, offset: 0 }, Op::Load { dst: 1, address: 0, size: 8 },
        Op::ResetThreadLocals, Op::Return]);
    let jit = Jit::new_resumable(&p, false, MAX_CODE_BYTES, true).unwrap();
    let f = &p.functions[0];
    let plan = jit.analyze_function(f);
    for pc in [1, f.code.len(), usize::MAX] {
        assert!(matches!(jit.emit_analyzed_function(f, MAX_CODE_BYTES / 4, 0, None, &plan, Some(pc)),
            Err(EmitError::InvalidRelocation(_))));
    }
    assert!(jit.emit_analyzed_function(f, MAX_CODE_BYTES / 4, 0, None, &plan, Some(2)).unwrap().is_none());
    assert!(jit.emit_analyzed_function(f, 0, 0, None, &plan, Some(0)).unwrap().is_none());
    assert!(jit.code.is_none() && jit.assertions.is_empty() && jit.blocks.iter().all(Vec::is_empty));
    assert_eq!((jit.bytes, jit.operations, jit.compiled_functions), (0, 0, 0));
}

fn number(v: &Value, key: &str) -> usize { usize::try_from(v[key].as_u64().unwrap()).unwrap() }

#[test]
#[ignore = "Requires exact saved original artifact, native words and operation map"]
fn reconstruct_saved_regions_independently() {
    let artifact = std::fs::read(std::env::var("STAGING_ARTIFACT").unwrap()).unwrap();
    assert!(artifact.len() <= 128 * 1024 * 1024);
    let p: Program = bincode::deserialize(&artifact).unwrap(); crate::validate(&p).unwrap();
    let map = std::fs::read(std::env::var("STAGING_MAP").unwrap()).unwrap();
    assert!(map.len() <= MAX_OUTPUT_BYTES);
    let map: Value = serde_json::from_slice(&map).unwrap();
    let bytes = std::fs::read(std::env::var("STAGING_CODE").unwrap()).unwrap();
    assert!(bytes.len() <= MAX_CODE_BYTES);
    assert_eq!(number(&map, "schema_version"), 2);
    assert_eq!(map["profiled"], false);
    for flag in ["persistent_registers", "resumable_calls", "complete", "reconstructed_bytes_match"] {
        assert_eq!(map[flag], true);
    }
    assert_eq!(number(&map, "code_bytes"), bytes.len());
    assert_eq!(map["code_sha256"], format!("{:x}", Sha256::digest(&bytes)));
    let mut jit = Jit::new_resumable(&p, false, MAX_CODE_BYTES, true).unwrap();
    jit.enable_scalar_calls();
    let mut scalars = BTreeSet::new();
    for saved in map["functions"].as_array().unwrap() {
        if saved["spans"][0]["kind"] != "scalar_leaf" { continue; }
        let id = number(saved, "function"); assert!(scalars.insert(id));
        let start = number(saved, "offset"); let end = number(saved, "end");
        let words = jit.observe_saved_scalar_entry(id, start, end - start, number(&map, "arena_base"));
        verify_words(&words, &bytes[start..end]).unwrap();
    }
    let (mut cursor, mut assertions, mut regions, mut edges) = (0, 0, 0, 0);
    let mut seen = BTreeSet::new();
    for saved in map["functions"].as_array().unwrap() {
        let id = number(saved, "function"); let f = &p.functions[id];
        assert_eq!(saved["name"], f.name);
        let start = number(saved, "offset"); let end = number(saved, "end");
        assert_eq!(start, cursor); assert!(start < end && end <= bytes.len());
        assert_eq!(number(saved, "assertion_base"), assertions);
        if saved["spans"][0]["kind"] == "scalar_leaf" {
            assert!(scalars.contains(&id)); assert_eq!(number(saved, "assertion_count"), 0);
            cursor = end; continue;
        }
        assert!(seen.insert(id));
        let mut collector = Collector { rows: vec![], limit: MAX_SPANS };
        let full = jit.emit_function_inner(f, (end - start) / 4, assertions, Some(&mut collector)).unwrap().unwrap();
        verify_words(&full.words, &bytes[start..end]).unwrap();
        collector.validate(f, &full).unwrap();
        let (n, e) = verify_fragments(&jit, f, &full, &collector, assertions);
        regions += n; edges += e;
        assert_eq!(full.assertions.len(), number(saved, "assertion_count"));
        for s in &mut collector.rows { s.offset += start; s.end += start; }
        assert_eq!(serde_json::to_value(&collector.rows).unwrap(), saved["spans"]);
        assertions += full.assertions.len(); cursor = end;
    }
    assert_eq!(cursor, bytes.len()); assert!(jit.code.is_none()); assert_eq!(jit.bytes, 0);
    let file = std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("STAGING_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file, &json!({"status":"passed", "ordinary_functions":seen.len(),
        "scalar_bodies":scalars.len(), "regions":regions, "edges":edges, "code_bytes":bytes.len(),
        "code_sha256":map["code_sha256"], "exact_eager_reconstruction":true,
        "exact_reassembled_regions":true, "guest_commands":0, "executable_code_publications":0})).unwrap();
}
