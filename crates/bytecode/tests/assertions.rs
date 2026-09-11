#![cfg(all(target_arch = "aarch64", target_os = "macos"))]
use rust_interp_bytecode::{Binary, Engine, Function, Limits, Op, Program, Slot, VERSION, execute_with_engine};

fn program(code: Vec<Op>, registers: usize) -> Program {
    Program {
        version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 16], statics: vec![], thread_locals: vec![],
        functions: vec![Function {
            name: "assertion fixture λ\n\0tail".into(), frame_size: 48, frame_align: 16,
            registers, args: vec![Slot { offset: 0, size: 16 }, Slot { offset: 16, size: 16 }],
            result: Slot { offset: 32, size: 16 }, code,
        }],
    }
}

fn prefix() -> Vec<Op> {
    vec![Op::Local { dst:0, offset:0 }, Op::Load { dst:2, address:0, size:16 },
         Op::Local { dst:1, offset:16 }, Op::Load { dst:3, address:1, size:16 }]
}

fn assertion(value: u32, expected: bool, message: &str) -> Op {
    Op::Assert { value, expected, message:message.into() }
}

fn finish(code: &mut Vec<Op>, value: u32) {
    code.extend([Op::Local { dst:6, offset:32 }, Op::Store { address:6, src:value, size:16 }, Op::Return]);
}

fn compare(p: &Program, args: &[u128], instructions: u64) -> Result<(u128,u64,u64),String> {
    let limits = || Limits { instructions, ..Limits::default() };
    let expected = execute_with_engine(p,args,limits(),Engine::Interpreter);
    let got = execute_with_engine(p,args,limits(),Engine::Jit);
    match (expected,got) {
        (Ok(a),Ok(b)) => {
            assert_eq!(a.value,b.value); assert_eq!(a.instructions,b.instructions);
            Ok((b.value,b.instructions,b.jit_instructions))
        }
        (Err(a),Err(b)) => { assert_eq!(a,b); Err(b) }
        _ => panic!("engines disagree on success"),
    }
}

#[test]
fn assertions_use_full_u128_truth_for_dynamic_constant_and_large_registers() {
    let values = [0,1,2,255,1u128<<63,1u128<<64,1u128<<127,u128::MAX];
    for value in values {
        for expected in [false,true] {
            for constant in [false,true] {
                for r in [2,4097] {
                    let mut code=prefix();
                    code.push(if constant { Op::Imm { dst:r,value } } else { Op::Load { dst:r,address:0,size:16 } });
                    code.push(assertion(r,expected,"truth λ\n\0message"));
                    finish(&mut code,r);
                    let p=program(code,(r as usize+1).max(7));
                    let got=compare(&p,&[value,0],100).map(|(result,steps,jitted)| {
                        assert_eq!(result,value); assert_eq!(jitted+1,steps);
                    });
                    assert_eq!(got.is_ok(),(value!=0)==expected);
                    if let Err(error)=got {
                        assert_eq!(error,"guest assertion: truth λ\n\0message in assertion fixture λ\n\0tail");
                    }
                }
            }
        }
    }
}

#[test]
fn local_address_facts_are_nonzero_and_assertions_do_not_clobber_values() {
    let mut code=prefix();
    code.extend([assertion(0,true,"local"),assertion(1,true,"second local")]);
    finish(&mut code,2);
    let p=program(code,7);
    for value in [0,1u128<<127,u128::MAX] {
        let (result,steps,jitted)=compare(&p,&[value,0],100).unwrap();
        assert_eq!(result,value);assert_eq!(jitted+1,steps);
    }
}

#[test]
fn each_failure_keeps_its_own_message_and_budget_boundary() {
    let mut code=prefix();
    code.extend([assertion(2,true,"first"),assertion(3,false,"second"),assertion(3,true,"third")]);
    finish(&mut code,2);
    let p=program(code,7);
    for (args,message) in [([0,0],"first"),([1,1],"second"),([1,0],"third")] {
        for budget in 0..=p.functions[0].code.len() as u64+1 {
            let error=compare(&p,&args,budget).unwrap_err();
            if error!="interpreter instruction limit exceeded" {
                assert_eq!(error,format!("guest assertion: {message} in {}",p.functions[0].name));
            }
        }
    }
    let mut p=p;
    p.functions[0].code[6]=assertion(3,false,"third passes");
    for budget in 0..=p.functions[0].code.len() as u64+1 {
        let got=compare(&p,&[1,0],budget);
        assert_eq!(got.is_ok(),budget>=p.functions[0].code.len() as u64);
    }
}

