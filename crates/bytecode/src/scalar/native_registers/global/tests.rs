use super::*;

pub(super) fn straight(split: bool) -> Plan {
    let mut code=vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8}];
    for r in 4..10 {code.extend([Op::Imm{dst:14,value:r as u128},
        Op::Binary{dst:r,overflow:15,op:Binary::Add,a:1,b:14,bits:64,signed:false}]);}
    if split {code.push(Op::Jump{target:code.len()+1});}
    code.push(Op::Imm{dst:11,value:0});
    for r in 4..10 {code.push(Op::Binary{dst:11,overflow:15,op:Binary::Add,a:11,b:r,bits:64,signed:false});}
    code.extend([Op::Store{address:0,src:11,size:8},Op::Return]);
    lower_fixture(code,16,vec![crate::Slot{offset:0,size:8}],crate::Slot{offset:0,size:8})
}

fn lower_fixture(code:Vec<Op>,frame:usize,args:Vec<crate::Slot>,result:crate::Slot) -> Plan {
    let f=crate::Function{name:"global register fixture".into(),frame_size:frame,frame_align:16,registers:24,args,result,code};
    let p=crate::Program{version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,
        functions:vec![f],data:vec![],statics:vec![],thread_locals:vec![]};crate::validate(&p).unwrap();
    let memory=crate::proof::memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());
    crate::scalar_ir::lower(&p.functions[0],&memory,250_000).unwrap()
}

fn diamond(seed: usize, width: u8) -> Plan {
    let mut code=vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},
        Op::Local{dst:2,offset:8},Op::Load{dst:3,address:2,size:8},
        Op::Local{dst:4,offset:16},Op::Imm{dst:5,value:(seed+1) as u128},
        Op::Binary{dst:6,overflow:23,op:Binary::Add,a:1,b:5,bits:64,signed:false},
        Op::Switch{value:3,cases:vec![(0,8)],otherwise:12},
        Op::Unary{dst:7,src:6,op:Unary::Not,bits:64},
        Op::Store{address:4,src:7,size:width},Op::Imm{dst:8,value:19},Op::Jump{target:16},
        Op::Binary{dst:7,overflow:23,op:Binary::Xor,a:6,b:5,bits:64,signed:false},
        Op::Store{address:4,src:7,size:width},Op::Imm{dst:8,value:23},Op::Jump{target:16},
        Op::Load{dst:9,address:4,size:width},
        Op::Binary{dst:10,overflow:23,op:Binary::Add,a:9,b:6,bits:64,signed:false},
        Op::Binary{dst:11,overflow:23,op:Binary::Xor,a:10,b:8,bits:64,signed:false},
        Op::Store{address:0,src:11,size:8},Op::Return];
    if seed%2==1 {code[8]=Op::Binary{dst:7,overflow:23,op:Binary::Mul,a:6,b:5,bits:64,signed:false};}
    lower_fixture(code,32,vec![crate::Slot{offset:0,size:8},crate::Slot{offset:8,size:8}],crate::Slot{offset:0,size:8})
}

