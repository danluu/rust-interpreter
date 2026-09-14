use super::*;
use crate::{Program,Slot,VERSION};

fn program(code:Vec<Op>,frame:usize,args:Vec<Slot>,result:Slot)->Program {
    Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![],statics:vec![],thread_locals:vec![],
        functions:vec![Function{name:"native scalar control".into(),frame_size:frame,frame_align:8,registers:8,args,result,code}]}
}
fn local(dst:u32,offset:usize)->Op {Op::Local{dst,offset}}
fn load(dst:u32,address:u32,size:u8)->Op {Op::Load{dst,address,size}}
fn store(address:u32,src:u32,size:u8)->Op {Op::Store{address,src,size}}
fn make_plan(p:&Program)->Plan {
    crate::validate(p).unwrap();let memory=crate::proof::memory_plan(p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());
    assert!(memory.eligible,"{:?}",memory.decline);lower(&p.functions[0],&memory,250_000).unwrap()
}
fn compare(p:&Program,plan:&Plan,native:&Native,args:&[u128],budget:usize) {
    let expected=plan.evaluate(args,16,budget,&p.functions[0].name);
    let actual=native.attempt(args,16,budget).unwrap();
    match actual {
        Some(actual)=>{
            let expected=expected.unwrap();assert_eq!(actual.value,expected.value);assert_eq!(actual.steps as usize,expected.pcs.len());
            if native.emitted.profiled {let mut visited=[0u64;8];for pc in expected.pcs {visited[pc/64]|=1u64<<(pc%64);}assert_eq!(actual.visited,visited);}
            else {assert_eq!(actual.visited,[u64::MAX;8]);}
        },
        None=>assert!(budget<plan.maximum_steps || expected.is_err(),"unexpected decline"),
    }
}

fn variants(p: &Program, plan: &Plan, profiled: bool) -> [Native; 3] {
    [0, 1, 2].map(|variant| {
        let emitted = if variant == 2 { emit(plan, profiled) }
            else { emit_with_registers(plan, profiled, variant == 1) }.unwrap();
        let mut code = memory::Code::reserve(MAX_CODE_BYTES).unwrap();
        assert_eq!(code.append(&emitted.words).unwrap(), 0);
        Native { code, emitted, argument_widths: p.functions[0].args.iter().map(|s| s.size).collect(),
            frame_size: p.functions[0].frame_size.max(1) }
    })
}

#[test]
fn native_scalar_register_pressure_reuses_values_and_spills_complete_intervals() {
    let mut code = vec![local(62, 0), load(0, 62, 8)];
    // Twelve simultaneously live values exceed the four available registers.
    for index in 0..12 {
        code.push(Op::Imm { dst: 1, value: index as u128 + 1 });
        code.push(Op::Binary { dst: index + 2, overflow: 40 + index,
            op: Binary::Mul, a: 0, b: 1, bits: 64, signed: false });
    }
    code.push(Op::Imm { dst: 30, value: 0 });
    for index in [3, 9, 0, 8, 2, 11, 1, 7, 4, 10, 5, 6] {
        code.push(Op::Binary { dst: 30, overflow: 40, op: Binary::Xor,
            a: 30, b: index + 2, bits: 64, signed: false });
        code.push(Op::Unary { dst: 30, op: Unary::SwapBytes, src: 30, bits: 64 });
    }
    code.extend([store(62, 30, 8), Op::Return]);
    let mut p = program(code, 8, vec![Slot { offset: 0, size: 8 }], Slot { offset: 0, size: 8 });
    p.functions[0].registers = 64;
    let plan = make_plan(&p);
    for profiled in [false, true] {
        let [spilled, allocated, optimized] = variants(&p, &plan, profiled);
        assert!(allocated.emitted.register_values > 4);
        assert!(allocated.emitted.stack_bytes < spilled.emitted.stack_bytes);
        assert!(allocated.emitted.stack_bytes > 0);
        assert!(optimized.emitted.words.len() < allocated.emitted.words.len());
        for input in [0, 1, 255, 1 << 31, 1 << 63, u64::MAX as u128, 0x123456789abcdef] {
            for budget in 0..=plan.maximum_steps + 1 {
                compare(&p, &plan, &allocated, &[input], budget);
                compare(&p, &plan, &optimized, &[input], budget);
                assert_eq!(allocated.attempt(&[input], 16, budget).unwrap(), spilled.attempt(&[input], 16, budget).unwrap());
                assert_eq!(optimized.attempt(&[input], 16, budget).unwrap(), spilled.attempt(&[input], 16, budget).unwrap());
            }
        }
    }
}

