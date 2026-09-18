//! Observe smaller range admission against exact retained native code.
use super::*;
use serde_json::{json,Value};
use super::super::range_groups;
fn n(v:&Value,k:&str)->usize {usize::try_from(v[k].as_u64().unwrap()).unwrap()}
#[test]
#[ignore="Requires exact closed adopted code/map and artifact"]
fn observe_saved_range_admission() {
    let artifact=std::fs::read(std::env::var("RANGE_ADMISSION_ARTIFACT").unwrap()).unwrap();
    assert!(artifact.len()<=128*1024*1024);
    let p:Program=bincode::deserialize(&artifact).unwrap();crate::validate(&p).unwrap();
    let map=std::fs::read(std::env::var("RANGE_ADMISSION_MAP").unwrap()).unwrap();assert!(map.len()<=MAX_OUTPUT_BYTES);
    let map:Value=serde_json::from_slice(&map).unwrap();
    let bytes=std::fs::read(std::env::var("RANGE_ADMISSION_CODE").unwrap()).unwrap();assert!(bytes.len()<=MAX_CODE_BYTES);
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
        let (mut old_work,mut small_work)=(4_000_000,4_000_000);
        let mut groups=vec![];let mut retained_groups=0;
        for (start,entry) in a.entries.iter().enumerate() {
            let Some(entry)=entry else {continue;};
            let old=range_groups::runtime_plan(f,start,entry.end,&mut old_work);
            let small=range_groups::small_plan(f,start,entry.end,&mut small_work);
            assert_eq!(old_work,small_work);
            if let Some(old)=old {
                let small=small.unwrap();assert_eq!(old.sites,small.sites);
                assert_eq!((old.root,old.low,old.high,old.writes,old.frame_disjoint),
                    (small.root,small.low,small.high,small.writes,small.frame_disjoint));
                retained_groups+=1;
            } else if let Some(small)=small {
                assert!((4..8).contains(&small.sites.len()));
                let sites:Vec<_>=small.sites.iter().map(|s|json!({"pc":s.pc,"register":s.register,
                    "offset":s.offset,"size":s.size,"write":s.write})).collect();
                groups.push(json!({"start":start,"end":entry.end,"root":small.root,"low":small.low,
                    "high":small.high,"writes":small.writes,"frame_disjoint":small.frame_disjoint,"sites":sites}));
            }
        }
        assert_eq!(a.assertions.len(),n(saved,"assertion_count"));
        rows.push(json!({"id":id,"name":f.name,"operations":f.code.len(),"registers":f.registers,"native_bytes":end-offset,
            "groups":groups,"retained_groups":retained_groups,"analysis_work":4_000_000-old_work}));
        assertions+=a.assertions.len();cursor=end;
    }
    assert_eq!(cursor,bytes.len());assert!(jit.code.is_none());assert_eq!(jit.bytes,0);
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("RANGE_ADMISSION_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","functions":rows,"scalar_bodies":scalars.len(),
        "code_bytes":bytes.len(),"code_sha256":map["code_sha256"],"full_code_and_entries_reconstructed":true,
        "observer_scope":"Additional 4–7-access groups under existing typed range proofs; original eight-access admission unchanged",
        "observation_changes_code":false,"guest_commands":0,"executable_code_publications":0,"performance_measurement":false})).unwrap();
}
