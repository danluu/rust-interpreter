use super::*;

fn function() -> Function {
    Function { name:"same".into(), frame_size:16, frame_align:8, registers:2,
        args:vec![Slot{offset:8,size:8}],result:Slot{offset:0,size:8},
        code:vec![Op::Local{dst:0,offset:8},Op::Load{dst:1,address:0,size:8},Op::Return] }
}
fn profile_value(f: &Function) -> Value {
    json!({"functions":[{"name":f.name,"frame_size":f.frame_size,"registers":f.registers,
        "operations":f.code.iter().map(|op|format!("{op:?}")).collect::<Vec<_>>(),
        "interpreted":[0,0,0],"jit_blocks":[2,0,0],"jit_block_ends":[3,0,0],
        "jit_tree_blocks":[0,3,0],"jit_tree_block_ends":[0,3,0]}]})
}
fn inventory_value(f: &Function) -> Value {
    json!({"schema_version":1,"diagnostic_only":true,"boundary_rows":1,"program_functions":1,
        "functions":[{"function_id":0,"function_sha256":format!("{:x}",Sha256::digest(bincode::serialize(f).unwrap())),
        "args":f.args,"result":f.result,"status":"observed","ordinary_private_primitive_slots":0,
        "spread_argument":false,"synthetic_caller_location":false,"rows":[{
        "local":1,"role":"argument","slot":f.args[0],"abi_binding":true,"abi_argument_indices":[0],
        "primitive":true,"scalar_layout":true,"eligible_primitive":true,"eligible_scalar_layout":true}]}]})
}
fn program(f: Function) -> Program {
    Program {version:rust_interp_bytecode::VERSION,target:"test".into(),entry:0,functions:vec![f],data:vec![],statics:vec![],thread_locals:vec![]}
}

#[test]
fn interval_sweep_matches_overlaps_and_rejects_invalid_profiles() {
    let f = function();
    let p: Profile = serde_json::from_value(profile_value(&f)).unwrap();
    assert_eq!(frequencies(&f,&p.functions[0]).unwrap(),[2,5,5]);
    for field in ["name","operations","jit_block_ends"] {
        let mut bad=profile_value(&f);
        match field {
            "name"=>bad["functions"][0][field]=json!("changed"),
            "operations"=>bad["functions"][0][field][1]=json!("wrong"),
            _=>bad["functions"][0][field][0]=json!(4),
        }
        let p: Profile=serde_json::from_value(bad).unwrap();
        assert!(frequencies(&f,&p.functions[0]).is_err());
    }
    let mut bad=profile_value(&f);bad["functions"][0]["jit_blocks"][0]=json!(u64::MAX);
    let p:Profile=serde_json::from_value(bad).unwrap();
    assert!(frequencies(&f,&p.functions[0]).is_err());
}

#[test]
fn overlap_does_not_confuse_partial_or_zero_width() {
    let s=Slot{offset:8,size:8};
    assert_eq!(overlap(8,8,s),Some(true));
    assert_eq!(overlap(10,2,s),Some(false));
    assert_eq!(overlap(0,8,s),None);
    assert_eq!(overlap(8,0,s),None);
    assert_eq!(overlap(usize::MAX,8,s),None);
}

#[test]
fn exact_body_abi_and_duplicate_id_guards() {
    let f=function();let p=program(f.clone());
    let good:Inventory=serde_json::from_value(inventory_value(&f)).unwrap();
    check_inventory(&p,&good).unwrap();
    for kind in ["hash","slot","duplicate","unbound"] {
        let mut bad=inventory_value(&f);
        match kind {
            "hash"=>bad["functions"][0]["function_sha256"]=json!("wrong"),
            "slot"=>bad["functions"][0]["rows"][0]["slot"]["offset"]=json!(0),
            "unbound"=>bad["functions"][0]["rows"][0]["abi_binding"]=json!(false),
            _=>{let duplicate=bad["functions"][0].clone();bad["functions"].as_array_mut().unwrap().push(duplicate);bad["boundary_rows"]=json!(2);}
        }
        assert!(check_inventory(&p,&serde_json::from_value(bad).unwrap()).is_err());
    }
}

#[test]
fn full_partial_and_unknown_accesses_stay_separate() {
    let f=function();
    let row=inventory_value(&f)["functions"][0]["rows"][0].clone();
    let mut counts=vec![Counts::new()];let mut totals=Counts::new();
    let facts=vec![Some(Fact::Local(8)),None];
    memory("load",0,8,&facts,&f,&[row.clone()],&mut counts,&mut totals,7,2);
    memory("load",0,4,&facts,&f,&[row.clone()],&mut counts,&mut totals,3,0);
    memory("load",1,8,&facts,&f,&[row],&mut counts,&mut totals,5,0);
    assert_eq!(counts[0]["load_full_hits"],9);
    assert_eq!(counts[0]["load_partial_hits"],3);
    assert_eq!(totals["load_unknown_or_nonframe_address_hits"],5);
    assert_eq!(totals["load_hits"],17);
}

#[test]
fn register_redefinition_invalidates_known_address() {
    let mut facts=vec![Some(Fact::Local(8)),None];
    transfer(&Op::Load{dst:0,address:0,size:8},&mut facts,16);
    assert_eq!(facts[0],None);
    transfer(&Op::Local{dst:0,offset:8},&mut facts,16);
    assert_eq!(facts[0],Some(Fact::Local(8)));
}
