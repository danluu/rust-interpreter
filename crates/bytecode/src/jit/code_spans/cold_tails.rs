//! Offline, exact relocation proof against retained adopted machine code.
use super::*;
use serde_json::{Value,json};

fn direct(word:u32,pc:usize)->Option<(u32,i64)> {
    let (mask,bits,shift)=if word&0x7c000000==0x14000000 {(0x03ffffff,26,0)}
        else if word&0xff000010==0x54000000 || word&0x7e000000==0x34000000 {(0x00ffffe0,19,5)}
        else if word&0x7e000000==0x36000000 {(0x0007ffe0,14,5)} else {return None;};
    let raw=(word&mask)>>shift;
    let signed=((raw as i32)<<(32-bits))>>(32-bits);
    Some((mask,pc as i64+signed as i64))
}

fn word_equal(before:u32,after:u32,pc:usize,new_pc:usize,relocation:&[usize])->bool {
    if let Some((mask,target))=direct(before,pc) {
        let Some((new_mask,new_target))=direct(after,new_pc) else {return false;};
        target>=0 && (target as usize)<relocation.len() && mask==new_mask
            && before&!mask==after&!mask && new_target==relocation[target as usize] as i64
    } else {
        // Never silently accept an unchanged PC-relative data displacement.
        before&0x1f000000!=0x10000000 && before&0x3b000000!=0x18000000 && before==after
    }
}

fn translation(before:&CompiledFunction<'_>,after:&CompiledFunction<'_>,old:&Collector,new:&Collector)->usize {
    assert_eq!(old.rows.len(),new.rows.len());
    assert_eq!(before.operations,after.operations);assert_eq!(before.assertions,after.assertions);
    let mut relocation=vec![usize::MAX;before.words.len()];
    let mut replaced=BTreeSet::new();
    let new_tails:BTreeMap<_,_>=new.rows.iter().filter(|s|s.kind==Kind::FaultTail && s.end-s.offset>4)
        .map(|s|(s.offset/4,s.end/4)).collect();
    for (a,b) in old.rows.iter().zip(&new.rows) {
        assert_eq!((a.kind,a.pc,a.region_pc),(b.kind,b.pc,b.region_pc));
        let (start,end,next,finish)=(a.offset/4,a.end/4,b.offset/4,b.end/4);
        if end-start==finish-next {
            for (index,at) in (start..end).enumerate() {relocation[at]=next+index;}
        } else {
            assert_eq!(a.kind,Kind::FaultTail);assert_eq!(finish-next,1);assert!(end-start>1);
            let branch=after.words[next];assert_eq!(branch&0xfc000000,0x14000000);
            let (_,target)=direct(branch,next).unwrap();assert!(target>=0 && (target as usize)<next);
            let target=target as usize;let target_end=new_tails[&target];
            assert_eq!(end-start,target_end-target);
            assert_eq!(before.words[start..end],after.words[target..target_end]);
            for (index,at) in (start..end).enumerate() {relocation[at]=target+index;}
            // Original fault edges still enter the replacement local branch.
            relocation[start]=next;
            replaced.insert(start);
        }
    }
    assert!(!relocation.contains(&usize::MAX));
    for (a,b) in old.rows.iter().zip(&new.rows) {
        if replaced.contains(&(a.offset/4)) {continue;}
        for (pc,new_pc) in (a.offset/4..a.end/4).zip(b.offset/4..b.end/4) {
            assert!(word_equal(before.words[pc],after.words[new_pc],pc,new_pc,&relocation),
                "changed non-tail instruction or target at old word {pc}, new {new_pc}");
        }
    }
    assert_eq!(before.entries.len(),after.entries.len());
    for (a,b) in before.entries.iter().zip(&after.entries) {
        match (a,b) {
            (Some(a),Some(b))=>{assert_eq!(a.end,b.end);assert_eq!(relocation[a.offset/4]*4,b.offset);},
            (None,None)=>{},_=>panic!("native entry set changed"),
        }
    }
    assert_eq!(before.resumes.len(),after.resumes.len());
    for (a,b) in before.resumes.iter().zip(&after.resumes) {assert_eq!(a.map(|at|relocation[at]),*b);}
    replaced.len()
}

#[test]
fn cold_tail_relocation_rejects_payload_target_condition_and_relative_data_changes() {
    let map=[0,1,2,3];
    assert!(word_equal(0xf9400069,0xf9400069,0,0,&map));
    assert!(!word_equal(0xf9400069,0xf940006a,0,0,&map));
    assert!(word_equal(0x14000002,0x14000002,0,0,&map));
    assert!(!word_equal(0x14000002,0x14000001,0,0,&map));
    assert!(!word_equal(0x54000040,0x54000041,0,0,&map));
    assert!(!word_equal(0x10000000,0x10000000,0,0,&map));
    assert!(!word_equal(0x58000000,0x58000000,0,0,&map));
    assert!(!word_equal(0x17ffffff,0x17ffffff,0,0,&map));
}

