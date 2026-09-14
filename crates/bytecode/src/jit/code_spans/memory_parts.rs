//! Reconstruct first, then partition the original small-memory operation spans.
use super::*;
use serde_json::{Value,json};

fn partition(f: &Function, staged: &CompiledFunction<'_>, rows: &[Span]) {
    let mut next=0;
    for coarse in rows {
        if coarse.kind!=Kind::Operation { continue; }
        let pc=coarse.pc.unwrap();
        let Some((op,size))=super::super::memory_parts::selected(&f.code[pc]) else { continue; };
        let mut cursor=coarse.offset;
        while next<staged.memory_spans.len() && staged.memory_spans[next].offset<coarse.end {
            let s=&staged.memory_spans[next];
            assert_eq!(s.offset,cursor);assert!(s.offset<s.end && s.end<=coarse.end);
            assert_eq!((s.pc,s.operation,s.size),(pc,op,size));
            assert_eq!(s.region_start,coarse.region_pc);
            assert_eq!(s.region_end,staged.entries[s.region_start].unwrap().end);
            assert_ne!(s.part,"unclassified");
            assert!(["none","source","destination","both"].contains(&s.access));
            cursor=s.end;next+=1;
        }
        assert_eq!(cursor,coarse.end);
    }
    assert_eq!(next,staged.memory_spans.len());
}

fn program(code: Vec<Op>) -> Program {
    Program {version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,
        data:vec![0;16],statics:vec![],thread_locals:vec![],
        functions:vec![Function {name:"memory parts".into(),frame_size:128,frame_align:16,
            registers:12,args:vec![],result:crate::Slot {offset:0,size:8},code}]}
}

fn observe(p: &Program, heap: bool) -> Vec<super::super::memory_parts::Span> {
    crate::validate(p).unwrap();
    let mut plain=Jit::new_resumable(p,false,MAX_CODE_BYTES,true).unwrap();plain.uses_heap=heap;
    let mut observer=Jit::new_resumable(p,false,MAX_CODE_BYTES,true).unwrap();observer.uses_heap=heap;
    observer.observe_memory_parts=true;
    let f=&p.functions[0];
    let mut cm=Collector {rows:vec![],limit:MAX_SPANS};
    let a=plain.emit_function_inner(f,MAX_CODE_BYTES/4,0,Some(&mut cm)).unwrap().unwrap();
    let mut om=Collector {rows:vec![],limit:MAX_SPANS};
    let b=observer.emit_function_inner(f,MAX_CODE_BYTES/4,0,Some(&mut om)).unwrap().unwrap();
    assert_eq!(a.words,b.words);assert_eq!(a.assertions,b.assertions);assert_eq!(a.resumes,b.resumes);
    assert_eq!(a.operations,b.operations);assert_eq!(a.local_fact_events,b.local_fact_events);
    assert_eq!(a.retained_local_writes,b.retained_local_writes);assert!(a.memory_spans.is_empty());
    cm.validate(f,&a).unwrap();om.validate(f,&b).unwrap();
    assert_eq!(serde_json::to_value(&cm.rows).unwrap(),serde_json::to_value(&om.rows).unwrap());
    partition(f,&b,&cm.rows);
    assert!(plain.code.is_none() && observer.code.is_none());assert_eq!(plain.bytes+observer.bytes,0);
    assert!(b.memory_spans.iter().all(|s|s.heap_enabled==heap));
    b.memory_spans
}

