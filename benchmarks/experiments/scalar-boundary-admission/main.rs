//! Probe the unchanged scalar transform on private copies; never run probe bodies.
use bincode::Options;
use rust_interp_bytecode::{Binary, Function, Op, Program, Reg, Slot, diagnostic_visit_registers, validate};
use serde::Deserialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
#[path="../../../crates/mir-export/src/lower/scalar_promote_transform.rs"]
mod transform;
#[allow(dead_code)]
#[path="../scalar-boundary-census/profile.rs"]
mod profile;

const WORK_LIMIT: usize = 32_000_000;

fn probe(f: &Function, slot: Slot, work: &mut usize) -> Value {
    if f.code.len()>100_000 || f.registers>100_000 {
        return json!({"admitted":false,"reason":"function_bound"});
    }
    let Some(next) = work.checked_add(f.code.len()).filter(|&n| n<=WORK_LIMIT) else {
        return json!({"admitted":false,"reason":"total_work_bound"});
    };
    *work=next;
    // This zero-initialized probe is NOT a valid argument/result ABI rewrite.
    // Only its existing address-use selection is observed; discard the body.
    let mut code=f.code.clone();let mut registers=f.registers as u32;
    let r=transform::promote(&mut code,&mut registers,&[slot]);
    json!({"admitted":r.slots==1,"reason":if r.slots==1 {"address_shape_admitted"} else {"existing_transform_rejected"},
        "removed_addresses":r.removed_addresses,"rewritten":r.rewritten,"removed_moves":r.removed_moves})
}

fn typed_slot(program: &Program, row: &Value) -> Result<(usize, u64, Slot), String> {
    let id=row["function_id"].as_u64().ok_or("missing function ID")? as usize;
    let f=program.functions.get(id).ok_or("function ID out of range")?;
    if row["function_sha256"] != format!("{:x}",Sha256::digest(bincode::serialize(f).map_err(|e|e.to_string())?)) {
        return Err("exact function hash differs".into());
    }
    let typed=&row["typed"];let local=typed["local"].as_u64().ok_or("missing local ID")?;
    if typed["abi_binding"]!=true || (typed["eligible_primitive"]!=true && typed["eligible_scalar_layout"]!=true) {
        return Err("row lacks typed eligibility or ABI binding".into());
    }
    let s:Slot=serde_json::from_value(typed["slot"].clone()).map_err(|e|e.to_string())?;
    let expected=if typed["role"]=="result" && local==0 { &f.result }
    else if typed["role"]=="argument" && local!=0 {
        let indices=typed["abi_argument_indices"].as_array().ok_or("missing ABI index")?;
        if indices.len()!=1 {return Err("ambiguous ABI index".into());}
        f.args.get(indices[0].as_u64().ok_or("invalid ABI index")? as usize).ok_or("ABI index out of range")?
    } else {return Err("invalid typed role".into());};
    if (s.offset,s.size)!=(expected.offset,expected.size) || !matches!(s.size,1|2|4|8|16) {
        return Err("typed ABI slot differs".into());
    }
    Ok((id,local,s))
}

type Counts=BTreeMap<String,u128>;
fn add(out:&mut Counts,k:&str,v:u128) {*out.entry(k.into()).or_default()+=v;}
fn count(out:&mut Counts,key:&str,j:u64,i:u64,size:usize) {
    add(out,&format!("{key}:hits"),j as u128+i as u128);
    add(out,&format!("{key}:bytes"),(j as u128+i as u128)*size as u128);
    add(out,&format!("{key}:native_hits"),j as u128);
    add(out,&format!("{key}:native_bytes"),j as u128*size as u128);
}

