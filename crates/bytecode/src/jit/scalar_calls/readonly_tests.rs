use super::*;

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
