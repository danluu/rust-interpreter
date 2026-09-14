use super::*;

#[test]
fn native_readonly_heap_free_context_never_uses_uninitialized_heap_registers() {
    let tag=crate::heap::TAG as u128;
    let mut p=read_pair(8,false);p.statics.clear();
    let jit=Jit::new_resumable(&p,false,16*1024*1024,true).unwrap();assert!(!jit.uses_heap);
    for pointer in [0,1,32,152,159,160,176,tag-1,tag,tag+1,tag+16,u64::MAX as u128] {
        let result=compare(&p,&[pointer],100,65536,8);
        if pointer==32 {assert_eq!(result.commits,1);}
    }
    for profiled in [false,true] {
        let mut jit=Jit::new_resumable(&p,profiled,16*1024*1024,true).unwrap();jit.enable_scalar_calls();
        jit.ensure_function(0).unwrap();assert!(jit.scalar_entry(1).is_some());
        let map=serde_json::to_value(jit.operation_map().unwrap()).unwrap();
        assert_eq!(map["reconstructed_bytes_match"],true);
    }
}

fn read_pair(size:u8,copy:bool)->Program {
    let parent=function("readonly parent",64,8,vec![Slot{offset:0,size:8}],Slot{offset:16,size:16},vec![
        local(0,0),local(1,16),Op::Call{function:1,args:vec![0],destination:1},Op::Return]);
    let mut code=vec![local(0,16),load(1,0,8),local(2,0)];
    if copy {code.push(Op::Copy{src:1,dst:2,size:size as usize});}
    else {code.push(load(3,1,size));code.push(Op::Store{address:2,src:3,size});}
    code.push(Op::Return);
    let leaf=function("readonly leaf",32,8,vec![Slot{offset:16,size:8}],Slot{offset:0,size:16},code);
    let mut p=program(vec![parent,leaf]);p.data=(0..96).map(|i|(i*37+11) as u8).collect();
    p.statics=(0..64).map(|i|(i*19+3) as u8).collect();p
}

#[test]
fn native_readonly_widths_linear_heap_and_every_budget_match() {
    let tag=crate::heap::TAG as u128;
    for size in 1..=16 {for copy in [false,true] {
        let p=read_pair(size,copy);
        for pointer in [0,1,32,80,95,96,144,159,160,176,tag,tag+1,tag+16,tag+48,tag+64,u64::MAX as u128] {
            let result=compare(&p,&[pointer],100,65536,8);
            if pointer==32 || pointer==tag+16 {assert_eq!(result.commits,1);}
        }
        for budget in 0..=12 {compare(&p,&[32],budget,65536,8);}
    }}
}

#[test]
fn native_readonly_fault_order_padding_and_capacity_tails_match() {
    let mut p=read_pair(8,false);
    p.functions[0].frame_size=33;p.functions[1].frame_align=64;
    p.functions[1].code=vec![local(0,16),load(1,0,8),load(2,1,8),
        Op::Assert{value:1,expected:false,message:"after unused external read".into()},Op::Return];
    for pointer in [0,32,128,129,136,191,192,208,u64::MAX as u128] {
        for budget in 0..=10 {compare(&p,&[pointer],budget,65536,8);}
    }
    p.functions[1].code.pop();p.functions[1].code.pop();p.functions[1].code.push(Op::Return);
    for memory in [0,95,128,256,511,512,1023,1024,65536] {for frames in 0..=3 {
        compare(&p,&[32],100,memory,frames);
    }}
}

#[test]
fn native_readonly_result_can_alias_its_external_source_after_private_reads() {
    let tag=crate::heap::TAG as u128;let mut p=read_pair(8,false);
    p.functions[0].result=Slot{offset:16,size:8};
    p.functions[0].code=vec![local(0,0),load(1,0,8),Op::Imm{dst:2,value:0x8877665544332211},
        Op::Store{address:1,src:2,size:8},Op::Call{function:1,args:vec![0],destination:1},
        load(2,1,8),local(3,16),Op::Store{address:3,src:2,size:8},Op::Return];
    p.functions[1].result=Slot{offset:0,size:8};
    p.functions[1].code=vec![local(0,16),load(1,0,8),load(2,1,8),Op::Imm{dst:3,value:1},
        Op::Binary{dst:4,overflow:5,op:crate::Binary::Add,a:2,b:3,bits:64,signed:false},
        local(6,0),Op::Store{address:6,src:4,size:8},Op::Return];
    for pointer in [112,tag+16,tag+24,tag+56] {
        assert_eq!(compare(&p,&[pointer],100,65536,8).commits,1);
        for budget in 0..=18 {compare(&p,&[pointer],budget,65536,8);}
    }
}

