use super::*;
use crate::{Engine, Limits, Slot, VERSION, execute_profiled, execute_with_engine};

fn function(name: &str, code: Vec<Op>, registers: usize) -> Function {
    Function { name: name.into(), frame_size: 32, frame_align: 16, registers,
        args: vec![], result: Slot { offset: 0, size: 16 }, code }
}
fn program(functions: Vec<Function>) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        functions, data: vec![], statics: vec![], thread_locals: vec![] }
}
fn abi(output: [usize;13]) {
    assert_eq!(output[0],0);
    assert_eq!(&output[1..5], &[0x1357,0x2468,0x3579,0x468a]);
    assert_eq!(&output[7..], &[0x579b,0x68ac,0x79bd,0x8ace,0x9bdf,0xace0]);
    assert_eq!(output[5],output[6]); assert_eq!(output[6]%16,0);
}

#[test]
fn narrow_storage_native_reads_and_spills_keep_poisoned_backing_unobservable() {
    for reg in [0,1,2048] {
        let mut narrow=vec![false;reg as usize+1];narrow[reg as usize]=true;
        let reads=vec![Some((0,10));narrow.len()];
        let mut a=Assembler { narrow_registers:Some(&narrow),reads:&reads,..Assembler::default() };
        a.external_entry();
        a.imm(9,77);a.imm(10,0);
        a.raw_spill(reg,9,10);
        a.get(9,reg,false);a.get(10,reg,true);
        a.store_mem(9,10,2,16);
        a.mov(0,31);a.restore_external_values();a.emit(0xd65f03c0);
        let mut code=platform::Code::reserve(4096).unwrap();let offset=code.append(&a.words).unwrap();
        for poison in [1u128<<64,u128::MAX,0xabcdef0123456789u128<<64] {
            let mut registers=vec![poison;narrow.len()];let mut memory=[0xa5u8;16];
            // SAFETY: owned leaf accesses only these complete initialized slices.
            let output=unsafe {code.tree_abi_probe(offset,[registers.as_mut_ptr() as usize,0,
                memory.as_mut_ptr() as usize,memory.len(),0,0,0,0])};
            abi(output);assert_eq!(u128::from_le_bytes(memory),77);
            assert_eq!(registers[reg as usize],(poison&(!0u128<<64))|77);
            for (r,&v) in registers.iter().enumerate() {if r!=reg as usize {assert_eq!(v,poison);}}
        }
    }
}

#[test]
fn narrow_storage_persistent_reload_synthesizes_zero_and_preserves_host_registers() {
    let f=function("persistent",vec![Op::Imm{dst:0,value:0},Op::Jump{target:2},
        Op::Assert{value:0,expected:false,message:"zero".into()},Op::Jump{target:2}],1);
    let allocation=values::analyze(&f).unwrap();assert_eq!(allocation.registers,vec![0]);
    let narrow=[true];let reads=read_registers(&f);
    let mut a=Assembler{narrow_registers:Some(&narrow),values:Some(&allocation),reads:&reads,..Assembler::default()};
    a.external_entry();
    // Read the actual physical pair directly: get() alone could hide a missed reload.
    a.store_mem(23,24,2,16);a.mov(0,31);a.restore_external_values();a.emit(0xd65f03c0);
    let mut code=platform::Code::reserve(4096).unwrap();let offset=code.append(&a.words).unwrap();
    let mut registers=[u128::MAX];let mut memory=[0xa5u8;16];
    // SAFETY: owned leaf only loads this register and stores its16-byte result.
    abi(unsafe {code.tree_abi_probe(offset,[registers.as_mut_ptr() as usize,0,
        memory.as_mut_ptr() as usize,memory.len(),0,0,0,0])});
    assert_eq!(u128::from_le_bytes(memory),u64::MAX as u128);
    assert_eq!(registers,[u128::MAX]);
}

#[test]
fn narrow_storage_repair_reads_precede_alias_writes_and_keep_wide_values() {
    let ops=[
        (Op::Binary{dst:0,overflow:1,op:Binary::Mul,a:0,b:0,bits:128,signed:false},vec![0]),
        (Op::Select{dst:0,condition:2,yes:1,no:0},vec![0,2]),
        (Op::CallIndirect{callee:0,args:vec![2,1],arg_sizes:vec![8,8],destination:3,result_size:8},vec![0,2,3]),
        (Op::RegisterTlsDestructor{callback:0,argument:2},vec![0,2]),
        (Op::DescriptorWrite{dst:0,descriptor:1,address:2,size:3,errno:0},vec![0,2,3]),
        (Op::Imm{dst:0,value:7},vec![]),
    ];
    for (op,expected) in ops {
        let mut actual=[u128::MAX;4];register_widths::repair_reads(&[true,false,true,true],&op,&mut actual);
        for (r,&value) in actual.iter().enumerate() {
            assert_eq!(value,if expected.contains(&r) {u64::MAX as u128} else {u128::MAX});
        }
    }
}

