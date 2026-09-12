use super::*;
use crate::{Binary, Engine, Limits, Slot, VERSION, execute_profiled};

fn generated(seed: u64) -> (Program, Vec<u128>) {
    let mut state = seed;
    let mut next = || {state ^= state << 13; state ^= state >> 7; state ^= state << 17; state};
    let args: Vec<_> = (0..8).map(|_| u128::from(next()) | (u128::from(next())<<64)).collect();
    let mut code = vec![];
    for r in 0..8 {
        code.push(Op::Local {dst:24,offset:16+r as usize*16});
        code.push(Op::Load {dst:r,address:24,size:if next()%3==0 {16} else {8}});
    }
    code.extend([Op::Imm{dst:16,value:2},Op::Imm{dst:17,value:1}]);
    let loop_start = code.len();
    for i in 0..36 {
        let (a,b,dst) = ((next()%8) as Reg,(next()%8) as Reg,(next()%8) as Reg);
        let bits = [8,16,32,64,128][next() as usize%5];
        let op = if bits==128 {Binary::Sub} else {[Binary::Add,Binary::Sub,Binary::Mul,Binary::Xor,Binary::Shr][next() as usize%5]};
        let overflow = match next()%4 {0=>dst,1=>a,_=>18};
        code.push(Op::Binary{dst,overflow,op,a,b,bits,signed:next()%2==0});
        // Distinct temporary identities die at each store, while the original
        // loop values remain live. Coalescing must preserve both classes.
        let temp=32+i*2;
        code.extend([Op::Imm {dst:temp,value:u128::from(next())<<64},
            Op::Binary {dst:temp+1,overflow:18,op:Binary::Sub,a:temp,b:a,bits:128,signed:false},
            Op::Local {dst:30,offset:384},Op::Store {address:30,src:temp+1,size:16}]);
        if i==10 {
            code.extend([Op::Local {dst:24,offset:256},Op::Local {dst:25,offset:288},
                Op::Store {address:24,src:a,size:16},Op::Copy {dst:25,src:24,size:24},
                Op::Call {function:1,args:vec![24],destination:25},Op::Load {dst:b,address:25,size:16}]);
        }
        if i==24 { code.push(Op::ResetThreadLocals); }
        if i%7==0 {code.push(Op::Select{dst,condition:a,yes:b,no:dst});}
    }
    code.push(Op::Binary{dst:16,overflow:18,op:Binary::Sub,a:16,b:17,bits:64,signed:false});
    let end = code.len()+1;
    code.push(Op::Switch{value:16,cases:vec![(0,end)],otherwise:loop_start});
    for r in 1..8 {
        code.push(Op::Binary{dst:0,overflow:18,op:Binary::Sub,a:0,b:r,bits:128,signed:false});
    }
    code.extend([Op::Local {dst:31,offset:0},Op::Store {address:31,src:0,size:16},Op::Return]);
    let root = Function{name:"seeded lifetime allocation".into(),frame_size:512,frame_align:16,registers:128,
        args:(0..8).map(|i|Slot{offset:16+i*16,size:16}).collect(),result:Slot{offset:0,size:16},code};
    let child = Function{name:"seeded native child".into(),frame_size:32,frame_align:16,registers:5,
        args:vec![Slot{offset:16,size:16}],result:Slot{offset:0,size:16},code:vec![
            Op::Local {dst:0,offset:16},Op::Load {dst:1,address:0,size:16},
            Op::Imm {dst:2,value:u128::from(next())<<64},
            Op::Binary{dst:1,overflow:3,op:Binary::Sub,a:1,b:2,bits:128,signed:false},
            Op::Local {dst:4,offset:0},Op::Store {address:4,src:1,size:16},Op::Return]};
    (Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![0;64],
        statics:vec![],thread_locals:vec![],functions:vec![root,child]},args)
}

fn logical(profile: &crate::ExecutionProfile) -> Vec<Vec<u64>> {
    profile.functions.iter().map(|f| {
        let mut counts=f.interpreted.clone();
        for (start,&hits) in f.jit_blocks.iter().enumerate() {
            if hits!=0 {for count in &mut counts[start..f.jit_block_ends[start]] {*count+=hits;}}
        }
        counts
    }).collect()
}

fn outcome(p: &Program, args: &[u128], limits: Limits, engine: Engine)
    -> Result<(u128,u64,usize,Vec<Vec<u64>>),String> {
    execute_profiled(p,args,limits,engine).map(|(e,p)|(e.value,e.instructions,e.peak_memory,logical(&p)))
}