#[test]
fn assertion_memory_and_division_failures_keep_program_order() {
    for order in [[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]] {
        let mut code=prefix();
        code.extend([Op::Imm { dst:4,value:u128::MAX },Op::Imm { dst:5,value:0 },Op::Imm { dst:6,value:1 }]);
        for op in order {
            code.push(match op {
                0=>assertion(2,true,"first assertion"),
                1=>Op::Binary { dst:7,overflow:8,op:Binary::Div,a:6,b:5,bits:64,signed:false },
                _=>Op::Load { dst:9,address:4,size:1 },
            });
        }
        code.push(Op::Return);
        let p=program(code,10);
        for budget in 0..=p.functions[0].code.len() as u64+1 {
            let limits=|| Limits { instructions:budget,..Limits::default() };
            let a=execute_with_engine(&p,&[0,0],limits(),Engine::Interpreter).err().unwrap();
            let b=execute_with_engine(&p,&[0,0],limits(),Engine::Jit).err().unwrap();
            if b=="JIT guest memory access failed" {
                assert_eq!(order[0],2);
                assert!(!a.contains("assertion") && !a.contains("division") && !a.contains("instruction limit"));
            } else { assert_eq!(a,b); }
        }
    }
}

#[test]
fn assertions_preserve_values_at_branch_joins_and_backedges() {
    let mut code=prefix();
    code.extend([
        Op::Switch { value:3,cases:vec![(0,5)],otherwise:9 }, // 4
        Op::Imm { dst:4,value:1u128<<127 },
        assertion(4,true,"constant high half"),
        Op::Imm { dst:5,value:17 },
        Op::Jump { target:13 },
        Op::Imm { dst:4,value:0 },
        assertion(4,false,"zero"),
        Op::Imm { dst:5,value:23 },
        Op::Jump { target:13 },
        assertion(5,true,"join"), // 13
        Op::Imm { dst:7,value:1 },
        Op::Binary { dst:2,overflow:8,op:Binary::Sub,a:2,b:7,bits:64,signed:false },
        assertion(8,false,"loop underflow"),
        Op::Switch { value:2,cases:vec![(0,18)],otherwise:13 },
    ]);
    finish(&mut code,5);
    let p=program(code,9);
    for count in [1,2,17] {
        for branch in [0,1,u128::MAX] {
            let (value,steps,jitted)=compare(&p,&[count,branch],1000).unwrap();
            assert_eq!(value,if branch==0 {17} else {23});
            // The final Local/Store pair is below the three-op region minimum;
            // those two instructions and Return remain interpreted.
            assert_eq!(jitted+3,steps);
        }
    }
    for budget in 0..=35 { let _=compare(&p,&[3,1],budget); }
    assert!(compare(&p,&[0,0],100).unwrap_err().contains("loop underflow"));
}

#[test]
fn assertion_identities_span_bounded_regions_and_functions() {
    let mut code=prefix();
    for i in 0..2100 { code.push(assertion(2,true,&format!("region assertion {i}"))); }
    code.push(assertion(3,false,"last assertion"));
    finish(&mut code,2);
    let p=program(code,7);
    let (_,steps,jitted)=compare(&p,&[1,0],10000).unwrap();
    assert_eq!(jitted+1,steps);
    assert!(compare(&p,&[1,1],10000).unwrap_err().contains("last assertion"));
    assert!(compare(&p,&[0,0],10000).unwrap_err().contains("region assertion 0"));
    for budget in [0,1,4,5,1023,1024,1025,2047,2048,2049,2104,2105,2108,2109] {
        let _=compare(&p,&[1,1],budget);
    }

    let mut callee=prefix();
    callee.push(assertion(2,true,"callee only"));
    finish(&mut callee,2);
    let mut caller=prefix();
    caller.extend([assertion(3,true,"caller only"),Op::Local { dst:6,offset:32 },
        Op::Call { function:1,args:vec![0,1],destination:6 },Op::Return]);
    let mut p=program(caller,7);
    let mut f=program(callee,7).functions.remove(0);f.name="callee function".into();p.functions.push(f);
    assert!(compare(&p,&[1,1],100).is_ok());
    assert_eq!(compare(&p,&[0,1],100).unwrap_err(),"guest assertion: callee only in callee function");
    assert_eq!(compare(&p,&[0,0],100).unwrap_err(),format!("guest assertion: caller only in {}",p.functions[0].name));
}
