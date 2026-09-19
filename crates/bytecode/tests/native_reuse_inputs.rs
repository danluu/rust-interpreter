//! Offline necessary-input census. This module never creates or executes a JIT.
use rust_interp_bytecode::{Function, Op, Program, Slot, PARTIAL_VALIDATION, VERSION};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::{collections::BTreeSet, io::Write};

const MAX_BYTES: usize = 128 * 1024 * 1024;
const MAX_FUNCTIONS: usize = 100_000;
const MAX_OPS: usize = 4_000_000;
const DOMAIN: &str = "native-reuse-necessary-inputs-v1";

struct HashWriter { digest: Sha256, bytes: usize }
impl Write for HashWriter {
    fn write(&mut self, bytes: &[u8]) -> std::io::Result<usize> {
        let end = self.bytes.checked_add(bytes.len()).filter(|n| *n <= MAX_BYTES)
            .ok_or_else(|| std::io::Error::other("diagnostic hash size limit"))?;
        self.digest.update(bytes); self.bytes = end; Ok(bytes.len())
    }
    fn flush(&mut self) -> std::io::Result<()> { Ok(()) }
}

fn fingerprint(value: &impl Serialize) -> Result<([u8;32],usize), String> {
    let mut writer = HashWriter { digest: Sha256::new(), bytes: 0 };
    bincode::serialize_into(&mut writer,value).map_err(|e| e.to_string())?;
    Ok((writer.digest.finalize().into(),writer.bytes))
}
fn hex(bytes: &[u8]) -> String {
    const DIGITS: &[u8] = b"0123456789abcdef";
    let mut out=String::with_capacity(bytes.len()*2);
    for &b in bytes { out.push(DIGITS[(b>>4) as usize] as char); out.push(DIGITS[(b&15) as usize] as char); }
    out
}

#[derive(Debug,PartialEq,Eq,Serialize)]
struct Identity {
    function: usize,
    name_sha256: String,
    body_sha256: String,
    necessary_inputs_sha256: String,
    operations: usize,
    serialized_bytes: usize,
    direct_callees: Vec<usize>,
}
#[derive(Debug,PartialEq,Eq,Serialize)]
struct Identities {
    namespace_sha256: String,
    uses_heap: bool,
    functions: Vec<Identity>,
}

fn identities(program: &Program) -> Result<Identities,String> {
    if program.version & PARTIAL_VALIDATION != 0 || program.functions.is_empty()
        || program.functions.len()>MAX_FUNCTIONS { return Err("program shape/validation scope".into()); }
    let total=program.functions.iter().try_fold(0usize,|n,f|n.checked_add(f.code.len()));
    if total.is_none_or(|n|n>MAX_OPS) { return Err("operation bound".into()); }
    rust_interp_bytecode::validate(program)?;
    // Exact adopted Jit::new_with_options decision, pinned by the controller.
    let uses_heap=!program.statics.is_empty() || program.functions.iter().flat_map(|f|&f.code).any(|op|
        matches!(op,Op::Allocate{..}|Op::Deallocate{..}|Op::Reallocate{..}|Op::CAllocate{..}
            |Op::CReallocate{..}|Op::CAlignedAllocate{..}|Op::CurrentDirectory{..}));
    let (namespace,_)=fingerprint(&(DOMAIN,program.version,&program.target,program.functions.len(),
        &program.data,&program.statics,&program.thread_locals,uses_heap))?;
    let bodies=program.functions.iter().map(fingerprint).collect::<Result<Vec<_>,_>>()?;
    let mut functions=Vec::with_capacity(program.functions.len());
    for (id,f) in program.functions.iter().enumerate() {
        let mut callees=BTreeSet::new();
        for op in &f.code { if let Op::Call{function,..}=op { callees.insert(*function); } }
        let dependencies=callees.iter().map(|&id| bodies.get(id).map(|b|(id,b.0))
            .ok_or_else(||"invalid direct callee".to_owned())).collect::<Result<Vec<_>,_>>()?;
        let (key,_)=fingerprint(&(DOMAIN,namespace,id,bodies[id].0,&dependencies))?;
        functions.push(Identity {function:id,name_sha256:hex(&Sha256::digest(f.name.as_bytes())),
            body_sha256:hex(&bodies[id].0),necessary_inputs_sha256:hex(&key),operations:f.code.len(),
            serialized_bytes:bodies[id].1,direct_callees:callees.into_iter().collect()});
    }
    Ok(Identities {namespace_sha256:hex(&namespace),uses_heap,functions})
}