// Independent forward path simulation checks every read against the identity
// actually last written to the chosen physical register. It uses no liveness
// sets or interference edges from the allocation algorithm.
fn paths(plan:&Plan,assigned:&[Option<u32>]) -> Result<usize,&'static str> {
    let mut todo=vec![(plan.at[0],std::collections::BTreeMap::<u32,Id>::new(),0usize)];let mut completed=0;
    let check=|id:Id,physical:&std::collections::BTreeMap<u32,Id>| {
        if let Some(reg)=assigned[id] {if physical.get(&reg)!=Some(&id) {return Err("read after physical register clobber");}}
        Ok(())
    };
    while let Some((block,mut physical,depth))=todo.pop() {
        if depth>plan.blocks.len() {return Err("fixture has cycle");}
        let b=&plan.blocks[block];
        for pc in b.start..b.end {
            for &id in &plan.computations[pc] {
                if !plan.live[id] {continue;}
                for input in plan.nodes[id].inputs() {check(input,&physical)?;}
                if let Some(reg)=assigned[id] {physical.insert(reg,id);}
            }
            if let Effect::Assert{value,..}|Effect::Switch{value,..}|Effect::Return(value)=plan.effects[pc] {check(value,&physical)?;}
        }
        if b.successors.is_empty() {completed+=1;}
        for &to in &b.successors {
            for &phi in &plan.blocks[to].phis {
                if !plan.live[phi] {continue;}
                assert!(assigned[phi].is_none());
                let Value::Phi(parts)=&plan.nodes[phi].value else {panic!("phi shape")};
                let (_,part)=parts.iter().find(|(from,_)|*from==block).unwrap();check(part.value,&physical)?;
            }
            todo.push((to,physical.clone(),depth+1));
        }
        if completed+todo.len()>256 {return Err("fixture path bound");}
    }
    Ok(completed)
}

#[test]
fn cross_block_values_gain_registers_without_expanding_the_bank() {
    let plan=straight(true);let old=allocate(&plan).unwrap();let new=allocate_global(&plan).unwrap();
    assert!(new.global_selected && new.global_weight>new.baseline_weight);
    assert!(new.registers.iter().flatten().all(|r|REGISTERS.contains(r)));
    assert!(new.registers.iter().zip(&old).any(|(a,b)|a.is_some() && b.is_none()));
    assert_eq!(paths(&plan,&old),Ok(1));assert_eq!(paths(&plan,&new.registers),Ok(1));
}

#[test]
fn all_diamond_paths_preserve_values_and_leave_phis_in_stack_slots() {
    for seed in 0..64 {for width in [1,2,4,8] {
        let plan=diamond(seed,width);let new=allocate_global(&plan).unwrap();
        assert!(plan.nodes.iter().zip(&plan.live).any(|(n,l)|*l && matches!(n.value,Value::Phi(_))));
        assert!(plan.nodes.iter().enumerate().filter(|(_,n)|matches!(n.value,Value::Phi(_))).all(|(id,_)|new.registers[id].is_none()));
        assert_eq!(paths(&plan,&new.registers),Ok(2));assert!(new.global_weight>=new.baseline_weight || !new.global_selected);
    }}
}

#[test]
fn path_oracle_detects_forced_clobbers_and_dead_values_do_not_change_assignments() {
    let mut plan=straight(true);let old=allocate_global(&plan).unwrap();let graph=graph(&plan,MAX_WORK).unwrap();
    let mut bad=vec![None;plan.nodes.len()];for &id in &graph.ids {bad[id]=Some(3);}
    assert!(paths(&plan,&bad).is_err());
    plan.nodes.push(Node{value:Value::Unary{src:0,op:Unary::Not,bits:64},width:8,pc:Some(0)});
    plan.live.push(false);plan.computations[0].push(plan.nodes.len()-1);
    let new=allocate_global(&plan).unwrap();assert_eq!(&new.registers[..old.registers.len()],old.registers.as_slice());
    assert!(new.registers.last().unwrap().is_none());
}

#[test]
fn shape_and_work_bounds_decline_before_unbounded_analysis() {
    let plan=straight(false);assert_eq!(graph(&plan,0).err(),Some("global_register_work"));
    let mut too_many=plan.clone();too_many.blocks.resize(MAX_BLOCKS+1,plan.blocks[0].clone());
    assert_eq!(graph(&too_many,MAX_WORK).err(),Some("global_register_shape"));
    let mut invalid=plan.clone();let id=invalid.computations.iter().flatten().copied().find(|&id|invalid.live[id]).unwrap();
    let pc=invalid.nodes[id].pc.unwrap();invalid.computations[pc].push(id);
    assert_eq!(graph(&invalid,MAX_WORK).err(),Some("global_register_definition"));
}
