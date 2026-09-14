use super::*;
use crate::{Engine,Execution,Limits,Slot,VERSION,execute_with_engine};

fn function(code:Vec<Op>)->Function {
    Function {name:"guarded fixture".into(),frame_size:32,frame_align:16,registers:8,
        args:vec![Slot {offset:0,size:8}],result:Slot {offset:8,size:8},code}
}
fn program(functions:Vec<Function>)->Program {
    Program {version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,functions,
        data:vec![0;64],statics:vec![],thread_locals:vec![]}
}
fn load(dst:Reg,address:Reg)->Op {Op::Load {dst,address,size:8}}
fn compare(actual:Result<Execution,String>,expected:&Result<Execution,String>) {
    match (actual,expected) {
        (Ok(a),Ok(b))=>assert_eq!((a.value,a.instructions,a.peak_memory),(b.value,b.instructions,b.peak_memory)),
        (Err(a),Err(b))=>assert_eq!(a,*b),
        (a,b)=>panic!("different outcomes: {a:?} / {b:?}"),
    }
}

#[test]
fn guarded_local_facts_preserve_alias_declines_and_unselected_writes() {
    for copied in [false,true] { for unselected in [false,true] {
        let mut ops=vec![Op::Local {dst:0,offset:0},load(1,0),Op::Local {dst:3,offset:16},
            Op::Imm {dst:4,value:23},Op::Store {address:3,src:4,size:8},
            Op::Imm {dst:2,value:7},Op::Local {dst:7,offset:24},Op::Store {address:7,src:2,size:8}];
        for _ in 0..8 {
            ops.push(if copied {Op::Copy {dst:1,src:7,size:8}} else {Op::Store {address:1,src:2,size:8}});
            ops.push(load(5,3));
        }
        if unselected {
            ops.extend([Op::Local {dst:8,offset:32},load(9,8),Op::Store {address:9,src:2,size:8},load(5,3)]);
        }
        ops.extend([Op::Local {dst:6,offset:8},Op::Store {address:6,src:5,size:8},Op::Return]);
        let mut f=function(ops);f.frame_size=64;f.registers=10;
        f.args.push(Slot {offset:32,size:8});
        let mut p=program(vec![f]);p.statics=vec![0;32];crate::validate(&p).unwrap();
        if !unselected {
            let jit=Jit::new_resumable(&p,false,MAX_CODE_BYTES,true).unwrap();
            let staged=jit.emit_function(&p.functions[0],MAX_CODE_BYTES/4).unwrap().unwrap();
            assert!(!staged.retained_local_writes.is_empty(),"positive retention path must be exercised");
        }
        // Mutable statics are tagged heap bytes; 80 is the frame-local slot
        // and 81 overlaps it partially. All are initialized valid addresses.
        for address in [crate::heap::TAG+16,80,81] { for persistent in [false,true] {
            let args=[address as u128,80];
            let expected=execute_with_engine(&p,&args,Limits::default(),Engine::Interpreter).unwrap();
            if !unselected && address==crate::heap::TAG+16 {assert_eq!(expected.value,23);}
            if unselected || address==80 {assert_eq!(expected.value,7);}
            for instructions in 0..=expected.instructions+1 {
                let limits=Limits {instructions,jit_resumable_calls:true,jit_persistent_registers:persistent,..Limits::default()};
                let reference=execute_with_engine(&p,&args,Limits {instructions,..Limits::default()},Engine::Interpreter);
                compare(execute_with_engine(&p,&args,limits,Engine::Jit),&reference);
            }
        }}
    }}
}

