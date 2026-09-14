//! Offline typed census of current decisions and projected bitmap dimensions.
use super::*;
use serde_json::json;
use sha2::{Digest,Sha256};

fn dimensions(f:&Function)->(usize,usize,usize,usize) {
    let mut starts=vec![false;f.code.len()];starts[0]=true;
    for (pc,op) in f.code.iter().enumerate() {
        match op {
            Op::Jump{target}=>starts[*target]=true,
            Op::Switch{cases,otherwise,..}=>{
                starts[*otherwise]=true;
                for (_,target) in cases { starts[*target]=true; }
            }
            _=>{}
        }
        if matches!(op,Op::Jump{..}|Op::Switch{..}|Op::Return|Op::Trap{..}) && pc+1<starts.len() { starts[pc+1]=true; }
    }
    let blocks=starts.iter().filter(|b|**b).count();
    let mut definitions=vec![0;f.registers];let mut required=vec![false;f.registers];let mut epoch=0;
    for (pc,op) in f.code.iter().enumerate() {
        if starts[pc] { epoch=pc+1; }
        let mut writes=[0;2];let mut n=0;
        crate::registers::visit_registers(op,|r| {
            if definitions[r as usize]!=epoch { required[r as usize]=true; }
        },|r|{writes[n]=r;n+=1;});
        for &r in &writes[..n] { definitions[r as usize]=epoch; }
    }
    let needed=required.into_iter().filter(|b|*b).count();
    (blocks,needed,blocks*f.registers.div_ceil(64).max(1),blocks*needed.div_ceil(64).max(1))
}

#[test]
#[ignore="Requires a bound validated artifact, saved direct-call census and fresh output"]
fn observe_saved_register_initialization() {
    let bytes=std::fs::read(std::env::var("INITIALIZATION_ARTIFACT").unwrap()).unwrap();
    assert!(bytes.len()<=128*1024*1024);
    let program:crate::Program=bincode::deserialize(&bytes).unwrap();crate::validate(&program).unwrap();
    let calls:Vec<serde_json::Value>=serde_json::from_slice(&std::fs::read(std::env::var("INITIALIZATION_CALLS").unwrap()).unwrap()).unwrap();
    let mut rows=vec![];let mut nominal=0u128;let mut current_zeroes=0u128;
    for call in calls {
        let id=call["function"].as_u64().unwrap() as usize;let f=&program.functions[id];
        assert_eq!(call["name"].as_str().unwrap(),f.name);
        assert_eq!(call["registers"].as_u64().unwrap() as usize,f.registers);
        assert_eq!(call["operations"].as_u64().unwrap() as usize,f.code.len());
        assert_eq!(call["frame_bytes"].as_u64().unwrap() as usize,f.frame_size);
        let needs=crate::registers::needs_initial_zeroes(f);
        let (blocks,required,dense_cells,projected_cells)=dimensions(f);
        let weight=call["nominal_register_bytes"].as_u64().unwrap() as u128;
        nominal+=weight;if needs { current_zeroes+=weight; }
        rows.push(json!({"function":id,"name":f.name,"registers":f.registers,"operations":f.code.len(),
            "ordinary_direct_calls_lower_bound":call["ordinary_direct_calls_lower_bound"],
            "nominal_register_bytes":call["nominal_register_bytes"],"needs_initial_zeroes":needs,
            "blocks":blocks,"upward_exposed_registers":required,"dense_cells":dense_cells,"projected_cells":projected_cells,
            "register_bound_exceeded":f.registers>BOUNDS.registers,"block_bound_exceeded":blocks>BOUNDS.blocks,
            "dense_cell_bound_exceeded":dense_cells>BOUNDS.cells,"projected_cell_bound_exceeded":projected_cells>BOUNDS.cells}));
    }
    let output=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("INITIALIZATION_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(output,&json!({"status":"passed","artifact_sha256":format!("{:x}",Sha256::digest(&bytes)),
        "nominal_register_bytes":nominal,"current_zeroing_direct_weight":current_zeroes,"functions":rows,
        "bounds":{"registers":BOUNDS.registers,"operations":BOUNDS.operations,"blocks":BOUNDS.blocks,"cells":BOUNDS.cells,"edges":BOUNDS.edges,"work":BOUNDS.work},
        "guest_commands":0,"production_changes":0,
        "scope":"Current production initialization decisions on typed validated functions. Direct-call byte weights are not measured traffic. Projected dimensions conservatively include unreachable blocks and do not establish initialization or a future proof's resource/work success."})).unwrap();
}
