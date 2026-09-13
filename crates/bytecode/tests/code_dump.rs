#![cfg(all(target_arch = "aarch64", target_os = "macos"))]
use rust_interp_bytecode::{Engine, Function, Limits, Op, Program, Slot, VERSION,
    execute_profiled, execute_with_engine};
use std::{path::PathBuf, sync::atomic::{AtomicUsize, Ordering}};

fn directory() -> PathBuf {
    static ID: AtomicUsize = AtomicUsize::new(0);
    let root = std::env::temp_dir().join(format!("rust-interp-code-dump-{}-{}-{}",
        std::process::id(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos(),
        ID.fetch_add(1, Ordering::Relaxed)));
    std::fs::create_dir(&root).unwrap();
    root
}
fn fixture() -> Program {
    let function = |name: &str, calls: bool| {
        let mut code = vec![Op::Local { dst: 0, offset: 0 }, Op::Imm { dst: 1, value: 42 },
            Op::Store { address: 0, src: 1, size: 8 }];
        if calls { for _ in 0..2 { code.push(Op::Call { function: 1, args: vec![], destination: 0 }); } }
        code.push(Op::Return);
        Function { name: name.into(), frame_size: 16, frame_align: 16, registers: 2,
            args: vec![], result: Slot { offset: 0, size: 8 }, code }
    };
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0;16], statics: vec![], thread_locals: vec![],
        functions: vec![function("caller", true), function("child", false)] }
}

#[test]
fn dumped_ranges_cover_exact_published_bytes_in_every_native_mode() {
    let root = directory();
    let p = fixture();
    for (native, stubs) in [(false, false), (true, false), (true, true)] {
        for profiled in [false, true] {
            let mut previous = None;
            for repeat in 0..2 {
                let path = root.join(format!("{native}-{stubs}-{profiled}-{repeat}"));
                let limits = Limits { jit_native_calls: native, jit_native_call_stubs: stubs,
                    jit_code_dump: Some(path.clone()), ..Limits::default() };
                let r = if profiled { execute_profiled(&p, &[], limits, Engine::Jit).unwrap().0 }
                    else { execute_with_engine(&p, &[], limits, Engine::Jit).unwrap() };
                assert_eq!((r.value, r.instructions), (42, 14));
                let bytes = std::fs::read(path.join("code.bin")).unwrap();
                assert!(!path.join("operations.json").exists());
                let map: serde_json::Value = serde_json::from_slice(&std::fs::read(path.join("map.json")).unwrap()).unwrap();
                assert_eq!(map["schema_version"], 1);
                assert_eq!(map["pid"], std::process::id());
                assert_eq!(map["profiled"], profiled);
                assert_eq!(map["native_call_stubs"], stubs);
                assert_eq!(map["code_bytes"], bytes.len());
                assert_eq!(bytes.len(), r.jit_bytes);
                assert_ne!(map["arena_base"], 0);
                let mut end = 0;
                let mut kinds = std::collections::BTreeSet::new();
                for row in map["ranges"].as_array().unwrap() {
                    assert_eq!(row["offset"], end);
                    let next = row["end"].as_u64().unwrap() as usize;
                    assert!(next > end && next % 4 == 0);
                    end = next;
                    kinds.insert(row["kind"].as_str().unwrap());
                    let f = &p.functions[row["function"].as_u64().unwrap() as usize];
                    assert_eq!(row["name"], f.name);
                    if let Some(pc) = row["pc"].as_u64() {
                        assert!(pc < row["pc_end"].as_u64().unwrap());
                        assert!(row["pc_end"].as_u64().unwrap() <= f.code.len() as u64);
                        if row["kind"] == "call_stub" { assert!(matches!(f.code[pc as usize], Op::Call { .. })); }
                    } else { assert_eq!(row["kind"], "native_tree"); }
                }
                assert_eq!(end, bytes.len());
                assert!(kinds.contains("ordinary_region"));
                assert_eq!(kinds.contains("call_stub"), stubs);
                assert_eq!(kinds.contains("native_tree"), native);
                if let Some(old) = previous { assert_eq!(bytes, old); }
                previous = Some(bytes);
            }
        }
    }
    std::fs::remove_dir_all(root).unwrap();
}

