//! Bounded, thread-local test observation after complete indirect-call validation.
use super::*;
use std::{cell::RefCell, collections::BTreeMap};

type Key = (usize, usize, usize, bool, bool, bool);
struct State { limit: usize, overflow: bool, rows: BTreeMap<Key, u64> }
thread_local! { static ACTIVE: RefCell<Option<State>> = const { RefCell::new(None) }; }

pub(super) fn record(caller: usize, pc: usize, target: usize, entry_ready: bool,
    continuation_ready: bool, local_arguments: bool) {
    ACTIVE.with(|active| {
        let mut active = active.borrow_mut();
        let Some(state) = active.as_mut() else { return; };
        let key = (caller, pc, target, entry_ready, continuation_ready, local_arguments);
        if let Some(count) = state.rows.get_mut(&key) {
            if let Some(next) = count.checked_add(1) { *count = next; }
            else { state.overflow = true; }
        } else if state.rows.len() < state.limit { state.rows.insert(key, 1); }
        else { state.overflow = true; }
    });
}

struct Guard(bool);
impl Guard {
    fn new(limit: usize) -> Self {
        assert!((1..=4096).contains(&limit));
        ACTIVE.with(|active| {
            assert!(active.borrow().is_none(), "nested indirect-call observer");
            *active.borrow_mut() = Some(State { limit, overflow: false, rows: BTreeMap::new() });
        });
        Self(true)
    }
    fn finish(mut self) -> State {
        self.0 = false;
        ACTIVE.with(|active| active.borrow_mut().take().unwrap())
    }
}
impl Drop for Guard {
    fn drop(&mut self) {
        if self.0 { ACTIVE.with(|active| *active.borrow_mut() = None); }
    }
}

fn fixture(pointer: u128, argument_size: usize, result_size: usize) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0;16], statics: vec![], thread_locals: vec![], functions: vec![
            Function { name: "indirect caller".into(), frame_size: 32, frame_align: 16,
                registers: 3, args: vec![Slot { offset: 16, size: 8 }], result: Slot { offset: 0, size: 8 },
                code: vec![Op::Local { dst: 0, offset: 16 }, Op::Imm { dst: 1, value: pointer },
                    Op::Local { dst: 2, offset: 0 },
                    Op::CallIndirect { callee: 1, args: vec![0], arg_sizes: vec![argument_size], destination: 2, result_size },
                    Op::CallIndirect { callee: 1, args: vec![0], arg_sizes: vec![argument_size], destination: 2, result_size },
                    Op::Return] },
            Function { name: "indirect target".into(), frame_size: 8, frame_align: 8,
                registers: 0, args: vec![Slot { offset: 0, size: 8 }], result: Slot { offset: 0, size: 8 },
                code: vec![Op::Return] } ] }
}

#[test]
fn indirect_trace_records_validated_targets_and_native_readiness() {
    let p = fixture((FUNCTION_POINTER_TAG | 2) as u128, 8, 8);
    let guard = Guard::new(16);
    let run = execute_with_engine(&p, &[81], Limits { jit_resumable_calls: true,
        jit_persistent_registers: true, ..Limits::default() }, Engine::Jit).unwrap();
    assert_eq!(run.value, 81);
    let state = guard.finish(); assert!(!state.overflow); assert_eq!(state.rows.len(), 2);
    let rows: Vec<_> = state.rows.iter().map(|(&(caller,pc,target,ready,next,_),&count)|
        (caller,pc,target,ready,next,count)).collect();
    assert_eq!(rows, [(0,3,1,false,false,1),(0,4,1,true,true,1)]);
    assert_eq!(run.jit_resumable_calls, 0); assert_eq!(run.jit_resumable_returns, 2);
}

#[test]
fn indirect_trace_does_not_observe_invalid_handles_or_signatures() {
    for (pointer, arg, result) in [(0,8,8),(FUNCTION_POINTER_TAG as u128,8,8),
        ((FUNCTION_POINTER_TAG|99) as u128,8,8),((1u128<<64)|((FUNCTION_POINTER_TAG|2) as u128),8,8),
        ((FUNCTION_POINTER_TAG|2) as u128,4,8),((FUNCTION_POINTER_TAG|2) as u128,8,4)] {
        for engine in [Engine::Interpreter, Engine::Jit] {
            let p=fixture(pointer,arg,result);let guard=Guard::new(16);
            assert!(execute_with_engine(&p,&[81],Limits {jit_resumable_calls:true,..Limits::default()},engine).is_err());
            let state=guard.finish();assert!(!state.overflow);assert!(state.rows.is_empty());
        }
    }
}