#[test]
fn memory_parts_separate_dynamic_address_checks_without_changing_words() {
    let p=program(vec![Op::Local {dst:0,offset:16},Op::Load {dst:1,address:0,size:8},
        Op::Load {dst:2,address:1,size:8},Op::Local {dst:3,offset:24},
        Op::Load {dst:4,address:3,size:8},Op::Local {dst:5,offset:64},
        Op::Copy {dst:5,src:4,size:16},Op::Local {dst:6,offset:32},
        Op::Load {dst:7,address:6,size:8},Op::Store {address:7,src:2,size:8},Op::Return]);
    for heap in [false,true] {
        let rows=observe(&p,heap);
        assert!(rows.iter().any(|s|s.part=="bounds_check" && s.access=="source"));
        assert!(rows.iter().any(|s|s.part=="readonly_check" && s.access=="destination"));
        assert_eq!(rows.iter().any(|s|s.part=="address_space_selection"),heap);
        assert!(rows.iter().any(|s|s.part=="register_publication"));
        assert!(rows.iter().any(|s|s.part=="register_value"));
    }
}

#[test]
fn memory_parts_preserve_shared_frame_forwarding_and_odd_transfers() {
    let p=program(vec![Op::Local {dst:0,offset:16},Op::Local {dst:1,offset:32},
        Op::Copy {dst:1,src:0,size:16},Op::Load {dst:2,address:0,size:8},
        Op::Copy {dst:1,src:0,size:8},Op::Load {dst:3,address:1,size:8},
        Op::Copy {dst:1,src:0,size:3},Op::Imm {dst:4,value:7},
        Op::Store {address:1,src:4,size:8},Op::Load {dst:5,address:1,size:8},
        Op::Store {address:0,src:5,size:8},Op::Store {address:1,src:2,size:8},Op::Return]);
    let rows=observe(&p,true);
    assert!(rows.iter().any(|s|s.part=="shared_frame_address" && s.access=="both"));
    assert!(rows.iter().any(|s|s.part=="forwarded_value"));
    for part in ["load_data","store_data"] {assert!(rows.iter().any(|s|s.pc==6 && s.part==part));}
    assert!(!rows.iter().any(|s|s.pc==9),"static forwarded Load emits no words");
    assert!(!rows.iter().any(|s|s.part=="bounds_check"));
}

#[test]
fn memory_parts_stop_at_operations_and_exclude_fills_and_large_copies() {
    let p=program(vec![Op::Local {dst:0,offset:16},Op::Load {dst:1,address:0,size:8},
        Op::Jump {target:3},Op::Local {dst:2,offset:32},Op::Imm {dst:3,value:0},
        Op::Imm {dst:4,value:48},Op::FillBytes {address:2,value:3,size:4},
        Op::Local {dst:5,offset:80},Op::Copy {dst:2,src:5,size:40},
        Op::Load {dst:6,address:2,size:8},Op::Return]);
    let rows=observe(&p,true);
    assert!(rows.iter().any(|s|s.region_start==0));
    assert!(rows.iter().any(|s|s.region_start==3));
    assert!(rows.iter().all(|s|[1,9].contains(&s.pc)));
    assert!(!rows.iter().any(|s|s.part=="fused_fill"));
}

fn number(v: &Value, key: &str) -> usize { usize::try_from(v[key].as_u64().unwrap()).unwrap() }

