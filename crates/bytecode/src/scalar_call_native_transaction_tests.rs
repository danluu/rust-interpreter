use super::*;
use super::transaction_tests::{fixture,prefix,local,load,SnapshotGuard};
use crate::{Op,Engine,execute_profiled};

fn counts(profile:&ExecutionProfile)->Vec<Vec<u64>> {
    profile.functions.iter().map(|f| {
        let mut counts=f.interpreted.clone();for (n,h) in counts.iter_mut().zip(&f.jit_scalar_hits) {*n+=h;}
        for (pc,h) in f.jit_blocks.iter().enumerate() {if *h!=0 {for n in &mut counts[pc..f.jit_block_ends[pc]] {*n+=h;}}}counts
    }).collect()
}
fn compare(p:&Program,args:&[u128],budget:u64,memory:usize,frames:usize)->usize {
    let options=||Limits{instructions:budget,memory,frames,..Limits::default()};
    let snapshots=SnapshotGuard::new();let reference=execute_profiled(p,args,options(),Engine::Interpreter);
    let expected=SNAPSHOT.with(|s|s.borrow_mut().take());let mut commits=0;
    for persistent in [false,true] {
        let mut limits=options();limits.jit_resumable_calls=true;limits.jit_scalar_calls=true;limits.jit_persistent_registers=persistent;
        let mut baseline_limits=limits.clone();baseline_limits.jit_scalar_calls=false;
        let baseline=execute_profiled(p,args,baseline_limits,Engine::Jit);SNAPSHOT.with(|s|s.borrow_mut().take());
        let native=NativeEnabled::new();let actual=execute_profiled(p,args,limits,Engine::Jit);drop(native);
        let observed=SNAPSHOT.with(|s|s.borrow_mut().take());
        assert_eq!(expected,observed,"native store transaction active memory differs, budget {budget}");
        match (&reference,actual) {
            (Ok((a,ap)),Ok((b,bp)))=>{
                assert_eq!((a.value,a.instructions,a.peak_memory),(b.value,b.instructions,b.peak_memory));assert_eq!(counts(ap),counts(&bp));
                commits=bp.functions.iter().zip(&p.functions).map(|(p,f)|p.jit_scalar_hits.iter().zip(&f.code)
                    .filter(|(_,op)|matches!(op,Op::Return)).map(|(hits,_)|*hits as usize).sum::<usize>()).sum();
            },
            (Err(a),Err(b))=>{
                assert_eq!(baseline.unwrap_err(),b);
                assert!(*a==b || (b=="JIT guest memory access failed"
                    && matches!(a.as_str(),"invalid guest memory access"|"write to read-only guest memory")),"interpreter {a}, JIT {b}");
            },(a,b)=>panic!("reference {a:?}, native stores {b:?}"),
        }
    }
    drop(snapshots);commits
}
#[test]
fn native_private_widths_runtime_aliases_and_every_budget_match() {
    let tag=crate::heap::TAG as u128;
    for size in 1..=16 {for overlap in 0..=16 {
        let mut code=prefix();code.extend([Op::Store{address:1,src:4,size},Op::Imm{dst:4,value:u128::MAX},
            Op::Store{address:3,src:4,size},load(5,1,size),local(6,0),Op::Store{address:6,src:5,size},Op::Return]);
        let p=fixture(code);let args=[tag+16,tag+16+overlap];
        assert_eq!(compare(&p,&args,100,65536,8),usize::from(overlap==0 || overlap>=size as u128));
        for budget in 0..=p.functions[1].code.len() as u64+7 {compare(&p,&args,budget,65536,8);}
    }}
}
#[test]
fn native_private_contained_reads_and_static_partial_aliases_match() {
    let tag=crate::heap::TAG as u128;
    for written in [1,2,3,4,7,8,9,15,16] {for read in 1..=written {for offset in [0,written-read] {
        let mut code=prefix();code.extend([Op::Store{address:1,src:4,size:written},Op::Imm{dst:7,value:offset as u128},
            Op::Binary{dst:9,overflow:8,op:crate::Binary::Add,a:1,b:7,bits:64,signed:false},load(5,9,read),
            local(6,0),Op::Store{address:6,src:5,size:read},Op::Return]);
        assert_eq!(compare(&fixture(code),&[tag+16,0],100,65536,8),1);
    }}}
    let mut code=prefix();code.extend([Op::Store{address:1,src:4,size:8},load(5,1,16),local(6,0),Op::Store{address:6,src:5,size:16},Op::Return]);
    assert_eq!(compare(&fixture(code),&[tag+16,0],100,65536,8),0);
}
#[test]
fn native_private_branch_order_and_nonidempotent_faults_match() {
    let tag=crate::heap::TAG as u128;let mut code=prefix();
    code.extend([load(5,1,8),Op::Imm{dst:7,value:1},
        Op::Binary{dst:5,overflow:8,op:crate::Binary::Add,a:5,b:7,bits:64,signed:false},
        Op::Store{address:1,src:5,size:8},Op::Switch{value:3,cases:vec![(0,12)],otherwise:10},
        Op::Store{address:3,src:4,size:8},Op::Jump{target:14},Op::Imm{dst:5,value:7},
        Op::Store{address:1,src:5,size:8},load(5,1,8),local(6,0),Op::Store{address:6,src:5,size:8},Op::Return]);
    let p=fixture(code);
    for pointer in [0,1,tag+16,tag+19,tag+40] {
        let commits=compare(&p,&[tag+16,pointer],100,65536,8);
        assert_eq!(commits,usize::from(pointer!=1 && pointer!=tag+19));
        for budget in 0..=26 {compare(&p,&[tag+16,pointer],budget,65536,8);}
    }
    for fail in [Op::Trap{message:"after increment".into()},Op::Assert{value:4,expected:false,message:"after increment".into()},
        load(5,3,8),Op::Binary{dst:5,overflow:8,op:crate::Binary::Div,a:5,b:3,bits:64,signed:false}] {
        let mut p=p.clone();p.functions[1].code[9]=fail;
        for budget in 0..=26 {compare(&p,&[tag+16,0],budget,65536,8);}
    }
}
#[test]
fn native_private_bounds_fresh_frames_heap_free_high_bits_and_resources_match() {
    let tag=crate::heap::TAG as u128;let mut code=prefix();
    code.extend([Op::Store{address:1,src:4,size:8},load(5,1,8),local(6,0),Op::Store{address:6,src:5,size:8},Op::Return]);
    let p=fixture(code);
    for heap in [false,true] {
        let mut p=p.clone();if !heap {p.statics.clear();}
        p.functions[0].frame_size=49;p.functions[1].frame_align=64;
        for pointer in [0,1,31,32,40,72,79,80,81,88,120,127,128,144,tag,tag+1,tag+88,tag+95,u64::MAX as u128] {
            compare(&p,&[pointer,0],100,65536,8);
        }
    }
    for memory in [0,32,79,80,128,256,511,512,1024,65536] {for frames in 0..=3 {
        compare(&p,&[tag+16,0],100,memory,frames);
    }}
    let mut p=p;p.functions[1].code[1]=Op::Imm{dst:1,value:(1u128<<100)|(tag+16)};
    assert_eq!(compare(&p,&[0,0],100,65536,8),1);
}
#[test]
fn native_private_copy_fill_and_chained_pointer_forwarding_match() {
    let tag=crate::heap::TAG as u128;
    for size in [0,1,2,4,8,16] {
        let mut code=prefix();code.extend([load(5,1,16),Op::Copy{src:1,dst:3,size},Op::Imm{dst:7,value:size as u128},
            Op::FillBytes{address:1,value:4,size:7},local(6,0),Op::Store{address:6,src:5,size:16},Op::Return]);
        assert_eq!(compare(&fixture(code),&[tag+16,tag+20],100,65536,8),1);
    }
    let mut code=prefix();code.extend([Op::Store{address:1,src:3,size:8},load(5,1,8),Op::Store{address:5,src:4,size:8},
        load(5,3,8),local(6,0),Op::Store{address:6,src:5,size:8},Op::Return]);
    assert_eq!(compare(&fixture(code),&[tag+16,tag+40],100,65536,8),1);
}
#[test]
fn native_private_preserves_live_values_and_result_alias_commit_order() {
    let tag=crate::heap::TAG as u128;let mut code=prefix();
    for i in 0..12 {
        code.extend([load(12+i,1,8),Op::Imm{dst:30,value:i as u128+1},
            Op::Binary{dst:12+i,overflow:31,op:crate::Binary::Mul,a:12+i,b:30,bits:64,signed:false},
            Op::Store{address:1,src:12+i,size:8}]);
    }
    code.push(Op::Imm{dst:32,value:0});
    for i in [3,9,0,8,2,11,1,7,4,10,5,6] {
        code.push(Op::Binary{dst:32,overflow:31,op:crate::Binary::Xor,a:32,b:12+i,bits:64,signed:false});
    }
    code.extend([local(6,0),Op::Store{address:6,src:32,size:8},Op::Return]);
    let mut p=fixture(code);p.functions[1].registers=64;
    assert_eq!(compare(&p,&[tag+16,0],200,65536,8),1);
    // The Call result overwrites the external mutation only after successful
    // native Return. The parent then reads that aliased destination.
    p.functions[0].code=vec![local(0,0),local(1,8),load(3,0,8),
        Op::Call{function:1,args:vec![0,1],destination:3},load(4,3,8),local(2,16),Op::Store{address:2,src:4,size:8},Op::Return];
    assert_eq!(compare(&p,&[tag+16,0],200,65536,8),1);
}
#[test]
fn native_private_store_limits_shared_arena_reconstruction_and_closed_admission() {
    let tag=crate::heap::TAG as u128;
    for stores in [1,16,17] {
        let mut code=prefix();code.extend((0..stores).map(|_|Op::Store{address:1,src:4,size:8}));code.push(Op::Return);
        let p=fixture(code);assert_eq!(compare(&p,&[tag+16,0],100,65536,8),usize::from(stores<=16));
        let mut ordinary=crate::jit::Jit::new_resumable(&p,false,16*1024*1024,true).unwrap();ordinary.enable_scalar_calls();ordinary.ensure_function(0).unwrap();
        let map=serde_json::to_value(ordinary.operation_map().unwrap()).unwrap();
        assert!(map["functions"].as_array().unwrap().iter().filter(|f|f["function"]==1).all(|f|f["spans"][0]["kind"]!="scalar_leaf"));
        for profiled in [false,true] {
            let native=NativeEnabled::new();let mut jit=crate::jit::Jit::new_resumable(&p,profiled,16*1024*1024,true).unwrap();
            jit.enable_scalar_calls();jit.ensure_function(0).unwrap();let map=serde_json::to_value(jit.operation_map().unwrap()).unwrap();
            assert_eq!(map["complete"],true);assert_eq!(map["reconstructed_bytes_match"],true);
            let present=map["functions"].as_array().unwrap().iter().any(|f|f["function"]==1 && f["spans"][0]["kind"]=="scalar_leaf");
            assert_eq!(present,stores<=16);drop(native);
        }
    }
}