#[test]
fn native_scalar_registers_preserve_cross_block_values_phis_and_wide_results() {
    let binary = |dst, op, a, b| Op::Binary { dst, overflow: 29, op, a, b, bits: 64, signed: false };
    let code = vec![
        local(30, 0), load(0, 30, 8), local(31, 8), load(1, 31, 8),
        binary(2, Binary::Add, 0, 1),
        Op::Switch { value: 0, cases: vec![(0, 6)], otherwise: 11 },
        binary(3, Binary::Mul, 2, 1), binary(4, Binary::Xor, 3, 1), store(31, 4, 8),
        Op::Jump { target: 15 }, Op::Trap { message: "unreachable gap".into() },
        Op::Unary { dst: 3, op: Unary::Not, src: 2, bits: 64 },
        binary(4, Binary::Sub, 3, 0), store(31, 4, 8), Op::Jump { target: 15 },
        Op::Select { dst: 5, condition: 0, yes: 2, no: 4 }, binary(6, Binary::Xor, 5, 4),
        Op::Cast { dst: 6, src: 6, from: 64, to: 128, signed: true }, store(30, 6, 16), Op::Return,
    ];
    let mut p = program(code, 16, vec![Slot { offset: 0, size: 8 }, Slot { offset: 8, size: 8 }], Slot { offset: 0, size: 16 });
    p.functions[0].registers = 32;
    let plan = make_plan(&p);
    for profiled in [false, true] {
        let [spilled, allocated, optimized] = variants(&p, &plan, profiled);
        assert!(allocated.emitted.register_values > 0);
        for a in [0, 1, 1 << 63, u64::MAX as u128] {
            for b in [0, 255, 1 << 63, u64::MAX as u128] {
                for budget in 0..=plan.maximum_steps + 1 {
                    compare(&p, &plan, &allocated, &[a, b], budget);
                    compare(&p, &plan, &optimized, &[a, b], budget);
                    assert_eq!(allocated.attempt(&[a, b], 16, budget).unwrap(), spilled.attempt(&[a, b], 16, budget).unwrap());
                    assert_eq!(optimized.attempt(&[a, b], 16, budget).unwrap(), spilled.attempt(&[a, b], 16, budget).unwrap());
                }
            }
        }
    }
}

#[test]
fn native_scalar_registers_preserve_nonmonotonic_cfg_and_private_faults() {
    // The executed order is block 0, block 2, block 1: source PC order is not
    // dominance order. Both results and fault tails must survive that order.
    let code = vec![
        Op::Jump { target: 7 },
        Op::Binary { dst: 4, overflow: 5, op: Binary::Div, a: 2, b: 1, bits: 64, signed: true },
        Op::Unary { dst: 4, op: Unary::CountOnes, src: 4, bits: 64 },
        Op::Binary { dst: 4, overflow: 5, op: Binary::Xor, a: 4, b: 2, bits: 64, signed: false },
        local(6, 0), store(6, 4, 8), Op::Return,
        local(6, 0), load(0, 6, 8), local(7, 8), load(1, 7, 8),
        Op::Unary { dst: 2, op: Unary::SwapBytes, src: 0, bits: 64 },
        Op::Jump { target: 1 },
    ];
    let p = program(code, 16, vec![Slot { offset: 0, size: 8 }, Slot { offset: 8, size: 8 }], Slot { offset: 0, size: 8 });
    let plan = make_plan(&p);
    for profiled in [false, true] {
        let [spilled, allocated, optimized] = variants(&p, &plan, profiled);
        assert!(allocated.emitted.register_values > 0);
        for args in [[0, 0], [1, 1], [128, u64::MAX as u128], [0xabcdef, 3], [u64::MAX as u128, 1]] {
            for budget in 0..=plan.maximum_steps + 1 {
                compare(&p, &plan, &allocated, &args, budget);
                compare(&p, &plan, &optimized, &args, budget);
                assert_eq!(allocated.attempt(&args, 16, budget).unwrap(), spilled.attempt(&args, 16, budget).unwrap());
                assert_eq!(optimized.attempt(&args, 16, budget).unwrap(), spilled.attempt(&args, 16, budget).unwrap());
            }
        }
    }
}

