use super::*;
use crate::{Binary, Slot};

fn program(code:Vec<Op>,widths:&[usize])->Program {
    let mut offset=0;
    let args=widths.iter().map(|&size|{let slot=Slot{offset,size};offset+=size;slot}).collect();
    Program {version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:(0u8..64).collect(),statics:vec![],thread_locals:vec![],functions:vec![
        Function{name:"same".into(),frame_size:512,frame_align:16,registers:32,args:vec![],result:Slot{offset:0,size:0},code},
        Function{name:"same".into(),frame_size:512,frame_align:16,registers:1,args,result:Slot{offset:0,size:0},code:vec![Op::Return]}
    ]}
}
fn call(args:Vec<Reg>)->Op {Op::Call{function:1,args,destination:0}}
fn seed()->Vec<Op> {vec![Op::Local{dst:0,offset:32},Op::Imm{dst:1,value:0x0807060504030201},Op::Store{address:0,src:1,size:8}]}
fn sites(p:&Program)->Vec<Site> {crate::validate(p).unwrap();analyze(p,0,None).unwrap().0}
fn value(site:&Site,index:usize)->Option<&str> {site.arguments.iter().find(|a|a.index==index).map(|a|a.value.as_str())}

#[test]
fn immutable_and_local_bytes_use_callee_widths_without_mutating_artifact() {
    let mut code=seed();code.extend([Op::Imm{dst:2,value:16},Op::Imm{dst:3,value:crate::HEAP_POINTER_TAG as u128},call(vec![0,2,3]),Op::Return]);
    let p=program(code,&[8,2,8]);let before=bincode::serialize(&p).unwrap();let s=sites(&p);
    assert_eq!(value(&s[0],0),Some("0x807060504030201"));assert_eq!(value(&s[0],1),Some("0x1110"));assert_eq!(value(&s[0],2),None);
    let report=census(&p,None).unwrap();assert_eq!(report["sites_with_constant_arguments"],1);assert!(report["direct_call_executions"].is_null());
    assert_eq!(bincode::serialize(&p).unwrap(),before);
}

#[test]
fn partial_stores_invalidate_unknown_bytes_and_copy_uses_a_snapshot() {
    let mut code=seed();code.extend([Op::Local{dst:2,offset:36},Op::Copy{dst:2,src:0,size:8},call(vec![0,2]),Op::Return]);
    let s=sites(&program(code,&[8,8]));assert_eq!(value(&s[0],0),Some("0x403020104030201"));assert_eq!(value(&s[0],1),Some("0x807060504030201"));
    let mut code=seed();code.extend([Op::Local{dst:2,offset:36},Op::Store{address:2,src:31,size:1},call(vec![0,0]),Op::Return]);
    let s=sites(&program(code,&[8,4]));assert_eq!(value(&s[0],0),None);assert_eq!(value(&s[0],1),Some("0x4030201"));
}

#[test]
fn every_opaque_memory_effect_clears_local_bytes_but_preserves_value_registers() {
    let effects=vec![
        Op::Store{address:31,src:1,size:1},Op::Copy{dst:31,src:0,size:8},
        Op::CopyDynamic{dst:0,src:1,size:2},Op::FillBytes{address:0,value:1,size:2},call(vec![0]),
        Op::CallIndirect{callee:1,args:vec![0],arg_sizes:vec![8],destination:0,result_size:0},
        Op::Allocate{dst:9,size:1,align:2,zeroed:true},Op::Deallocate{pointer:0,size:1,align:2},
        Op::Reallocate{dst:9,pointer:0,old_size:1,align:2,new_size:3},Op::ResetThreadLocals,
        Op::RandomBytes{dst:9,address:0,size:1},Op::CpuFeatureQuery{dst:9,name:0,output:1,output_len:2,new_data:3,new_len:4},
        Op::CurrentDirectory{dst:9,address:0,size:1,errno:2},
        Op::DescriptorStat{dst:9,descriptor:0,address:1,errno:2},
        Op::CAllocate{dst:9,count:1,size:2,errno:0,zeroed:true},Op::CDeallocate{pointer:0},
        Op::CReallocate{dst:9,pointer:0,size:1,errno:2},Op::CAlignedAllocate{dst:9,output:0,align:1,size:2},
        Op::RegisterTlsDestructor{callback:1,argument:0},
    ];
    for effect in effects {
        let mut code=seed();code.extend([effect.clone(),call(vec![0]),Op::Store{address:0,src:1,size:8},call(vec![0]),Op::Return]);
        let s=sites(&program(code,&[8]));assert!(s[s.len()-2].arguments.is_empty(),"{effect:?}");
        assert_eq!(value(s.last().unwrap(),0),Some("0x807060504030201"),"{effect:?}");
    }
}

#[test]
fn branch_entries_backedges_and_unreachable_blocks_forget_all_facts() {
    let mut code=seed();code.extend([Op::Switch{value:1,cases:vec![(1,4)],otherwise:6},call(vec![0]),Op::Jump{target:4},
        Op::Local{dst:0,offset:32},call(vec![0]),Op::Return,call(vec![0]),Op::Return]);
    let s=sites(&program(code,&[8]));assert_eq!(s.len(),3);assert!(s.iter().all(|s|s.arguments.is_empty()));
}