#[test]
fn cold_tail_relocation_checks_forward_backward_and_test_branch_forms() {
    let map=[0,1,2,3,5,6];
    // Changing the layout before this source changes a backwards displacement.
    assert!(word_equal(0x17fffffe,0x17fffffd,4,5,&map));
    assert!(word_equal(0x54000080,0x540000a0,0,0,&map));
    assert!(word_equal(0xb4000080,0xb40000a0,0,0,&map));
    assert!(word_equal(0x36000080,0x360000a0,0,0,&map));
    assert!(!word_equal(0x14000001,0x94000001,0,0,&map));
}

fn number(v:&Value,key:&str)->usize {usize::try_from(v[key].as_u64().unwrap()).unwrap()}

#[test]
#[ignore="Requires exact closed adopted native capture and original artifact"]
fn observe_saved_cold_tails() {
    let artifact=std::fs::read(std::env::var("TAIL_ARTIFACT").unwrap()).unwrap();assert!(artifact.len()<=128*1024*1024);
    let program:Program=bincode::deserialize(&artifact).unwrap();crate::validate(&program).unwrap();
    let mapping=std::fs::read(std::env::var("TAIL_MAP").unwrap()).unwrap();assert!(mapping.len()<=MAX_OUTPUT_BYTES);
    let mapping:Value=serde_json::from_slice(&mapping).unwrap();
    let bytes=std::fs::read(std::env::var("TAIL_CODE").unwrap()).unwrap();assert!(bytes.len()<=MAX_CODE_BYTES);
    assert_eq!(mapping["schema_version"],2);assert_eq!(mapping["profiled"],false);
    for flag in ["persistent_registers","resumable_calls","complete","reconstructed_bytes_match"] {assert_eq!(mapping[flag],true);}
    assert_eq!(mapping["code_bytes"],bytes.len());assert_eq!(mapping["code_sha256"],format!("{:x}",Sha256::digest(&bytes)));
    let mut baseline=Jit::new_resumable(&program,false,MAX_CODE_BYTES,true).unwrap();baseline.share_fault_tails=false;
    let mut candidate=Jit::new_resumable(&program,false,MAX_CODE_BYTES,true).unwrap();
    baseline.enable_scalar_calls();candidate.enable_scalar_calls();
    let mut scalar_ids=BTreeSet::new();
    for row in mapping["functions"].as_array().unwrap() {
        if row["spans"][0]["kind"]!="scalar_leaf" {continue;}
        let id=number(row,"function");assert!(scalar_ids.insert(id));
        let (start,end)=(number(row,"offset"),number(row,"end"));assert!(start<end && end<=bytes.len());
        for jit in [&mut baseline,&mut candidate] {
            let words=jit.observe_saved_scalar_entry(id,start,end-start,number(&mapping,"arena_base"));
            verify_words(&words,&bytes[start..end]).unwrap();
        }
    }
    let (mut cursor,mut assertions,mut saved,mut duplicates)=(0,0,0,0);
    let mut seen=BTreeSet::new();let mut rows=vec![];
    for row in mapping["functions"].as_array().unwrap() {
        let id=number(row,"function");let f=&program.functions[id];assert_eq!(row["name"],f.name);
        let (start,end)=(number(row,"offset"),number(row,"end"));assert_eq!(start,cursor);assert!(start<end && end<=bytes.len());
        assert_eq!(number(row,"assertion_base"),assertions);cursor=end;
        if row["spans"][0]["kind"]=="scalar_leaf" {assert!(scalar_ids.contains(&id));assert_eq!(row["assertion_count"],0);continue;}
        assert!(seen.insert(id));
        let mut old=Collector{rows:vec![],limit:MAX_SPANS};let mut new=Collector{rows:vec![],limit:MAX_SPANS};
        let a=baseline.emit_function_inner(f,(end-start)/4,assertions,Some(&mut old)).unwrap().unwrap();
        let b=candidate.emit_function_inner(f,(end-start)/4,assertions,Some(&mut new)).unwrap().unwrap();
        verify_words(&a.words,&bytes[start..end]).unwrap();old.validate(f,&a).unwrap();new.validate(f,&b).unwrap();
        let count=translation(&a,&b,&old,&new);
        assert_eq!(a.assertions.len(),number(row,"assertion_count"));assertions+=a.assertions.len();
        for span in &mut old.rows {span.offset+=start;span.end+=start;}
        assert_eq!(serde_json::to_value(&old.rows).unwrap(),row["spans"]);
        let removed=(a.words.len()-b.words.len())*4;saved+=removed;duplicates+=count;
        rows.push(json!({"function":id,"original_bytes":a.words.len()*4,"candidate_bytes":b.words.len()*4,
            "shared_tails":count,"saved_bytes":removed}));
    }
    assert_eq!(cursor,bytes.len());assert!(baseline.code.is_none() && candidate.code.is_none());
    assert_eq!(baseline.bytes+candidate.bytes,0);
    let output=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("TAIL_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(output,&json!({"status":"passed","code_sha256":mapping["code_sha256"],
        "original_bytes":bytes.len(),"saved_bytes":saved,"shared_tails":duplicates,
        "ordinary_functions":seen.len(),"scalar_bodies":scalar_ids.len(),"functions":rows,
        "exact_adopted_reconstruction":true,"only_fault_tail_and_required_branch_displacements_change":true,
        "entries_resumes_assertions_and_operations_preserved":true,"guest_commands":0,"executable_code_publications":0})).unwrap();
}
