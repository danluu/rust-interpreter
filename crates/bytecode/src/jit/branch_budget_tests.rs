//! Native reservation boundaries, kept separate from the typed graph model.
use super::*;

fn diamond() -> Program {
    program(vec![function(vec![
        Op::Switch { value: 0, cases: vec![(0,1),(1,4),(1,8),(1u128<<100,4)], otherwise: 8 },
        Op::Imm { dst: 1, value: 11 },
        Op::Store { address: 4, src: 1, size: 8 },
        Op::Jump { target: 10 },
        Op::Imm { dst: 1, value: 22 },
        Op::Store { address: 4, src: 1, size: 8 },
        Op::Imm { dst: 2, value: 99 },
        Op::Jump { target: 10 },
        Op::Imm { dst: 1, value: 33 },
        Op::Store { address: 4, src: 1, size: 8 },
        Op::Imm { dst: 3, value: 77 },
        Op::ResetThreadLocals,
        Op::Return,
    ])])
}

#[derive(Debug, PartialEq, Eq)]
struct Snapshot {
    output: u64, remaining: u64, frame: Frame, memory: Vec<u8>, registers: Vec<u128>, hits: Vec<u64>,
}

fn probe(jit: &Jit<'_>, entry: usize, budget: u64, selector: u128, address: u128,
    dividend: u128, divisor: u128) -> Snapshot {
    let mut memory = vec![0;80];memory[48..].fill(0xad);
    let mut registers = vec![0;10];registers[0]=selector;registers[4]=address;
    registers[5]=dividend;registers[6]=divisor;registers[8..].fill(u128::MAX-7);
    let canary=Frame {function:987,pc:456,base:123,register_base:789,return_address:321,tls_callback:true};
    let mut frames=[Frame {function:0,pc:entry,base:16,register_base:0,return_address:0,tls_callback:false},canary];
    let mut hits=vec![0; jit.program.functions[0].code.len()];let profiles=[hits.as_mut_ptr()];
    let mut cursor=ResumeCursor {scalar_profiles:std::ptr::null(),
        state:State {remaining:budget,profile_hits:profiles[0],memory_len:48,peak_linear:48,
            register_len:8,frame_len:1,calls:0,returns:0},
        frames:frames.as_mut_ptr(),registers:registers.as_mut_ptr(),entries:jit.resumable.as_ref().unwrap().pointers.as_ptr(),
        profiles:profiles.as_ptr(),memory_end:48,register_end:8,frame_end:1,working_budget:1024};
    let args=[registers.as_mut_ptr() as usize,16,memory.as_mut_ptr() as usize,48,16,0,0,
        std::ptr::addr_of_mut!(cursor) as usize];
    // SAFETY: one validated function; exclusive initialized backing with explicit
    // extents and canaries; the entry was published by this exact JIT instance.
    let output=unsafe { jit.code.as_ref().unwrap().tree_abi_probe(jit.blocks[0][entry].unwrap().offset,args) };
    assert_eq!(&output[1..5],&[0x1357,0x2468,0x3579,0x468a]);
    assert_eq!(&output[7..],&[0x579b,0x68ac,0x79bd,0x8ace,0x9bdf,0xace0]);
    assert_eq!(output[5],output[6]);assert_eq!(output[6]%16,0);
    assert_eq!(frames[1],canary);assert!(memory[48..].iter().all(|&b|b==0xad));
    assert!(registers[8..].iter().all(|&v|v==u128::MAX-7));
    assert_eq!((cursor.state.memory_len,cursor.state.peak_linear,cursor.state.register_len,cursor.state.frame_len),(48,48,8,1));
    assert_eq!((cursor.state.calls,cursor.state.returns),(0,0));assert!(cursor.state.remaining<=budget);
    if jit.profiled {
        let charged:u64=hits.iter().enumerate().filter(|(_,n)|**n!=0)
            .map(|(pc,n)|n*(jit.blocks[0][pc].unwrap().end-pc) as u64).sum();
        assert_eq!(budget-cursor.state.remaining,charged);
    }
    Snapshot {output:output[0] as u64,remaining:cursor.state.remaining,frame:frames[0],memory,registers,hits}
}

fn compiled(p:&Program,profiled:bool,persistent:bool,reservations:bool)->Jit<'_> {
    crate::validate(p).unwrap();let mut jit=Jit::new_resumable(p,profiled,MAX_CODE_BYTES,persistent).unwrap();
    jit.budget_reservations_enabled=reservations;assert!(jit.ensure_function(0).unwrap());jit
}