#[test]
fn native_readonly_preserves_live_scalar_allocations_across_checked_reads() {
    let mut p=read_pair(8,false);let f=&mut p.functions[1];f.registers=64;
    f.code=vec![local(0,16),load(1,0,8)];
    for i in 0..12 {
        f.code.push(load(2+i,1,8));
        f.code.push(Op::Imm{dst:30,value:i as u128+1});
        f.code.push(Op::Binary{dst:2+i,overflow:31,op:crate::Binary::Mul,a:2+i,b:30,bits:64,signed:false});
    }
    f.code.push(Op::Imm{dst:32,value:0});
    for i in [3,9,0,8,2,11,1,7,4,10,5,6] {
        f.code.push(Op::Binary{dst:32,overflow:31,op:crate::Binary::Xor,a:32,b:2+i,bits:64,signed:false});
    }
    f.code.extend([local(33,0),Op::Store{address:33,src:32,size:8},Op::Return]);
    for pointer in [1,16,32,crate::heap::TAG as u128+16] {
        assert_eq!(compare(&p,&[pointer],200,65536,8).commits,1);
    }
    for budget in 0..=p.functions[1].code.len() as u64+5 {compare(&p,&[32],budget,65536,8);}
}

#[test]
fn native_readonly_conditional_reads_and_high_pointer_bits_retain_original_semantics() {
    let mut p=read_pair(8,false);
    p.functions[1].code=vec![local(0,16),load(1,0,8),
        Op::Switch{value:1,cases:vec![(0,6)],otherwise:3},load(2,1,8),
        local(3,0),Op::Store{address:3,src:2,size:8},Op::Return];
    for pointer in [0,32,160,176,crate::heap::TAG as u128+16] {
        let statistics=compare(&p,&[pointer],100,65536,8);
        if pointer==0 || pointer==32 {assert_eq!(statistics.commits,1);}
        if pointer==160 || pointer==176 {assert_eq!(statistics.commits,0);}
    }
    // This full u128 address is computed in the leaf. Only its low usize is
    // consumed by Load; high bits cannot affect arena choice or bounds checks.
    p.functions[1].code[1]=Op::Imm{dst:1,value:(1u128<<100)|32};
    assert_eq!(compare(&p,&[0],100,65536,8).commits,1);
}

#[test]
fn native_readonly_shared_arena_reconstruction_and_write_rejection_are_exact() {
    let p=read_pair(8,false);
    for profiled in [false,true] {
        let mut jit=Jit::new_resumable(&p,profiled,16*1024*1024,true).unwrap();jit.enable_scalar_calls();
        jit.ensure_function(0).unwrap();let entry=jit.scalar_entry(1).unwrap();assert!(entry.bytes>0);
        let map=serde_json::to_value(jit.operation_map().unwrap()).unwrap();
        assert_eq!(map["complete"],true);assert_eq!(map["reconstructed_bytes_match"],true);
    }
    let mut p=p;p.functions[1].code.insert(3,Op::Store{address:1,src:2,size:8});
    let mut jit=Jit::new_resumable(&p,false,16*1024*1024,true).unwrap();jit.enable_scalar_calls();
    jit.ensure_function(0).unwrap();assert!(jit.scalar_entry(1).is_none());
}

