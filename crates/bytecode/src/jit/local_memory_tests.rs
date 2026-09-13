use super::*;
use crate::{Engine, Limits, Slot, VERSION, execute_profiled, execute_with_engine};

const WIDE: u128 = 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef;

fn program(code: Vec<Op>, registers: usize, args: usize) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0;64], statics: vec![], thread_locals: vec![],
        functions: vec![Function { name: "local_forwarding".into(), frame_size: 512, frame_align: 16,
            registers, args: (0..args).map(|n| Slot {offset:16+n*16,size:16}).collect(),
            result: Slot {offset:0,size:16}, code }] }
}
fn output(code: &mut Vec<Op>, value: Reg) {
    code.extend([Op::Local {dst:30,offset:0}, Op::Store {address:30,src:value,size:16}, Op::Return]);
}
fn events(p: &Program) -> Vec<(usize,&'static str)> {
    Jit::new(p,false,MAX_CODE_BYTES).unwrap().emit_function(&p.functions[0],MAX_CODE_BYTES/4)
        .unwrap().unwrap().local_forwarding
}
fn check(p: &Program, args: &[u128], value: Option<u128>, max: u64) {
    crate::validate(p).unwrap();
    let result=execute_with_engine(p,args,Limits {instructions:max,..Limits::default()},Engine::Interpreter);
    if let Some(value)=value { assert_eq!(result.unwrap().value,value); } else { assert!(result.is_err()); }
    let budgets:Vec<u64>=if max<160 {(0..=max).collect()} else {vec![0,1,2,3,1022,1023,1024,1025,1026,max-2,max-1,max]};
    for budget in budgets { for capacity in [0,MAX_CODE_BYTES] { for persistent in [false,true] {
        let limits=|| Limits {instructions:budget,jit_code_bytes:capacity,..Limits::default()};
        let reference=execute_profiled(p,args,limits(),Engine::Interpreter);
        let limits=|| Limits {jit_persistent_registers:persistent,..limits()};
        let normal=execute_with_engine(p,args,limits(),Engine::Jit);
        let observed=execute_profiled(p,args,limits(),Engine::Jit);
        match reference {
            Err(error)=> {
                let compare=|actual:String| {
                    // Retained JIT consolidates these two memory errors into
                    // one fixed native fault code. Budgets and all other
                    // faults still require their exact original messages.
                    let memory=matches!(error.as_str(),"invalid guest memory access"|"write to read-only guest memory");
                    assert!(actual==error || (capacity!=0 && memory && actual=="JIT guest memory access failed"),
                        "budget={budget} capacity={capacity}: {actual:?} != {error:?}");
                };
                compare(normal.unwrap_err());compare(observed.unwrap_err());
            },
            Ok((reference,reference_profile))=> {
                let normal=normal.unwrap(); let (observed,profile)=observed.unwrap();
                assert_eq!(normal.value,reference.value,"budget={budget}");
                assert_eq!(observed.value,reference.value);
                assert_eq!(normal.instructions,reference.instructions);
                assert_eq!(observed.instructions,reference.instructions);
                assert_eq!(normal.jit_entries,observed.jit_entries);
                assert_eq!(normal.jit_instructions,observed.jit_instructions);
                for (f,r) in profile.functions.iter().zip(&reference_profile.functions) {
                    let mut logical=f.interpreted.clone();
                    for (start,&hits) in f.jit_blocks.iter().enumerate() {
                        if hits!=0 { for count in &mut logical[start..f.jit_block_ends[start]] {*count+=hits;} }
                    }
                    assert_eq!(logical,r.interpreted);
                }
            }
        }
    }}}
}
fn low(value:u128,size:usize)->u128 {if size==16 {value} else {value & ((1u128<<(size*8))-1)}}