#[test]
fn emitted_preflight_matches_independent_complete_range_oracle() {
    let tag=crate::heap::TAG as u64;
    let mut code=platform::Code::reserve(2*1024*1024).unwrap();
    let reads=vec![Some((0,8));8];
    for heap in [false,true] {for slot in [false,true] {for write in [false,true] {
        for disjoint in [false,true] {for low in [-4096i64,-8,0,8,4096] {for span in [1usize,8,16,31,32,128,4096] {
            let mut a=Assembler {heap,resumable:true,frame_size:32,reads:&reads,..Assembler::default()};
            if heap {a.mov(7,5);a.mov(8,6);}
            let plan=Plan {root:if slot {Root::FrameSlot(3)} else {Root::Register(0)},
                low,high:low+span as i64,writes:write,frame_disjoint:disjoint,sites:vec![]};
            let declines=a.prepare_guarded_range(Some(&plan)).unwrap();
            a.mov(0,11);a.emit(0xd65f03c0);
            let target=a.words.len();a.mov(0,31);a.emit(0xd65f03c0);
            for at in declines {a.patch_conditional(at,target).unwrap();}
            let entry=code.append(&a.words).unwrap();
            for root in [0,1,8,24,31,32,56,63,64,67,80,88,95,96,127,128,248,255,256,
                tag-8,tag-1,tag,tag+1,tag+16,tag+184,tag+192,2*tag,3*tag,u64::MAX-7,u64::MAX] {
                let mut linear=vec![0xa5u8;256];let mut arena=vec![0x5au8;192];
                linear[67..75].copy_from_slice(&root.to_le_bytes());
                let before=linear.clone();let arena_before=arena.clone();
                let mut registers=vec![root as u128;8];
                let begin=root as i128+low as i128;let end=begin+span as i128;
                let expected=if begin<0 || end>u64::MAX as i128 {None} else {
                    let begin=begin as u64;let end=end as u64;
                    let in_heap=heap && begin>=tag;
                    let offset=if in_heap {begin-tag} else {begin};
                    let length=if in_heap {192} else {256};
                    if offset==0 || offset as u128+span as u128>length
                        || (heap && !in_heap && end>tag)
                        || (write && !in_heap && offset<32)
                        || (disjoint && !in_heap && offset<96 && offset+span as u64>64) {None}
                    else {Some((if in_heap {arena.as_ptr()} else {linear.as_ptr()}) as u64+offset)}
                };
                // SAFETY: this owned preflight leaf only reads the supplied
                // initialized slot and validates ranges; it never dereferences
                // a speculative pointee or writes guest/ABI storage.
                let actual=unsafe {code.call(entry,registers.as_mut_ptr(),64,linear.as_mut_ptr(),256,32,
                    arena.as_mut_ptr(),192,std::ptr::null_mut())};
                assert_eq!(actual,expected.unwrap_or(0),"heap {heap} slot {slot} write {write} disjoint {disjoint} low {low} span {span} root {root}");
                assert_eq!(linear,before);assert_eq!(arena,arena_before);
                assert_eq!(registers,vec![root as u128;8]);
            }
        }}}}}
    }
}

#[test]
fn cached_base_survives_every_fixed_copy_width_and_popcount() {
    for size in 0..=128 {for heap in [false,true] {
        let mut ops=vec![Op::Local {dst:2,offset:32},Op::Local {dst:3,offset:64}];
        for _ in 0..8 {ops.extend([load(7,0),Op::Unary {dst:6,op:Unary::CountOnes,src:7,bits:64},
            Op::Copy {dst:3,src:2,size}]);}
        let mut f=function(ops);f.frame_size=512;
        let plan=range_groups::runtime_plan(&f,0,f.code.len(),&mut 4_000_000).unwrap();
        let reads=read_registers(&f);
        let mut a=Assembler {heap,resumable:true,observe_scalar_copy:true,observe_static_local_facts:true,observe_guarded_local_retention:true,frame_size:512,reads:&reads,region_end:f.code.len(),..Assembler::default()};
        if heap {a.mov(7,5);a.mov(8,6);}
        let declines=a.prepare_guarded_range(Some(&plan)).unwrap();
        for (pc,op) in f.code.iter().enumerate() {a.current_pc=pc;a.lower(op);}
        a.guarded_base(0);a.emit(0xd65f03c0);
        let target=a.words.len();a.mov(0,31);a.emit(0xd65f03c0);
        for at in declines {a.patch_conditional(at,target).unwrap();}
        let mut code=platform::Code::reserve(128*1024).unwrap();let entry=code.append(&a.words).unwrap();
        let mut linear:Vec<_>=(0..1024).map(|i|(i%251) as u8).collect();let mut arena=vec![0x5a;192];
        let mut expected=linear.clone();for _ in 0..8 {expected.copy_within(160..160+size,192);}
        let pointer=if heap {crate::heap::TAG+16} else {16};let mut registers=vec![0u128;8];registers[0]=pointer as u128;
        let expected_base=if heap {arena.as_ptr() as u64+16} else {linear.as_ptr() as u64+16};
        // SAFETY: every selected read and complete local-copy extent belongs
        // to these stable initialized buffers; only caller-saved scratch is used.
        let result=unsafe {code.call(entry,registers.as_mut_ptr(),128,linear.as_mut_ptr(),1024,32,
            arena.as_mut_ptr(),192,std::ptr::null_mut())};
        assert_eq!(result,expected_base,"size {size} heap {heap}");assert_eq!(linear,expected);
        assert_eq!(arena,vec![0x5a;192]);
    }}
}