#[test]
fn branch_reservation_external_entries_refund_unequal_paths_and_preserve_abi() {
    let p=diamond();
    for profiled in [false,true] {for persistent in [false,true] {
        let candidate=compiled(&p,profiled,persistent,true);let reference=compiled(&p,profiled,persistent,false);
        for (entry,credit) in [(0,6),(1,4),(4,5),(8,3),(10,1)] {
            for selector in [0,1,2,1u128<<100,u128::MAX] {for budget in 0..=8 {
                let actual=probe(&candidate,entry,budget,selector,16,0,0);
                if budget<credit {
                    assert_eq!((actual.output,actual.remaining,actual.frame.pc),(0,budget,entry));
                    assert!(actual.hits.iter().all(|&n|n==0));assert!(actual.memory[16..24].iter().all(|&v|v==0));
                } else {
                    assert_eq!(actual,probe(&reference,entry,budget,selector,16,0,0));
                    assert_eq!((actual.output,actual.frame.pc),(0,11));
                }
            }}
        }
    }}
}

#[test]
fn branch_reservation_faults_refund_only_the_unentered_suffix() {
    for fault in ["memory","zero","overflow","assertion"] {
        let mut p=diamond();
        let (address,dividend,divisor)=match fault {
            "memory"=>(u64::MAX as u128,0,0),
            "zero"=>{p.functions[0].code[2]=Op::Binary {dst:1,overflow:7,op:Binary::Div,a:5,b:6,bits:64,signed:true};(16,1,0)},
            "overflow"=>{p.functions[0].code[2]=Op::Binary {dst:1,overflow:7,op:Binary::Div,a:5,b:6,bits:64,signed:true};(16,1u128<<63,u64::MAX as u128)},
            _=>{p.functions[0].code[2]=Op::Assert {value:5,expected:true,message:"reservation fault".into()};(16,0,0)},
        };
        for profiled in [false,true] {for persistent in [false,true] {
            let candidate=compiled(&p,profiled,persistent,true);let reference=compiled(&p,profiled,persistent,false);
            for (entry,credit,charged) in [(0,6,4),(1,4,3)] {for budget in 0..=8 {
                let actual=probe(&candidate,entry,budget,0,address,dividend,divisor);
                if budget<credit {assert_eq!((actual.output,actual.remaining,actual.frame.pc),(0,budget,entry));}
                else {
                    assert!(actual.output>=FAILURE_MIN);assert_eq!(actual.remaining,budget-charged);
                    assert_eq!(actual,probe(&reference,entry,budget,0,address,dividend,divisor));
                }
            }}
        }}
    }
}

#[test]
fn branch_reservation_refund_encoding_is_non_flag_setting_and_bounded() {
    let mut a=Assembler {resumable:true,..Assembler::default()};
    a.refund_budget(0).unwrap();assert!(a.words.is_empty());
    for (refund,word) in [(1,0x910006d6),(2,0x91000ad6),(4095,0x913ffed6)] {
        a.refund_budget(refund).unwrap();assert_eq!(a.words.last(),Some(&word));
    }
    let old=a.words.clone();assert!(a.refund_budget(4096).is_err());assert_eq!(a.words,old);
    let mut plain=Assembler::default();assert!(plain.refund_budget(1).is_err());assert!(plain.words.is_empty());
}

#[test]
fn branch_reservation_operation_map_reconstructs_refund_thunks() {
    let p=diamond();
    for profiled in [false,true] {for persistent in [false,true] {for enabled in [false,true] {
        let jit=compiled(&p,profiled,persistent,enabled);let mut bytes=vec![];
        jit.operation_map().unwrap().write(&mut bytes).unwrap();
        let map:serde_json::Value=serde_json::from_slice(&bytes).unwrap();
        let words=jit.code.as_ref().unwrap().published().1;
        let mut edges=0;
        for f in map["functions"].as_array().unwrap() {for span in f["spans"].as_array().unwrap() {
            if span["kind"]!="budget_edge" {continue;}
            edges+=1;assert!(span["pc"].is_null());
            let start=span["offset"].as_u64().unwrap() as usize;let end=span["end"].as_u64().unwrap() as usize;
            assert_eq!(end-start,8);
            let add=u32::from_le_bytes(words[start..start+4].try_into().unwrap());
            let branch=u32::from_le_bytes(words[start+4..end].try_into().unwrap());
            assert_eq!(add & !0x003ffc00,0x910002d6);assert!((add>>10)&4095!=0);
            assert_eq!(branch>>26,5);
        }}
        assert_eq!(edges>0,enabled);
    }}}
}