#[test]
fn local_scalar_roundtrips_truncate_and_zero_extend_all_widths() {
    for size in 0..=16 { for copied in [false,true] { for value in [0,WIDE,u128::MAX] {
        let mut code=vec![Op::Local {dst:0,offset:16},Op::Load {dst:1,address:0,size:16},
            Op::Local {dst:2,offset:129},Op::Store {address:2,src:1,size:size as u8}];
        let address=if copied {code.extend([Op::Local {dst:3,offset:161},Op::Copy {dst:3,src:2,size}]);3} else {2};
        code.push(Op::Load {dst:4,address,size:size as u8});output(&mut code,4);
        let p=program(code,31,1);check(&p,&[value],Some(low(value,size)),15);
        let forwarded=events(&p);
        if [1,2,4,8].contains(&size) {
            assert!(forwarded.iter().any(|e| e.1=="Load"));
            assert_eq!(forwarded.iter().any(|e| e.1=="Copy"),copied);
        } else { assert!(forwarded.is_empty()); }
    }}}
}

#[test]
fn repeated_local_loads_and_register_address_aliases_keep_old_values() {
    for size in [1,2,4,8] { for dst in [0,1,2] {
        let mut code=vec![Op::Local {dst:0,offset:16},Op::Load {dst:1,address:0,size},
            Op::Load {dst,address:0,size},Op::Local {dst:29,offset:200},
            Op::Store {address:29,src:1,size:8}];output(&mut code,dst);
        let p=program(code,31,1);assert!(events(&p).contains(&(2,"Load")));
        check(&p,&[WIDE],Some(low(WIDE,size as usize)),10);
    }}
    // Overwrite the register that used to describe the stored bytes.
    for dynamic in [false,true] {
        let mut code=vec![Op::Local {dst:0,offset:128},Op::Imm {dst:1,value:17},Op::Store {address:0,src:1,size:8}];
        if dynamic {code.extend([Op::Local {dst:2,offset:16},Op::Load {dst:1,address:2,size:8}]);}
        else {code.push(Op::Imm {dst:1,value:99});}
        let load=code.len();code.push(Op::Load {dst:3,address:0,size:8});output(&mut code,3);
        let p=program(code,31,1);assert!(!events(&p).contains(&(load,"Load")));
        check(&p,&[99],Some(17),14);
    }
}

#[test]
fn partial_and_unknown_alias_writes_invalidate_the_right_ranges() {
    for unknown in [false,true] { for delta in [0,1,3,7,8,15] { for size in [1,2,4,8,16] {
        let mut bytes=[0u8;40];bytes[..8].copy_from_slice(&(WIDE as u64).to_le_bytes());
        bytes[delta..delta+size].copy_from_slice(&(!WIDE).to_le_bytes()[..size]);
        let expected=u64::from_le_bytes(bytes[..8].try_into().unwrap()) as u128;
        let mut code=vec![Op::Local {dst:0,offset:128},Op::Imm {dst:1,value:WIDE},Op::Store {address:0,src:1,size:8},
            Op::Local {dst:2,offset:128+delta},Op::Imm {dst:3,value:!WIDE}];
        let address=if unknown {
            code.extend([Op::Local {dst:4,offset:112},Op::Store {address:4,src:2,size:8},Op::Load {dst:5,address:4,size:8}]);5
        } else {2};
        code.push(Op::Store {address,src:3,size:size as u8});
        let load=code.len();code.push(Op::Load {dst:6,address:0,size:8});output(&mut code,6);
        let p=program(code,31,0);check(&p,&[],Some(expected),18);
        // Exact same-width replacement can itself be forwarded.
        if unknown {assert!(!events(&p).contains(&(load,"Load")));}
        if !unknown && delta>=8 {assert!(events(&p).contains(&(load,"Load")));}
    }}}
}

#[test]
fn forwarded_overlapping_copies_preserve_memmove_source_capture() {
    for delta in [-7isize,-1,0,1,3,7,8] {
        let target=(128isize+delta) as usize;
        let mut bytes=[0u8;40];bytes[8..16].copy_from_slice(&(WIDE as u64).to_le_bytes());
        bytes.copy_within(8..16,target-120);
        let after=u64::from_le_bytes(bytes[8..16].try_into().unwrap()) as u128;
        let mut code=vec![Op::Local {dst:0,offset:128},Op::Imm {dst:1,value:WIDE},Op::Store {address:0,src:1,size:8},
            Op::Local {dst:2,offset:target},Op::Copy {dst:2,src:0,size:8},Op::Load {dst:3,address:2,size:8},
            Op::Load {dst:4,address:0,size:8},Op::Binary {dst:5,overflow:6,op:Binary::Sub,a:4,b:3,bits:128,signed:false}];
        output(&mut code,5);let p=program(code,31,0);
        assert!(events(&p).contains(&(4,"Copy")));
        check(&p,&[],Some(after.wrapping_sub(WIDE as u64 as u128)),15);
    }
}