#[test]
fn generated_lifetimes_preserve_wide_values_aliases_loops_calls_and_exact_budgets() {
    for index in 0..32u64 {
        let seed=0xc31a_7142_6559_872bu64.wrapping_add(index*7919);
        let (original,args)=generated(seed);
        let (allocated,report)=allocate(original.clone()).unwrap();
        assert!(report["after"].as_u64().unwrap()<report["before"].as_u64().unwrap()/2);
        let n=outcome(&original,&args,Limits::default(),Engine::Interpreter).unwrap().1;
        for budget in [0,1,2,20,52,n-2,n-1,n,n+1] {
            let reference=outcome(&original,&args,Limits{instructions:budget,..Limits::default()},Engine::Interpreter);
            for engine in [Engine::Interpreter,Engine::Jit] {
                for resumable in [false,true] {for persistent in [false,true] {for capacity in [0,16*1024*1024] {
                    if engine==Engine::Interpreter && (resumable || persistent || capacity!=0) {continue;}
                    let actual=outcome(&allocated,&args,Limits{instructions:budget,jit_code_bytes:capacity,
                        jit_persistent_registers:persistent,jit_resumable_calls:resumable,..Limits::default()},engine);
                    if actual!=reference {
                        let directory=std::env::temp_dir().join(format!("rust-interp-lifetimes-failure-{}-{seed:016x}",std::process::id()));
                        std::fs::create_dir(&directory).unwrap();
                        for (label,program) in [("original",&original),("allocated",&allocated)] {
                            std::fs::write(directory.join(format!("{label}.rbc")),bincode::serialize(program).unwrap()).unwrap();
                        }
                        std::fs::write(directory.join("inputs.json"),serde_json::to_vec_pretty(&serde_json::json!({
                            "seed":seed,"arguments":args.iter().map(|v|v.to_string()).collect::<Vec<_>>(),
                            "instructions":budget,"jit_persistent_registers":persistent,"jit_resumable_calls":resumable,
                            "jit_code_bytes":capacity,"engine":format!("{engine:?}")
                        })).unwrap()).unwrap();
                        panic!("saved {}; reference {reference:?}, actual {actual:?}",directory.display());
                    }
                }}}
            }
        }
    }
}

#[test]
fn allocation_keeps_fault_and_budget_order_with_initial_zero_reads() {
    for fault in [Op::Assert {value:1,expected:true,message:"initial zero".into()},
        Op::Load {dst:5,address:0,size:16},
        Op::Binary {dst:5,overflow:6,op:Binary::Div,a:0,b:1,bits:64,signed:false}] {
        let (mut original,_)=generated(7);
        original.functions.truncate(1);
        original.functions[0].args.clear();
        original.functions[0].code=vec![Op::Imm {dst:0,value:123},fault,Op::Trap {message:"later".into()}];
        let (allocated,_)=allocate(original.clone()).unwrap();
        for budget in 0..6 {
            let limits=||Limits {instructions:budget,..Limits::default()};
            let reference=outcome(&original,&[],limits(),Engine::Interpreter);
            assert!(reference.is_err());
            assert_eq!(outcome(&allocated,&[],limits(),Engine::Interpreter),reference);
            for resumable in [false,true] {for persistent in [false,true] {
                assert_eq!(outcome(&allocated,&[],Limits{jit_resumable_calls:resumable,jit_persistent_registers:persistent,..limits()},Engine::Jit),reference);
            }}
        }
    }
}

#[test]
fn allocation_preserves_program_and_call_layouts_and_declines_large_functions() {
    let (mut original,_)=generated(11);
    original.functions[1].registers=65_537;
    let untouched=bincode::serialize(&original.functions[1]).unwrap();
    let (allocated,report)=allocate(original.clone()).unwrap();
    assert_eq!(report["declined_functions"],1);
    assert_eq!(bincode::serialize(&allocated.functions[1]).unwrap(),untouched);
    assert_eq!((allocated.version,&allocated.target,allocated.entry,&allocated.data,&allocated.statics),
        (original.version,&original.target,original.entry,&original.data,&original.statics));
    for (a,b) in original.functions.iter().zip(&allocated.functions) {
        assert_eq!((&a.name,a.frame_size,a.frame_align,a.code.len()),(&b.name,b.frame_size,b.frame_align,b.code.len()));
        assert_eq!(bincode::serialize(&a.args).unwrap(),bincode::serialize(&b.args).unwrap());
        assert_eq!(bincode::serialize(&a.result).unwrap(),bincode::serialize(&b.result).unwrap());
    }
}

#[test]
fn memory_limits_still_charge_each_artifacts_actual_register_storage() {
    let (mut original,_)=generated(13);
    original.functions.truncate(1);original.functions[0].args.clear();
    original.functions[0].code=vec![Op::Imm {dst:100,value:123},Op::Local {dst:101,offset:0},
        Op::Store {address:101,src:100,size:16},Op::Return];
    let (allocated,_)=allocate(original.clone()).unwrap();
    assert_eq!(allocated.functions[0].registers,2);
    // Guest working-memory accounting includes register bytes. Reducing the
    // artifact's storage can legitimately make a formerly insufficient budget
    // sufficient; every engine must still enforce the new exact threshold.
    for program in [&original,&allocated] {
        let minimum=program.data.len()+program.functions[0].frame_size+program.functions[0].registers*16;
        for memory in [minimum-1,minimum] {
            let reference=outcome(program,&[],Limits{memory,..Limits::default()},Engine::Interpreter);
            assert_eq!(reference.is_ok(),memory==minimum);
            for resumable in [false,true] {for persistent in [false,true] {
                assert_eq!(outcome(program,&[],Limits{memory,jit_resumable_calls:resumable,
                    jit_persistent_registers:persistent,..Limits::default()},Engine::Jit),reference);
            }}
        }
    }
}
