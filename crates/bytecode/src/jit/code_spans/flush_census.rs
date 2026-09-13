//! Verify the entire saved code, then partition every existing flush by value.
use super::*;
use serde_json::{Value,json};

fn number(v: &Value, key: &str) -> usize { usize::try_from(v[key].as_u64().unwrap()).unwrap() }

#[test]
#[ignore = "Requires exact saved unprofiled code, operation map and artifact"]
fn observe_saved_consumed_flush_values() {
    let artifact = std::fs::read(std::env::var("FLUSH_ARTIFACT").unwrap()).unwrap();
    assert!(artifact.len() <= 128*1024*1024);
    let p: Program = bincode::deserialize(&artifact).unwrap(); crate::validate(&p).unwrap();
    let mapping = std::fs::read(std::env::var("FLUSH_MAP").unwrap()).unwrap();
    assert!(mapping.len() <= MAX_OUTPUT_BYTES);
    let mapping: Value = serde_json::from_slice(&mapping).unwrap();
    let bytes = std::fs::read(std::env::var("FLUSH_CODE").unwrap()).unwrap();
    assert!(bytes.len() <= MAX_CODE_BYTES);
    assert_eq!(number(&mapping,"schema_version"),1); assert_eq!(mapping["profiled"],false);
    for flag in ["persistent_registers","resumable_calls","complete","reconstructed_bytes_match"] {
        assert_eq!(mapping[flag],true);
    }
    assert_eq!(number(&mapping,"code_bytes"),bytes.len());
    assert_eq!(mapping["code_sha256"],format!("{:x}",Sha256::digest(&bytes)));
    let plain = Jit::new_resumable(&p,false,MAX_CODE_BYTES,true).unwrap().use_adopted_emission();
    let mut observer = Jit::new_resumable(&p,false,MAX_CODE_BYTES,true).unwrap().use_adopted_emission();
    observer.observe_flush = true;
    let (mut cursor,mut assertions) = (0,0);
    let mut seen = BTreeSet::new(); let mut output = vec![];
    for saved in mapping["functions"].as_array().unwrap() {
        let id = number(saved,"function"); assert!(seen.insert(id)); let f = &p.functions[id];
        assert_eq!(saved["name"],f.name);
        let offset = number(saved,"offset"); let end = number(saved,"end");
        assert_eq!(offset,cursor); assert!(offset < end && end <= bytes.len());
        assert_eq!(number(saved,"assertion_base"),assertions);
        let mut cm = Collector {rows:vec![],limit:MAX_SPANS};
        let a = plain.emit_function_inner(f,(end-offset)/4,assertions,Some(&mut cm)).unwrap().unwrap();
        let mut om = Collector {rows:vec![],limit:MAX_SPANS};
        let mut b = observer.emit_function_inner(f,(end-offset)/4,assertions,Some(&mut om)).unwrap().unwrap();
        verify_words(&a.words,&bytes[offset..end]).unwrap(); assert_eq!(a.words,b.words);
        assert_eq!(a.operations,b.operations); assert_eq!(a.resumes,b.resumes); assert_eq!(a.assertions,b.assertions);
        assert_eq!(a.local_fact_events,b.local_fact_events); assert_eq!(a.retained_local_writes,b.retained_local_writes);
        assert!(a.flush_spans.is_empty()); assert!(a.scratch_hits.is_empty() && b.scratch_hits.is_empty());
        cm.validate(f,&a).unwrap(); om.validate(f,&b).unwrap();
        assert_eq!(serde_json::to_value(&cm.rows).unwrap(),serde_json::to_value(&om.rows).unwrap());
        let allocation = values::analyze(f);
        let mut next = 0;
        for coarse in cm.rows.iter().filter(|s|s.kind==Kind::Flush) {
            let mut position = coarse.offset;
            while next < b.flush_spans.len() && b.flush_spans[next].region_start == coarse.region_pc {
                let s = &b.flush_spans[next];
                assert_eq!(s.offset,position); assert!(s.offset < s.end && s.end <= coarse.end);
                assert_eq!(s.region_end,a.entries[s.region_start].unwrap().end);
                assert_eq!(s.tail_consumed,!branch(&f.code[s.region_end-1]));
                assert_eq!(s.analysis_available,allocation.is_some());
                assert_eq!(s.live_before,allocation.as_ref().is_some_and(|v|v.live.at(s.region_end-1,s.register)));
                assert_eq!(s.live_after,allocation.as_ref().is_some_and(|v|v.live.after(s.region_end-1,s.register)));
                assert_eq!(s.eligible,s.analysis_available && s.tail_consumed && s.live_before && !s.live_after);
                position=s.end; next+=1;
            }
            assert_eq!(position,coarse.end);
        }
        assert_eq!(next,b.flush_spans.len());
        assert_eq!(a.assertions.len(),number(saved,"assertion_count"));
        for s in &mut cm.rows {s.offset+=offset;s.end+=offset;}
        assert_eq!(serde_json::to_value(&cm.rows).unwrap(),saved["spans"]);
        for s in &mut b.flush_spans {s.offset+=offset;s.end+=offset;}
        output.push(json!({"function":id,"name":f.name,"flush_spans":b.flush_spans}));
        assertions+=a.assertions.len();cursor=end;
    }
    assert_eq!(cursor,bytes.len()); assert!(plain.code.is_none() && observer.code.is_none());
    assert_eq!(plain.bytes+observer.bytes,0);
    let file = std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("FLUSH_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","functions":output,"code_bytes":bytes.len(),
        "code_sha256":mapping["code_sha256"],"exact_full_function_reconstruction":true,
        "observer_words_unchanged":true,"complete_flush_partition":true,
        "guest_commands":0,"executable_code_publications":0})).unwrap();
}
