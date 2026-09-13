use super::*;
use crate::{Limits, Slot, VERSION};

fn function(size: usize, align: usize, code: Vec<Op>) -> Function {
    Function { name: "same bridge fixture name".into(), frame_size: size, frame_align: align,
        registers: 4, args: vec![], result: Slot { offset: 0, size: 8 }, code }
}
fn program(functions: Vec<Function>) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        functions, data: vec![0;16], statics: vec![], thread_locals: vec![] }
}
fn local() -> Op { Op::Local { dst: 0, offset: 0 } }
fn call(id: usize) -> Op { Op::Call { function: id, args: vec![], destination: 0 } }
fn imm(dst: Reg, value: u128) -> Op { Op::Imm { dst, value } }
fn frame(id: usize, pc: usize, base: usize, reg: usize, ret: usize) -> Frame {
    Frame { function: id, pc, base, register_base: reg, return_address: ret, tls_callback: false }
}

struct Observed { cursor: BridgeCursor, frames: Vec<Frame>, value: u128, status: u64 }

fn run(p: &Program, persistent: bool, profiled: bool) -> Observed {
    crate::validate(p).unwrap();
    let mut jit = Jit::new_with_options(p, profiled, MAX_CODE_BYTES, false, persistent).unwrap();
    jit.bridge_trees = true;
    let plan = jit.ensure_tree(0).unwrap().unwrap();
    let bounds = plan.requirements(p.data.len(), 5, 0).unwrap();
    let base = bounds.root_base;
    let len = base + p.functions[0].frame_size.max(1);
    let mut memory = vec![0xc7; bounds.memory_end + 32];
    memory[..p.data.len()].copy_from_slice(&p.data);
    memory[p.data.len()..len].fill(0);
    let mut registers = vec![u128::MAX; bounds.register_end + 2];
    registers[5..5+p.functions[0].registers].fill(0);
    let sentinel = frame(99,99,99,99,99);
    let mut frames = vec![sentinel;plan.depth+2];
    let mut hits: Vec<Vec<u64>> = p.functions.iter().map(|f| vec![0;f.code.len()]).collect();
    let table: Vec<_> = hits.iter_mut().map(|h| h.as_mut_ptr()).collect();
    let mut cursor = BridgeCursor {
        tree: TreeCursor { base: Cursor { remaining: plan.instructions+7,
            profile_hits: if profiled { table[0] } else { std::ptr::null_mut() } },
            memory_len: len, peak_linear: len, return_address: base,
            profile_table: table.as_ptr(), calls: 0, tree_instructions: 0, regions_ready: 0, stub_calls: 0 },
        frames: frames.as_mut_ptr(), registers: registers.as_mut_ptr(), depth: 1,
        fault_depth: 0, fault_register_end: 0,
    };
    let entry = jit.trees.as_ref().unwrap().entries[0].as_ref().unwrap().wrapper;
    // SAFETY: validated complete tree; all conservative extents are fully
    // initialized and distinct. The extended cursor and profile arrays outlive
    // the synchronous owned code probe. Root is depth one, register slot five.
    let output = unsafe { jit.code.as_ref().unwrap().tree_abi_probe(entry,
        [registers.as_mut_ptr().add(5) as usize,base,memory.as_mut_ptr() as usize,len,
         p.data.len(),0,0,(&mut cursor as *mut BridgeCursor) as usize]) };
    assert_eq!(&output[1..5], &[0x1357,0x2468,0x3579,0x468a]);
    assert_eq!(output[5],output[6]);
    assert_eq!(&output[7..], &[0x579b,0x68ac,0x79bd,0x8ace,0x9bdf,0xace0]);
    assert!(memory[bounds.memory_end..].iter().all(|&b|b==0xc7));
    assert!(registers[..5].iter().chain(&registers[bounds.register_end..]).all(|&r|r==u128::MAX));
    assert_eq!(cursor.depth,0);
    assert!(cursor.tree.peak_linear<=bounds.memory_end);
    assert!(frames[cursor.fault_depth..].iter().all(|f|*f==sentinel));
    let consumed = plan.instructions+7-cursor.tree.base.remaining;
    if profiled {
        let charged: u64 = hits.iter().enumerate().map(|(id,row)| row.iter().enumerate()
            .filter(|(_,n)|**n!=0).map(|(pc,n)| n*(jit.trees.as_ref().unwrap().entries[id]
                .as_ref().unwrap().ends[pc].unwrap()-pc) as u64).sum::<u64>()).sum();
        assert_eq!(charged,consumed);
    } else { assert!(hits.iter().flatten().all(|&n|n==0)); }
    let expected = crate::execute(p,&[],Limits::default());
    if output[0]==0 {
        let expected=expected.unwrap(); assert_eq!(consumed,expected.instructions);
        assert_eq!(cursor.tree.peak_linear,expected.peak_memory);
        assert_eq!(cursor.tree.memory_len,base);
        assert_eq!(cursor.fault_depth,0); assert_eq!(cursor.fault_register_end,0);
        assert_eq!(u64::from_le_bytes(memory[base..base+8].try_into().unwrap()) as u128,expected.value);
    } else {
        let expected=expected.unwrap_err(); let actual=jit.fault_message(output[0] as u64).unwrap();
        if expected.contains("memory access") || expected.contains("address overflow") || expected.contains("read-only") {
            assert_eq!(actual,"JIT guest memory access failed");
        } else { assert_eq!(actual,expected); }
    }
    // Raw pointers in this returned diagnostic cursor are never dereferenced.
    Observed { cursor,frames,value:u64::from_le_bytes(memory[base..base+8].try_into().unwrap()) as u128,status:output[0] as u64 }
}

