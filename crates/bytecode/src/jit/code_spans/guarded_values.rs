//! Observe immutable reads while reconstructing exact retained native code.
use super::*;
use serde_json::{json,Value};
use super::super::guarded_value_census::capture;
fn n(v:&Value,k:&str)->usize {usize::try_from(v[k].as_u64().unwrap()).unwrap()}
#[test]
#[ignore="Requires exact closed adopted code/map and artifact"]
fn observe_saved_guarded_values() {
    let artifact=std::fs::read(std::env::var("GUARDED_VALUE_ARTIFACT").unwrap()).unwrap();
    assert!(artifact.len()<=128*1024*1024);
    let p:Program=bincode::deserialize(&artifact).unwrap();crate::validate(&p).unwrap();
    let map=std::fs::read(std::env::var("GUARDED_VALUE_MAP").unwrap()).unwrap();assert!(map.len()<=MAX_OUTPUT_BYTES);
    let map:Value=serde_json::from_slice(&map).unwrap();
    let bytes=std::fs::read(std::env::var("GUARDED_VALUE_CODE").unwrap()).unwrap();assert!(bytes.len()<=MAX_CODE_BYTES);
    assert_eq!(n(&map,"schema_version"),2);assert_eq!(map["profiled"],false);
    for key in ["persistent_registers","resumable_calls","complete","reconstructed_bytes_match"] {assert_eq!(map[key],true);}
    assert_eq!(n(&map,"code_bytes"),bytes.len());assert_eq!(map["code_sha256"],format!("{:x}",Sha256::digest(&bytes)));
    let mut jit=Jit::new_resumable(&p,false,MAX_CODE_BYTES,true).unwrap();jit.enable_scalar_calls();
    let mut scalars=BTreeSet::new();let base=n(&map,"arena_base");assert!(base>0);
    for saved in map["functions"].as_array().unwrap() {
        if saved["spans"][0]["kind"]!="scalar_leaf" {continue;}
        let id=n(saved,"function");assert!(scalars.insert(id));
        let offset=n(saved,"offset");let end=n(saved,"end");assert!(offset<end && end<=bytes.len());
        let words=jit.observe_saved_scalar_entry(id,offset,end-offset,base);verify_words(&words,&bytes[offset..end]).unwrap();
    }
    let (mut cursor,mut assertions)=(0,0);let mut seen=BTreeSet::new();let mut rows=vec![];
    for saved in map["functions"].as_array().unwrap() {
        let id=n(saved,"function");let f=&p.functions[id];let offset=n(saved,"offset");let end=n(saved,"end");
        assert_eq!(saved["name"],f.name);assert_eq!(offset,cursor);assert!(offset<end && end<=bytes.len());
        assert_eq!(n(saved,"assertion_base"),assertions);
        if saved["spans"][0]["kind"]=="scalar_leaf" {
            assert!(scalars.contains(&id));assert_eq!(n(saved,"assertion_count"),0);
            assert_eq!(saved["spans"],json!([{"offset":offset,"end":end,"region_pc":0,"pc":null,"kind":"scalar_leaf"}]));
            cursor=end;continue;
        }
        assert!(seen.insert(id));
        let mut collector=Collector{rows:vec![],limit:MAX_SPANS};
        let a=jit.emit_function_inner(f,(end-offset)/4,assertions,Some(&mut collector)).unwrap().unwrap();
        collector.validate(f,&a).unwrap();verify_words(&a.words,&bytes[offset..end]).unwrap();
        for s in &mut collector.rows {s.offset+=offset;s.end+=offset;}
        assert_eq!(serde_json::to_value(&collector.rows).unwrap(),saved["spans"]);
        let (b,hits)=capture(||jit.emit_function_inner(f,(end-offset)/4,assertions,None).unwrap().unwrap());
        assert_eq!(a.words,b.words);assert_eq!(a.resumes,b.resumes);assert_eq!(a.operations,b.operations);assert_eq!(a.assertions,b.assertions);
        let entries=|v:&CompiledFunction<'_>|v.entries.iter().map(|b|b.map(|b|(b.offset,b.end))).collect::<Vec<_>>();
        assert_eq!(entries(&a),entries(&b));assert_eq!(a.register_pairs,b.register_pairs);assert_eq!(a.liveness_declined,b.liveness_declined);
        assert_eq!(a.assertions.len(),n(saved,"assertion_count"));
        rows.push(json!({"id":id,"name":f.name,"operations":f.code.len(),"registers":f.registers,"native_bytes":end-offset,
            "reads":hits}));
        assertions+=a.assertions.len();cursor=end;
    }
    assert_eq!(cursor,bytes.len());assert!(jit.code.is_none());assert_eq!(jit.bytes,0);
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("GUARDED_VALUE_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","functions":rows,"scalar_bodies":scalars.len(),
        "code_bytes":bytes.len(),"code_sha256":map["code_sha256"],"full_code_and_entries_reconstructed":true,
        "observer_scope":"available guarded external Load/Copy values in frame-disjoint ordinary regions; original facts only",
        "observation_changes_code":false,"guest_commands":0,"executable_code_publications":0,"performance_measurement":false})).unwrap();
}