fn fixture() -> Program {
    fn f(name:&str,code:Vec<Op>,registers:usize)->Function {
        Function {name:name.into(),frame_size:16,frame_align:8,registers,args:vec![],
            result:Slot {offset:0,size:0},code}
    }
    Program {version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![],statics:vec![],thread_locals:vec![],
        functions:vec![f("caller",vec![Op::Local{dst:0,offset:0},Op::Call{function:1,args:vec![],destination:0},Op::Return],1),
            f("callee",vec![Op::Imm{dst:0,value:7},Op::Return],1),f("unrelated",vec![Op::Return],0)]}
}

#[test]
fn streaming_identity_matches_complete_serialization_and_bounds_writes() {
    let p=fixture();let bytes=bincode::serialize(&p.functions[0]).unwrap();
    let (hash,size)=fingerprint(&p.functions[0]).unwrap();
    assert_eq!(hash,<[u8;32]>::from(Sha256::digest(&bytes)));assert_eq!(size,bytes.len());
    let mut writer=HashWriter {digest:Sha256::new(),bytes:MAX_BYTES};
    assert!(writer.write(&[0]).is_err());assert_eq!(writer.bytes,MAX_BYTES);
}

#[test]
fn callee_body_edit_invalidates_unchanged_caller_and_revert_restores_identity() {
    let p=fixture();let old=identities(&p).unwrap();let mut edited=p.clone();
    edited.functions[1].code[0]=Op::Imm{dst:0,value:8};let new=identities(&edited).unwrap();
    assert_eq!(old.namespace_sha256,new.namespace_sha256);
    assert_eq!(old.functions[0].body_sha256,new.functions[0].body_sha256);
    assert_ne!(old.functions[0].necessary_inputs_sha256,new.functions[0].necessary_inputs_sha256);
    assert_ne!(old.functions[1],new.functions[1]);assert_eq!(old.functions[2],new.functions[2]);
    edited.functions[1]=p.functions[1].clone();assert_eq!(identities(&edited).unwrap(),old);
}

#[test]
fn unrelated_body_edits_preserve_other_functions_without_whole_program_hashing() {
    let p=fixture();let old=identities(&p).unwrap();let mut edited=p.clone();
    edited.functions[2].registers=1;edited.functions[2].code.insert(0,Op::Imm{dst:0,value:42});
    let new=identities(&edited).unwrap();assert_eq!(old.namespace_sha256,new.namespace_sha256);
    assert_eq!(old.functions[..2],new.functions[..2]);assert_ne!(old.functions[2],new.functions[2]);
}

#[test]
fn callee_frame_and_initial_read_changes_also_invalidate_callers() {
    let p=fixture();let old=identities(&p).unwrap();
    for initialization in [false,true] {
        let mut edited=p.clone();
        if initialization {edited.functions[1].code.insert(0,Op::Store{address:0,src:0,size:8});}
        else {edited.functions[1].frame_size=32;edited.functions[1].frame_align=16;}
        let new=identities(&edited).unwrap();
        assert_eq!(old.functions[0].body_sha256,new.functions[0].body_sha256);
        assert_ne!(old.functions[0].necessary_inputs_sha256,new.functions[0].necessary_inputs_sha256);
    }
}

#[test]
fn heap_mode_and_global_initializers_are_explicit_namespace_inputs() {
    let p=fixture();let old=identities(&p).unwrap();assert!(!old.uses_heap);
    for kind in 0..4 {
        let mut edited=p.clone();
        match kind {
            0=>{edited.functions[2].registers=3;edited.functions[2].code=vec![Op::Imm{dst:0,value:8},Op::Imm{dst:1,value:8},
                Op::Allocate{dst:2,size:0,align:1,zeroed:false},Op::Return];},
            1=>edited.data=vec![0,1,2,3],
            2=>edited.statics=vec![0;16],
            _=>{edited.statics=vec![1;16];edited.thread_locals=vec![Slot{offset:0,size:8}];},
        }
        let new=identities(&edited).unwrap();assert_ne!(old.namespace_sha256,new.namespace_sha256);
        assert_eq!(old.functions[0].body_sha256,new.functions[0].body_sha256);
        assert_ne!(old.functions[0].necessary_inputs_sha256,new.functions[0].necessary_inputs_sha256);
    }
}