#[test]
fn narrow_storage_declines_proof_storage_and_code_limits_without_partial_publication() {
    let p=program(vec![function("bound",vec![Op::Local{dst:0,offset:0},
        Op::Load{dst:1,address:0,size:8},Op::Store{address:0,src:1,size:16},Op::Return],2)]);
    crate::validate(&p).unwrap();
    for (capacity,bytes,disabled,expected) in [(0,0,false,false),
        (MAX_CODE_BYTES,MAX_NARROW_REGISTER_BYTES,false,false),
        (MAX_CODE_BYTES,MAX_NARROW_REGISTER_BYTES-1,false,false),
        (MAX_CODE_BYTES,MAX_NARROW_REGISTER_BYTES-2,false,true),
        (MAX_CODE_BYTES,0,true,false),(MAX_CODE_BYTES,0,false,true)] {
        let mut jit=Jit::new_resumable(&p,false,capacity,true).unwrap();
        jit.narrow_register_bytes=bytes;jit.disable_narrow_registers=disabled;
        jit.ensure_function(0).unwrap();
        assert_eq!(jit.narrow_registers[0].is_some(),expected);
        assert_eq!(jit.narrow_register_bytes,bytes+if expected {2} else {0});
        if capacity!=0 {
            // Exhaust remaining admission after publication. Re-emission must use
            // the retained proof, rather than applying a fresh capacity decision.
            jit.narrow_register_bytes=MAX_NARROW_REGISTER_BYTES;
            let map=jit.operation_map().unwrap();assert_eq!(serde_json::to_value(map).unwrap()["reconstructed_bytes_match"],true);
        }
    }
    let mut ordinary=Jit::new(&p,false,MAX_CODE_BYTES).unwrap();ordinary.ensure_function(0).unwrap();
    assert!(ordinary.narrow_registers[0].is_none());
}

fn reused(wide_after: bool, fault: bool, initial: bool) -> Program {
    let poison=function("wide storage",vec![Op::Local{dst:0,offset:0},Op::Imm{dst:1,value:u128::MAX},
        Op::Jump{target:3},Op::Store{address:0,src:1,size:16},Op::Return],6);
    let mut code=vec![Op::Local{dst:0,offset:0},Op::Imm{dst:1,value:0},Op::Jump{target:3},
        // Native full read after a real spill; zero's stale high half is observable.
        Op::Assert{value:1,expected:false,message:"narrow native zero".into()},
        Op::Binary{dst:2,overflow:3,op:Binary::Mul,a:1,b:1,bits:128,signed:false},
        // Mul128 is interpreted and must see exactly zero before resuming native.
        Op::Assert{value:2,expected:false,message:"narrow VM zero".into()},
        Op::Imm{dst:1,value:7},Op::Jump{target:8},Op::Store{address:0,src:1,size:16},Op::Return];
    assert!(!supported(&code[4]));
    if initial {code[1]=Op::Jump{target:3};}
    if fault {code[5]=Op::Assert{value:2,expected:true,message:"intentional fault".into()};}
    let narrow=function("narrow storage",code,6);
    assert_eq!(crate::registers::needs_initial_zeroes(&narrow),initial);
    let mut root=vec![Op::Local{dst:0,offset:0},Op::Call{function:1,args:vec![],destination:0},
        Op::Call{function:2,args:vec![],destination:0}];
    if wide_after {root.push(Op::Call{function:1,args:vec![],destination:0});}
    root.push(Op::Return);
    program(vec![function("reuse caller",root,2),poison,narrow])
}
fn check(p:&Program, max:u64) {
    crate::validate(p).unwrap();
    for budget in 0..=max {for capacity in [0,MAX_CODE_BYTES] {for persistent in [false,true] {
        let limits=||Limits{instructions:budget,jit_code_bytes:capacity,jit_resumable_calls:true,
            jit_persistent_registers:persistent,..Limits::default()};
        let expected=execute_profiled(p,&[],Limits{instructions:budget,..Limits::default()},Engine::Interpreter);
        let plain=execute_with_engine(p,&[],limits(),Engine::Jit);
        let observed=execute_profiled(p,&[],limits(),Engine::Jit);
        match expected {
            Err(error)=> {assert_eq!(plain.unwrap_err(),error);assert_eq!(observed.unwrap_err(),error);},
            Ok((expected,ep))=> {
                let (observed,op)=observed.unwrap();
                for actual in [plain.unwrap(),observed] {
                    assert_eq!((actual.value,actual.instructions,actual.peak_memory),
                        (expected.value,expected.instructions,expected.peak_memory));
                }
                for (actual,expected) in op.functions.iter().zip(ep.functions) {
                    let mut logical=actual.interpreted.clone();
                    for (pc,&hits) in actual.jit_blocks.iter().enumerate() {
                        if hits!=0 {for n in &mut logical[pc..actual.jit_block_ends[pc]] {*n+=hits;}}
                    }
                    assert_eq!(logical,expected.interpreted);
                }
            }
        }
    }}}
}

#[test]
fn narrow_storage_reused_wide_frames_and_all_budget_prefixes_match_interpreter() {
    for wide_after in [false,true] {for initial in [false,true] {check(&reused(wide_after,false,initial),32);}}
}

#[test]
fn narrow_storage_faults_after_interpreter_reentry_keep_original_order() {
    for initial in [false,true] {check(&reused(false,true,initial),28);}
}

#[test]
fn narrow_storage_arithmetic_proof_matches_actual_masked_and_comparison_values() {
    let values=[0,1,63,64,u64::MAX as u128,1u128<<64,1u128<<127,u128::MAX];
    for op in [Binary::Add,Binary::Sub,Binary::Mul,Binary::Div,Binary::Rem,Binary::And,
        Binary::Or,Binary::Xor,Binary::Shl,Binary::Shr,Binary::Eq,Binary::Ne,Binary::Lt,
        Binary::Le,Binary::Gt,Binary::Ge,Binary::Cmp,Binary::RotateLeft,Binary::RotateRight] {
        for bits in [8,16,32,64,128] {for signed in [false,true] {
            let f=function("arith",vec![Op::Binary{dst:0,overflow:1,op,a:2,b:3,bits,signed},Op::Return],4);
            let proof=register_widths::prove(&f).unwrap();assert!(proof[1]);
            for a in values {for b in values {
                if let Ok((value,_))=crate::binary(op,a,b,bits,signed) {
                    if proof[0] {assert_eq!(value>>64,0,"{op:?} {bits} {signed} {a} {b}");}
                }
            }}
        }}
    }
}