#[test]
fn evicted_dead_sources_are_never_reloaded_from_unspilled_register_slots() {
    for width in [8,16] { for r in [0,2050] {
        let mut code=vec![Op::Local {dst:r,offset:16},Op::Load {dst:r+1,address:r,size:width},
            Op::Local {dst:r+2,offset:128},Op::Store {address:r+2,src:r+1,size:8},
            Op::Local {dst:r,offset:32},Op::Load {dst:r+3,address:r,size:8},
            Op::Local {dst:r,offset:48},Op::Load {dst:r+4,address:r,size:8},
            Op::Load {dst:r+5,address:r+2,size:8},
            Op::Binary {dst:r+6,overflow:r+7,op:Binary::Add,a:r+3,b:r+4,bits:64,signed:false},
            Op::Binary {dst:r+8,overflow:r+9,op:Binary::Add,a:r+5,b:r+6,bits:64,signed:false}];
        output(&mut code,r+8);let p=program(code,(r as usize+10).max(31),3);
        assert!(!events(&p).contains(&(8,"Load")));
        check(&p,&[WIDE,17,31],Some((WIDE as u64).wrapping_add(48) as u128),17);
    }}
}

#[test]
fn fused_fill_and_wide_copies_invalidate_without_clobbering_live_cache_values() {
    for size in [1,7,8,16,17,24,32,33,64,128] { for fill in [false,true] {
        let mut code=vec![Op::Local {dst:0,offset:128},Op::Imm {dst:1,value:WIDE},Op::Store {address:0,src:1,size:8}];
        let expected=if fill {
            code.extend([Op::Local {dst:2,offset:128},Op::Imm {dst:3,value:0xab},Op::Imm {dst:4,value:size as u128},
                Op::FillBytes {address:2,value:3,size:4}]);
            let mut bytes=(WIDE as u64).to_le_bytes();bytes[..size.min(8)].fill(0xab);u64::from_le_bytes(bytes) as u128
        } else {
            code.extend([Op::Local {dst:2,offset:256},Op::Copy {dst:0,src:2,size}]);
            let mut bytes=(WIDE as u64).to_le_bytes();bytes[..size.min(8)].fill(0);u64::from_le_bytes(bytes) as u128
        };
        let load=code.len();code.push(Op::Load {dst:5,address:0,size:8});output(&mut code,5);
        let p=program(code,31,0);assert!(!events(&p).contains(&(load,"Load")));
        check(&p,&[],Some(expected),15);
    }}
}

#[test]
fn branches_and_region_splits_reload_changed_local_storage() {
    let p=program(vec![Op::Local {dst:0,offset:128},Op::Local {dst:1,offset:16},Op::Load {dst:2,address:1,size:8},
        Op::Store {address:0,src:2,size:8},Op::Imm {dst:3,value:1},Op::Jump {target:6},
        Op::Local {dst:0,offset:128},Op::Load {dst:2,address:0,size:8},
        Op::Binary {dst:2,overflow:4,op:Binary::Sub,a:2,b:3,bits:64,signed:false},
        Op::Store {address:0,src:2,size:8},Op::Switch {value:2,cases:vec![(0,11)],otherwise:6},
        Op::Local {dst:0,offset:128},Op::Load {dst:5,address:0,size:8},
        Op::Local {dst:30,offset:0},Op::Store {address:30,src:5,size:16},Op::Return],31,1);
    for n in [1,2,5] {check(&p,&[n],Some(0),40);}
    assert!(!events(&p).contains(&(7,"Load")));
    let mut code=vec![Op::Local {dst:0,offset:128},Op::Imm {dst:1,value:91},Op::Store {address:0,src:1,size:8}];
    while code.len()<1024 {code.push(Op::Imm {dst:2,value:0});}
    code.extend([Op::Local {dst:0,offset:128},Op::Load {dst:3,address:0,size:8}]);output(&mut code,3);
    let p=program(code,31,0);assert!(!events(&p).contains(&(1025,"Load")));check(&p,&[],Some(91),1032);
}

