use super::*;

#[path = "../../tests/common/call_copy_cases.rs"]
mod call_copy_cases;

fn limits(persistent: bool) -> Limits {
    Limits { jit_resumable_calls: true, jit_tree_bridge: true,
        jit_persistent_registers: persistent, ..Limits::default() }
}
fn bounded() -> Program {
    let mut p=looping_program(false);
    p.functions[1].code=vec![Op::Local {dst:0,offset:0},Op::Load {dst:1,address:0,size:8},
        Op::Imm {dst:2,value:3},binary(1,Binary::Add,1,2),Op::Store {address:0,src:1,size:8},
        Op::Call {function:2,args:vec![0],destination:0},Op::Return];
    p.functions[1].result.offset=0;
    let mut leaf=function(vec![Op::Local {dst:0,offset:0},Op::Load {dst:1,address:0,size:8},
        Op::Imm {dst:2,value:1},binary(1,Binary::Add,1,2),Op::Store {address:0,src:1,size:8},Op::Return]);
    leaf.args=vec![Slot {offset:0,size:8}];p.functions.push(leaf);
    p
}
fn equal_faults(actual: Result<Execution,String>, expected: &Result<Execution,String>) {
    match (&actual,expected) {
        (Err(a),Err(b)) if b.contains("memory access") || b.contains("read-only") || b.contains("address overflow") => {
            assert!(a==b || a=="JIT guest memory access failed", "{a} / {b}");
        }
        _=>equal_result(actual,expected),
    }
}

#[test]
fn bounded_bridges_match_logical_profiles_and_reuse_fresh_guest_state() {
    let p=bounded();
    let (reference,reference_profile)=execute_profiled(&p,&[],Limits::default(),Engine::Interpreter).unwrap();
    assert_eq!(reference.value,8);
    for persistent in [false,true] {
        let (actual,profile)=execute_profiled(&p,&[],limits(persistent),Engine::Jit).unwrap();
        assert_eq!((actual.value,actual.instructions,actual.peak_memory),
            (reference.value,reference.instructions,reference.peak_memory));
        assert_eq!(logical(&profile),logical(&reference_profile));
        assert_eq!((actual.jit_tree_entries,actual.jit_tree_calls),(2,2));
        assert_eq!((actual.jit_resumable_calls,actual.jit_resumable_returns),(4,4));
        let mut tree_instructions=0;let mut tree_calls=0;
        for (id,f) in profile.functions.iter().enumerate() {
            for (pc,&hits) in f.jit_tree_blocks.iter().enumerate().filter(|(_,hits)|**hits>0) {
                let end=f.jit_tree_block_ends[pc];tree_instructions+=hits*(end-pc) as u64;
                tree_calls+=hits*p.functions[id].code[pc..end].iter().filter(|op|matches!(op,Op::Call {..})).count() as u64;
            }
        }
        assert_eq!(tree_instructions,actual.jit_tree_instructions);assert_eq!(tree_calls,actual.jit_tree_calls);
        let mut prepared=crate::PreparedJit::new(&p,&limits(persistent)).unwrap();
        for n in 0..3 {
            let result=prepared.execute(&[],limits(persistent)).unwrap();
            assert_eq!((result.value,result.instructions,result.peak_memory),(reference.value,reference.instructions,reference.peak_memory));
            assert_eq!((result.jit_tree_entries,result.jit_tree_calls),(2,2));
            if n>0 {assert_eq!(result.jit_compile_nanos,0);}
        }
        let mut changed=limits(persistent);changed.jit_tree_bridge=false;
        assert!(prepared.execute(&[],changed).unwrap_err().contains("options changed"));
    }
}

#[test]
fn every_instruction_and_storage_limit_keeps_the_ordinary_fallback() {
    let p=bounded();let total=crate::execute(&p,&[],Limits::default()).unwrap().instructions;
    for persistent in [false,true] {
        for budget in 0..=total+1 {for capacity in [0,512,4096,MAX_CODE_BYTES] {
            let reference=crate::execute(&p,&[],Limits {instructions:budget,..Limits::default()});
            equal_faults(execute_with_engine(&p,&[],Limits {instructions:budget,jit_code_bytes:capacity,..limits(persistent)},Engine::Jit),&reference);
        }}
        for depth in 0..=5 {for memory in [0,16,32,100,175,176,180,300,335,336,400,447,448,511,512,1024] {
            let reference=crate::execute(&p,&[],Limits {frames:depth,memory,..Limits::default()});
            equal_faults(execute_with_engine(&p,&[],Limits {frames:depth,memory,..limits(persistent)},Engine::Jit),&reference);
        }}
    }
}

#[test]
fn original_call_copy_alias_and_fault_contracts_hold_through_bridges() {
    let mut successful_bridges=0;
    for case in call_copy_cases::cases() {
        let reference=crate::execute(&case.program,&[],Limits::default());
        assert_eq!(reference.as_ref().map(|r|r.value).map_err(String::as_str),case.expected,"{}",case.name);
        for persistent in [false,true] {
            let actual=execute_with_engine(&case.program,&[],limits(persistent),Engine::Jit);
            if let Ok(actual)=&actual {successful_bridges+=actual.jit_tree_entries;}
            equal_faults(actual,&reference);
        }
    }
    assert!(successful_bridges>10,"positive bridge route must execute");
}

