//! Classify structural drift only; classifications never admit native reuse.
use crate::{Function,Op,Program};
use sha2::{Digest,Sha256};
use std::collections::BTreeMap;

fn hash(value:&impl serde::Serialize)->String {
    format!("{:x}",Sha256::digest(bincode::serialize(value).unwrap()))
}
fn metadata(f:&Function)->String {
    hash(&(&f.name,f.frame_size,f.frame_align,f.registers,&f.args,&f.result))
}
fn bytes(a:&[u8],b:&[u8])->serde_json::Value {
    let prefix=a.iter().zip(b).take_while(|(a,b)|a==b).count();
    let suffix=a[prefix..].iter().rev().zip(b[prefix..].iter().rev()).take_while(|(a,b)|a==b).count();
    serde_json::json!({"equal":a==b,"previous_bytes":a.len(),"current_bytes":b.len(),
        "differing_positions":a.iter().zip(b).filter(|(a,b)|a!=b).count()+a.len().abs_diff(b.len()),
        "common_prefix_bytes":prefix,"common_suffix_bytes":suffix})
}
fn category(a:&Op,b:&Op)->&'static str {
    match (a,b) {
        (Op::Imm{dst:a,value:x},Op::Imm{dst:b,value:y}) if a==b && x!=y => "immediate_value_only",
        (Op::Call{function:a,args:x,destination:d},Op::Call{function:b,args:y,destination:e})
            if a!=b && x==y && d==e => "direct_call_id_only",
        (Op::Assert{value:a,expected:x,message:m},Op::Assert{value:b,expected:y,message:n})
            if a==b && x==y && m!=n => "assertion_message_only",
        _ if std::mem::discriminant(a)!=std::mem::discriminant(b) => "opcode_kind_changed",
        _ => "other_operands_changed",
    }
}
fn function(a:&Function,b:&Function)->serde_json::Value {
    let same_metadata=metadata(a)==metadata(b);
    let mut categories=BTreeMap::<&str,usize>::new();let mut examples=vec![];
    // Positional categories are meaningful only when the operation counts match.
    if a.code.len()==b.code.len() {
        for (pc,(old,new)) in a.code.iter().zip(&b.code).enumerate() {
            if bincode::serialize(old).unwrap()==bincode::serialize(new).unwrap() {continue;}
            let kind=category(old,new);*categories.entry(kind).or_default()+=1;
            if examples.len()<4 {
                let mut example=serde_json::json!({"pc":pc,"category":kind});
                if let (Op::Imm{value:a,..},Op::Imm{value:b,..})=(old,new) {
                    example["previous_value_hex"]=format!("{a:x}").into();example["current_value_hex"]=format!("{b:x}").into();
                }
                examples.push(example);
            }
        }
    }
    let only_immediates=same_metadata && categories.len()==1 && categories.contains_key("immediate_value_only");
    serde_json::json!({"previous_name":a.name,"name":b.name,"same_name":a.name==b.name,
        "same_metadata":same_metadata,"previous_operations":a.code.len(),"operations":b.code.len(),
        "same_operation_count":a.code.len()==b.code.len(),"categories":categories,"examples":examples,
        "only_immediate_values_changed":only_immediates,"cache_admission":false})
}
fn heap(p:&Program)->bool {
    !p.statics.is_empty() || p.functions.iter().flat_map(|f|&f.code).any(|op|matches!(op,
        Op::Allocate{..}|Op::Deallocate{..}|Op::Reallocate{..}|Op::CAllocate{..}|
        Op::CReallocate{..}|Op::CAlignedAllocate{..}|Op::CurrentDirectory{..}))
}
fn compare(a:&Program,b:&Program)->serde_json::Value {
    assert_eq!((a.version|b.version)&crate::PARTIAL_VALIDATION,0);
    crate::validate(a).unwrap();crate::validate(b).unwrap();
    let mut changed=vec![];let mut same=0usize;
    for (id,new) in b.functions.iter().enumerate() {
        if let Some(old)=a.functions.get(id) {
            if hash(old)==hash(new) {same+=1;continue;}
            let mut row=function(old,new);row["function"]=id.into();changed.push(row);
        } else {changed.push(serde_json::json!({"function":id,"name":new.name,"new_id":true,"operations":new.code.len()}));}
    }
    let fields=serde_json::json!({"version":a.version==b.version,"target":a.target==b.target,
        "entry":a.entry==b.entry,"function_count":a.functions.len()==b.functions.len(),
        "heap_mode":heap(a)==heap(b),"data":a.data==b.data,"statics":a.statics==b.statics,
        "thread_locals":hash(&a.thread_locals)==hash(&b.thread_locals)});
    serde_json::json!({"current_functions":b.functions.len(),"previous_functions":a.functions.len(),
        "unchanged_functions":same,"changed_functions":changed,"global_fields_equal":fields,
        "data_difference":bytes(&a.data,&b.data),"static_difference":bytes(&a.statics,&b.statics),
        "cache_admission":false,"performance_measurement":false})
}
fn fixture(code:Vec<Op>)->Function {
    Function{name:"f".into(),frame_size:16,frame_align:8,registers:2,args:vec![],
        result:crate::Slot{offset:0,size:0},code}
}
#[test]
fn cross_edit_difference_immediates_do_not_imply_safe_relocation() {
    let a=fixture(vec![Op::Imm{dst:0,value:1},Op::Return]);let mut b=a.clone();b.code[0]=Op::Imm{dst:0,value:2};
    let r=function(&a,&b);assert_eq!(r["only_immediate_values_changed"],true);assert_eq!(r["cache_admission"],false);
    b.frame_size=32;assert_eq!(function(&a,&b)["only_immediate_values_changed"],false);
    b=a.clone();b.code[0]=Op::Imm{dst:1,value:2};
    assert_eq!(function(&a,&b)["categories"]["other_operands_changed"],1);
}
#[test]
fn cross_edit_difference_calls_and_assertions_keep_typed_categories() {
    let call=|id,destination|Op::Call{function:id,args:vec![0],destination};
    assert_eq!(category(&call(1,1),&call(2,1)),"direct_call_id_only");
    assert_eq!(category(&call(1,1),&call(2,0)),"other_operands_changed");
    let assertion=|expected,message:&str|Op::Assert{value:0,expected,message:message.into()};
    assert_eq!(category(&assertion(true,"a"),&assertion(true,"b")),"assertion_message_only");
    assert_eq!(category(&assertion(true,"a"),&assertion(false,"b")),"other_operands_changed");
    assert_eq!(category(&Op::Return,&Op::Jump{target:0}),"opcode_kind_changed");
}
#[test]
fn cross_edit_difference_insertions_are_not_misclassified_positionally() {
    let a=fixture(vec![Op::Return]);let mut b=a.clone();b.code.insert(0,Op::Imm{dst:0,value:1});
    let r=function(&a,&b);assert_eq!(r["same_operation_count"],false);
    assert!(r["categories"].as_object().unwrap().is_empty());assert_eq!(r["only_immediate_values_changed"],false);
}
#[test]
fn cross_edit_difference_byte_prefix_suffix_never_overlap() {
    for (a,b,prefix,suffix,diff) in [(&b""[..],&b""[..],0,0,0),(&b"abc"[..],&b"abc"[..],3,0,0),
        (&b"abc"[..],&b"ab"[..],2,0,1),(&b"axb"[..],&b"ayb"[..],1,1,1)] {
        let r=bytes(a,b);assert_eq!(r["common_prefix_bytes"],prefix);
        assert_eq!(r["common_suffix_bytes"],suffix);assert_eq!(r["differing_positions"],diff);
    }
}

