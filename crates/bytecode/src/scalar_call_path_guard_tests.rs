use super::*;
use crate::{Op,Engine,execute_profiled};
use super::transaction_tests::{fixture,prefix,local,load,SnapshotGuard};
fn counts(profile:&ExecutionProfile)->Vec<Vec<u64>> {
    profile.functions.iter().map(|f|{let mut result=f.interpreted.clone();
        for (pc,hits) in f.jit_blocks.iter().enumerate() {if *hits!=0 {for n in &mut result[pc..f.jit_block_ends[pc]] {*n+=hits;}}}result}).collect()
}
fn compare(p:&Program,args:&[u128],budget:u64,memory:usize,frames:usize)->Statistics {
    let options=||Limits{instructions:budget,memory,frames,..Limits::default()};
    let snapshots=SnapshotGuard::new();let reference=execute_profiled(p,args,options(),Engine::Interpreter);
    let expected=SNAPSHOT.with(|s|s.borrow_mut().take());
    let enabled=Enabled::path_guards();let actual=execute_profiled(p,args,options(),Engine::Interpreter);
    let observed=SNAPSHOT.with(|s|s.borrow_mut().take());let stats=STATISTICS.with(Cell::get);drop(enabled);drop(snapshots);
    assert_eq!(expected,observed,"complete memory differs, including error exit");
    match (reference,actual) {
        (Ok((a,ap)),Ok((b,bp)))=>{assert_eq!((a.value,a.instructions,a.peak_memory),(b.value,b.instructions,b.peak_memory));
            assert_eq!(counts(&ap),counts(&bp));assert_eq!(b.jit_entries as usize,stats.commits);},
        (Err(a),Err(b))=>assert_eq!(a,b),
        (a,b)=>panic!("ordinary {a:?}, guarded direct {b:?}"),
    }stats
}
fn budgets(p:&Program,args:&[u128]) {for budget in 0..=p.functions[1].code.len() as u64+7 {compare(p,args,budget,65536,8);}}
#[test]
fn path_direct_widths_and_overlapping_payload_reads_preserve_every_budget() {
    let tag=crate::heap::TAG as u128;
    for size in 1..=16 {for overlap in 0..=16 {
        let mut code=prefix();code.extend([Op::Store{address:1,src:4,size},Op::Imm{dst:4,value:u128::MAX},
            Op::Store{address:3,src:4,size},load(5,1,16),local(6,0),Op::Store{address:6,src:5,size:16},Op::Return]);
        let p=fixture(code);let args=[tag+16,tag+16+overlap];assert_eq!(compare(&p,&args,100,65536,8).commits,1);budgets(&p,&args);
    }}
}
#[test]
fn late_assertions_certify_before_nonidempotent_updates_or_replay_once() {
    let tag=crate::heap::TAG as u128;let mut code=prefix();
    code.extend([load(5,1,8),Op::Imm{dst:7,value:1},
        Op::Binary{dst:5,overflow:8,op:crate::Binary::Add,a:5,b:7,bits:64,signed:false},
        Op::Store{address:1,src:5,size:8},Op::Assert{value:3,expected:true,message:"late condition".into()},
        local(6,0),Op::Store{address:6,src:5,size:8},Op::Return]);let p=fixture(code);
    for condition in [0,1] {assert_eq!(compare(&p,&[tag+16,condition],100,65536,8).commits,condition as usize);budgets(&p,&[tag+16,condition]);}
}
#[test]
fn temporal_alias_guard_rejects_changed_pointer_before_any_effect() {
    let tag=crate::heap::TAG as u128;let mut code=prefix();code[4]=Op::Imm{dst:4,value:tag+80};
    code.extend([Op::Store{address:3,src:4,size:8},load(5,1,8),Op::Store{address:5,src:4,size:8},Op::Return]);
    let mut p=fixture(code);p.statics[16..24].copy_from_slice(&((tag+64) as u64).to_le_bytes());
    for pointer in [tag+16,tag+48] {let args=[tag+16,pointer];
        assert_eq!(compare(&p,&args,100,65536,8).commits,usize::from(pointer==tag+48));budgets(&p,&args);
    }
    let proof=crate::proof::memory_plan_transaction(&p,1,&mut crate::proof::MAX_GLOBAL_WORK.clone());
    let plan=scalar_ir::lower(&p.functions[1],&proof,250_000).unwrap();
    let memory=Memory{bytes:vec![0;80].into(),heap:crate::heap::Heap::with_statics(&p.statics,128),
        limit:65536,readonly_end:32,peak:176,auxiliary_bytes:0};
    assert_eq!(plan.check_path_entry(&[tag+16,tag+16],80,&memory).unwrap_err(),"path read follows overlapping write");
}
#[test]
fn path_phis_and_full_width_switches_follow_the_selected_edge() {
    let tag=crate::heap::TAG as u128;let mut code=prefix();code[3]=load(3,2,16);
    code.extend([Op::Switch{value:3,cases:vec![(1u128<<100,8)],otherwise:6},Op::Imm{dst:5,value:0x1111},Op::Jump{target:9},
        Op::Imm{dst:5,value:0x2222},Op::Store{address:1,src:5,size:8},
        Op::Assert{value:5,expected:true,message:"phi condition".into()},local(6,0),Op::Store{address:6,src:5,size:8},Op::Return]);
    let mut p=fixture(code);p.functions[0].args[1].size=16;p.functions[1].args[1].size=16;p.functions[1].frame_size=48;
    for condition in [0,1,1u128<<100,(1u128<<100)|1] {let args=[tag+16,condition];
        assert_eq!(compare(&p,&args,100,65536,8).commits,1);budgets(&p,&args);
    }
}
#[test]
fn late_division_remainder_and_trap_paths_keep_original_faults() {
    let tag=crate::heap::TAG as u128;
    for op in [crate::Binary::Div,crate::Binary::Rem] {for signed in [false,true] {
        let mut code=prefix();code[4]=Op::Imm{dst:4,value:1u128<<63};
        code.extend([Op::Store{address:1,src:4,size:8},Op::Binary{dst:5,overflow:7,op,a:4,b:3,bits:64,signed},
            local(6,0),Op::Store{address:6,src:5,size:8},Op::Return]);let p=fixture(code);
        for divisor in [0,1,u64::MAX as u128] {let args=[tag+16,divisor];
            assert_eq!(compare(&p,&args,100,65536,8).commits,usize::from(divisor!=0 && !(signed && divisor==u64::MAX as u128)));budgets(&p,&args);
        }
    }}
    let mut code=prefix();code.extend([Op::Store{address:1,src:4,size:8},
        Op::Switch{value:3,cases:vec![(0,8)],otherwise:7},Op::Return,Op::Trap{message:"late trap".into()}]);let p=fixture(code);
    for condition in [0,1] {let args=[tag+16,condition];assert_eq!(compare(&p,&args,100,65536,8).commits,condition as usize);budgets(&p,&args);}
}
#[test]
fn direct_bounds_readonly_fresh_frames_and_resource_tails_match() {
    let tag=crate::heap::TAG as u128;let mut code=prefix();
    code.extend([Op::Store{address:1,src:4,size:8},load(5,3,8),local(6,0),Op::Store{address:6,src:5,size:8},Op::Return]);let p=fixture(code);
    for pointer in [0,1,31,32,40,72,79,80,88,tag,tag+1,tag+88,tag+95,u64::MAX as u128] {budgets(&p,&[pointer,pointer]);}
    for memory in [0,32,79,80,128,256,511,512,1024,65536] {for frames in 0..=3 {compare(&p,&[tag+16,tag+16],100,memory,frames);}}
    let mut p=p;p.functions[1].code[1]=Op::Imm{dst:1,value:(1u128<<100)|(tag+16)};
    assert_eq!(compare(&p,&[0,tag+16],100,65536,8).commits,1);
}
#[test]
fn captured_inputs_result_aliases_and_retained_padding_match() {
    let tag=crate::heap::TAG as u128;let mut code=prefix();
    code.extend([Op::Store{address:1,src:4,size:8},load(5,0,8),Op::Store{address:3,src:5,size:8},
        local(6,0),Op::Store{address:6,src:5,size:8},Op::Return]);let mut p=fixture(code);p.functions[1].frame_align=64;
    for pointer in [32,40,48,64,tag+16] {let args=[pointer,tag+48];assert_eq!(compare(&p,&args,100,65536,8).commits,1);budgets(&p,&args);}
}
#[test]
fn failed_path_guard_leaves_active_memory_and_peak_unchanged() {
    let tag=crate::heap::TAG as u128;let mut code=prefix();
    code.extend([Op::Store{address:1,src:4,size:8},Op::Trap{message:"after store".into()}]);let p=fixture(code);
    let enabled=Enabled::path_guards();let mut context=Context::new(&p,false,false).unwrap().unwrap();
    let mut memory=Memory{bytes:vec![0x57;80].into(),heap:crate::heap::Heap::with_statics(&p.statics,128),
        limit:65536,readonly_end:16,peak:176,auxiliary_bytes:0};memory.store(32,8,tag+16).unwrap();memory.store(40,8,tag+40).unwrap();
    let before=(memory.bytes.to_vec(),memory.heap.bytes.clone(),memory.peak,memory.total_len());
    assert!(context.try_call(1,&[0,1],&[32,40],48,&mut memory,128,1,&Limits::default(),100,None).unwrap().is_none());
    assert_eq!((memory.bytes.to_vec(),memory.heap.bytes.clone(),memory.peak,memory.total_len()),before);
    assert_eq!(STATISTICS.with(Cell::get).declines,1);drop(enabled);
}
#[test]
fn bounded_store_admission_keeps_the_original_fallback() {
    let tag=crate::heap::TAG as u128;
    for count in [16,17] {let mut code=prefix();code.extend((0..count).map(|_|Op::Store{address:1,src:4,size:8}));code.push(Op::Return);
        let p=fixture(code);let args=[tag+16,tag+40];assert_eq!(compare(&p,&args,100,65536,8).commits,usize::from(count==16));budgets(&p,&args);}
}