#[test]
#[ignore = "Requires exact saved unprofiled code, operation map and artifact"]
fn observe_saved_small_memory_parts() {
    let artifact = std::fs::read(std::env::var("MEMORY_ARTIFACT").unwrap()).unwrap();
    assert!(artifact.len() <= 128*1024*1024);
    let p: Program = bincode::deserialize(&artifact).unwrap(); crate::validate(&p).unwrap();
    let mapping = std::fs::read(std::env::var("MEMORY_MAP").unwrap()).unwrap();
    assert!(mapping.len() <= MAX_OUTPUT_BYTES);
    let mapping: Value = serde_json::from_slice(&mapping).unwrap();
    let bytes = std::fs::read(std::env::var("MEMORY_CODE").unwrap()).unwrap();
    assert!(bytes.len() <= MAX_CODE_BYTES);
    let schema=number(&mapping,"schema_version");assert!([1,2].contains(&schema)); assert_eq!(mapping["profiled"],false);
    for flag in ["persistent_registers","resumable_calls","complete","reconstructed_bytes_match"] {
        assert_eq!(mapping[flag],true);
    }
    assert_eq!(number(&mapping,"code_bytes"),bytes.len());
    assert_eq!(mapping["code_sha256"],format!("{:x}",Sha256::digest(&bytes)));
    let mut plain = Jit::new_resumable(&p,false,MAX_CODE_BYTES,true).unwrap();
    let mut observer = Jit::new_resumable(&p,false,MAX_CODE_BYTES,true).unwrap();
    observer.observe_memory_parts = true;
    let mut scalar_ids=BTreeSet::new();
    if schema==2 {
        plain.enable_scalar_calls();observer.enable_scalar_calls();
        let base=number(&mapping,"arena_base");assert!(base>0);
        for saved in mapping["functions"].as_array().unwrap() {
            if saved["spans"][0]["kind"]!="scalar_leaf" {continue;}
            let id=number(saved,"function");assert!(scalar_ids.insert(id));
            let offset=number(saved,"offset");let end=number(saved,"end");
            assert!(offset<end && end<=bytes.len());
            let a=plain.observe_saved_scalar_entry(id,offset,end-offset,base);
            let b=observer.observe_saved_scalar_entry(id,offset,end-offset,base);
            assert_eq!(a,b);verify_words(&a,&bytes[offset..end]).unwrap();
        }
    }
    let (mut cursor,mut assertions) = (0,0);
    let mut seen = BTreeSet::new(); let mut output = vec![];
    for saved in mapping["functions"].as_array().unwrap() {
        let id = number(saved,"function");let f = &p.functions[id];
        assert_eq!(saved["name"],f.name);
        let offset = number(saved,"offset"); let end = number(saved,"end");
        assert_eq!(offset,cursor); assert!(offset < end && end <= bytes.len());
        assert_eq!(number(saved,"assertion_base"),assertions);
        if saved["spans"][0]["kind"]=="scalar_leaf" {
            assert_eq!(schema,2);assert!(scalar_ids.contains(&id));
            assert_eq!(number(saved,"assertion_count"),0);
            assert_eq!(saved["spans"],json!([{"offset":offset,"end":end,"region_pc":0,"pc":null,"kind":"scalar_leaf"}]));
            cursor=end;continue;
        }
        assert!(seen.insert(id));
        let mut cm = Collector {rows:vec![],limit:MAX_SPANS};
        let a = plain.emit_function_inner(f,(end-offset)/4,assertions,Some(&mut cm)).unwrap().unwrap();
        let mut om = Collector {rows:vec![],limit:MAX_SPANS};
        let mut b = observer.emit_function_inner(f,(end-offset)/4,assertions,Some(&mut om)).unwrap().unwrap();
        verify_words(&a.words,&bytes[offset..end]).unwrap(); assert_eq!(a.words,b.words);
        assert_eq!(a.operations,b.operations); assert_eq!(a.resumes,b.resumes); assert_eq!(a.assertions,b.assertions);
        assert_eq!(a.local_fact_events,b.local_fact_events); assert_eq!(a.retained_local_writes,b.retained_local_writes);
        assert!(a.memory_spans.is_empty()); assert!(a.scratch_hits.is_empty() && b.scratch_hits.is_empty());
        cm.validate(f,&a).unwrap(); om.validate(f,&b).unwrap();
        assert_eq!(serde_json::to_value(&cm.rows).unwrap(),serde_json::to_value(&om.rows).unwrap());
        partition(f,&b,&cm.rows);
        assert_eq!(a.assertions.len(),number(saved,"assertion_count"));
        for s in &mut cm.rows {s.offset+=offset;s.end+=offset;}
        assert_eq!(serde_json::to_value(&cm.rows).unwrap(),saved["spans"]);
        for s in &mut b.memory_spans {s.offset+=offset;s.end+=offset;}
        let selected:Vec<_>=f.code.iter().enumerate().filter_map(|(pc,op)| {
            super::super::memory_parts::selected(op).map(|(operation,size)|json!({"pc":pc,"operation":operation,"size":size}))
        }).collect();
        output.push(json!({"function":id,"name":f.name,"selected":selected,"memory_spans":b.memory_spans}));
        assertions+=a.assertions.len();cursor=end;
    }
    assert_eq!(cursor,bytes.len()); assert!(plain.code.is_none() && observer.code.is_none());
    assert_eq!(plain.bytes+observer.bytes,0);
    let file = std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("MEMORY_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","functions":output,"code_bytes":bytes.len(),
        "code_sha256":mapping["code_sha256"],"exact_full_function_reconstruction":true,
        "observer_words_unchanged":true,"complete_small_memory_partition":true,
        "schema_version":schema,"scalar_bodies_reconstructed":scalar_ids.len(),
        "guest_commands":0,"executable_code_publications":0})).unwrap();
}

