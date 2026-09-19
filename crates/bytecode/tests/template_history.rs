#![cfg(all(feature="jit-template-session",target_arch="aarch64",target_os="macos"))]
use rust_interp_bytecode::{Engine,Function,Limits,Op,PreparedJit,Program,Slot,TemplateHistory,
    VERSION,PARTIAL_VALIDATION,ValidatedProgram,execute_with_engine};

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
        equal(kept.execute(&[],limits()),execute_with_engine(&original,&[],Limits::default(),Engine::Interpreter));
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
        equal(owner.execute(&[],limits()),execute_with_engine(&restored,&[],Limits::default(),Engine::Interpreter));
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
            equal(owner.execute(&[],limits()),execute_with_engine(&current,&[],Limits::default(),Engine::Interpreter));
            assert!(history.storage().charged_bytes<=capacity);
            if capacity==512 {let stats=owner.template_statistics().unwrap();assert_eq!(stats.hits,0);assert!(stats.capture_declines>0);}
        }
        let current=program(9,27);let mut owner=PreparedJit::with_template_history(&current,&limits(),&history).unwrap();
        drop(history);
        equal(owner.execute(&[],limits()),execute_with_engine(&current,&[],Limits::default(),Engine::Interpreter));
    }
}

fn environment_program()->Program {
    let mut p=program(7,0);p.data.extend_from_slice(b"SESSION_VALUE\0");
    p.functions[0].result.size=8;
    p.functions[0].code=vec![Op::Imm{dst:0,value:16},Op::EnvironmentGet{dst:1,name:0},
        Op::Load{dst:2,address:1,size:1},Op::Local{dst:3,offset:0},Op::Store{address:3,src:2,size:8},Op::Return];p
}

#[test]
fn request_environment_is_owned_current_and_independent_of_reused_code() {
    let history=TemplateHistory::new(1024*1024,true).unwrap();let p=environment_program();let mut hits=0;
    for value in [b'a',b'b',b'c'] {
        let mut input=vec![(b"SESSION_VALUE".to_vec(),vec![value])];
        let mut owner=PreparedJit::with_session_inputs(&p,&limits(),Some(&history),&input).unwrap();
        let mut fresh=PreparedJit::with_session_inputs(&p,&limits(),None,&input).unwrap();
        input[0].1[0]=b'z';drop(input);
        for _ in 0..2 {
            let actual=owner.execute(&[],limits()).unwrap();assert_eq!(actual.value,value as u128);
            equal(Ok(actual),fresh.execute(&[],limits()));
        }
        let counts=owner.template_statistics().unwrap();hits+=counts.hits;assert_eq!(counts.hits,counts.verified_hits);
    }
    assert!(hits>0);
    let mut missing=PreparedJit::with_session_inputs(&p,&limits(),Some(&history),&[]).unwrap();
    let mut reference=PreparedJit::with_session_inputs(&p,&limits(),None,&[]).unwrap();
    equal(missing.execute(&[],limits()),reference.execute(&[],limits()));
}

#[test]
fn request_snapshot_rejection_does_not_mutate_history_or_host_environment() {
    let history=TemplateHistory::new(1024*1024,true).unwrap();let p=environment_program();
    let host=std::env::var_os("SESSION_VALUE");
    for pairs in [vec![(b"BAD\0".to_vec(),vec![])],vec![(b"SESSION_VALUE".to_vec(),vec![1;4096])]] {
        let small=Limits{memory:1024,..limits()};
        assert!(PreparedJit::with_session_inputs(&p,&small,Some(&history),&pairs).is_err());
        assert!(PreparedJit::with_session_inputs(&p,&small,None,&pairs).is_err());
        assert_eq!(history.storage().entries,0);
    }
    let mut partial=p.clone();partial.version|=PARTIAL_VALIDATION;
    assert!(PreparedJit::with_session_inputs(&partial,&limits(),None,&[]).is_err());
    let input=vec![(b"SESSION_VALUE".to_vec(),b"v".to_vec())];
    let mut owner=PreparedJit::with_session_inputs(&p,&limits(),Some(&history),&input).unwrap();
    assert_eq!(owner.execute(&[],limits()).unwrap().value,b'v' as u128);
    assert_eq!(std::env::var_os("SESSION_VALUE"),host);
}