#[test]
fn certified_wide_values_are_reused_while_payload_reads_keep_effect_order() {
    let tag=crate::heap::TAG as u128;let pointer=(1u128<<100)|(tag+64);
    let mut code=prefix();code.extend([load(5,1,16),Op::Store{address:5,src:4,size:8},load(7,5,8),
        local(6,0),Op::Store{address:6,src:5,size:16},Op::Return]);
    let mut p=fixture(code);p.statics[16..32].copy_from_slice(&pointer.to_le_bytes());
    let args=[tag+16,0];assert_eq!(compare(&p,&args,100,65536,8).commits,1);budgets(&p,&args);
    let memory=Memory{bytes:vec![0;80].into(),heap:crate::heap::Heap::with_statics(&p.statics,128),
        limit:65536,readonly_end:32,peak:176,auxiliary_bytes:0};
    let proof=crate::proof::memory_plan_transaction(&p,1,&mut crate::proof::MAX_GLOBAL_WORK.clone());
    let plan=scalar_ir::lower(&p.functions[1],&proof,250_000).unwrap();let certificate=plan.check_path_entry(&args,80,&memory).unwrap();
    let shadow=RefCell::new(memory);let reads=RefCell::new(vec![]);
    let outcome=plan.evaluate_path_effects(&certificate,&args,80,100,&p.functions[1].name,
        &mut |a,n|{reads.borrow_mut().push(a as usize);shadow.borrow().load(a as usize,n as usize)},
        &mut |a,v,n|shadow.borrow_mut().store(a as usize,n as usize,v)).unwrap();
    assert_eq!(outcome.pcs,certificate.pcs);assert_eq!(outcome.value,pointer);
    assert_eq!(*reads.borrow(),[(tag+64) as usize],"only the post-store payload read may execute again");
}
