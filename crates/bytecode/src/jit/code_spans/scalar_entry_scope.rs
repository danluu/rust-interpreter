//! Typed scope only; do not change scalar admission or publish executable code.
use super::*;
use serde_json::{Value,json};

fn empty_padding(caller_align:usize,caller_size:usize,callee_align:usize)->bool {
    assert!(caller_align.is_power_of_two() && callee_align.is_power_of_two());
    caller_align>=callee_align && caller_size.max(1)%callee_align==0
}
fn aligned(value:usize,align:usize)->usize {value.checked_add(align-1).unwrap()&!(align-1)}

#[test]
fn empty_padding_proof_matches_retained_alignment_histories_and_rejects_missing_hypotheses() {
    let aligns=[1,2,4,8,16,32,64,256,4096];
    let sizes=[0,1,2,3,4,7,8,15,16,24,31,64,120,128,256,511,512,513];
    let mut cases=0;
    for ca in aligns {for size in sizes {for na in aligns {
        if !empty_padding(ca,size,na) {continue;}
        for base in [0,ca,7*ca,1024*ca] {
            let initial=base+size.max(1);
            assert_eq!(aligned(initial,na),initial);
            for first in aligns {for second in aligns {
                let retained=aligned(aligned(initial,first),second);
                assert_eq!(aligned(retained,na),retained);
                cases+=1;
            }}
            // Longer histories include increasing and decreasing alignments.
            let mut retained=initial;
            for a in aligns.into_iter().chain(aligns.into_iter().rev()).cycle().take(128) {
                retained=aligned(retained,a);
                assert_eq!(aligned(retained,na),retained);
            }
        }
    }}}
    assert!(cases>100_000);
    // Extent alone cannot establish alignment of the caller's base.
    assert!(!empty_padding(1,8,8));assert_ne!(aligned(1+8,8),1+8);
    // Base alignment alone cannot establish alignment of its memory end.
    assert!(!empty_padding(8,1,8));assert_ne!(aligned(8+1,8),8+1);
    assert!(!empty_padding(16,0,16));assert_ne!(aligned(16+1,16),16+1);
}

#[test]
fn positive_scalar_budget_guard_subsumes_only_the_common_zero_budget_check() {
    for steps in 1_u64..=512 {
        let required=steps.checked_add(1).unwrap();
        for budget in (0..=514).chain([u64::MAX-1,u64::MAX]) {
            let admitted=budget>=required;
            assert_eq!(budget!=0 && admitted,admitted);
            if budget==0 {assert!(!admitted);}
        }
    }
    // Do not replace the stronger guard by merely checking a nonzero budget.
    assert!(1_u64!=0 && 1<2);
}

fn number(v:&Value,key:&str)->usize {usize::try_from(v[key].as_u64().unwrap()).unwrap()}

#[test]
#[ignore="Requires SHA-bound typed bytecode and a closed native protocol report"]
fn observe_saved_scalar_entry_empty_work() {
    let bytes=std::fs::read(std::env::var("ENTRY_ARTIFACT").unwrap()).unwrap();
    assert!(bytes.len()<=128*1024*1024);
    let p:Program=bincode::deserialize(&bytes).unwrap();crate::validate(&p).unwrap();
    let source=std::fs::read(std::env::var("ENTRY_PROTOCOL").unwrap()).unwrap();
    assert!(source.len()<=MAX_OUTPUT_BYTES);
    let protocol:Value=serde_json::from_slice(&source).unwrap();
    assert_eq!(protocol["status"],"passed");assert_eq!(protocol["schema_version"],2);
    for key in ["complete_partition","exact_full_function_reconstruction","exact_transition_reconstruction"] {assert_eq!(protocol[key],true);}
    assert_eq!(protocol["guest_commands"],0);assert_eq!(protocol["executable_code_publications"],0);
    let mut sites=BTreeSet::new();let mut callees=BTreeMap::new();let mut rows=vec![];
    let mut proof_work=crate::proof::MAX_GLOBAL_WORK;
    for span in protocol["spans"].as_array().unwrap() {
        if span["kind"]!="scalar_entry_budget" {continue;}
        assert_eq!(span["operation"],"Call");assert!(span["argument"].is_null());
        let caller_id=number(span,"function");let pc=number(span,"pc");
        assert!(sites.insert((caller_id,pc)));
        let caller=&p.functions[caller_id];
        let Op::Call {function:callee_id,args,..}=&caller.code[pc] else {panic!("not a typed Call");};
        let callee=&p.functions[*callee_id];assert_eq!(args.len(),callee.args.len());
        let steps=*callees.entry(*callee_id).or_insert_with(|| {
            let memory=crate::proof::memory_plan(&p,*callee_id,&mut proof_work);
            let plan=crate::scalar_ir::lower(callee,&memory,250_000).unwrap();
            let emitted=crate::scalar_ir::native_leaf::emit_call(&plan,false).unwrap();
            assert!(!emitted.words.is_empty());
            assert!(plan.maximum_steps>0 && plan.maximum_steps<=512);
            plan.maximum_steps
        });
        let required=steps.checked_add(1).unwrap();
        rows.push(json!({"caller":caller_id,"pc":pc,"callee":callee_id,
            "caller_frame_align":caller.frame_align,"caller_frame_size":caller.frame_size,
            "callee_frame_align":callee.frame_align,"callee_frame_size":callee.frame_size,
            "argument_sizes":callee.args.iter().map(|a|a.size).collect::<Vec<_>>(),
            "padding_proven_empty":empty_padding(caller.frame_align,caller.frame_size,callee.frame_align),
            "maximum_steps":steps,"minimum_scalar_budget":required,"zero_entry_check_subsumed":true}));
        assert!(rows.len()<=131_072 && callees.len()<=4096);
    }
    assert!(!rows.is_empty());
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("ENTRY_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","artifact_sha256":format!("{:x}",Sha256::digest(&bytes)),
        "protocol_sha256":format!("{:x}",Sha256::digest(&source)),"code_sha256":protocol["code_sha256"],
        "sites":rows,"unique_callees":callees.len(),"guest_commands":0,"executable_code_publications":0})).unwrap();
}