fn run(program:&Program,profile:&profile::Profile,prior:&Value)->Result<Value,String> {
    validate(program)?;
    if profile.functions.len()!=program.functions.len() || prior["performance_measurement"]!=false {
        return Err("original census identity differs".into());
    }
    let original=prior["rows"].as_array().ok_or("missing census rows")?;
    if original.len()>32_768 {return Err("row bound exceeded".into());}
    let mut rows=vec![];let mut work=0;let mut seen=BTreeSet::new();
    let mut argument_rows=BTreeMap::new();let mut result_rows=BTreeMap::new();
    for row in original {
        if row["typed"]["eligible_primitive"]!=true && row["typed"]["eligible_scalar_layout"]!=true {continue;}
        let (id,local,slot)=typed_slot(program,row)?;
        if !seen.insert((id,local)) {return Err("duplicate typed boundary row".into());}
        let shape=probe(&program.functions[id],slot,&mut work);
        let category=row["category"].as_str().ok_or("missing scalar category")?;
        if !matches!(category,"eligible_primitive"|"eligible_other_scalar") {return Err("wrong scalar category".into());}
        let index=rows.len();
        if local==0 {result_rows.insert(id,index);}
        else {
            let argument=row["typed"]["abi_argument_indices"][0].as_u64().unwrap() as usize;
            if argument_rows.insert((id,argument),index).is_some() {return Err("duplicate argument binding".into());}
        }
        rows.push(json!({"function_id":id,"local":local,"category":category,"typed":row["typed"],
            "function_sha256":row["function_sha256"],"shape":shape,"accesses":row["accesses"],"boundary":Counts::new()}));
    }
    let mut totals=Counts::new();let mut boundary=Counts::new();let mut per_row=vec![Counts::new();rows.len()];
    for (id,(f,p)) in program.functions.iter().zip(&profile.functions).enumerate() {
        let native=profile::frequencies(f,p)?;
        for (pc,op) in f.code.iter().enumerate() {
            let j=native[pc];let i=p.interpreted[pc];let hits=j as u128+i as u128;
            add(&mut totals,"instructions",hits);add(&mut totals,"native_instructions",j as u128);
            match op {
                Op::Call{function,..}=>{
                    add(&mut totals,"direct_calls",hits);add(&mut totals,"native_direct_calls",j as u128);
                    for (arg,s) in program.functions[*function].args.iter().enumerate() {
                        if let Some(&index)=argument_rows.get(&(*function,arg)) {
                            let row=&rows[index];let status=if row["shape"]["admitted"]==true {"admitted"} else {"rejected"};
                            count(&mut boundary,&format!("argument:{}:{status}",row["category"].as_str().unwrap()),j,i,s.size);
                            count(&mut per_row[index],"incoming_argument",j,i,s.size);
                        } else {count(&mut boundary,"argument:outside_mir_candidates",j,i,s.size);}
                    }
                }
                Op::CallIndirect{arg_sizes,..}=>{
                    add(&mut totals,"indirect_calls",hits);
                    for size in arg_sizes {count(&mut boundary,"indirect_argument:unresolved",j,i,*size);}
                }
                Op::Return=>{
                    add(&mut totals,"returns",hits);add(&mut totals,"native_returns",j as u128);
                    if let Some(&index)=result_rows.get(&id) {
                        let row=&rows[index];let status=if row["shape"]["admitted"]==true {"admitted"} else {"rejected"};
                        count(&mut boundary,&format!("result:{}:{status}",row["category"].as_str().unwrap()),j,i,f.result.size);
                        count(&mut per_row[index],"return",j,i,f.result.size);
                    } else {count(&mut boundary,"result:outside_mir_candidates",j,i,f.result.size);}
                }
                Op::RandomBytes{..}=>add(&mut totals,"random_events",hits),
                _=>{},
            }
        }
    }
    for key in ["instructions","native_instructions","direct_calls","native_direct_calls","indirect_calls","returns","native_returns","random_events"] {
        let expected=prior["totals"][key].as_u64().unwrap_or(0) as u128;
        if totals.get(key).copied().unwrap_or(0)!=expected {return Err(format!("original {key} does not reconcile"));}
    }
    for (row,counts) in rows.iter_mut().zip(per_row) {row["boundary"]=json!(counts);}
    Ok(json!({"rows":rows,"totals":totals,"boundary":boundary,"probe_operations":work,"work_limit":WORK_LIMIT,
        "performance_measurement":false,"probe_bodies_executed":false,
        "note":"Exact existing transform address-shape admission only. Probe bodies are discarded. Argument initialization and result publication require a separate scalar ABI implementation."}))
}

