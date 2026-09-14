//! Explain exact field changes. Numeric address resemblance is never a proof.
use super::*;
use std::collections::BTreeMap;

fn difference(before: &Function, after: &Function, old_data: &[u8], new_data: &[u8]) -> Option<Value> {
    if bincode::serialize(before).unwrap() == bincode::serialize(after).unwrap() { return None; }
    let names_equal = before.name == after.name;
    let layouts_equal = layout(before) == layout(after);
    let lengths_equal = before.code.len() == after.code.len();
    let mut immediate_only = names_equal && layouts_equal && lengths_equal;
    let (mut imm, mut other, mut in_data, mut equal_window) = (0usize, 0usize, 0usize, 0usize);
    let mut examples = vec![]; let mut deltas = BTreeMap::<String, usize>::new();
    for (pc, (old, new)) in before.code.iter().zip(&after.code).enumerate() {
        if bincode::serialize(old).unwrap() == bincode::serialize(new).unwrap() { continue; }
        match (old, new) {
            (Op::Imm {dst: a, value: x}, Op::Imm {dst: b, value: y}) if a == b => {
                imm += 1;
                let delta = if y >= x { format!("+{}", y-x) } else { format!("-{}", x-y) };
                *deltas.entry(delta.clone()).or_default() += 1;
                let offsets = usize::try_from(*x).ok().zip(usize::try_from(*y).ok());
                let fits = offsets.is_some_and(|(x,y)| x < old_data.len() && y < new_data.len());
                let same = offsets.is_some_and(|(x,y)| {
                    x.checked_add(16).zip(y.checked_add(16)).is_some_and(|(ex,ey)| {
                        old_data.get(x..ex).zip(new_data.get(y..ey)).is_some_and(|(a,b)| a == b)
                    })
                });
                in_data += usize::from(fits); equal_window += usize::from(same);
                if examples.len() < 4 { examples.push(json!({"pc": pc, "before_hex":format!("{x:x}"),
                    "after_hex":format!("{y:x}"), "delta":delta, "both_numbers_fit_data":fits,
                    "equal_16_byte_data_windows":same})); }
            }
            _ => { other += 1; immediate_only = false; }
        }
    }
    Some(json!({"name":after.name,"names_equal":names_equal,"layouts_equal":layouts_equal,
        "code_lengths_equal":lengths_equal,"immediate_values_only":immediate_only,
        "changed_immediates":imm,"other_changed_operations_at_same_pc":other,
        "both_numbers_fit_data":in_data,"equal_16_byte_data_windows":equal_window,
        "deltas":deltas,"examples":examples,
        "address_relocation_proven":false}))
}

fn fixture() -> Function {
    Function { name:"literal".into(), frame_size:8, frame_align:8, registers:2,args:vec![],
        result:crate::Slot{offset:0,size:0}, code:vec![Op::Imm{dst:0,value:1},Op::Return] }
}

#[test]
fn immediate_classification_keeps_width_and_all_other_identity_fields() {
    let old=fixture(); let mut new=old.clone();
    new.code[0]=Op::Imm{dst:0,value:1u128<<127};
    let row=difference(&old,&new,&[],&[]).unwrap();
    assert_eq!(row["immediate_values_only"],true); assert_eq!(row["changed_immediates"],1);
    assert_eq!(row["examples"][0]["after_hex"],"80000000000000000000000000000000");
    assert_eq!(row["both_numbers_fit_data"],0);
    assert!(difference(&old,&old,&[],&[]).is_none());
    for field in 0..4 {
        let mut new=new.clone();
        match field {0=>new.name.push('x'),1=>new.frame_size=16,
            2=>new.code.push(Op::Return),_=>new.code[0]=Op::Imm{dst:1,value:2}}
        assert_eq!(difference(&old,&new,&[],&[]).unwrap()["immediate_values_only"],false);
    }
}

#[test]
fn matching_data_windows_do_not_certify_integer_literals_as_addresses() {
    let old=fixture();let mut new=old.clone();new.code[0]=Op::Imm{dst:0,value:2};
    // Plain integers happen to index equal bytes. Preserve the ambiguity.
    let row=difference(&old,&new,&[0;32],&[0;32]).unwrap();
    assert_eq!(row["both_numbers_fit_data"],1);assert_eq!(row["equal_16_byte_data_windows"],1);
    assert_eq!(row["address_relocation_proven"],false);
}

fn program(item: &Value) -> Program {
    let bytes=bounded(Path::new(item["artifact"].as_str().unwrap()),64*1024*1024);
    assert_eq!(format!("{:x}",Sha256::digest(&bytes)),item["sha256"].as_str().unwrap());
    let p: Program=bincode::DefaultOptions::new().with_fixint_encoding()
        .with_limit(64*1024*1024).reject_trailing_bytes().deserialize(&bytes).unwrap();
    crate::validate(&p).unwrap();p
}

#[test]
#[ignore="Requires closed real-edit artifact pairs and fresh outputs; no guest"]
fn observe_saved_immediate_changes() {
    let pairs:Vec<Value>=serde_json::from_slice(&bounded(Path::new(&std::env::var("NATIVE_CHURN_INPUT").unwrap()),1024*1024)).unwrap();
    assert!(!pairs.is_empty() && pairs.len()<=32);
    for pair in pairs {
        let before=program(&pair["before"]);let after=program(&pair["after"]);
        assert_eq!(before.functions.len(),after.functions.len());
        let mut rows=vec![];
        for (id,(old,new)) in before.functions.iter().zip(&after.functions).enumerate() {
            if let Some(mut row)=difference(old,new,&before.data,&after.data) {
                row["function"]=id.into();rows.push(row);
            }
        }
        let mut deltas=BTreeMap::<String,u64>::new();
        for row in &rows {for (delta,count) in row["deltas"].as_object().unwrap() {
            *deltas.entry(delta.clone()).or_default()+=count.as_u64().unwrap();
        }}
        let summary=json!({"functions":after.functions.len(),"changed_functions":rows.len(),
            "immediate_only_functions":rows.iter().filter(|r|r["immediate_values_only"]==true).count(),
            "name_changes":rows.iter().filter(|r|r["names_equal"]==false).count(),
            "layout_changes":rows.iter().filter(|r|r["layouts_equal"]==false).count(),
            "code_length_changes":rows.iter().filter(|r|r["code_lengths_equal"]==false).count(),
            "changed_immediates":rows.iter().map(|r|r["changed_immediates"].as_u64().unwrap()).sum::<u64>(),
            "both_numbers_fit_data":rows.iter().map(|r|r["both_numbers_fit_data"].as_u64().unwrap()).sum::<u64>(),
            "equal_16_byte_data_windows":rows.iter().map(|r|r["equal_16_byte_data_windows"].as_u64().unwrap()).sum::<u64>()});
        let output=serde_json::to_vec(&json!({"status":"passed","before_sha256":pair["before"]["sha256"],
            "after_sha256":pair["after"]["sha256"],"summary":summary,"deltas":deltas,"rows":rows,
            "guest_commands":0,"code_publications":0,"address_relocation_proven":false})).unwrap();
        assert!(output.len()<=32*1024*1024);
        let mut file=fs::OpenOptions::new().write(true).create_new(true).open(pair["output"].as_str().unwrap()).unwrap();
        file.write_all(&output).unwrap();file.write_all(b"\n").unwrap();
    }
}