#[test]
fn numerical_identity_and_duplicate_direct_edges_are_preserved() {
    let mut p=fixture();p.functions[0].code.insert(2,Op::Call{function:1,args:vec![],destination:0});
    let old=identities(&p).unwrap();assert_eq!(old.functions[0].direct_callees,[1]);
    // Swap the two leaf slots: each leaf body is identical to its earlier self,
    // but its numeric binding and the caller's bound callee have changed.
    p.functions.swap(1,2);let new=identities(&p).unwrap();
    assert_eq!(old.functions[1].body_sha256,new.functions[2].body_sha256);
    assert_ne!(old.functions[1].necessary_inputs_sha256,new.functions[2].necessary_inputs_sha256);
    assert_ne!(old.functions[0].necessary_inputs_sha256,new.functions[0].necessary_inputs_sha256);
}

#[test]
fn partial_and_structurally_invalid_artifacts_are_rejected() {
    let mut p=fixture();p.version|=PARTIAL_VALIDATION;assert!(identities(&p).is_err());
    let mut p=fixture();p.functions[0].code[1]=Op::Call{function:99,args:vec![],destination:0};
    assert!(identities(&p).is_err());
    let mut p=fixture();p.functions[1].frame_align=3;assert!(identities(&p).is_err());
}

#[test]
#[ignore="Requires source-bound saved artifact manifest; no guest or executable publication"]
fn observe_saved_native_reuse_inputs() {
    let manifest=std::fs::read(std::env::var("NATIVE_REUSE_MANIFEST").unwrap()).unwrap();
    assert!(manifest.len()<=1024*1024);
    let manifest:serde_json::Value=serde_json::from_slice(&manifest).unwrap();
    let artifacts=manifest["artifacts"].as_array().unwrap();assert!(!artifacts.is_empty() && artifacts.len()<=128);
    let directory=std::path::PathBuf::from(std::env::var("NATIVE_REUSE_OUTPUT").unwrap());
    std::fs::create_dir(&directory).unwrap();
    let mut total_bytes=0usize;let mut total_functions=0usize;let mut output_bytes=0usize;
    let mut reports=vec![];let mut seen=BTreeSet::new();
    for artifact in artifacts {
        let expected=artifact["sha256"].as_str().unwrap();assert!(seen.insert(expected.to_owned()));
        assert!(expected.len()==64 && expected.bytes().all(|b|b.is_ascii_hexdigit() && !b.is_ascii_uppercase()));
        let path=artifact["path"].as_str().unwrap();
        assert!(std::fs::metadata(path).unwrap().len()<=MAX_BYTES as u64);
        let bytes=std::fs::read(path).unwrap();assert!(bytes.len()<=MAX_BYTES);
        total_bytes=total_bytes.checked_add(bytes.len()).unwrap();assert!(total_bytes<=4*1024*1024*1024);
        assert_eq!(hex(&Sha256::digest(&bytes)),expected);
        let started=std::time::Instant::now();
        let program:Program=bincode::deserialize(&bytes).unwrap();let decode_ns=started.elapsed().as_nanos();
        let started=std::time::Instant::now();let rows=identities(&program).unwrap();
        let validation_and_keying_ns=started.elapsed().as_nanos();
        total_functions+=rows.functions.len();assert!(total_functions<=2_000_000);
        let report=serde_json::json!({"artifact_sha256":expected,"artifact_bytes":bytes.len(),
            "decode_ns":decode_ns,"validation_and_keying_ns":validation_and_keying_ns,
            "scope":"standalone diagnostic intervals, not end-to-end or actual cache lookup cost","identities":rows});
        let encoded=serde_json::to_vec(&report).unwrap();assert!(encoded.len()<=128*1024*1024);
        output_bytes=output_bytes.checked_add(encoded.len()).unwrap();assert!(output_bytes<=512*1024*1024);
        let output=directory.join(format!("{expected}.json"));
        let mut file=std::fs::OpenOptions::new().write(true).create_new(true).open(&output).unwrap();
        file.write_all(&encoded).unwrap();
        reports.push(serde_json::json!({"artifact_sha256":expected,"path":output,
            "sha256":hex(&Sha256::digest(&encoded)),"functions":program.functions.len()}));
    }
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(directory.join("summary.json")).unwrap();
    serde_json::to_writer(file,&serde_json::json!({"status":"passed","reports":reports,
        "total_artifact_bytes":total_bytes,"total_functions":total_functions,"output_bytes":output_bytes,
        "new_guest_commands":0,"executable_code_publications":0,"production_runtime_changes":0})).unwrap();
}