#[test]
fn dumps_handle_empty_code_and_preserve_existing_destinations() {
    let root = directory();
    let p = fixture();
    let path = root.join("empty");
    let config = || Limits { jit_code_bytes: 0, jit_code_dump: Some(path.clone()), ..Limits::default() };
    let r = execute_with_engine(&p, &[], config(), Engine::Jit).unwrap();
    assert_eq!(r.value, 42);
    assert!(std::fs::read(path.join("code.bin")).unwrap().is_empty());
    let saved = std::fs::read(path.join("map.json")).unwrap();
    let map: serde_json::Value = serde_json::from_slice(&saved).unwrap();
    assert_eq!(map["arena_base"], 0);
    assert_eq!(map["ranges"].as_array().unwrap().len(), 0);
    assert!(execute_with_engine(&p, &[], config(), Engine::Jit).unwrap_err().starts_with("write native code dump:"));
    assert_eq!(std::fs::read(path.join("map.json")).unwrap(), saved);
    assert_eq!(execute_with_engine(&p, &[], config(), Engine::Interpreter).unwrap_err(),
        "native code dumps require the JIT engine");
    let failed = root.join("failed-execution");
    let limits = Limits { instructions: 0, jit_code_dump: Some(failed.clone()), ..Limits::default() };
    assert!(execute_with_engine(&p, &[], limits, Engine::Jit).is_err());
    assert!(!failed.exists());
    std::fs::remove_dir_all(root).unwrap();
}

#[test]
fn operation_maps_preserve_execution_and_original_dump_bytes() {
    let root = directory();
    let p = fixture();
    for resumable in [false, true] { for persistent in [false, true] { for profiled in [false, true] {
        let mut previous = None;
        for enabled in [false, true] {
            let path = root.join(format!("{resumable}-{persistent}-{profiled}-{enabled}"));
            let limits = Limits { jit_resumable_calls: resumable, jit_persistent_registers: persistent,
                jit_code_dump: Some(path.clone()), jit_operation_map: enabled, ..Limits::default() };
            let (r, profile) = if profiled {
                let (r, p) = execute_profiled(&p, &[], limits, Engine::Jit).unwrap();
                (r, Some(serde_json::to_value(p).unwrap()))
            } else { (execute_with_engine(&p, &[], limits, Engine::Jit).unwrap(), None) };
            assert_eq!((r.value, r.instructions), (42, 14));
            let bytes = std::fs::read(path.join("code.bin")).unwrap();
            let old_map: serde_json::Value = serde_json::from_slice(&std::fs::read(path.join("map.json")).unwrap()).unwrap();
            if enabled {
                let map: serde_json::Value = serde_json::from_slice(&std::fs::read(path.join("operations.json")).unwrap()).unwrap();
                assert_eq!(map["schema_version"], 1);
                assert_eq!(map["complete"], true);
                assert_eq!(map["reconstructed_bytes_match"], true);
                for key in ["arena_base", "pid", "code_bytes", "profiled", "persistent_registers", "resumable_calls"] {
                    assert_eq!(map[key], old_map[key], "{key}");
                }
                let mut end = 0;
                let mut count = 0;
                for function in map["functions"].as_array().unwrap() {
                    assert_eq!(function["offset"], end);
                    let id = function["function"].as_u64().unwrap() as usize;
                    assert_eq!(function["name"], p.functions[id].name);
                    for span in function["spans"].as_array().unwrap() {
                        assert_eq!(span["offset"], end);
                        end = span["end"].as_u64().unwrap() as usize;
                        count += 1;
                        if let Some(pc) = span["pc"].as_u64() { assert!((pc as usize) < p.functions[id].code.len()); }
                    }
                    assert_eq!(function["end"], end);
                }
                assert_eq!(end, bytes.len()); assert_eq!(map["spans"], count);
            } else { assert!(!path.join("operations.json").exists()); }
            let actual = (bytes, r.value, r.instructions, r.peak_memory, profile);
            if let Some(old) = previous { assert_eq!(actual, old); }
            previous = Some(actual);
        }
    } } }
    std::fs::remove_dir_all(root).unwrap();
}

