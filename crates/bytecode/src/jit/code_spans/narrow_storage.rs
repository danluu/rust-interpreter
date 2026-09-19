//! Diagnostic bounds for a possible implicit-zero register representation.
use super::*;
use serde_json::{Value, json};

#[derive(Debug, PartialEq, Eq, Serialize)]
struct Work {
    interpreted_instructions: u64,
    interpreted_instructions_with_narrow_reads: u64,
    narrow_read_operands: u64,
    unique_narrow_read_operands: u64,
}

fn work(f: &Function, profile: &Value, narrow: &[bool]) -> Result<Work, &'static str> {
    if narrow.len() != f.registers || profile["name"] != f.name
        || profile["frame_size"] != f.frame_size || profile["registers"] != f.registers {
        return Err("typed profile identity mismatch");
    }
    let ops = profile["operations"].as_array().ok_or("missing operations")?;
    if ops.len() != f.code.len() || ops.iter().zip(&f.code).any(|(a,b)| *a != format!("{b:?}")) {
        return Err("typed profile operation mismatch");
    }
    for key in ["interpreted", "jit_blocks", "jit_block_ends", "jit_tree_blocks",
        "jit_tree_block_ends", "jit_scalar_hits"] {
        let values = profile[key].as_array().ok_or("missing counter vector")?;
        if values.len() != f.code.len() || values.iter().any(|v| v.as_u64().is_none()) {
            return Err("invalid counter vector");
        }
    }
    let mut result = Work { interpreted_instructions: 0,
        interpreted_instructions_with_narrow_reads: 0, narrow_read_operands: 0,
        unique_narrow_read_operands: 0 };
    for (pc, op) in f.code.iter().enumerate() {
        let count = profile["interpreted"][pc].as_u64().unwrap();
        let mut reads = 0u64;
        let mut unique = BTreeSet::new();
        let mut valid = true;
        crate::registers::visit_registers(op, |r| {
            if let Some(&known) = narrow.get(r as usize) {
                if known { reads += 1; unique.insert(r); }
            } else { valid = false; }
        }, |_| {});
        if !valid { return Err("invalid register use"); }
        let add = |out: &mut u64, each: u64| -> Result<(), &'static str> {
            *out = each.checked_mul(count).and_then(|n| out.checked_add(n)).ok_or("counter overflow")?;
            Ok(())
        };
        add(&mut result.interpreted_instructions, 1)?;
        add(&mut result.narrow_read_operands, reads)?;
        add(&mut result.unique_narrow_read_operands, unique.len() as u64)?;
        if reads != 0 { add(&mut result.interpreted_instructions_with_narrow_reads, 1)?; }
    }
    Ok(result)
}

fn fixture() -> (Function, Value) {
    let f = Function { name: "narrow storage work".into(), frame_size: 16, frame_align: 16,
        registers: 4, args: vec![], result: crate::Slot { offset: 0, size: 0 },
        code: vec![Op::Imm { dst: 0, value: 7 }, Op::Local { dst: 1, offset: 0 },
            Op::Store { address: 1, src: 0, size: 8 },
            Op::Binary { dst: 2, overflow: 3, op: crate::Binary::Add, a: 0, b: 0, bits: 64, signed: false },
            Op::Assert { value: 2, expected: true, message: "full".into() }, Op::Return] };
    let program = Program { version: crate::VERSION, target: "aarch64-apple-darwin".into(),
        entry: 0, functions: vec![f.clone()], data: vec![], statics: vec![], thread_locals: vec![] };
    crate::validate(&program).unwrap();
    let mut p = serde_json::to_value(crate::ExecutionProfile::new(&program)).unwrap()["functions"][0].clone();
    p["interpreted"] = json!([0,0,2,3,5,0]);
    (f, p)
}

