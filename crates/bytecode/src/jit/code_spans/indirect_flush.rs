use super::*;
use serde_json::{Value,json};

fn number(v:&Value,key:&str)->usize {usize::try_from(v[key].as_u64().unwrap()).unwrap()}

#[test]
#[ignore="Requires the retained native-indirect profiled artifact, map and exact machine code"]
fn observe_successor_flush_code() {
    let artifact=std::fs::read(std::env::var("SUCCESSOR_ARTIFACT").unwrap()).unwrap();assert!(artifact.len()<=128*1024*1024);
    let p:Program=bincode::deserialize(&artifact).unwrap();crate::validate(&p).unwrap();
    let mapping=std::fs::read(std::env::var("SUCCESSOR_MAP").unwrap()).unwrap();assert!(mapping.len()<=MAX_OUTPUT_BYTES);
    let mapping:Value=serde_json::from_slice(&mapping).unwrap();
    let bytes=std::fs::read(std::env::var("SUCCESSOR_CODE").unwrap()).unwrap();assert!(bytes.len()<=MAX_CODE_BYTES);
    assert_eq!(number(&mapping,"schema_version"),1);assert_eq!(mapping["profiled"],true);
    for flag in ["persistent_registers","resumable_calls","indirect_calls","complete","reconstructed_bytes_match"] {assert_eq!(mapping[flag],true);}
    assert_eq!(number(&mapping,"code_bytes"),bytes.len());
    assert_eq!(mapping["code_sha256"],format!("{:x}",Sha256::digest(&bytes)));
    let mut baseline=Jit::new_resumable(&p,true,MAX_CODE_BYTES,true).unwrap();
    baseline.enable_indirect_calls();baseline.omit_dead_exit_spills=Some(false);baseline.observe_flush=true;
    let mut candidate=Jit::new_resumable(&p,true,MAX_CODE_BYTES,true).unwrap();
    candidate.enable_indirect_calls();assert!(candidate.indirect.is_some() && candidate.omit_dead_exit_spills.is_none());candidate.observe_flush=true;
    let (mut cursor,mut assertions,mut candidate_bytes)=(0,0,0);let mut seen=BTreeSet::new();let mut output=vec![];
    for saved in mapping["functions"].as_array().unwrap() {
        let id=number(saved,"function");assert!(seen.insert(id));let f=&p.functions[id];assert_eq!(saved["name"],f.name);
        let offset=number(saved,"offset");let end=number(saved,"end");assert_eq!(cursor,offset);assert!(offset<end && end<=bytes.len());
        assert_eq!(number(saved,"assertion_base"),assertions);
        let mut cm=Collector {rows:vec![],limit:MAX_SPANS};let a=baseline.emit_function_inner(f,(end-offset)/4,assertions,Some(&mut cm)).unwrap().unwrap();
        verify_words(&a.words,&bytes[offset..end]).unwrap();cm.validate(f,&a).unwrap();
        let mut om=Collector {rows:vec![],limit:MAX_SPANS};let b=candidate.emit_function_inner(f,(end-offset)/4,assertions,Some(&mut om)).unwrap().unwrap();
        om.validate(f,&b).unwrap();assert_eq!(a.operations,b.operations);assert_eq!(a.assertions,b.assertions);
        assert_eq!(a.local_fact_events,b.local_fact_events);assert_eq!(a.retained_local_writes,b.retained_local_writes);
        assert!(a.scratch_hits.is_empty() && b.scratch_hits.is_empty());
        assert_eq!(a.entries.iter().map(|e|e.map(|e|e.end)).collect::<Vec<_>>(),b.entries.iter().map(|e|e.map(|e|e.end)).collect::<Vec<_>>());
        let removed:Vec<_>=a.flush_spans.iter().filter(|s|s.analysis_available && !s.live_after).collect();
        assert!(removed.iter().all(|s|s.live_before));
        let removed_bytes:usize=removed.iter().map(|s|s.end-s.offset).sum();
        assert_eq!(a.words.len()*4-b.words.len()*4,removed_bytes);
        assert!(b.flush_spans.iter().all(|s|!s.analysis_available || s.live_after));
        // An empty flush span is absent from the candidate map. Every other
        // kind retains the same PC ownership and number of emitted words.
        let old_nonflush:Vec<_>=cm.rows.iter().filter(|s|s.kind!=Kind::Flush).map(|s|(s.kind,s.region_pc,s.pc,s.end-s.offset)).collect();
        let new_nonflush:Vec<_>=om.rows.iter().filter(|s|s.kind!=Kind::Flush).map(|s|(s.kind,s.region_pc,s.pc,s.end-s.offset)).collect();
        assert_eq!(old_nonflush,new_nonflush);
        assert_eq!(a.assertions.len(),number(saved,"assertion_count"));
        for s in &mut cm.rows {s.offset+=offset;s.end+=offset;}
        assert_eq!(serde_json::to_value(&cm.rows).unwrap(),saved["spans"]);
        output.push(json!({"function":id,"name":f.name,"baseline_bytes":a.words.len()*4,"candidate_bytes":b.words.len()*4,
            "removed_flush_bytes":removed_bytes,"removed_values":removed}));
        candidate_bytes+=b.words.len()*4;cursor=end;assertions+=a.assertions.len();
    }
    assert_eq!(cursor,bytes.len());assert!(baseline.code.is_none() && candidate.code.is_none());assert_eq!(baseline.bytes+candidate.bytes,0);
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("SUCCESSOR_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","functions":output,"baseline_bytes":bytes.len(),"candidate_bytes":candidate_bytes,
        "code_sha256":mapping["code_sha256"],"exact_baseline_reconstruction":true,"only_flush_word_counts_change":true,
        "guest_commands":0,"executable_code_publications":0})).unwrap();
}
