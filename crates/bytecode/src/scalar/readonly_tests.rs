use super::*;
use crate::{Engine,Limits,Program,Slot,VERSION};

fn fixture(code:Vec<Op>,frame:usize,args:Vec<Slot>,result:Slot)->Program {
    Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,
        data:(0..96).map(|i|(i*37+11) as u8).collect(),statics:vec![],thread_locals:vec![],
        functions:vec![Function{name:"readonly scalar control".into(),frame_size:frame,frame_align:8,registers:8,args,result,code}]}
}
fn plan(p:&Program)->Result<Plan,&'static str> {
    crate::validate(p).unwrap();
    let memory=crate::proof::memory_plan_readonly(p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());
    lower(&p.functions[0],&memory,250_000)
}
fn checked_read(data:&[u8],fresh:std::ops::Range<usize>,address:u128,size:u8)->Result<u128,String> {
    // Guest addresses consume the low native usize, matching the reference VM.
    let address=address as usize;let size=size as usize;
    let end=address.checked_add(size).ok_or("address overflow")?;
    if size!=0 && address<fresh.end && fresh.start<end {
        return Err("readonly private replay required".into());
    }
    if address==0 || end>data.len() {return Err("invalid guest memory access".into());}
    let mut bytes=[0u8;16];bytes[..size].copy_from_slice(&data[address..end]);Ok(u128::from_le_bytes(bytes))
}
fn compare(p:&Program,args:&[u128],budget:usize) {
    let plan=plan(p).unwrap();let f=&p.functions[0];let base=p.data.len();
    let scalar=plan.evaluate_reads(args,base,budget,&f.name,&mut |a,n|checked_read(&p.data,base..base+f.frame_size.max(1),a,n));
    let reference=crate::execute_profiled(p,args,Limits{instructions:budget as u64,..Limits::default()},Engine::Interpreter);
    match (scalar,reference) {
        (Ok(s),Ok((v,profile)))=>{
            assert_eq!(s.value,v.value);assert_eq!(s.pcs.len() as u64,v.instructions);
            let mut hits=vec![0u64;f.code.len()];for pc in s.pcs {hits[pc]+=1;}
            assert_eq!(hits,profile.functions[0].interpreted);
        },
        (Err(a),Err(b))=>assert_eq!(a,b),
        (a,b)=>panic!("scalar {a:?}, reference {b:?}"),
    }
}

#[test]
fn readonly_loads_copies_and_padding_match_original_budgets() {
    for size in [1u8,2,4,8,16] {for copy in [false,true] {
        let mut code=vec![Op::Local{dst:0,offset:16},Op::Load{dst:1,address:0,size:8},Op::Local{dst:2,offset:0}];
        if copy {code.push(Op::Copy{src:1,dst:2,size:size as usize});}
        else {code.push(Op::Load{dst:3,address:1,size});code.push(Op::Store{address:2,src:3,size});}
        code.push(Op::Return);
        let p=fixture(code,24,vec![Slot{offset:16,size:8}],Slot{offset:0,size:16});
        assert!(!crate::proof::memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone()).eligible);
        for pointer in [1,17,63] {for budget in 0..=p.functions[0].code.len()+1 {compare(&p,&[pointer],budget);}}
    }}
}

#[test]
fn readonly_dead_reads_keep_fault_order_and_conditional_reachability() {
    let p=fixture(vec![Op::Local{dst:0,offset:8},Op::Load{dst:1,address:0,size:8},
        Op::Switch{value:1,cases:vec![(0,5)],otherwise:3},Op::Load{dst:2,address:1,size:8},
        Op::Assert{value:1,expected:false,message:"after the unused read".into()},Op::Return],
        16,vec![Slot{offset:8,size:8}],Slot{offset:0,size:8});
    let plan=plan(&p).unwrap();let id=plan.computations[3][0];
    assert!(plan.live[id] && matches!(plan.nodes[id].value,Value::Read{..}));
    for pointer in [0,16,1024] {for budget in 0..=7 {compare(&p,&[pointer],budget);}}
}

#[test]
fn readonly_chained_reads_and_join_values_preserve_pointer_bits() {
    let mut p=fixture(vec![Op::Local{dst:0,offset:16},Op::Load{dst:1,address:0,size:8},
        Op::Load{dst:2,address:1,size:8},Op::Local{dst:3,offset:8},Op::Store{address:3,src:2,size:8},
        Op::Load{dst:4,address:3,size:8},Op::Load{dst:5,address:4,size:8},
        Op::Switch{value:5,cases:vec![(0,10)],otherwise:8},Op::Imm{dst:5,value:47},Op::Jump{target:11},
        Op::Imm{dst:5,value:93},Op::Local{dst:6,offset:0},Op::Store{address:6,src:5,size:8},Op::Return],
        24,vec![Slot{offset:16,size:8}],Slot{offset:0,size:8});
    p.data[16..24].copy_from_slice(&32u64.to_le_bytes());p.data[24..32].copy_from_slice(&40u64.to_le_bytes());
    p.data[32..40].fill(0);
    for pointer in [16,24] {for budget in 0..=15 {compare(&p,&[pointer],budget);}}
}