#[test]
fn operation_maps_cover_real_backedges_and_never_publish_after_budget_failure() {
    use rust_interp_bytecode::Binary;
    let root = directory();
    let mut p = fixture(); p.functions.truncate(1);
    let f = &mut p.functions[0]; f.registers = 5;
    f.args = vec![Slot { offset: 0, size: 8 }];
    f.code = vec![Op::Local { dst: 0, offset: 0 }, Op::Load { dst: 1, address: 0, size: 8 },
        Op::Imm { dst: 2, value: 1 },
        Op::Binary { dst: 1, overflow: 3, op: Binary::Sub, a: 1, b: 2, bits: 64, signed: false },
        Op::Imm { dst: 4, value: 0 }, Op::Switch { value: 1, cases: vec![(0, 6)], otherwise: 3 },
        Op::Store { address: 0, src: 1, size: 8 }, Op::Return];
    for resumable in [false, true] { for persistent in [false, true] {
        for budget in [0, 1, 2, 3, 4, 100, 304, 305, 306] {
            let path = root.join(format!("{resumable}-{persistent}-{budget}"));
            let reference = execute_with_engine(&p, &[100], Limits { instructions: budget, ..Limits::default() }, Engine::Interpreter);
            let observed = execute_with_engine(&p, &[100], Limits { instructions: budget,
                jit_resumable_calls: resumable, jit_persistent_registers: persistent,
                jit_code_dump: Some(path.clone()), jit_operation_map: true, ..Limits::default() }, Engine::Jit);
            match (reference, observed) {
                (Ok(a), Ok(b)) => {
                    assert_eq!((a.value, a.instructions, a.peak_memory), (b.value, b.instructions, b.peak_memory));
                    assert_eq!(b.value, 0);
                    let map: serde_json::Value = serde_json::from_slice(&std::fs::read(path.join("operations.json")).unwrap()).unwrap();
                    assert_eq!(map["complete"], true);
                    assert!(map["functions"][0]["spans"].as_array().unwrap().iter()
                        .any(|s| s["kind"] == "operation" && s["pc"] == 5));
                },
                (Err(a), Err(b)) => { assert_eq!(a, b); assert!(!path.exists()); },
                _ => panic!("budget outcome differs"),
            }
        }
    } }
    std::fs::remove_dir_all(root).unwrap();
}

#[test]
fn operation_map_options_reject_unsupported_modes_and_preserve_exclusive_paths() {
    let root = directory(); let p = fixture();
    for (engine, dump, native, stubs) in [(Engine::Jit, false, false, false),
        (Engine::Interpreter, false, false, false), (Engine::Jit, true, true, false),
        (Engine::Jit, true, true, true)] {
        let path = root.join(format!("{engine:?}-{dump}-{native}-{stubs}"));
        let error = execute_with_engine(&p, &[], Limits { jit_operation_map: true,
            jit_code_dump: dump.then(|| path.clone()), jit_native_calls: native,
            jit_native_call_stubs: stubs, ..Limits::default() }, engine).unwrap_err();
        assert_eq!(error, "operation maps require a code dump and ordinary or resumable JIT");
        assert!(!path.exists());
    }
    let path = root.join("empty");
    let config = || Limits { jit_operation_map: true, jit_code_dump: Some(path.clone()),
        jit_code_bytes: 0, ..Limits::default() };
    execute_with_engine(&p, &[], config(), Engine::Jit).unwrap();
    let saved = std::fs::read(path.join("operations.json")).unwrap();
    let map: serde_json::Value = serde_json::from_slice(&saved).unwrap();
    assert_eq!(map["code_bytes"], 0); assert_eq!(map["spans"], 0);
    assert!(execute_with_engine(&p, &[], config(), Engine::Jit).unwrap_err().starts_with("write native code dump:"));
    assert_eq!(std::fs::read(path.join("operations.json")).unwrap(), saved);
    std::fs::remove_dir_all(root).unwrap();
}