#[test]
fn memory_parts_preserve_scalar_call_targets_without_publishing_code() {
    let mut p=program(vec![Op::Local{dst:0,offset:16},Op::Local{dst:1,offset:32},
        Op::Call{function:1,args:vec![0],destination:1},Op::Load{dst:2,address:1,size:8},Op::Return]);
    p.functions.push(Function{name:"scalar memory observer".into(),frame_size:24,frame_align:8,
        registers:2,args:vec![crate::Slot{offset:16,size:8}],result:crate::Slot{offset:0,size:8},
        code:vec![Op::Local{dst:0,offset:16},Op::Load{dst:1,address:0,size:8},
            Op::Local{dst:0,offset:0},Op::Store{address:0,src:1,size:8},Op::Return]});
    crate::validate(&p).unwrap();
    let mut work=crate::proof::MAX_GLOBAL_WORK;
    let memory=crate::proof::memory_plan(&p,1,&mut work);
    let plan=crate::scalar_ir::lower(&p.functions[1],&memory,250_000).unwrap();
    let leaf=crate::scalar_ir::native_leaf::emit_call(&plan,false).unwrap();
    for base in [0x10000000,0x123456789000] {
        let mut plain=Jit::new_resumable(&p,false,MAX_CODE_BYTES,true).unwrap();
        let mut observer=Jit::new_resumable(&p,false,MAX_CODE_BYTES,true).unwrap();
        plain.enable_scalar_calls();observer.enable_scalar_calls();observer.observe_memory_parts=true;
        for jit in [&mut plain,&mut observer] {
            assert_eq!(jit.observe_saved_scalar_entry(1,64,leaf.words.len()*4,base),leaf.words);
            assert_eq!(jit.reconstruct_scalar(1).unwrap(),leaf.words);
        }
        let f=&p.functions[0];
        let mut cm=Collector{rows:vec![],limit:MAX_SPANS};
        let a=plain.emit_function_inner(f,MAX_CODE_BYTES/4,0,Some(&mut cm)).unwrap().unwrap();
        let mut om=Collector{rows:vec![],limit:MAX_SPANS};
        let b=observer.emit_function_inner(f,MAX_CODE_BYTES/4,0,Some(&mut om)).unwrap().unwrap();
        assert_eq!(a.words,b.words);assert_eq!(a.resumes,b.resumes);assert_eq!(a.assertions,b.assertions);
        assert!(a.words.contains(&0xd63f0200),"private scalar branch is present");
        cm.validate(f,&a).unwrap();om.validate(f,&b).unwrap();partition(f,&b,&cm.rows);
        assert_eq!(serde_json::to_value(&cm.rows).unwrap(),serde_json::to_value(&om.rows).unwrap());
        assert!(plain.code.is_none() && observer.code.is_none());assert_eq!(plain.bytes+observer.bytes,0);
    }
}