#[test]
fn narrow_storage_work_separates_scalar_hits_and_duplicate_read_roles() {
    let (f, mut p) = fixture();
    let proof = register_widths::prove(&f).unwrap();
    assert_eq!(proof, [true; 4]);
    let expected = Work { interpreted_instructions: 10,
        interpreted_instructions_with_narrow_reads: 10, narrow_read_operands: 15,
        unique_narrow_read_operands: 12 };
    assert_eq!(work(&f, &p, &proof).unwrap(), expected);
    p["jit_scalar_hits"] = json!(vec![100; 6]);
    assert_eq!(work(&f, &p, &proof).unwrap(), expected);
    assert_eq!(work(&f, &p, &[false;4]).unwrap().narrow_read_operands, 0);
}

#[test]
fn narrow_storage_work_rejects_wrong_shapes_operands_and_counters() {
    let (f, p) = fixture();
    for (key, value) in [("name", json!("wrong")), ("registers", json!(5)),
        ("frame_size", json!(0)), ("operations", json!([])), ("interpreted", json!([0])),
        ("jit_scalar_hits", json!(vec![true;6]))] {
        let mut bad = p.clone(); bad[key] = value;
        assert!(work(&f,&bad,&[true;4]).is_err());
    }
    for value in [json!(-1), json!(0.5), json!(true), Value::Null] {
        let mut bad = p.clone(); bad["interpreted"][0] = value;
        assert!(work(&f,&bad,&[true;4]).is_err());
    }
    assert!(work(&f,&p,&[true;3]).is_err());
}

#[test]
fn narrow_storage_work_rejects_arithmetic_overflow_and_opcode_drift() {
    let (f, mut p) = fixture(); p["interpreted"][2] = json!(u64::MAX);
    assert!(work(&f,&p,&[true;4]).is_err());
    let (f, mut p) = fixture(); p["operations"][0] = json!("Imm { dst: 0, value: 8 }");
    assert!(work(&f,&p,&[true;4]).is_err());
}

#[test]
#[ignore = "Requires exact retained artifact and current-host profiles; publishes JSON only"]
fn observe_saved_narrow_storage() {
    let bytes = std::fs::read(std::env::var("NARROW_STORAGE_ARTIFACT").unwrap()).unwrap();
    assert!(bytes.len() <= 128*1024*1024);
    let program: Program = bincode::deserialize(&bytes).unwrap();
    crate::validate(&program).unwrap(); assert!(program.functions.len() <= 100_000);
    let proofs: Vec<_> = program.functions.iter().map(register_widths::prove).collect();
    let functions: Vec<_> = program.functions.iter().zip(&proofs).enumerate().map(|(id,(f,p))|
        json!({"function": id,"name": f.name,"registers": f.registers,"declined": p.is_none(),
            "narrow": p.as_ref().map(|v| v.iter().enumerate().filter_map(|(r,&n)| n.then_some(r)).collect::<Vec<_>>())})).collect();
    let paths: Vec<String> = serde_json::from_str(&std::env::var("NARROW_STORAGE_PROFILES").unwrap()).unwrap();
    assert_eq!(paths.len(),2);
    let mut profiles = vec![];
    for path in paths {
        let bytes = std::fs::read(&path).unwrap(); assert!(bytes.len() <= 256*1024*1024);
        let p: Value = serde_json::from_slice(&bytes).unwrap();
        let fs = p["functions"].as_array().unwrap(); assert_eq!(fs.len(),program.functions.len());
        let mut rows = vec![];
        for (id, ((f,p),proof)) in program.functions.iter().zip(fs).zip(&proofs).enumerate() {
            let fallback = vec![false;f.registers];
            let row = work(f,p,proof.as_ref().unwrap_or(&fallback)).unwrap();
            rows.push(json!({"function": id,"work":row}));
        }
        profiles.push(json!({"path":path,"sha256":format!("{:x}",Sha256::digest(bytes)),"functions":rows}));
    }
    let output = std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("NARROW_STORAGE_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(output,&json!({"status":"passed","functions":functions,"profiles":profiles,
        "artifact_sha256":format!("{:x}",Sha256::digest(bytes)),"guest_commands":0,
        "production_runtime_changes":0,"executable_code_publications":0})).unwrap();
}
