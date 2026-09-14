use super::*;
use crate::{Function,Slot,Op,Engine,VERSION,execute_profiled};
fn local(dst:Reg,offset:usize)->Op {Op::Local{dst,offset}}
fn load(dst:Reg,address:Reg,size:u8)->Op {Op::Load{dst,address,size}}
fn fixture(code:Vec<Op>)->Program {
    let parent=Function{name:"transaction parent".into(),frame_size:48,frame_align:8,registers:8,
        args:vec![Slot{offset:0,size:8},Slot{offset:8,size:8}],result:Slot{offset:16,size:16},
        code:vec![local(0,0),local(1,8),local(2,16),Op::Call{function:1,args:vec![0,1],destination:2},Op::Return]};
    let leaf=Function{name:"transaction leaf".into(),frame_size:32,frame_align:8,registers:12,
        args:vec![Slot{offset:16,size:8},Slot{offset:24,size:8}],result:Slot{offset:0,size:16},code};
    Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,functions:vec![parent,leaf],
        data:vec![0x57;32],statics:(0..96).map(|i|(i*37+19) as u8).collect(),thread_locals:vec![]}
}
fn prefix()->Vec<Op> {vec![local(0,16),load(1,0,8),local(2,24),load(3,2,8),Op::Imm{dst:4,value:0xfedcba98765432100123456789abcdef}]}
fn counts(profile:&ExecutionProfile)->Vec<Vec<u64>> {
    profile.functions.iter().map(|f|{
        let mut counts=f.interpreted.clone();
        for (pc,hits) in f.jit_blocks.iter().enumerate() {if *hits!=0 {for n in &mut counts[pc..f.jit_block_ends[pc]] {*n+=hits;}}}
        counts
    }).collect()
}
struct SnapshotGuard;
impl SnapshotGuard {fn new()->Self {SNAPSHOT_ENABLED.with(|s|assert!(!s.replace(true)));SNAPSHOT.with(|s|*s.borrow_mut()=None);Self}}
impl Drop for SnapshotGuard {fn drop(&mut self) {SNAPSHOT_ENABLED.with(|s|s.set(false));}}
fn compare(p:&Program,args:&[u128],budget:u64,memory:usize,frames:usize)->Statistics {
    let options=||Limits{instructions:budget,memory,frames,..Limits::default()};
    let snapshots=SnapshotGuard::new();let reference=execute_profiled(p,args,options(),Engine::Interpreter);
    let expected=SNAPSHOT.with(|s|s.borrow_mut().take());
    let enabled=Enabled::transaction();let actual=execute_profiled(p,args,options(),Engine::Interpreter);
    let observed=SNAPSHOT.with(|s|s.borrow_mut().take());let stats=STATISTICS.with(Cell::get);drop(enabled);drop(snapshots);
    assert_eq!(expected,observed,"complete active linear/heap memory differs, including error exit");
    match (reference,actual) {
        (Ok((a,ap)),Ok((b,bp)))=>{
            assert_eq!((a.value,a.instructions,a.peak_memory),(b.value,b.instructions,b.peak_memory));assert_eq!(counts(&ap),counts(&bp));
            assert_eq!(b.jit_entries as usize,stats.commits);
        },
        (Err(a),Err(b))=>assert_eq!(a,b),
        (a,b)=>panic!("reference {a:?}, private store model {b:?}"),
    }
    stats
}
#[test]
fn private_stores_overlap_forward_bytes_and_preserve_every_budget() {
    let tag=crate::heap::TAG as u128;
    for size in 1..=16 {for overlap in 0..=16 {
        let mut code=prefix();code.extend([Op::Store{address:1,src:4,size},Op::Imm{dst:4,value:u128::MAX},
            Op::Store{address:3,src:4,size},load(5,1,16),local(6,0),Op::Store{address:6,src:5,size:16},Op::Return]);
        let p=fixture(code);let args=[tag+16,tag+16+overlap];
        assert_eq!(compare(&p,&args,100,65536,8).commits,1);
        for budget in 0..=p.functions[1].code.len() as u64+7 {compare(&p,&args,budget,65536,8);}
    }}
}
#[test]
fn private_copy_fill_read_before_write_and_chained_pointer_updates_match() {
    let tag=crate::heap::TAG as u128;
    for size in [0,1,2,4,8,16] {
        let mut code=prefix();code.extend([load(5,1,16),Op::Copy{src:1,dst:3,size},Op::Imm{dst:7,value:size as u128},
            Op::FillBytes{address:1,value:4,size:7},local(6,0),Op::Store{address:6,src:5,size:16},Op::Return]);
        let p=fixture(code);assert_eq!(compare(&p,&[tag+16,tag+20],100,65536,8).commits,1);
    }
    let mut code=prefix();code.extend([Op::Store{address:1,src:3,size:8},load(5,1,8),Op::Store{address:5,src:4,size:8},
        load(5,3,8),local(6,0),Op::Store{address:6,src:5,size:8},Op::Return]);
    let p=fixture(code);assert_eq!(compare(&p,&[tag+16,tag+40],100,65536,8).commits,1);
}
#[test]
fn private_faults_after_stores_replay_all_original_memory_effects() {
    let tag=crate::heap::TAG as u128;
    for fail in [Op::Trap{message:"after store".into()},Op::Assert{value:4,expected:false,message:"after store".into()},
        load(5,3,8),Op::Binary{dst:5,overflow:6,op:crate::Binary::Div,a:4,b:0,bits:64,signed:false}] {
        let mut code=prefix();code.extend([Op::Store{address:1,src:4,size:8},Op::Imm{dst:0,value:0},fail,Op::Return]);
        let p=fixture(code);
        for budget in 0..=20 {compare(&p,&[tag+16,0],budget,65536,8);}
    }
}
#[test]
fn private_bounds_readonly_fresh_frames_high_bits_and_resource_tails_match() {
    let tag=crate::heap::TAG as u128;let mut code=prefix();
    code.extend([Op::Store{address:1,src:4,size:8},load(5,3,8),local(6,0),Op::Store{address:6,src:5,size:8},Op::Return]);
    let p=fixture(code);
    for pointer in [0,1,31,32,40,72,79,80,88,tag,tag+1,tag+88,tag+95,u64::MAX as u128] {
        compare(&p,&[pointer,pointer],100,65536,8);
    }
    for memory in [0,32,79,80,128,256,511,512,1024,65536] {for frames in 0..=3 {
        compare(&p,&[tag+16,tag+16],100,memory,frames);
    }}
    let mut p=p;p.functions[1].code[1]=Op::Imm{dst:1,value:(1u128<<100)|(tag+16)};
    assert_eq!(compare(&p,&[0,tag+16],100,65536,8).commits,1);
}
#[test]
fn private_store_limit_declines_whole_call_and_keeps_effects() {
    let tag=crate::heap::TAG as u128;
    for count in [16,17] {
        let mut code=prefix();code.extend((0..count).map(|_|Op::Store{address:1,src:4,size:8}));code.push(Op::Return);
        let p=fixture(code);let stats=compare(&p,&[tag+16,tag+16],100,65536,8);
        assert_eq!(stats.commits,usize::from(count==16));
    }
}