fn call_program()->Program {
    let mut root=function(vec![Op::Local {dst:0,offset:0},Op::Local {dst:1,offset:32},
        Op::Imm {dst:2,value:17},Op::Store {address:1,src:2,size:8},
        Op::Store {address:0,src:1,size:8},Op::Local {dst:3,offset:8},
        Op::Call {function:1,args:vec![0],destination:3},Op::Return]);
    root.args.clear();root.frame_size=96;
    let mut ops=vec![Op::Local {dst:0,offset:0},Op::Imm {dst:2,value:1}];
    for _ in 0..8 {ops.extend([load(1,0),load(4,1),
        Op::Binary {dst:4,overflow:5,op:Binary::Add,a:4,b:2,bits:64,signed:false},
        Op::Store {address:1,src:4,size:8}]);}
    ops.extend([Op::Local {dst:3,offset:8},Op::Store {address:3,src:4,size:8},Op::Return]);
    program(vec![root,function(ops)])
}

#[test]
fn guarded_calls_preserve_results_all_budgets_and_persistent_modes() {
    let p=call_program();crate::validate(&p).unwrap();
    let expected=execute_with_engine(&p,&[],Limits::default(),Engine::Interpreter).unwrap();
    assert_eq!(expected.value,25);
    for persistent in [false,true] {
        for instructions in 0..=expected.instructions+2 {
            let reference=execute_with_engine(&p,&[],Limits {instructions,..Limits::default()},Engine::Interpreter);
            compare(execute_with_engine(&p,&[],Limits {instructions,jit_resumable_calls:true,
                jit_persistent_registers:persistent,..Limits::default()},Engine::Jit),&reference);
        }
        let mut jit=Jit::new_resumable(&p,true,MAX_CODE_BYTES,persistent).unwrap();
        jit.ensure_function(0).unwrap();jit.ensure_function(1).unwrap();
        let map=serde_json::to_value(jit.operation_map().unwrap()).unwrap();
        assert!(map["functions"].as_array().unwrap().iter().flat_map(|f|f["spans"].as_array().unwrap())
            .any(|s|s["kind"]=="range_guard"));
    }
}

#[test]
fn stronger_guard_decline_preserves_an_earlier_store_and_assertion() {
    let mut ops=vec![Op::Local {dst:0,offset:0},load(1,0),Op::Imm {dst:2,value:42},
        Op::Store {address:1,src:2,size:8},load(4,1),
        Op::Binary {dst:6,overflow:7,op:Binary::Eq,a:4,b:2,bits:64,signed:false},
        Op::Assert {value:6,expected:false,message:"ordered store observed".into()},
        Op::Imm {dst:2,value:64},Op::Binary {dst:3,overflow:7,op:Binary::Add,a:1,b:2,bits:64,signed:false}];
    ops.extend(vec![load(4,3);8]);ops.push(Op::Return);
    let p=program(vec![function(ops)]);crate::validate(&p).unwrap();
    let reference=execute_with_engine(&p,&[80],Limits::default(),Engine::Interpreter);
    assert!(reference.as_ref().unwrap_err().contains("ordered store observed"));
    for persistent in [false,true] {
        compare(execute_with_engine(&p,&[80],Limits {jit_resumable_calls:true,
            jit_persistent_registers:persistent,..Limits::default()},Engine::Jit),&reference);
    }
}

#[test]
fn loop_entry_roots_and_same_frame_aliases_do_not_reuse_stale_values() {
    let mut ops=vec![Op::Local {dst:0,offset:0},Op::Imm {dst:2,value:80}];
    for _ in 0..8 {ops.extend([load(1,0),Op::Store {address:1,src:2,size:8}]);}
    ops.extend([load(4,1),Op::Local {dst:3,offset:8},Op::Store {address:3,src:4,size:8},Op::Return]);
    let p=program(vec![function(ops)]);
    for pointer in [64,72,80,88] {
        let expected=execute_with_engine(&p,&[pointer],Limits::default(),Engine::Interpreter);
        assert!(expected.is_ok());
        for persistent in [false,true] {
            compare(execute_with_engine(&p,&[pointer],Limits {jit_resumable_calls:true,
                jit_persistent_registers:persistent,..Limits::default()},Engine::Jit),&expected);
        }
    }
    // A linked backedge must run the preflight again with current slot bytes.
    let mut p=call_program();let f=&mut p.functions[1];let end=f.code.len()-1;
    f.code[end]=Op::Jump {target:0};
    for persistent in [false,true] {for instructions in [1,7,20,80,200,500] {
        compare(execute_with_engine(&p,&[],Limits {instructions,jit_resumable_calls:true,
            jit_persistent_registers:persistent,..Limits::default()},Engine::Jit),
            &execute_with_engine(&p,&[],Limits {instructions,..Limits::default()},Engine::Interpreter));
    }}
}