#[test]
fn aliased_outputs_integer_errors_and_unknown_writers_are_conservative() {
    let mut code=seed();code.extend([
        Op::Imm{dst:1,value:255},Op::Imm{dst:2,value:1},
        Op::Binary{dst:1,overflow:1,op:Binary::Add,a:1,b:2,bits:8,signed:false},
        Op::Store{address:0,src:1,size:8},call(vec![0]),
        Op::Imm{dst:1,value:7},Op::Imm{dst:2,value:0},
        Op::Binary{dst:1,overflow:2,op:Binary::Div,a:1,b:2,bits:8,signed:false},
        Op::Store{address:0,src:1,size:8},call(vec![0]),
        Op::Imm{dst:1,value:7},Op::Unary{dst:1,src:1,op:crate::Unary::Not,bits:8},
        Op::Store{address:0,src:1,size:8},call(vec![0]),Op::Return]);
    let s=sites(&program(code,&[8]));assert_eq!(value(&s[0],0),Some("0x1"));
    assert!(s[1].arguments.is_empty());assert!(s[2].arguments.is_empty());
}

#[test]
fn casts_selects_and_known_loads_preserve_full_scalar_semantics() {
    let mut code=seed();code.extend([Op::Load{dst:1,address:0,size:1},Op::Imm{dst:2,value:255},
        Op::Cast{dst:2,src:2,from:8,to:64,signed:true},Op::Select{dst:2,condition:1,yes:2,no:31},
        Op::Store{address:0,src:2,size:8},call(vec![0]),Op::Return]);
    assert_eq!(value(&sites(&program(code,&[8]))[0],0),Some("0xffffffffffffffff"));
}

#[test]
fn large_shapes_decline_and_byte_facts_evict_without_inventing_values() {
    let mut code=vec![Op::Imm{dst:1,value:7}];
    for i in 0..33 {code.extend([Op::Local{dst:0,offset:i*8},Op::Store{address:0,src:1,size:8}]);}
    code.extend([Op::Local{dst:2,offset:0},call(vec![0,2]),Op::Return]);
    let mut p=program(code,&[8,8]);let (s,evictions)=analyze(&p,0,None).unwrap();assert_eq!(evictions,1);
    assert_eq!(value(&s[0],0),Some("0x7"));assert_eq!(value(&s[0],1),None);
    p.functions[0].registers=MAX_SHAPE+1;assert!(analyze(&p,0,None).is_none());
    let report=census(&p,None).unwrap();assert_eq!(report["declined_functions"],1);assert_eq!(report["direct_call_sites"],1);
    p.functions[0].registers=32;p.functions[0].code=vec![Op::Return;MAX_SHAPE+1];assert!(analyze(&p,0,None).is_none());
}

#[test]
fn exact_indexed_profiles_weight_calls_and_reject_shapes_even_with_duplicate_names() {
    let mut code=seed();code.extend([call(vec![0]),call(vec![0]),Op::Return]);let p=program(code,&[8]);
    let mut functions:Vec<_>=p.functions.iter().map(|f|serde_json::json!({"name":f.name,"frame_size":f.frame_size,"registers":f.registers,
        "operations":f.code.iter().map(|op|format!("{op:?}")).collect::<Vec<_>>(),"interpreted":vec![0;f.code.len()],
        "jit_blocks":vec![0;f.code.len()],"jit_block_ends":vec![0;f.code.len()],"jit_tree_blocks":vec![0;f.code.len()],"jit_tree_block_ends":vec![0;f.code.len()]})).collect();
    functions[0]["jit_blocks"][3]=7.into();functions[0]["jit_block_ends"][3]=4.into();functions[0]["interpreted"][3]=2.into();functions[0]["interpreted"][4]=3.into();
    let bytes=serde_json::to_vec(&serde_json::json!({"functions":functions})).unwrap();let r=census(&p,Some(&bytes)).unwrap();
    assert_eq!(r["direct_call_executions"],12);assert_eq!(r["executions_with_constant_arguments"],9);
    functions[0]["operations"][0]="Local { dst: 0, offset: 31 }".into();
    assert!(census(&p,Some(&serde_json::to_vec(&serde_json::json!({"functions":functions})).unwrap())).is_err());
}

#[test]
fn zero_large_arguments_and_pointer_arithmetic_are_not_constant_byte_proofs() {
    let mut code=seed();code.extend([Op::Imm{dst:2,value:1},Op::Binary{dst:3,overflow:4,op:Binary::Add,a:0,b:2,bits:64,signed:false},
        call(vec![0,0,3]),Op::Return]);
    assert!(sites(&program(code,&[0,16,8]))[0].arguments.is_empty());
}

#[test]
fn null_argument_addresses_are_not_immutable_data() {
    let code=vec![Op::Imm{dst:0,value:0},Op::Imm{dst:1,value:1},call(vec![0,1]),Op::Return];
    let p=program(code,&[8,8]);let s=sites(&p);
    assert_eq!(value(&s[0],0),None);
    assert_eq!(value(&s[0],1),Some("0x807060504030201"));
}