#[test]
fn private_branch_effect_order_and_nonidempotent_fault_replay_match() {
    let tag=crate::heap::TAG as u128;let mut code=prefix();
    code.extend([load(5,1,8),Op::Imm{dst:7,value:1},
        Op::Binary{dst:5,overflow:8,op:crate::Binary::Add,a:5,b:7,bits:64,signed:false},
        Op::Store{address:1,src:5,size:8},Op::Switch{value:3,cases:vec![(0,12)],otherwise:10},
        Op::Store{address:3,src:4,size:8},Op::Jump{target:14},Op::Imm{dst:5,value:7},
        Op::Store{address:1,src:5,size:8},load(5,1,8),local(6,0),Op::Store{address:6,src:5,size:8},Op::Return]);
    let p=fixture(code);
    for pointer in [0,1,tag+16,tag+19,tag+40] {
        assert_eq!(compare(&p,&[tag+16,pointer],100,65536,8).commits,usize::from(pointer!=1));
        for budget in 0..=26 {compare(&p,&[tag+16,pointer],budget,65536,8);}
    }
    // An accidentally published increment would execute a second time on
    // replay. Full error-exit memory equality detects that double mutation.
    let mut p=p;p.functions[1].code[9]=Op::Trap{message:"after increment".into()};
    for budget in 0..=26 {compare(&p,&[tag+16,tag+40],budget,65536,8);}
}

#[test]
fn failed_private_store_attempt_leaves_actual_memory_and_peak_unchanged() {
    let tag=crate::heap::TAG as u128;let mut code=prefix();
    code.extend([Op::Store{address:1,src:4,size:8},load(5,1,8),
        Op::Trap{message:"discard pending store".into()}]);let p=fixture(code);
    let enabled=Enabled::transaction();let mut context=Context::new(&p,false,false).unwrap().unwrap();
    let mut memory=Memory{bytes:vec![0x57;80].into(),heap:crate::heap::Heap::default(),
        limit:65536,readonly_end:16,peak:80,auxiliary_bytes:0};
    memory.heap.bytes=vec![0x29;96];memory.store(32,8,tag+16).unwrap();memory.store(40,8,tag+40).unwrap();
    let before=(memory.bytes.to_vec(),memory.heap.bytes.clone(),memory.peak,memory.total_len());
    assert!(context.try_call(1,&[0,1],&[32,40],48,&mut memory,128,1,&Limits::default(),100,None).unwrap().is_none());
    assert_eq!((memory.bytes.to_vec(),memory.heap.bytes.clone(),memory.peak,memory.total_len()),before);
    assert_eq!(STATISTICS.with(Cell::get).declines,1);drop(enabled);
}