#[derive(serde::Deserialize)]
struct Input {path:std::path::PathBuf,sha256:String,state:i32}
fn read(i:&Input)->Program {
    use bincode::Options;
    let meta=std::fs::symlink_metadata(&i.path).unwrap();assert!(meta.is_file() && meta.len()<=64*1024*1024);
    let bytes=std::fs::read(&i.path).unwrap();assert_eq!(format!("{:x}",Sha256::digest(&bytes)),i.sha256);
    let p:Program=bincode::DefaultOptions::new().with_fixint_encoding().with_limit(64*1024*1024).reject_trailing_bytes().deserialize(&bytes).unwrap();
    assert_eq!(p.version&crate::PARTIAL_VALIDATION,0);crate::validate(&p).unwrap();p
}
#[test]
#[ignore="explicit retained manifest; no guest or native code"]
fn cross_edit_observe_saved_differences() {
    use std::io::Write;
    let inputs:Vec<Input>=serde_json::from_slice(&std::fs::read(std::env::var_os("RUST_INTERP_CROSS_EDIT_INPUTS").unwrap()).unwrap()).unwrap();
    assert_eq!(inputs.iter().map(|i|i.state).collect::<Vec<_>>(),vec![0,-1,1,2,3,4,5,0]);
    let mut previous=read(&inputs[0]);let mut rows=vec![];
    for pair in inputs.windows(2) {
        let current=read(&pair[1]);let mut row=compare(&previous,&current);
        row["previous_artifact_sha256"]=pair[0].sha256.clone().into();row["artifact_sha256"]=pair[1].sha256.clone().into();
        row["previous_state"]=pair[0].state.into();row["state"]=pair[1].state.into();rows.push(row);previous=current;
    }
    let output=serde_json::to_vec_pretty(&serde_json::json!({"comparisons":rows,"guest_commands":0,
        "executable_code_publications":0,"cache_admission":false})).unwrap();assert!(output.len()<=64*1024*1024);
    std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var_os("RUST_INTERP_CROSS_EDIT_OUTPUT").unwrap()).unwrap().write_all(&output).unwrap();
}