#[test]
fn native_scalar_2187_copy_cases_in_both_profile_modes() {
    let mut cases=0;
    for src in 0..=8 {for dst in 0..=8 {for size in 0..=8 {
        let p=program(vec![local(0,src),local(1,dst),Op::Copy{src:0,dst:1,size},local(2,0),load(3,2,16),Op::Return],
            16,vec![Slot{offset:0,size:16}],Slot{offset:0,size:16});let plan=make_plan(&p);
        for profiled in [false,true] {let native=Native::compile(&plan,&p.functions[0],profiled).unwrap();
            for input in [0,u128::MAX,0x0123456789abcdef_fedcba9876543210] {compare(&p,&plan,&native,&[input],6);cases+=1;}
        }
    }}}
    assert_eq!(cases,4374);
}

#[test]
fn native_scalar_all_narrow_integer_operations_aliases_and_faults() {
    let operations=[Binary::Add,Binary::Sub,Binary::Mul,Binary::Div,Binary::Rem,Binary::And,Binary::Or,Binary::Xor,
        Binary::Shl,Binary::Shr,Binary::Eq,Binary::Ne,Binary::Lt,Binary::Le,Binary::Gt,Binary::Ge,Binary::Cmp,Binary::RotateLeft,Binary::RotateRight];
    for bits in [8,16,32,64] {for op in operations {for signed in [false,true] {for alias in [false,true] {
        let p=program(vec![local(0,0),local(1,16),load(2,0,16),load(3,1,16),
            Op::Binary{dst:2,overflow:if alias {2} else {3},op,a:2,b:3,bits,signed},local(0,32),store(0,2,16),Op::Return],
            48,vec![Slot{offset:0,size:16},Slot{offset:16,size:16}],Slot{offset:32,size:16});let plan=make_plan(&p);
        for profiled in [false,true] {let native=Native::compile(&plan,&p.functions[0],profiled).unwrap();
            for args in [[0,0],[u128::MAX,1],[1u128<<(bits-1),u128::MAX],[0x123456789abcdef,129],[0x8000000000000000,0x8000000000000001]] {
                compare(&p,&plan,&native,&args,8);
            }
        }
    }}}}
}

#[test]
fn native_scalar_unary_casts_phis_and_full_width_switches() {
    for bits in [8,16,32,64] {for op in [Unary::Not,Unary::Neg,Unary::CountOnes,Unary::LeadingZeros,Unary::TrailingZeros,Unary::SwapBytes] {
        let p=program(vec![local(0,0),load(1,0,16),Op::Unary{dst:1,op,src:1,bits},
            Op::Cast{dst:1,src:1,from:bits,to:128,signed:true},store(0,1,16),Op::Return],16,
            vec![Slot{offset:0,size:16}],Slot{offset:0,size:16});let plan=make_plan(&p);
        let native=Native::compile(&plan,&p.functions[0],true).unwrap();for input in [0,u128::MAX,1u128<<(bits-1),0x0102030405060708] {compare(&p,&plan,&native,&[input],6);}
    }}
    let p=program(vec![local(0,0),local(1,8),load(2,0,8),load(3,1,8),Op::Switch{value:2,cases:vec![(0,5)],otherwise:8},
        Op::Binary{dst:4,overflow:5,op:Binary::Add,a:2,b:3,bits:64,signed:false},store(1,4,8),Op::Jump{target:10},
        Op::Unary{dst:4,op:Unary::Not,src:3,bits:64},store(0,4,8),
        Op::Select{dst:6,condition:2,yes:4,no:3},Op::Cast{dst:6,src:6,from:8,to:64,signed:true},store(1,6,8),Op::Return],
        16,vec![Slot{offset:0,size:8},Slot{offset:8,size:8}],Slot{offset:0,size:16});let plan=make_plan(&p);
    for profiled in [false,true] {let native=Native::compile(&plan,&p.functions[0],profiled).unwrap();
        for args in [[0,255],[1,23],[u64::MAX as u128,128]] {for budget in 0..=15 {compare(&p,&plan,&native,&args,budget);}}
    }
    let p=program(vec![local(0,0),load(1,0,16),Op::Switch{value:1,cases:vec![(1u128<<100,3),(0,5)],otherwise:7},
        Op::Imm{dst:2,value:11},Op::Jump{target:8},Op::Imm{dst:2,value:22},Op::Jump{target:8},Op::Imm{dst:2,value:33},store(0,2,16),Op::Return],
        16,vec![Slot{offset:0,size:16}],Slot{offset:0,size:16});let plan=make_plan(&p);
    let native=Native::compile(&plan,&p.functions[0],true).unwrap();for input in [0,1u128<<100,1u128<<99,u128::MAX] {compare(&p,&plan,&native,&[input],10);}
}

