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
