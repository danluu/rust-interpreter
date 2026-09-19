fn indirect_fixture()->Program {
    let mut p=fixture();p.functions[0].result.size=0;p.functions[1].result.size=8;
    p.functions[0].code=vec![Op::Local{dst:0,offset:0},
        Op::Imm{dst:1,value:(crate::FUNCTION_POINTER_TAG|2) as u128},
        Op::CallIndirect{callee:1,args:vec![],arg_sizes:vec![],destination:0,result_size:8},Op::Return];
    p.functions[1].code=vec![Op::Local{dst:0,offset:0},Op::Imm{dst:1,value:7},
        Op::Store{address:0,src:1,size:8},Op::Return];
    let mut unused=p.functions[1].clone();unused.name="unrelated signature".into();unused.result.size=16;
    p.functions.push(unused);p
}
fn indirect_owner(p:&Program)->Jit<'_> {let mut j=owner(p);j.enable_indirect_calls();j}

#[test]
fn session_composition_keys_bind_changed_indirect_signature_ordinals_and_missing_targets() {
    let p=indirect_fixture();let a=indirect_owner(&p);let checked=Checked::new(&p).unwrap();
    for rebind in [false,true] {
        let request=Request::new(&checked,&a,0,EMITTER,rebind).unwrap();
        let emission=request.emit(MAX_CODE_BYTES/4).unwrap().unwrap();
        let t=Template::capture_emission(&emission,MAX_RETAINED).unwrap();
        for missing in [false,true] {
            let mut q=p.clone();q.functions[2].result.size=4;
            if missing {q.functions[1].result.size=4;}
            assert_eq!(bincode::serialize(&p.functions[0]).unwrap(),bincode::serialize(&q.functions[0]).unwrap());
            let b=indirect_owner(&q);let current=Checked::new(&q).unwrap();
            assert_ne!(a.indirect.as_ref().unwrap().signature(&[],8),b.indirect.as_ref().unwrap().signature(&[],8));
            assert_ne!(stage(&a,0).words,stage(&b,0).words);
            assert!(t.restore(&current,&b,0,&EMITTER,MAX_CODE_BYTES/4).is_none());
        }
    }
}
#[test]
fn session_composition_dynamic_layouts_reuse_exact_staging_with_current_owner_tables() {
    let p=indirect_fixture();let a=indirect_owner(&p);let c=Checked::new(&p).unwrap();
    let t=Template::capture_mode(&c,&a,0,EMITTER,&stage(&a,0),MAX_RETAINED,true).unwrap();
    let mut q=p.clone();let f=&mut q.functions[1];f.frame_size=64;f.frame_align=32;f.registers=6;f.result.offset=16;
    f.code=vec![Op::Assert{value:5,expected:false,message:"current zero requirement".into()},
        Op::Local{dst:0,offset:16},Op::Imm{dst:1,value:9},Op::Store{address:0,src:1,size:8},Op::Return];
    let b=indirect_owner(&q);let d=Checked::new(&q).unwrap();
    assert_ne!(a.indirect.as_ref().unwrap().layouts[1].zeroes,b.indirect.as_ref().unwrap().layouts[1].zeroes);
    assert_ne!(a.indirect.as_ref().unwrap().layouts[1].frame_size,b.indirect.as_ref().unwrap().layouts[1].frame_size);
    same(&stage(&b,0),&t.restore(&d,&b,0,&EMITTER,MAX_CODE_BYTES/4).unwrap());
    assert!(a.code.is_none() && b.code.is_none());
}
#[test]
fn session_composition_option_and_spill_model_changes_cannot_alias_history() {
    let p=indirect_fixture();let a=indirect_owner(&p);let c=Checked::new(&p).unwrap();
    let t=Template::capture_mode(&c,&a,0,EMITTER,&stage(&a,0),MAX_RETAINED,true).unwrap();
    let off=owner(&p);assert!(t.restore(&c,&off,0,&EMITTER,MAX_CODE_BYTES/4).is_none());
    let mut changed=indirect_owner(&p);changed.omit_dead_exit_spills=false;
    assert!(t.restore(&c,&changed,0,&EMITTER,MAX_CODE_BYTES/4).is_none());
    let mut declined=indirect_owner(&p);declined.indirect=None;
    assert!(t.restore(&c,&declined,0,&EMITTER,MAX_CODE_BYTES/4).is_none());
}
