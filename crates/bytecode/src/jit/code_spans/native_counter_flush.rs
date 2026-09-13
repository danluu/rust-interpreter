use super::*;
use serde_json::{Value,json};

fn number(v:&Value,key:&str)->usize {usize::try_from(v[key].as_u64().unwrap()).unwrap()}

fn counter_updates(words:&[u32])->usize {
    use crate::native_continuation::layout as state;
    [state::CALLS,state::RETURNS].into_iter().map(|field| {
        let pattern=[0xf9400000|((field as u32/8)<<10)|(19<<5)|9,0x91000529,
            0xf9000000|((field as u32/8)<<10)|(19<<5)|9];
        words.windows(3).filter(|w|*w==pattern).count()
    }).sum()
}

#[test]
#[ignore="Requires the adopted unprofiled artifact, map and exact machine code"]
fn observe_native_counter_flush_code() {
    let artifact=std::fs::read(std::env::var("NATIVE_COUNTER_ARTIFACT").unwrap()).unwrap();assert!(artifact.len()<=128*1024*1024);
    let p:Program=bincode::deserialize(&artifact).unwrap();crate::validate(&p).unwrap();
    let mapping=std::fs::read(std::env::var("NATIVE_COUNTER_MAP").unwrap()).unwrap();assert!(mapping.len()<=MAX_OUTPUT_BYTES);
    let mapping:Value=serde_json::from_slice(&mapping).unwrap();
    let bytes=std::fs::read(std::env::var("NATIVE_COUNTER_CODE").unwrap()).unwrap();assert!(bytes.len()<=MAX_CODE_BYTES);
    assert_eq!(number(&mapping,"schema_version"),1);assert_eq!(mapping["profiled"],false);
    for flag in ["persistent_registers","resumable_calls","complete","reconstructed_bytes_match"] {assert_eq!(mapping[flag],true);}
    assert_eq!(number(&mapping,"code_bytes"),bytes.len());
    assert_eq!(mapping["code_sha256"],format!("{:x}",Sha256::digest(&bytes)));
    let mut baseline=Jit::new_resumable(&p,false,MAX_CODE_BYTES,true).unwrap();
    baseline=baseline.use_adopted_emission();baseline.observe_flush=true;
    let mut counters=Jit::new_resumable(&p,false,MAX_CODE_BYTES,true).unwrap();
    counters.omit_dead_exit_spills=false;counters.observe_flush=true;
    let mut candidate=Jit::new_resumable(&p,false,MAX_CODE_BYTES,true).unwrap();
    assert!(candidate.omit_dead_exit_spills);candidate.observe_flush=true;
    let (mut cursor,mut assertions,mut candidate_bytes,mut counter_bytes)=(0,0,0,0);let mut seen=BTreeSet::new();let mut output=vec![];
    for saved in mapping["functions"].as_array().unwrap() {
        let id=number(saved,"function");assert!(seen.insert(id));let f=&p.functions[id];assert_eq!(saved["name"],f.name);
        let offset=number(saved,"offset");let end=number(saved,"end");assert_eq!(cursor,offset);assert!(offset<end && end<=bytes.len());
        assert_eq!(number(saved,"assertion_base"),assertions);
        let mut cm=Collector {rows:vec![],limit:MAX_SPANS};let a=baseline.emit_function_inner(f,(end-offset)/4,assertions,Some(&mut cm)).unwrap().unwrap();
        verify_words(&a.words,&bytes[offset..end]).unwrap();cm.validate(f,&a).unwrap();
        let mut km=Collector {rows:vec![],limit:MAX_SPANS};
        let k=counters.emit_function_inner(f,MAX_CODE_BYTES/4,assertions,Some(&mut km)).unwrap().unwrap();
        km.validate(f,&k).unwrap();
        assert_eq!(cm.rows.len(),km.rows.len());
        let mut delta_words=0isize;
        let (mut entry_count,mut exit_count,mut update_count)=(0,0,0);
        for (old,new) in cm.rows.iter().zip(&km.rows) {
            assert_eq!((old.kind,old.region_pc,old.pc),(new.kind,new.region_pc,new.pc));
            let words=&a.words[old.offset/4..old.end/4];
            let updates=counter_updates(words);
            let exits=words.iter().filter(|&&w|w==0xd65f03c0).count();
            let entries=usize::from(matches!(old.kind,Kind::Entry|Kind::Transition));
            let delta=(5*entries+exits) as isize-2*updates as isize;
            assert_eq!((new.end-new.offset) as isize-(old.end-old.offset) as isize,delta*4);
            delta_words+=delta;entry_count+=entries;exit_count+=exits;update_count+=updates;
        }
        assert_eq!(k.words.len() as isize-a.words.len() as isize,delta_words);
        assert_eq!(entry_count,a.entries.iter().filter(|e|e.is_some()).count());
        assert_eq!(k.words.iter().filter(|&&w|w==0x3dc00e7d).count(),entry_count);
        assert_eq!(k.words.iter().filter(|&&w|w==0x3d800e7d).count(),exit_count);
        assert_eq!(k.words.iter().filter(|&&w|matches!(w,0x4efe87bd|0x4eff87bd)).count(),update_count);
        let mut om=Collector {rows:vec![],limit:MAX_SPANS};let b=candidate.emit_function_inner(f,MAX_CODE_BYTES/4,assertions,Some(&mut om)).unwrap().unwrap();
        om.validate(f,&b).unwrap();assert_eq!(a.operations,b.operations);assert_eq!(a.assertions,b.assertions);
        assert_eq!(a.local_fact_events,b.local_fact_events);assert_eq!(a.retained_local_writes,b.retained_local_writes);
        assert!(a.scratch_hits.is_empty() && b.scratch_hits.is_empty());
        assert_eq!(a.entries.iter().map(|e|e.map(|e|e.end)).collect::<Vec<_>>(),b.entries.iter().map(|e|e.map(|e|e.end)).collect::<Vec<_>>());
        let removed:Vec<_>=a.flush_spans.iter().filter(|s|s.analysis_available && !s.live_after).collect();
        assert!(removed.iter().all(|s|s.live_before));
        let removed_bytes:usize=removed.iter().map(|s|s.end-s.offset).sum();
        assert_eq!(k.words.len()*4-b.words.len()*4,removed_bytes);
        assert!(b.flush_spans.iter().all(|s|!s.analysis_available || s.live_after));
        // An empty flush span is absent from the candidate map. Every other
        // kind retains the same PC ownership and number of emitted words.
        let old_nonflush:Vec<_>=km.rows.iter().filter(|s|s.kind!=Kind::Flush).map(|s|(s.kind,s.region_pc,s.pc,s.end-s.offset)).collect();
        let new_nonflush:Vec<_>=om.rows.iter().filter(|s|s.kind!=Kind::Flush).map(|s|(s.kind,s.region_pc,s.pc,s.end-s.offset)).collect();
        assert_eq!(old_nonflush,new_nonflush);
        assert_eq!(a.assertions.len(),number(saved,"assertion_count"));
        for s in &mut cm.rows {s.offset+=offset;s.end+=offset;}
        assert_eq!(serde_json::to_value(&cm.rows).unwrap(),saved["spans"]);
        output.push(json!({"function":id,"name":f.name,"baseline_bytes":a.words.len()*4,"candidate_bytes":b.words.len()*4,"counter_bytes":k.words.len()*4,"counter_delta_bytes":delta_words*4,
            "external_entries":entry_count,"vm_exit_sites":exit_count,"counter_update_sites":update_count,
            "removed_flush_bytes":removed_bytes,"removed_values":removed}));
        candidate_bytes+=b.words.len()*4;counter_bytes+=k.words.len()*4;cursor=end;assertions+=a.assertions.len();
    }
    assert_eq!(cursor,bytes.len());assert!(candidate_bytes<=MAX_CODE_BYTES && counter_bytes<=MAX_CODE_BYTES);assert!(baseline.code.is_none() && counters.code.is_none() && candidate.code.is_none());assert_eq!(baseline.bytes+candidate.bytes,0);
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("NATIVE_COUNTER_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","functions":output,"baseline_bytes":bytes.len(),"candidate_bytes":candidate_bytes,"counter_bytes":counter_bytes,
        "code_sha256":mapping["code_sha256"],"exact_baseline_reconstruction":true,"counter_words_accounted_by_scope":true,"composition_removes_only_dead_flush_word_counts":true,
        "guest_commands":0,"executable_code_publications":0})).unwrap();
}