#[test]
fn nested_faults_survive_boundary_validation_and_prepared_reuse() {
    let leaf_cases=vec![
        vec![Op::Trap {message:"bridge trap".into()}],
        vec![Op::Imm {dst:0,value:0},Op::Assert {value:0,expected:true,message:"bridge assertion".into()},Op::Return],
        vec![Op::Imm {dst:0,value:u128::MAX},Op::Load {dst:1,address:0,size:8},Op::Return],
        vec![Op::Imm {dst:0,value:1},Op::Imm {dst:1,value:0},binary(2,Binary::Div,0,1),Op::Return],
        vec![Op::Imm {dst:0,value:1u128<<63},Op::Imm {dst:1,value:u64::MAX as u128},
            Op::Binary {dst:2,overflow:7,op:Binary::Div,a:0,b:1,bits:64,signed:true},Op::Return],
    ];
    for leaf in leaf_cases {
        let mut p=bounded();p.functions[2].code=leaf;
        let bound=trees::analyze(&p)[0].unwrap().instructions;
        for persistent in [false,true] {
            let mut prepared=crate::PreparedJit::new(&p,&limits(persistent)).unwrap();
            for budget in 0..=bound+1 {
                let reference=crate::execute(&p,&[],Limits {instructions:budget,..Limits::default()});
                equal_faults(prepared.execute(&[],Limits {instructions:budget,..limits(persistent)}),&reference);
            }
        }
    }
    // Invalid outer/inner arguments and invalid root/descendant destinations.
    for function in [0,1] {for bad_argument in [false,true] {
        let mut p=bounded();let pc=if function==0 {2} else {5};
        p.functions[function].code.insert(pc,Op::Imm {dst:6,value:u128::MAX});
        let Op::Call {args,destination,..}=&mut p.functions[function].code[pc+1] else {unreachable!()};
        if bad_argument {args[0]=6;} else {*destination=6;}
        let reference=crate::execute(&p,&[],Limits::default());assert!(reference.is_err());
        for persistent in [false,true] {equal_faults(execute_with_engine(&p,&[],limits(persistent),Engine::Jit),&reference);}
    }}
}

#[test]
fn unavailable_trees_and_incompatible_options_remain_explicit() {
    for p in [looping_program(false),looping_program(true),recursive_program(70)] {
        let reference=crate::execute(&p,&[],Limits::default());
        for persistent in [false,true] {
            let actual=execute_with_engine(&p,&[],limits(persistent),Engine::Jit);
            assert_eq!(actual.as_ref().unwrap().jit_tree_entries,0);
            equal_result(actual,&reference);
        }
    }
    let p=bounded();
    assert!(execute_with_engine(&p,&[],Limits {jit_tree_bridge:true,..Limits::default()},Engine::Jit).unwrap_err().contains("requires resumable"));
    assert!(execute_with_engine(&p,&[],limits(false),Engine::Interpreter).is_err());
    assert!(execute_with_engine(&p,&[],Limits {jit_native_calls:true,..limits(false)},Engine::Jit).is_err());
}

#[test]
fn emitted_bridge_preflight_matches_wide_integer_bounds_without_side_effects() {
    let plan=trees::Plan {instructions:19,depth:3,frame_span:145,register_slots:17,frame_align:64};
    let mut a=Assembler::default();a.resumable_save_host(false);a.mov(19,7);a.resumable_load_budget();
    let declines=a.bridge_preflight(plan);
    a.add_imm(0,21,1);a.resumable_save_host(true);a.emit(0xd65f03c0);
    let fallback=a.words.len();a.mov(0,31);a.resumable_save_host(true);a.emit(0xd65f03c0);
    for at in declines {a.patch_conditional(at,fallback).unwrap();}
    let mut code=platform::Code::reserve(4096).unwrap();let entry=code.append(&a.words).unwrap();
    for memory in [0,1,63,64,65,usize::MAX-64,usize::MAX] {
        for registers in [0,1,19,usize::MAX/16,usize::MAX] {for frames in [0,1,7,usize::MAX] {
            for budget in [0,19,20,u64::MAX] {for cap in [0,16,256,1024,usize::MAX] {
                // All fields are integers or raw pointers, for which zero is
                // valid. This probe reads only scalar bounds, never pointees.
                let mut cursor:ResumeCursor=unsafe {std::mem::zeroed()};
                cursor.state.remaining=budget;cursor.state.memory_len=memory;
                cursor.state.register_len=registers;cursor.state.frame_len=frames;
                cursor.memory_end=cap;cursor.frame_end=cap;cursor.working_budget=cap;
                // Production bounds come from a Vec<u128>, not arbitrary u64.
                cursor.register_end=cap.min(isize::MAX as usize/16);
                let expected=tree_bridge::admission(plan,cursor.state,Capacity {
                    memory:cap,registers:cursor.register_end,frames:cap},cap);
                let output=unsafe {code.tree_abi_probe(entry,[0,0,0,memory,0,0,0,(&mut cursor as *mut ResumeCursor) as usize])};
                assert_eq!(output[0],expected.map_or(0,|r|r.root_base+1));
                assert_eq!(&output[1..5],&[0x1357,0x2468,0x3579,0x468a]);assert_eq!(output[5],output[6]);
                assert_eq!(&output[7..],&[0x579b,0x68ac,0x79bd,0x8ace,0x9bdf,0xace0]);
                assert_eq!((cursor.state.remaining,cursor.state.memory_len,cursor.state.register_len,cursor.state.frame_len),(budget,memory,registers,frames));
                assert_eq!((cursor.state.calls,cursor.state.returns,cursor.bridge.depth,cursor.bridge_entries),(0,0,0,0));
            }}
        }}
    }
}
