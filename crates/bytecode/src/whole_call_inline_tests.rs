use crate::{Binary, Engine, Function, Limits, Op, Program, Slot, VERSION,
    execute_profiled, execute_with_engine, inline};

fn function(name: &str, args: Vec<Slot>, code: Vec<Op>) -> Function {
    Function { name: name.into(), args, result: Slot { offset: 0, size: 8 },
        frame_size: 64, frame_align: 16, registers: 12, code }
}
fn program(functions: Vec<Function>) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        functions, data: vec![0; 256], statics: vec![], thread_locals: vec![] }
}
fn transform(p: &Program) -> Program {
    let (q, report) = inline::transform(p, inline::Options { program_growth_percent: 100, ..Default::default() }).unwrap();
    assert!(report["selected_sites"].as_u64().unwrap() > 0);
    assert_eq!(p.functions.len(), q.functions.len());
    q
}
fn limits(engine: Engine, resumable: bool, instructions: u64, fallback: bool) -> Limits {
    Limits { instructions, jit_resumable_calls: engine == Engine::Jit && resumable,
        jit_persistent_registers: engine == Engine::Jit && resumable,
        jit_code_bytes: if fallback { 0 } else { 16*1024*1024 }, ..Limits::default() }
}
fn configurations() -> [(Engine,bool,bool);4] {
    [(Engine::Interpreter,false,false),(Engine::Jit,false,false),
        (Engine::Jit,true,false),(Engine::Jit,true,true)]
}
fn check(p: &Program, q: &Program, args: &[u128], expected: u128) {
    assert_eq!(execute_with_engine(p,args,Limits::default(),Engine::Interpreter).unwrap().value, expected);
    let reference=execute_with_engine(q,args,Limits::default(),Engine::Interpreter).unwrap();
    assert_eq!(reference.value, expected);
    for (engine,resumable,fallback) in configurations() {
        let (got, profile)=execute_profiled(q,args,limits(engine,resumable,u64::MAX,fallback),engine).unwrap();
        assert_eq!((got.value,got.instructions,got.peak_memory),
            (expected,reference.instructions,reference.peak_memory));
        let mut counted=0u64;
        for f in profile.functions {
            counted+=f.interpreted.iter().sum::<u64>();
            for (hits,ends) in [(&f.jit_blocks,&f.jit_block_ends),(&f.jit_tree_blocks,&f.jit_tree_block_ends)] {
                for (pc,(&hits,&end)) in hits.iter().zip(ends).enumerate() {
                    if hits!=0 { counted+=hits*(end-pc) as u64; }
                }
            }
        }
        assert_eq!(counted,got.instructions);
        for budget in [0,1,reference.instructions/2,reference.instructions-1,reference.instructions] {
            let got=execute_with_engine(q,args,limits(engine,resumable,budget,fallback),engine);
            if budget==reference.instructions { assert_eq!(got.unwrap().value,expected); }
            else { assert!(got.unwrap_err().contains("instruction limit")); }
        }
    }
}

#[test]
fn compare_bytes_relocates_every_operand_and_matches_native_slice_order() {
    for size in [0,1,16,33,64] { for different in [false,true] {
        let root=function("root",vec![],vec![Op::Local {dst:0,offset:0},
            Op::Call {function:1,args:vec![],destination:0},Op::Return]);
        let leaf=function("compare",vec![],vec![Op::Imm {dst:0,value:16},Op::Imm {dst:1,value:96},
            Op::Imm {dst:2,value:size as u128},Op::CompareBytes {dst:3,left:0,right:1,size:2},
            Op::Local {dst:4,offset:0},Op::Store {address:4,src:3,size:8},Op::Return]);
        let mut p=program(vec![root,leaf]);
        // Pad the caller with real register definitions so bounded global growth
        // admits expansion even for this tiny standalone program.
        for _ in 0..20 { p.functions[0].code.insert(0,Op::Imm {dst:11,value:0}); }
        for i in 0..64 { p.data[16+i]=(i*3) as u8;p.data[96+i]=(i*3) as u8; }
        if different && size!=0 { p.data[96+size-1]^=1; }
        let expected=match p.data[16..16+size].cmp(&p.data[96..96+size]) {
            std::cmp::Ordering::Less=>u32::MAX as u128,std::cmp::Ordering::Equal=>0,std::cmp::Ordering::Greater=>1 };
        let q=transform(&p); assert!(q.functions[0].code.iter().any(|op|matches!(op,Op::CompareBytes{..})));
        check(&p,&q,&[],expected);
    }}
}