#[test]
fn call_and_tls_fallback_boundaries_preserve_frame_updates() {
    for tls in [false,true] {
        let mut code=vec![Op::Local {dst:0,offset:128},Op::Imm {dst:1,value:17},Op::Store {address:0,src:1,size:8}];
        if tls {code.push(Op::ResetThreadLocals);} else {code.push(Op::Call {function:1,args:vec![],destination:0});}
        code.extend([Op::Local {dst:0,offset:128},Op::Load {dst:2,address:0,size:8}]);output(&mut code,2);
        let mut p=program(code,31,0);
        if !tls {p.functions.push(Function {name:"return99".into(),frame_size:16,frame_align:16,registers:2,args:vec![],result:Slot {offset:0,size:8},
            code:vec![Op::Local {dst:0,offset:0},Op::Imm {dst:1,value:99},Op::Store {address:0,src:1,size:8},Op::Return]});}
        assert!(!events(&p).contains(&(5,"Load")));check(&p,&[],Some(if tls {17} else {99}),20);
    }
}

#[test]
fn forwarded_copy_keeps_destination_faults_and_exact_budget_order() {
    for bad in [0,1,64,u64::MAX as u128] { for size in [0,1,2,4,8] {
        let mut code=vec![Op::Local {dst:0,offset:128},Op::Imm {dst:1,value:WIDE},Op::Store {address:0,src:1,size:size as u8},
            Op::Imm {dst:2,value:bad},Op::Copy {dst:2,src:0,size}];
        code.extend([Op::Imm {dst:3,value:7}]);output(&mut code,3);
        let p=program(code,31,0);if size!=0 {assert!(events(&p).contains(&(4,"Copy")));}
        // With64 read-only bytes and16-byte alignment, this frame starts
        // at64. That address is writable; the other nonempty destinations
        // fault. Zero-byte copies accept every address without dereferencing.
        let expected=if size==0 || bad==64 {Some(7)} else {None};
        check(&p,&[],expected,12);
    }}
    // A Local fact outside the proved frame extent must take the original check.
    let mut code=vec![Op::Local {dst:0,offset:511},Op::Imm {dst:1,value:WIDE},Op::Store {address:0,src:1,size:8},
        Op::Load {dst:2,address:0,size:8}];output(&mut code,2);
    let p=program(code,31,0);assert!(events(&p).is_empty());check(&p,&[],None,10);
}

#[test]
fn bounded_value_table_preserves_register_ownership_and_cache_recency() {
    let mut a=Assembler {frame_size:512,..Assembler::default()};
    for i in 0..40 {a.facts.insert(i,Fact::Imm(i as u128));a.remember_local_memory(Some(i as usize*8),8,i);}
    assert_eq!(a.local_values.len(),16);
    assert!(a.local_value(Some(0),8).is_none());assert!(a.local_value(Some(39*8),8).is_some());
    a.forget_cached(39);assert!(a.local_value(Some(39*8),8).is_none());
    a.cache_recent=1;a.forward_local_value(Fact::Cached {lo:5,high_zero:true},1,"Load");assert_eq!(a.cache_recent,1);
    a.invalidate_local_memory(None,0);assert_eq!(a.local_values.len(),15);
    a.invalidate_local_memory(None,1);assert!(a.local_values.is_empty());
}

#[test]
#[ignore = "Explicit typed census of saved real bytecode; requires artifact paths"]
fn observe_local_forwarding_in_original_artifact() {
    let input=std::env::var("LOCAL_FORWARD_INPUT").unwrap();let output=std::env::var("LOCAL_FORWARD_OUTPUT").unwrap();
    let p:Program=bincode::deserialize(&std::fs::read(&input).unwrap()).unwrap();crate::validate(&p).unwrap();
    let jit=Jit::new(&p,false,MAX_CODE_BYTES).unwrap();let mut rows=vec![];
    for (id,f) in p.functions.iter().enumerate() {
        let Some(staged)=jit.emit_function(f,usize::MAX).unwrap() else {panic!("unbounded staging declined")};
        let sites:Vec<_>=staged.local_forwarding.iter().map(|&(pc,kind)| {
            let size=match f.code[pc] {Op::Load {size,..}=>size as usize,Op::Copy {size,..}=>size,_=>panic!("unreviewed forwarding opcode")};
            serde_json::json!({"pc":pc,"kind":kind,"size":size})
        }).collect();
        rows.push(serde_json::json!({"id":id,"name":f.name,"native_bytes":staged.words.len()*4,"sites":sites}));
    }
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(output).unwrap();
    serde_json::to_writer(file,&serde_json::json!({"input":input,"functions":rows})).unwrap();
}