#[test]
fn indirect_trace_is_bounded_and_scope_cleanup_preserves_execution() {
    let p=fixture((FUNCTION_POINTER_TAG|2) as u128,8,8);
    let guard=Guard::new(1);
    assert_eq!(execute(&p,&[81],Limits::default()).unwrap().value,81);
    let state=guard.finish();assert!(state.overflow);assert_eq!(state.rows.len(),1);
    { let _discarded=Guard::new(1); }
    let guard=Guard::new(16);
    std::thread::spawn(move || { let child=Guard::new(16);
        assert_eq!(execute(&p,&[81],Limits::default()).unwrap().value,81);
        assert_eq!(child.finish().rows.values().sum::<u64>(),2);
    }).join().unwrap();
    assert!(guard.finish().rows.is_empty());
}

#[test]
#[ignore="Requires an exact saved artifact, entry catalog, entropy tape and profile comparison"]
fn observe_saved_indirect_targets() {
    use serde_json::json;
    use sha2::{Digest,Sha256};
    let bytes=std::fs::read(std::env::var("INDIRECT_ARTIFACT").unwrap()).unwrap();assert!(bytes.len()<=128*1024*1024);
    let mut program:Program=bincode::deserialize(&bytes).unwrap();validate(&program).unwrap();
    let catalog_bytes=std::fs::read(std::env::var("INDIRECT_CATALOG").unwrap()).unwrap();assert!(catalog_bytes.len()<=8*1024*1024);
    let catalog:EntryCatalog=serde_json::from_slice(&catalog_bytes).unwrap();
    let name=std::env::var("INDIRECT_TEST").unwrap();
    let entries=catalog.validated_entries(&program,&bytes).unwrap();
    let entry=entries.iter().find(|(n,_)|*n==name).unwrap().1;
    program.entry=entry;
    let limits=Limits { instructions:std::env::var("INDIRECT_INSTRUCTIONS").unwrap().parse().unwrap(),
        allocations:std::env::var("INDIRECT_ALLOCATIONS").unwrap().parse().unwrap(),
        jit_resumable_calls:true,jit_persistent_registers:true,
        jit_code_dump:Some(std::env::var("INDIRECT_CODE").unwrap().into()),jit_operation_map:true,
        ..Limits::default() };
    let guard=Guard::new(4096);
    let (run,profile)=execute_profiled(&program,&[],limits,Engine::Jit).unwrap();
    assert_eq!(run.value,0);
    let state=guard.finish();assert!(!state.overflow);
    let rows:Vec<_>=state.rows.into_iter().map(|((caller,pc,target,entry_ready,continuation_ready,local_arguments),count)| {
        assert!(matches!(program.functions[caller].code[pc],Op::CallIndirect {..}));
        json!({"caller":caller,"caller_name":program.functions[caller].name,"pc":pc,
            "target":target,"target_name":program.functions[target].name,"entry_ready":entry_ready,
            "continuation_ready":continuation_ready,"local_arguments":local_arguments,"count":count})
    }).collect();
    let write=|variable:&str,value:&serde_json::Value| {
        let file=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var(variable).unwrap()).unwrap();
        serde_json::to_writer(std::io::BufWriter::new(file),value).unwrap();
    };
    write("INDIRECT_PROFILE",&serde_json::to_value(profile).unwrap());
    write("INDIRECT_REPORT",&json!({"status":"passed","pid":std::process::id(),"name":name,"entry":entry,
        "artifact_sha256":format!("{:x}",Sha256::digest(&bytes)),
        "catalog_sha256":format!("{:x}",Sha256::digest(&catalog_bytes)),"rows":rows,
        "overflow":false,"max_keys":4096,"statistics":{
            "instructions":run.instructions,"peak_guest_memory":run.peak_memory,
            "jit_instructions":run.jit_instructions,"jit_entries":run.jit_entries,
            "jit_resumable_calls":run.jit_resumable_calls,"jit_resumable_returns":run.jit_resumable_returns,
            "jit_bytes":run.jit_bytes,"jit_compiled_functions":run.jit_compiled_functions,
            "jit_declined_functions":run.jit_declined_functions},
        "guest_commands":1,"performance_measurement":false}));
}