fn nested() -> Program {
    let args=vec![Slot {offset:16,size:8},Slot {offset:24,size:8}];
    let root=function("root",args.clone(),vec![Op::Local {dst:0,offset:16},Op::Local {dst:1,offset:24},
        Op::Local {dst:2,offset:0},Op::Call {function:1,args:vec![0,1],destination:0},
        Op::Copy {dst:2,src:0,size:8},Op::Return]);
    let middle=function("middle",args,vec![Op::Local {dst:0,offset:16},Op::Local {dst:1,offset:24},
        Op::Local {dst:2,offset:0},Op::Call {function:2,args:vec![0,1],destination:2},
        Op::Load {dst:3,address:2,size:8},Op::Imm {dst:4,value:31},
        Op::Binary {dst:3,overflow:5,op:Binary::Xor,a:3,b:4,bits:64,signed:false},
        Op::Store {address:2,src:3,size:8},Op::Return]);
    // Ordered argument copies into overlapping callee slots must keep the last.
    let leaf=function("leaf",vec![Slot {offset:16,size:8};2],vec![Op::Local {dst:0,offset:16},
        Op::Load {dst:1,address:0,size:8},Op::Imm {dst:2,value:79},
        Op::Binary {dst:1,overflow:3,op:Binary::Xor,a:1,b:2,bits:64,signed:false},
        Op::Local {dst:4,offset:0},Op::Store {address:4,src:1,size:8},Op::Return]);
    program(vec![root,middle,leaf])
}

#[test]
fn nested_call_preserves_ordered_arguments_and_aliased_results() {
    let p=nested();let q=transform(&p);
    assert!(q.functions[0].code.iter().any(|op|matches!(op,Op::Call{function:2,..})));
    assert!(!q.functions[0].code.iter().any(|op|matches!(op,Op::Call{function:1,..})));
    for (a,b) in [(0,0),(7,11),(u64::MAX as u128,1),(0,u64::MAX as u128)] {
        check(&p,&q,&[a,b],b^79^31);
    }
}

#[test]
fn cross_branch_definitions_are_proven_and_banked_without_clearing() {
    let root=function("root",vec![Slot {offset:16,size:8}],vec![Op::Local {dst:0,offset:16},
        Op::Local {dst:1,offset:0},Op::Call {function:1,args:vec![0],destination:1},Op::Return]);
    let leaf=function("diamond",vec![Slot {offset:16,size:8}],vec![Op::Local {dst:0,offset:16},
        Op::Load {dst:1,address:0,size:8},Op::Switch {value:1,cases:vec![(0,5)],otherwise:3},
        Op::Imm {dst:2,value:29},Op::Jump {target:6},Op::Imm {dst:2,value:13},
        Op::Local {dst:3,offset:0},Op::Store {address:3,src:2,size:8},Op::Return]);
    let mut p=program(vec![root,leaf]);
    for _ in 0..20 {p.functions[0].code.insert(0,Op::Imm {dst:11,value:0});}
    assert!(crate::registers::needs_initial_zeroes_for_inlining(&p.functions[1]));
    assert!(!crate::registers::needs_initial_zeroes(&p.functions[1]));
    let q=transform(&p);assert!(!crate::registers::needs_initial_zeroes(&q.functions[0]));
    for seed in [0,1,7] {check(&p,&q,&[seed],if seed==0 {13}else{29});}
}

#[test]
fn nested_faults_keep_transformed_interpreter_order_at_every_budget() {
    let mut p=nested(); p.functions[2].code=vec![Op::Imm {dst:0,value:u64::MAX as u128},
        Op::Load {dst:1,address:0,size:8},Op::Return];
    for _ in 0..20 {p.functions[0].code.insert(0,Op::Imm {dst:11,value:0});}
    let q=transform(&p);
    let original=execute_with_engine(&p,&[7,11],Limits::default(),Engine::Interpreter).unwrap_err();
    assert_eq!(original,execute_with_engine(&q,&[7,11],Limits::default(),Engine::Interpreter).unwrap_err());
    for budget in 0..100 {
        let expected=execute_with_engine(&q,&[7,11],limits(Engine::Interpreter,false,budget,false),Engine::Interpreter).unwrap_err();
        for (engine,resumable,fallback) in configurations() {
            let got=execute_with_engine(&q,&[7,11],limits(engine,resumable,budget,fallback),engine).unwrap_err();
            // Retained native modes use a generic memory diagnostic. Keep its
            // exact spelling and require the same fault point; budget errors
            // still compare exactly and cannot be normalized into memory errors.
            if got == "JIT guest memory access failed" {
                assert_eq!(engine,Engine::Jit); assert!(!fallback);
                assert_eq!(expected,"invalid guest memory access");
            } else { assert_eq!(got,expected); }
        }
    }
}

#[test]
fn recursive_or_unknown_closures_do_not_expand_nonleaf_bodies() {
    for indirect in [false,true] {
        let mut p=nested();
        p.functions[2].code=vec![Op::Local {dst:0,offset:16},Op::Local {dst:1,offset:24},Op::Local {dst:2,offset:0},
            if indirect {Op::CallIndirect {callee:2,args:vec![0,1],arg_sizes:vec![8,8],destination:2,result_size:8}}
            else {Op::Call {function:1,args:vec![0,1],destination:2}},Op::Return];
        let (q,report)=inline::transform(&p,Default::default()).unwrap();
        assert_eq!(report["selected_sites"],0);
        assert_eq!(bincode::serialize(&p).unwrap(),bincode::serialize(&q).unwrap());
    }
}