#[test]
#[ignore = "Offline emission diagnosis; requires a bound artifact and function ID"]
fn observe_unpublished_function_emission() {
    let input = std::env::var("EMISSION_INPUT").unwrap();
    let output = std::env::var("EMISSION_OUTPUT").unwrap();
    let id: usize = std::env::var("EMISSION_FUNCTION").unwrap().parse().unwrap();
    let bytes = std::fs::read(&input).unwrap();
    assert!(bytes.len() <= 128 * 1024 * 1024);
    let p: Program = bincode::deserialize(&bytes).unwrap();
    crate::validate(&p).unwrap();
    let f = &p.functions[id];
    let mut rows = vec![];
    for profiled in [false, true] {
        let jit = Jit::new_resumable(&p, profiled, MAX_CODE_BYTES, true).unwrap();
        assert!(jit.resumable.as_ref().unwrap().fits(f.code.len()));
        // The larger allowance applies only to unexecuted staging words.
        // No arena, entry or native instruction is published or run here.
        for bytes in [MAX_CODE_BYTES, MAX_CODE_BYTES * 4] {
            let outcome = match jit.emit_function_inner(f, bytes / 4, 0, None) {
                Ok(Some(staged)) => serde_json::json!({"status":"emitted",
                    "code_bytes":staged.words.len()*4,"operations":staged.operations,
                    "entries":staged.entries.iter().filter(|r|r.is_some()).count()}),
                Ok(None) => serde_json::json!({"status":"code-budget-declined"}),
                Err(error) => serde_json::json!({"status":"emitter-error","reason":format!("{error:?}")}),
            };
            assert!(jit.code.is_none() && jit.bytes == 0 && jit.assertions.is_empty());
            rows.push(serde_json::json!({"profiled":profiled,"word_budget_bytes":bytes,"outcome":outcome}));
        }
    }
    let file = std::fs::OpenOptions::new().write(true).create_new(true).open(output).unwrap();
    serde_json::to_writer(file, &serde_json::json!({"function":id,"name":f.name,
        "operations":f.code.len(),"registers":f.registers,"frame_size":f.frame_size,
        "fresh_resume_table_fits":true,"published_or_executed":false,"observations":rows})).unwrap();
}

#[test]
fn forwarded_copy_fault_writes_only_the_preceding_store() {
    for heap in [false,true] { for profiled in [false,true] { for bad in [0,1,63,569,576,u64::MAX] {
        let mut p=program(vec![Op::Local {dst:0,offset:128},Op::Imm {dst:1,value:WIDE},Op::Store {address:0,src:1,size:8},
            Op::Imm {dst:2,value:bad as u128},Op::Copy {dst:2,src:0,size:8},Op::Imm {dst:3,value:7},Op::Return],31,0);
        if heap {p.statics=vec![0;16];}
        crate::validate(&p).unwrap();assert!(events(&p).contains(&(4,"Copy")));
        let mut jit=Jit::new(&p,profiled,MAX_CODE_BYTES).unwrap();jit.ensure_function(0).unwrap();
        let mut bytes=vec![0x5a;576];let mut heap_bytes=vec![0x3c;16];let saved_heap=heap_bytes.clone();
        let mut expected=bytes.clone();expected[192..200].copy_from_slice(&(WIDE as u64).to_le_bytes());
        let mut registers=vec![0u128;31];let mut hits=vec![0u64;7];
        let error=unsafe {jit.run(jit.blocks[0][0].unwrap(),7,6,
            if profiled {hits.as_mut_ptr()} else {std::ptr::null_mut()},registers.as_mut_ptr(),64,
            bytes.as_mut_ptr(),bytes.len(),64,heap_bytes.as_mut_ptr(),heap_bytes.len())}.unwrap_err();
        assert_eq!(error,"JIT guest memory access failed");assert_eq!(bytes,expected);assert_eq!(heap_bytes,saved_heap);
    }}}
}
