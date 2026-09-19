#![cfg(all(feature="jit-template-session",target_arch="aarch64",target_os="macos"))]
use rust_interp_bytecode::{Engine,Function,Limits,Op,PreparedJit,Program,Slot,TemplateHistory,
    VERSION,PARTIAL_VALIDATION,execute_with_engine};

fn limits()->Limits {Limits{jit_resumable_calls:true,jit_persistent_registers:true,jit_scalar_calls:true,..Default::default()}}
fn program(value:u128,data:u8)->Program {
    let mut bytes=vec![0;16];bytes[8]=data;
    Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:bytes,statics:vec![],thread_locals:vec![],
        functions:vec![
            Function{name:"caller".into(),frame_size:16,frame_align:8,registers:4,args:vec![],result:Slot{offset:0,size:16},
                code:vec![Op::Local{dst:0,offset:0},Op::Call{function:1,args:vec![],destination:0},
                    Op::Load{dst:1,address:0,size:8},Op::Assert{value:1,expected:true,message:"current caller assertion".into()},
                    Op::Imm{dst:1,value:8},Op::Load{dst:2,address:1,size:8},Op::Local{dst:3,offset:8},
                    Op::Store{address:3,src:2,size:8},Op::Return]},
            Function{name:"callee".into(),frame_size:8,frame_align:8,registers:2,args:vec![],result:Slot{offset:0,size:8},
                code:vec![Op::Local{dst:0,offset:0},Op::Imm{dst:1,value},Op::Store{address:0,src:1,size:8},Op::Return]}]}
}
fn equal(a:Result<rust_interp_bytecode::Execution,String>,b:Result<rust_interp_bytecode::Execution,String>) {
    match (a,b) {
        (Ok(a),Ok(b))=>assert_eq!((a.value,a.instructions,a.peak_memory),(b.value,b.instructions,b.peak_memory)),
        (Err(a),Err(b))=>assert_eq!(a,b),
        (a,b)=>panic!("execution outcomes differ: {a:?}, {b:?}"),
    }
}

#[test]
fn caller_templates_survive_changed_callees_data_and_dropped_original_owners() {
    for verify in [false,true] {
        let history=TemplateHistory::new(64*1024*1024,verify).unwrap();
        let original=program(7,11);
        let mut kept=PreparedJit::with_template_history(&original,&limits(),&history).unwrap();
        equal(kept.execute(&[],limits()),execute_with_engine(&original,&[],limits(),Engine::Interpreter));
        let mut hits=0;
        for value in [8,9,0,10] {
            let current=program(value,17);let mut owner=PreparedJit::with_template_history(&current,&limits(),&history).unwrap();
            for _ in 0..2 {
                let mut fresh=PreparedJit::new(&current,&limits()).unwrap();
                equal(owner.execute(&[],limits()),fresh.execute(&[],limits()));
            }
            let stats=owner.template_statistics().unwrap();hits+=stats.hits;
            assert_eq!(stats.verified_hits,if verify {stats.hits} else {0});
        }
        assert!(hits>0);drop(kept);drop(original);
        let restored=program(7,21);let mut owner=PreparedJit::with_template_history(&restored,&limits(),&history).unwrap();
        equal(owner.execute(&[],limits()),execute_with_engine(&restored,&[],limits(),Engine::Interpreter));
        assert!(owner.template_statistics().unwrap().hits>0);
    }
}

#[test]
fn reused_templates_preserve_current_budgets_modes_and_assertion_text() {
    let history=TemplateHistory::new(64*1024*1024,true).unwrap();
    for value in [7,0,7] {for persistent in [false,true] {for scalar in [false,true] {
        let mut current=program(value,13);
        if value==0 {let Op::Assert{message,..}=&mut current.functions[0].code[3] else {panic!()};*message="edited failure".into();}
        for bytes in [0,256,16*1024*1024] {
            let base=Limits{jit_code_bytes:bytes,jit_persistent_registers:persistent,jit_scalar_calls:scalar,..limits()};
            let mut owner=PreparedJit::with_template_history(&current,&base,&history).unwrap();
            for instructions in [0,1,4,12,100] {for frames in [1,3] {
                let run=Limits{instructions,frames,..base.clone()};let mut fresh=PreparedJit::new(&current,&base).unwrap();
                equal(owner.execute(&[],run.clone()),fresh.execute(&[],run));
            }}
            for memory in [128,4096] {
                let run=Limits{memory,..base.clone()};let mut fresh=PreparedJit::new(&current,&base).unwrap();
                equal(owner.execute(&[],run.clone()),fresh.execute(&[],run));
            }
        }
    }}}
}

#[test]
fn validation_and_partial_headers_cannot_use_an_existing_history() {
    assert!(TemplateHistory::new(511,false).is_err());assert!(TemplateHistory::new(64*1024*1024+1,false).is_err());
    let history=TemplateHistory::new(1024*1024,false).unwrap();let current=program(7,1);
    let mut owner=PreparedJit::with_template_history(&current,&limits(),&history).unwrap();owner.execute(&[],limits()).unwrap();
    let before=history.storage();
    let mut partial=current.clone();partial.version|=PARTIAL_VALIDATION;
    assert!(PreparedJit::with_template_history(&partial,&limits(),&history).is_err());
    let mut invalid=current.clone();invalid.functions[0].registers=0;
    assert!(PreparedJit::with_template_history(&invalid,&limits(),&history).is_err());
    assert!(PreparedJit::with_template_history(&current,&Limits::default(),&history).is_err());
    assert_eq!(before.entries,history.storage().entries);
    assert_eq!(before.charged_bytes,history.storage().charged_bytes);
    assert!(PreparedJit::new(&current,&limits()).unwrap().template_statistics().is_none());
}

#[test]
fn full_or_dropped_storage_preserves_fresh_execution() {
    for capacity in [512,4096,64*1024*1024] {
        let history=TemplateHistory::new(capacity,true).unwrap();
        for value in 1..10 {
            let current=program(value,19);let mut owner=PreparedJit::with_template_history(&current,&limits(),&history).unwrap();
            equal(owner.execute(&[],limits()),execute_with_engine(&current,&[],limits(),Engine::Interpreter));
            assert!(history.storage().charged_bytes<=capacity);
            if capacity==512 {let stats=owner.template_statistics().unwrap();assert_eq!(stats.hits,0);assert!(stats.capture_declines>0);}
        }
        let current=program(9,27);let mut owner=PreparedJit::with_template_history(&current,&limits(),&history).unwrap();
        drop(history);
        equal(owner.execute(&[],limits()),execute_with_engine(&current,&[],limits(),Engine::Interpreter));
    }
}