#[test]
fn native_scalar_budget_admission_leaves_output_untouched_and_counts_cross_words() {
    let mut code=vec![Op::Imm{dst:0,value:1};130];code.push(Op::Return);
    let p=program(code,0,vec![],Slot{offset:0,size:0});let plan=make_plan(&p);
    for profiled in [false,true] {let native=Native::compile(&plan,&p.functions[0],profiled).unwrap();
        for budget in [0,1,64,130,131,132] {compare(&p,&plan,&native,&[],budget);}
        let mut output=Output{value:0x123456789abcdef,steps:123,visited:[456;8]};let before=output.clone();
        let status=unsafe {native.code.call(0,std::ptr::NonNull::<u128>::dangling().as_ptr(),16,std::ptr::from_mut(&mut output).cast(),130,
            0,std::ptr::null_mut(),0,std::ptr::null_mut())};assert_eq!(status,1);assert_eq!(output,before);
    }
}

#[test]
fn native_scalar_assertions_address_bits_and_host_registers_are_preserved() {
    let p=program(vec![local(0,0),load(1,0,8),Op::Assert{value:1,expected:true,message:"must pass".into()},
        local(2,3),store(0,2,8),Op::Return],8,vec![Slot{offset:0,size:8}],Slot{offset:0,size:8});let plan=make_plan(&p);
    for profiled in [false,true] {let native=Native::compile(&plan,&p.functions[0],profiled).unwrap();
        for (arg,budget) in [(0,6),(1,6),(1,0)] {
            compare(&p,&plan,&native,&[arg],budget);
            let input=[arg];let mut output=Output{value:0,steps:0,visited:[0;8]};
            let actual=unsafe {native.code.tree_abi_probe(0,[input.as_ptr() as usize,16,std::ptr::from_mut(&mut output) as usize,budget,0,0,0,0])};
            assert_eq!(actual[0],usize::from(arg==0 || budget==0));
            assert_eq!([actual[1],actual[2],actual[3],actual[4],actual[7],actual[8],actual[9],actual[10],actual[11],actual[12]],
                [0x1357,0x2468,0x3579,0x468a,0x579b,0x68ac,0x79bd,0x8ace,0x9bdf,0xace0]);assert_eq!(actual[5],actual[6]);
        }
        assert!(native.attempt(&[],16,6).is_err());assert!(native.attempt(&[1u128<<64],16,6).is_err());assert!(native.attempt(&[1],usize::MAX,6).is_err());
    }
}

#[test]
fn native_scalar_unsupported_width_and_storage_code_bounds_decline_before_publication() {
    let p=program(vec![Op::Imm{dst:0,value:1},Op::Binary{dst:1,overflow:2,op:Binary::Add,a:0,b:0,bits:128,signed:false},
        local(3,0),store(3,1,16),Op::Return],16,vec![],Slot{offset:0,size:16});let plan=make_plan(&p);
    assert!(matches!(emit(&plan,false),Err("native_integer_128")));
    let p=program(vec![Op::Return],0,vec![],Slot{offset:0,size:0});let mut storage=super::super::lower(&p.functions[0],
        &crate::proof::memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone()),250_000).unwrap();
    for _ in 0..3000 {storage.nodes.push(Node{value:Value::Pack(vec![]),width:16,pc:None});storage.live.push(true);}
    assert!(matches!(emit(&storage,false),Err("native_stack_limit")));
    let p=program(vec![Op::Switch{value:0,cases:(0..8191).map(|i|(i,1)).collect(),otherwise:1},Op::Return],0,vec![],Slot{offset:0,size:0});
    let plan=super::super::lower(&p.functions[0],&crate::proof::memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone()),250_000).unwrap();
    assert!(matches!(emit(&plan,false),Err("native_word_limit")));
}