#[test]
fn readonly_rejects_external_writes_unknown_effects_and_nested_calls() {
    let prefix=vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8}];
    for op in [Op::Store{address:1,src:2,size:1},Op::Copy{dst:1,src:0,size:1},
        Op::Allocate{dst:2,size:1,align:1,zeroed:true},Op::Call{function:0,args:vec![0],destination:0}] {
        let mut code=prefix.clone();code.push(op);code.push(Op::Return);
        let p=fixture(code,8,vec![Slot{offset:0,size:8}],Slot{offset:0,size:0});assert!(plan(&p).is_err());
    }
}

#[test]
fn readonly_guard_replays_fresh_frame_padding_and_crossing_ranges() {
    let data=vec![0x55;128];
    for (address,size) in [(95,2),(96,1),(100,8),(111,1),(u128::MAX,2)] {
        assert!(checked_read(&data,96..112,address,size).is_err());
    }
    assert_eq!(checked_read(&data,96..112,88,8).unwrap(),0x5555555555555555);
    assert_eq!(checked_read(&data,96..112,112,8).unwrap(),0x5555555555555555);
    // An unknown pointer into the virtual frame must decline, even though
    // ordinary execution could read its freshly initialized/captured bytes.
    let p=fixture(vec![Op::Local{dst:0,offset:8},Op::Load{dst:1,address:0,size:8},
        Op::Load{dst:2,address:1,size:8},Op::Local{dst:3,offset:0},Op::Store{address:3,src:2,size:8},Op::Return],
        16,vec![Slot{offset:8,size:8}],Slot{offset:0,size:8});
    let result=plan(&p).unwrap().evaluate_reads(&[104],96,20,"test",&mut |a,n|checked_read(&p.data,96..112,a,n));
    assert_eq!(result.unwrap_err(),"readonly private replay required");
    assert_eq!(crate::execute(&p,&[104],Limits::default()).unwrap().value,104);
}

#[test]
fn readonly_limits_and_native_refusal_remain_explicit() {
    let p=fixture(vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},Op::Load{dst:2,address:1,size:8},Op::Return],
        8,vec![Slot{offset:0,size:8}],Slot{offset:0,size:8});
    let plan=plan(&p).unwrap();
    assert_eq!(native_leaf::emit_call(&plan,false).err(),Some("native_external_read_unimplemented"));
    assert!(!crate::proof::memory_plan_readonly(&p,0,&mut 0).eligible);
    let mut changed=p.clone();changed.functions[0].code[2]=Op::Copy{src:1,dst:0,size:17};
    changed.functions[0].frame_size=24;assert!(self::plan(&changed).is_err());
    changed=p.clone();changed.functions[0].code[3]=Op::Jump{target:2};
    assert_eq!(self::plan(&changed).err(),Some("scalar_cycle"));
    changed=p;changed.functions[0].frame_size=513;assert!(self::plan(&changed).is_err());
}

#[test]
#[ignore="Requires a pinned public artifact and a fresh output path"]
fn observe_saved_readonly_plans() {
    use serde_json::json;
    use sha2::{Digest,Sha256};
    let bytes=std::fs::read(std::env::var("READONLY_ARTIFACT").unwrap()).unwrap();assert!(bytes.len()<=128*1024*1024);
    let digest=format!("{:x}",Sha256::digest(&bytes));assert_eq!(digest,std::env::var("READONLY_ARTIFACT_SHA256").unwrap());
    let p:Program=bincode::deserialize(&bytes).unwrap();crate::validate(&p).unwrap();assert!(p.functions.len()<=65536);
    let mut work=crate::proof::MAX_GLOBAL_WORK;let mut rows=vec![];
    for (id,f) in p.functions.iter().enumerate() {
        let memory=crate::proof::memory_plan_readonly(&p,id,&mut work);
        let plan=lower(f,&memory,250_000);let summary=summary(&plan);
        let reads=plan.as_ref().ok().map(|p|p.nodes.iter().filter(|n|matches!(n.value,Value::Read{..})).count()).unwrap_or(0);
        rows.push(json!({"function":id,"name":f.name,"memory_eligible":memory.eligible,"memory_decline":memory.decline,
            "scalar":summary,"external_reads":reads,"candidate":plan.is_ok() && reads>0,"native_implemented":false}));
    }
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("READONLY_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","artifact_sha256":digest,"rows":rows,"functions":p.functions.len(),
        "memory_work_used":crate::proof::MAX_GLOBAL_WORK-work,"memory_work_remaining":work,
        "production_policy_changed":false,"original_project_guest_commands":0,"executable_code_publications":0})).unwrap();
}