#[test]
fn branch_reservation_capacity_refusal_publishes_no_partial_entry() {
    let p=diamond();let full=compiled(&p,false,true,true);let bytes=full.bytes;
    for capacity in [0,4,bytes/2,bytes-4] {
        let mut jit=Jit::new_resumable(&p,false,capacity,true).unwrap();jit.ensure_function(0).unwrap();
        assert_eq!(jit.bytes,0);assert!(jit.blocks[0].iter().all(Option::is_none));
        assert!(jit.resumable.as_ref().unwrap().published(0).iter().all(|&p|p==0));
    }
}

#[test]
fn branch_reservation_guard_declines_never_refund_unreserved_steps() {
    let mut code=vec![Op::Jump {target:1}];
    code.extend((0..8).map(|_|Op::Load {dst:1,address:4,size:8}));
    code.extend([Op::Jump {target:10},Op::Imm {dst:2,value:77},Op::ResetThreadLocals,Op::Return]);
    let p=program(vec![function(code)]);
    let mut work=4_000_000;
    assert!(crate::jit::range_groups::runtime_plan(&p.functions[0],1,10,&mut work).is_some());
    for profiled in [false,true] {for persistent in [false,true] {
        let candidate=compiled(&p,profiled,persistent,true);let reference=compiled(&p,profiled,persistent,false);
        for entry in [0,1] {for budget in 0..=12 {
            let actual=probe(&candidate,entry,budget,0,u64::MAX as u128,0,0);
            assert_eq!(actual,probe(&reference,entry,budget,0,u64::MAX as u128,0,0));
            assert_eq!(actual.output,0);
            assert_eq!(actual.remaining,budget-u64::from(entry==0&&budget>0));
        }}
        assert_eq!(probe(&candidate,0,12,0,16,0,0),probe(&reference,0,12,0,16,0,0));
    }}
}

#[test]
fn branch_reservation_credit_cap_keeps_long_initializers_and_budget_boundaries_exact() {
    let mut code:Vec<_>=(0..7168).map(|i|Op::Imm {dst:0,value:i}).collect();
    code.extend([Op::Local {dst:1,offset:0},Op::Store {address:1,src:0,size:8},Op::Return]);
    let p=program(vec![function(code)]);
    let mut budgets=vec![0,1,7168,7169,7170,7171,7172];
    for split in (1024..=7168).step_by(1024) {budgets.extend([split-1,split,split+1]);}
    budgets.sort_unstable();budgets.dedup();
    for budget in budgets {
        let expected=execute_profiled(&p,&[],Limits {instructions:budget,..Limits::default()},Engine::Interpreter);
        for persistent in [false,true] {
            let actual=execute_profiled(&p,&[],Limits {instructions:budget,jit_resumable_calls:true,
                jit_persistent_registers:persistent,..Limits::default()},Engine::Jit);
            match (actual,&expected) {
                (Ok((a,ap)),Ok((b,bp)))=>{
                    assert_eq!((a.value,a.instructions,a.peak_memory),(b.value,b.instructions,b.peak_memory));
                    assert_eq!(logical(&ap),logical(bp));
                },
                (Err(a),Err(b))=>assert_eq!(a,*b),
                (a,b)=>panic!("budget {budget}: {a:?} versus {b:?}"),
            }
        }
    }
}

#[test]
fn branch_reservation_fast_entries_do_not_supply_implicit_arithmetic_flags() {
    for op in [Binary::Sub,Binary::Shl,Binary::Shr,Binary::Eq,Binary::Lt] {
        let mut p=diamond();
        p.functions[0].code[1]=Op::Binary {dst:1,overflow:7,op,a:5,b:6,bits:128,signed:false};
        p.functions[0].code[2]=Op::Store {address:4,src:1,size:16};
        for profiled in [false,true] {for persistent in [false,true] {
            let candidate=compiled(&p,profiled,persistent,true);let reference=compiled(&p,profiled,persistent,false);
            for (a,b) in [(0u128,1u128),(1u128<<127,63),(u128::MAX,64),(1,127),(u128::MAX,u128::MAX)] {
                let actual=probe(&candidate,0,8,0,16,a,b);
                assert_eq!(actual,probe(&reference,0,8,0,16,a,b));
                let expected=match op {
                    Binary::Sub=>a.wrapping_sub(b),Binary::Shl=>a.wrapping_shl(b as u32),
                    Binary::Shr=>a.wrapping_shr(b as u32),Binary::Eq=>u128::from(a==b),
                    Binary::Lt=>u128::from(a<b),_=>unreachable!(),
                };
                assert_eq!(&actual.memory[16..32],&expected.to_le_bytes());
            }
        }}
    }
}
