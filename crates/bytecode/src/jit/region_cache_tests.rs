use super::*;
use crate::{Engine, Limits, Slot, VERSION, execute_profiled};

#[test]
fn region_cache_bank_excludes_every_persistent_pair_and_legacy_host_register() {
    let f = Function { name:"bank".into(),frame_size:0,frame_align:16,registers:4,
        args:vec![],result:Slot{offset:0,size:0},code:vec![Op::Return] };
    for count in 0..=3 {
        let mut values = values::analyze(&f).unwrap();
        values.registers = (0..count as Reg).collect();
        for resumable in [false,true] {
            let a = Assembler { values:Some(&values),resumable,..Assembler::default() };
            let physical: Vec<_> = (0..a.cache_capacity()).map(|slot|a.cache_physical(slot)).collect();
            assert_eq!(&physical[..2], &[5,6]);
            assert_eq!(physical.len(),if resumable {8-count*2} else {2});
            for reg in &physical[2..] {
                assert!((23+2*count as u32..=28).contains(reg));
            }
            for guest in 0..count as Reg {
                let pair=values.pair(guest).unwrap();
                assert!(!physical.contains(&pair) && !physical.contains(&(pair+1)));
            }
        }
    }
}

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
    let root = Function{name:"seeded region cache".into(),frame_size:512,frame_align:16,registers:32,
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

#[test]
fn seeded_wide_narrow_pressure_calls_aliases_loops_and_fallbacks_match_interpreter() {
    for index in 0..64u64 {
        let seed=0xc31a_7142_6559_872bu64.wrapping_add(index*7919);
        let (program,args)=generated(seed);
        crate::validate(&program).unwrap();
        let complete=execute_profiled(&program,&args,Limits::default(),Engine::Interpreter).unwrap();
        let n=complete.0.instructions;
        for budget in [0,1,2,20,52,n-2,n-1,n,n+1] {
            let reference=execute_profiled(&program,&args,Limits{instructions:budget,..Limits::default()},Engine::Interpreter)
                .map(|(e,p)|(e.value,e.instructions,e.peak_memory,logical(&p)));
            for persistent in [false,true] {for capacity in [0,MAX_CODE_BYTES] {
                let actual=execute_profiled(&program,&args,Limits{instructions:budget,jit_code_bytes:capacity,
                    jit_persistent_registers:persistent,jit_resumable_calls:true,..Limits::default()},Engine::Jit)
                    .map(|(e,p)|(e.value,e.instructions,e.peak_memory,logical(&p)));
                if actual!=reference {
                    // A failing seed is a complete standalone reproducer. Only
                    // create owned new files; never overwrite a prior failure.
                    let directory=std::env::temp_dir().join(format!("rust-interp-region-cache-failure-{}-{seed:016x}",std::process::id()));
                    std::fs::create_dir(&directory).unwrap();
                    std::fs::write(directory.join("program.rbc"),bincode::serialize(&program).unwrap()).unwrap();
                    std::fs::write(directory.join("inputs.json"),serde_json::to_vec_pretty(&serde_json::json!({
                        "seed":seed,"arguments":args.iter().map(|v|v.to_string()).collect::<Vec<_>>(),
                        "instructions":budget,"jit_persistent_registers":persistent,"jit_code_bytes":capacity
                    })).unwrap()).unwrap();
                    panic!("seed {seed:016x}, budget {budget}, persistent {persistent}, capacity {capacity}; saved {}; reference {reference:?}, actual {actual:?}",directory.display());
                }
            }}
        }
    }
}
