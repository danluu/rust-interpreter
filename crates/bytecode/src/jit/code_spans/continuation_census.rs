//! Inspect existing resume targets only after exact adopted-code reconstruction.
use super::*;
use serde_json::{Value,json};

fn number(v:&Value,key:&str)->usize {usize::try_from(v[key].as_u64().unwrap()).unwrap()}

fn calls(f:&Function, staged:&CompiledFunction<'_>, base:usize)->Vec<Value> {
    f.code.iter().enumerate().filter_map(|(pc,op)| {
        let Op::Call {function:callee,..}=op else {return None};
        let Some(entry)=staged.entries[pc] else {return None};
        assert_eq!(entry.end,pc+1);
        let target=staged.resumes.get(pc+1).copied().flatten().map(|word| {
            let relative=word.checked_mul(4).unwrap();
            let continuation=staged.entries[pc+1].unwrap();
            assert!(continuation.offset<relative && relative<staged.words.len()*4);
            let absolute=base.checked_add(relative).unwrap();
            assert!(absolute>0 && absolute<MAX_CODE_BYTES && absolute%4==0);
            u32::try_from(absolute).unwrap()
        });
        Some(json!({"pc":pc,"callee":callee,"next_pc":pc+1,"native_return_offset":target,
            "one_past_code":pc+1==f.code.len(),"native_call_offset":base+entry.offset,
            "immediate_store_words":target.map(|offset|if offset<65536 {2} else {3})}))
    }).collect()
}

#[test]
fn continuation_census_distinguishes_native_unsupported_and_one_past_returns() {
    for tail in [vec![Op::Return],vec![Op::Unary {dst:1,src:0,bits:128,op:Unary::CountOnes},Op::Return],vec![]] {
        let native=matches!(tail.first(),Some(Op::Return));let one_past=tail.is_empty();
        let mut code=vec![Op::Imm {dst:0,value:0},Op::Call {function:1,args:vec![],destination:0}];
        code.extend(tail);
        let function=|name:&str,code|Function {name:name.into(),frame_size:8,frame_align:8,registers:2,
            args:vec![],result:crate::Slot {offset:0,size:0},code};
        let p=Program {version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,
            data:vec![0;16],statics:vec![],thread_locals:vec![],functions:vec![function("caller",code),
                function("callee",vec![Op::Return])]};
        crate::validate(&p).unwrap();
        for profiled in [false,true] {for persistent in [false,true] {
            let jit=Jit::new_resumable(&p,profiled,MAX_CODE_BYTES,persistent).unwrap();
            let staged=jit.emit_function_inner(&p.functions[0],MAX_CODE_BYTES/4,0,None).unwrap().unwrap();
            for base in [0,65536] {
                let rows=calls(&p.functions[0],&staged,base);assert_eq!(rows.len(),1);
                assert_eq!(rows[0]["pc"],1);assert_eq!(rows[0]["callee"],1);
                assert_eq!(!rows[0]["native_return_offset"].is_null(),native);
                assert_eq!(rows[0]["one_past_code"],one_past);
                if native {assert_eq!(rows[0]["native_return_offset"],base+staged.resumes[2].unwrap()*4);}
            }
            assert!(jit.code.is_none());assert_eq!(jit.bytes,0);
        }}
    }
}

#[test]
fn continuation_census_checks_proposed_offset_field_without_changing_frame_layout() {
    // A separate type tests feasibility. Never reinterpret an existing Frame's
    // uninitialized padding; any runtime candidate must initialize the new field.
    #[repr(C)]
    struct Proposed {function:usize,pc:usize,base:usize,register_base:usize,
        return_address:usize,tls_callback:bool,return_code_offset:u32}
    #[cfg(all(target_arch="aarch64",target_os="macos"))]
    {
        use crate::frames::layout;
        assert_eq!(std::mem::size_of::<Proposed>(),layout::SIZE);
        assert_eq!(std::mem::align_of::<Proposed>(),layout::ALIGN);
        assert_eq!(std::mem::offset_of!(Proposed,tls_callback),layout::TLS_CALLBACK);
        assert_eq!(std::mem::offset_of!(Proposed,return_code_offset),44);
        assert_eq!(std::mem::size_of::<Proposed>(),48);
    }
}

#[test]
#[ignore="Requires exact adopted unprofiled code, map and artifact"]
fn observe_saved_native_continuations() {
    let artifact=std::fs::read(std::env::var("CONTINUATION_ARTIFACT").unwrap()).unwrap();assert!(artifact.len()<=128*1024*1024);
    let p:Program=bincode::deserialize(&artifact).unwrap();crate::validate(&p).unwrap();
    let mapping=std::fs::read(std::env::var("CONTINUATION_MAP").unwrap()).unwrap();assert!(mapping.len()<=MAX_OUTPUT_BYTES);
    let mapping:Value=serde_json::from_slice(&mapping).unwrap();
    let bytes=std::fs::read(std::env::var("CONTINUATION_CODE").unwrap()).unwrap();assert!(bytes.len()<=MAX_CODE_BYTES);
    assert_eq!(number(&mapping,"schema_version"),1);assert_eq!(mapping["profiled"],false);
    for flag in ["persistent_registers","resumable_calls","complete","reconstructed_bytes_match"] {assert_eq!(mapping[flag],true);}
    assert_eq!(number(&mapping,"code_bytes"),bytes.len());
    assert_eq!(mapping["code_sha256"],format!("{:x}",Sha256::digest(&bytes)));
    let jit=Jit::new_resumable(&p,false,MAX_CODE_BYTES,true).unwrap().use_adopted_emission();
    let (mut cursor,mut assertions)=(0,0);let mut seen=BTreeSet::new();let mut output=vec![];
    for saved in mapping["functions"].as_array().unwrap() {
        let id=number(saved,"function");assert!(seen.insert(id));let f=&p.functions[id];assert_eq!(saved["name"],f.name);
        let offset=number(saved,"offset");let end=number(saved,"end");assert_eq!(cursor,offset);assert!(offset<end && end<=bytes.len());
        assert_eq!(number(saved,"assertion_base"),assertions);
        let mut cm=Collector {rows:vec![],limit:MAX_SPANS};
        let a=jit.emit_function_inner(f,(end-offset)/4,assertions,Some(&mut cm)).unwrap().unwrap();
        verify_words(&a.words,&bytes[offset..end]).unwrap();cm.validate(f,&a).unwrap();
        assert_eq!(a.assertions.len(),number(saved,"assertion_count"));
        for s in &mut cm.rows {s.offset+=offset;s.end+=offset;}
        assert_eq!(serde_json::to_value(&cm.rows).unwrap(),saved["spans"]);
        output.push(json!({"function":id,"name":f.name,"calls":calls(f,&a,offset)}));
        cursor=end;assertions+=a.assertions.len();
    }
    assert_eq!(cursor,bytes.len());assert!(jit.code.is_none());assert_eq!(jit.bytes,0);
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("CONTINUATION_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","functions":output,"code_bytes":bytes.len(),
        "code_sha256":mapping["code_sha256"],"exact_baseline_reconstruction":true,
        "counter_offsets":{"Call":crate::native_continuation::layout::CALLS,"Return":crate::native_continuation::layout::RETURNS},
        "guest_commands":0,"executable_code_publications":0})).unwrap();
}