fn read(path:&str,limit:u64)->Result<Vec<u8>,Box<dyn std::error::Error>> {
    if std::fs::metadata(path)?.len()>limit {return Err("input bound exceeded".into());}
    let bytes=std::fs::read(path)?;if bytes.len() as u64>limit {return Err("input grew past bound".into());}Ok(bytes)
}
fn main()->Result<(),Box<dyn std::error::Error>> {
    let args:Vec<_>=std::env::args().skip(1).collect();
    if args.len()!=3 {return Err("usage: scalar-boundary-admission PROGRAM PROFILE PRIOR_CENSUS".into());}
    let program:Program=bincode::DefaultOptions::new().with_fixint_encoding().with_limit(64*1024*1024)
        .reject_trailing_bytes().deserialize(&read(&args[0],64*1024*1024)?)?;
    let profile:profile::Profile=serde_json::from_slice(&read(&args[1],128*1024*1024)?)?;
    let prior:Value=serde_json::from_slice(&read(&args[2],64*1024*1024)?)?;
    serde_json::to_writer_pretty(std::io::stdout().lock(),&run(&program,&profile,&prior)?)?;Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn function(code:Vec<Op>)->Function {
        Function{name:"argument".into(),frame_size:16,frame_align:8,registers:2,args:vec![Slot{offset:8,size:8}],
            result:Slot{offset:0,size:8},code}
    }
    #[test]
    fn probes_never_mutate_original_and_include_cold_uses() {
        let f=function(vec![Op::Local{dst:0,offset:8},Op::Load{dst:1,address:0,size:8},Op::Return]);
        let before=bincode::serialize(&f).unwrap();let s=Slot{offset:8,size:8};let mut work=0;
        assert_eq!(probe(&f,s,&mut work)["admitted"],true);assert_eq!(bincode::serialize(&f).unwrap(),before);
        let mut cold=f.clone();cold.code.extend([Op::Local{dst:0,offset:8},Op::Store{address:0,src:0,size:8},Op::Return]);
        assert_eq!(probe(&cold,s,&mut work)["admitted"],false);
        let partial=function(vec![Op::Local{dst:0,offset:8},Op::Load{dst:1,address:0,size:4},Op::Return]);
        assert_eq!(probe(&partial,s,&mut work)["admitted"],false);
    }
    #[test]
    fn work_exhaustion_never_admits_or_changes_budget() {
        let f=function(vec![Op::Return]);let mut work=WORK_LIMIT;
        assert_eq!(probe(&f,Slot{offset:8,size:8},&mut work)["reason"],"total_work_bound");
        assert_eq!(work,WORK_LIMIT);
    }
    #[test]
    fn typed_identity_and_abi_position_are_checked() {
        let f=function(vec![Op::Return]);
        let p=Program{version:rust_interp_bytecode::VERSION,target:"aarch64-apple-darwin".into(),entry:0,
            functions:vec![f.clone()],data:vec![],statics:vec![],thread_locals:vec![]};
        let mut row=json!({"function_id":0,"function_sha256":format!("{:x}",Sha256::digest(bincode::serialize(&f).unwrap())),
            "typed":{"local":1,"role":"argument","slot":f.args[0],"abi_binding":true,"abi_argument_indices":[0],"eligible_primitive":true}});
        assert!(typed_slot(&p,&row).is_ok());
        row["typed"]["slot"]["offset"]=json!(0);assert!(typed_slot(&p,&row).is_err());
        row["typed"]["slot"]=json!(f.args[0]);row["function_sha256"]=json!("same name is insufficient");assert!(typed_slot(&p,&row).is_err());
    }
}