#[test]
fn nested_bridge_faults_materialize_only_active_calls_and_keep_first_failure() {
    for persistent in [false,true] { for profiled in [false,true] {
        let leaves = vec![
            vec![local(),imm(1,73),Op::Store {address:0,src:1,size:8},Op::Return],
            vec![imm(0,u64::MAX as u128),Op::Load {dst:1,address:0,size:1},Op::Return],
            vec![Op::Trap {message:"nested trap".into()}],
            vec![imm(0,0),Op::Assert {value:0,expected:true,message:"nested assertion".into()},Op::Return],
            vec![imm(0,1),imm(1,0),Op::Binary {dst:2,overflow:3,op:Binary::Div,a:0,b:1,bits:64,signed:false},Op::Return],
            vec![imm(0,1u128<<63),imm(1,u64::MAX as u128),Op::Binary {dst:2,overflow:3,op:Binary::Div,a:0,b:1,bits:64,signed:true},Op::Return],
        ];
        for leaf in leaves {
            let p=program(vec![function(17,16,vec![local(),call(1),Op::Return]),
                function(33,64,vec![local(),call(2),Op::Return]),function(31,32,leaf)]);
            let observed=run(&p,persistent,profiled);
            assert_eq!(observed.cursor.tree.calls,2);
            if observed.status==0 { assert_eq!(observed.value,73); }
            else {
                assert_eq!(observed.cursor.fault_depth,3);
                assert_eq!(observed.cursor.fault_register_end,17);
                assert_eq!(&observed.frames[..3],&[frame(0,2,16,5,16),frame(1,2,64,9,16),frame(2,0,128,13,64)]);
                assert_eq!(observed.cursor.tree.memory_len,159);
            }
        }
        // The failing inner argument has cleared/extended memory but has not
        // pushed a child, advanced its parent's PC, or incremented call count.
        let mut p=program(vec![function(17,16,vec![local(),call(1),Op::Return]),
            function(33,64,vec![local(),imm(1,u64::MAX as u128),
                Op::Call {function:2,args:vec![1],destination:0},Op::Return]),
            function(31,32,vec![Op::Return])]);
        p.functions[2].args=vec![Slot {offset:0,size:8}];
        let observed=run(&p,persistent,profiled);
        assert_eq!(observed.cursor.tree.calls,1);assert_eq!(observed.cursor.fault_depth,2);
        assert_eq!(observed.cursor.fault_register_end,13);assert_eq!(observed.cursor.tree.memory_len,159);
        assert_eq!(&observed.frames[..2],&[frame(0,2,16,5,16),frame(1,0,64,9,16)]);
        // A completed child must remain popped when a later ancestor faults.
        p.functions[1].code=vec![local(),call(2),Op::Return];p.functions[2].args.clear();
        p.functions[0].code=vec![local(),call(1),imm(1,u64::MAX as u128),Op::Load {dst:2,address:1,size:1},Op::Return];
        let observed=run(&p,persistent,profiled);
        assert_eq!(observed.cursor.tree.calls,2);assert_eq!(observed.cursor.fault_depth,1);
        assert_eq!(observed.cursor.fault_register_end,9);assert_eq!(observed.cursor.tree.memory_len,64);
        assert_eq!(observed.frames[0],frame(0,2,16,5,16));
    }}
}

#[test]
fn guarded_body_exclusion_propagates_to_ancestors_without_changing_other_trees() {
    let mut body=vec![];
    for _ in 0..8 {body.push(Op::Load {dst:1,address:0,size:8});}
    body.push(Op::Return);
    let p=program(vec![function(16,16,vec![local(),call(1),Op::Return]),
        function(16,16,vec![local(),call(2),Op::Return]),function(16,16,body),
        function(16,16,vec![Op::Return])]);
    crate::validate(&p).unwrap();
    let ordinary=trees::analyze(&p);assert!(ordinary.iter().all(Result::is_ok));
    let fills=local_fills(&p.functions[2]);
    let native=|pc|supported(&p.functions[2].code[pc]) || fills.contains_key(&pc) || transfers::supported(&p.functions[2].code[pc]);
    let starts=region_starts(&p.functions[2],&native);
    let end=region_end(&p.functions[2],0,&starts,&native);
    assert_eq!(end,8);
    assert!(range_groups::runtime_plan(&p.functions[2],0,end,&mut 4_000_000).is_some());
    let filtered=plans(&p);
    assert_eq!(filtered[0],Err(trees::Decline::UnavailableDependency));
    assert_eq!(filtered[1],Err(trees::Decline::UnavailableDependency));
    assert_eq!(filtered[2],Err(trees::Decline::UnsupportedOperation));
    assert_eq!(filtered[3],ordinary[3]);
}