#[test]
fn shared_validation_preserves_worker_environments_budgets_and_fresh_guests() {
    let checked=std::sync::Arc::new(ValidatedProgram::new(environment_program()).unwrap());
    let mut handles=vec![];
    for value in [b'a',b'b'] {
        let checked=checked.clone();
        handles.push(std::thread::spawn(move || {
            let history=TemplateHistory::new(1024*1024,true).unwrap();
            for current in [value,value+1,value] {
                let input=vec![(b"SESSION_VALUE".to_vec(),vec![current])];
                for retained in [None,Some(&history)] {
                    let mut owner=PreparedJit::with_validated_session_inputs(&checked,&limits(),retained,&input).unwrap();
                    let mut reference=PreparedJit::with_session_inputs(checked.program(),&limits(),None,&input).unwrap();
                    for budget in [0,1000,1,1000] {
                        let run=Limits{instructions:budget,..limits()};
                        equal(owner.execute(&[],run.clone()),reference.execute(&[],run));
                    }
                    assert_eq!(owner.execute(&[],limits()).unwrap().value,current as u128);
                }
            }
            assert!(history.storage().entries>0);
        }));
    }
    for handle in handles {handle.join().unwrap();}
}

#[test]
fn shared_validation_cannot_admit_invalid_programs_or_bypass_current_runtime_limits() {
    let mut invalid=program(7,1);invalid.functions[0].registers=0;
    assert!(ValidatedProgram::new(invalid).is_err());
    let mut partial=program(7,1);partial.version|=PARTIAL_VALIDATION;
    assert!(ValidatedProgram::new(partial).is_err());
    let checked=ValidatedProgram::new(environment_program()).unwrap();
    let history=TemplateHistory::new(1024*1024,true).unwrap();
    for retained in [None,Some(&history)] {
        assert!(PreparedJit::with_validated_session_inputs(&checked,&Limits::default(),retained,&[]).is_err());
        let small=Limits{memory:1024,..limits()};
        let bad=vec![(b"SESSION_VALUE".to_vec(),vec![1;4096])];
        assert!(PreparedJit::with_validated_session_inputs(&checked,&small,retained,&bad).is_err());
    }
    assert_eq!(history.storage().entries,0);
}

#[test]
#[cfg(feature = "jit-preparation-observer")]
fn preparation_observer_reports_actual_budget_declines_without_changing_execution() {
    let mut p=program(7,1);
    // More declines than the64-row report bound, reached in one actual run.
    let leaf=p.functions[1].clone();
    p.functions=vec![p.functions[0].clone()];
    p.functions.extend((0..70).map(|_|leaf.clone()));
    p.functions[0].code=vec![Op::Local{dst:0,offset:0}];
    for function in 1..=70 {p.functions[0].code.push(Op::Call{function,args:vec![],destination:0});}
    p.functions[0].code.push(Op::Return);
    let current=Limits{jit_code_bytes:0,..limits()};
    let mut owner=PreparedJit::new(&p,&current).unwrap();
    equal(owner.execute(&[],current.clone()),execute_with_engine(&p,&[],Limits::default(),Engine::Interpreter));
    let observation=owner.preparation_observation();
    assert_eq!(observation["preparations"],71);assert_eq!(observation["declined"],71);
    assert_eq!(observation["declines_truncated"],7);
    assert_eq!(observation["declines"].as_array().unwrap().len(),64);
    for row in observation["declines"].as_array().unwrap() {
        assert_eq!(row["outcome"],"no-staging");assert_eq!(row["word_budget"],0);
        assert_eq!(row["site"]["kind"],"region-word-budget");
        assert!(row["site"]["next_words"].as_u64().unwrap()>0);
    }
}