#[test]
#[ignore="Requires pinned public bytecode, captures and a fresh output path"]
fn observe_saved_readonly_native_plans() {
    use serde_json::{Value,json};
    use sha2::{Digest,Sha256};
    let bytes=std::fs::read(std::env::var("READONLY_ARTIFACT").unwrap()).unwrap();assert!(bytes.len()<=128*1024*1024);
    let digest=format!("{:x}",Sha256::digest(&bytes));assert_eq!(digest,std::env::var("READONLY_ARTIFACT_SHA256").unwrap());
    let p:Program=bincode::deserialize(&bytes).unwrap();crate::validate(&p).unwrap();assert!(p.functions.len()<=65536);
    let jit=Jit::new_resumable(&p,false,16*1024*1024,true).unwrap();
    let captures:Vec<Value>=serde_json::from_str(&std::env::var("READONLY_CAPTURES").unwrap()).unwrap();
    assert_eq!(captures.len(),2);
    let mut saved=std::collections::BTreeMap::<usize,Vec<u8>>::new();let mut capture_counts=vec![];
    for capture in captures {
        let mapping=std::fs::read(capture["map"].as_str().unwrap()).unwrap();assert!(mapping.len()<=256*1024*1024);
        assert_eq!(format!("{:x}",Sha256::digest(&mapping)),capture["map_sha256"].as_str().unwrap());
        let mapping:Value=serde_json::from_slice(&mapping).unwrap();
        let code=std::fs::read(capture["code"].as_str().unwrap()).unwrap();assert!(code.len()<=16*1024*1024);
        let code_hash=format!("{:x}",Sha256::digest(&code));
        assert_eq!(code_hash,capture["code_sha256"].as_str().unwrap());assert_eq!(mapping["code_sha256"],code_hash);
        assert_eq!(mapping["schema_version"],2);assert_eq!(mapping["complete"],true);
        assert_eq!(mapping["reconstructed_bytes_match"],true);assert_eq!(mapping["profiled"],false);
        let mut count=0;
        for f in mapping["functions"].as_array().unwrap() {
            if f["spans"][0]["kind"]!="scalar_leaf" {continue;}
            let id=f["function"].as_u64().unwrap() as usize;assert_eq!(f["name"],p.functions[id].name);
            let start=f["offset"].as_u64().unwrap() as usize;let end=f["end"].as_u64().unwrap() as usize;
            assert!(start<end && end<=code.len());let body=code[start..end].to_vec();
            if let Some(previous)=saved.insert(id,body.clone()) {assert_eq!(previous,body);}
            count+=1;
        }
        capture_counts.push(json!({"case":capture["case"],"scalar_bodies":count}));
    }
    let mut work=crate::proof::MAX_GLOBAL_WORK;let mut rows=vec![];let mut existing_verified=0;
    for (id,f) in p.functions.iter().enumerate() {
        let memory=crate::proof::memory_plan_for_call(&p,id,&mut work);
        let external_reads=memory.accesses.iter().flat_map(|a|&a.reads).filter(|r|r.size>0 && r.offset.is_none()).count();
        let plan=crate::scalar_ir::lower(f,&memory,250_000);let summary=crate::scalar_ir::summary(&plan);let mut native=vec![];
        if let Ok(plan)=&plan {
            for profiled in [false,true] {
                native.push(match crate::scalar_ir::native_leaf::emit_call_with_heap(plan,profiled,jit.uses_heap) {
                    Ok(code)=>{
                        if !profiled {if let Some(previous)=saved.get(&id) {
                            assert_eq!(external_reads,0);let actual:Vec<u8>=code.words.iter().flat_map(|w|w.to_le_bytes()).collect();
                            assert_eq!(previous,&actual,"existing scalar function {id}");existing_verified+=1;
                        }}
                        json!({"profiled":profiled,"eligible":true,"bytes":code.words.len()*4,
                            "stack_bytes":code.stack_bytes,"success_steps":code.success_steps})
                    },
                    Err(reason)=>json!({"profiled":profiled,"eligible":false,"decline":reason}),
                });
            }
        }
        let candidate=external_reads>0 && f.args.len()<=64 && native.len()==2 && native.iter().all(|n|n["eligible"]==true);
        rows.push(json!({"function":id,"name":f.name,"memory_eligible":memory.eligible,"memory_decline":memory.decline,
            "scalar":summary,"external_reads":external_reads,"candidate":candidate,"native":native,"native_implemented":true}));
    }
    assert_eq!(existing_verified,saved.len());assert!(jit.code.is_none() && jit.bytes==0);
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("READONLY_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","artifact_sha256":digest,"rows":rows,"functions":p.functions.len(),
        "memory_work_used":crate::proof::MAX_GLOBAL_WORK-work,"memory_work_remaining":work,"heap_abi":jit.uses_heap,
        "production_policy_changed":true,"original_project_guest_commands":0,"executable_code_publications":0,
        "existing_scalar_bodies_verified":existing_verified,"captures":capture_counts})).unwrap();
}
