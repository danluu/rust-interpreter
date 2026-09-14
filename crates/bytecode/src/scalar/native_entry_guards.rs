//! Static obligations only. Never execute stores or select a native backend.
use super::*;
use serde::Serialize;
use std::collections::{BTreeMap,VecDeque};

const MAX_RANGES:usize=128;
#[derive(Clone,Copy,Debug,PartialEq,Eq,PartialOrd,Ord,Serialize)]
enum Root {Input(usize),Constant(u64)}
#[derive(Clone,Copy,Debug,PartialEq,Eq,PartialOrd,Ord,Serialize)]
struct Address {root:Root,offset:u64}
#[derive(Clone,Debug,Serialize)]
struct Range {address:Address,size:u8,write:bool}
#[derive(Debug,Serialize)]
struct EntryPlan {ranges:Vec<Range>,reads:usize,writes:usize,blocks:usize}

fn entry_address(plan:&Plan,identities:&[(Id,u64)],id:Id)->Result<Address,&'static str> {
    let (root,offset)=*identities.get(id).ok_or("entry_address_identity")?;
    match plan.nodes[root].value {
        Value::Input(index) if plan.nodes[root].width==8 => Ok(Address{root:Root::Input(index),offset}),
        Value::Constant(value)=>Ok(Address{root:Root::Constant((value as u64).wrapping_add(offset)),offset:0}),
        Value::Input(_)=>Err("entry_address_input_width"),
        Value::Base(_)=>Err("entry_address_frame_root"),
        Value::Read{..}=>Err("entry_address_memory_root"),
        Value::Phi(_)=>Err("entry_address_phi_root"),
        _=>Err("entry_address_non_affine_root"),
    }
}

fn failing_node(node:&Node)->bool {
    matches!(node.value,Value::Binary{op:Binary::Div|Binary::Rem,..})
}

fn no_failure_after_write(plan:&Plan)->Result<(),&'static str> {
    let mut incoming=vec![false;plan.blocks.len()];let mut outgoing=incoming.clone();
    let mut queued=plan.reachable.clone();let mut pending:VecDeque<_>=(0..plan.blocks.len()).filter(|&i|plan.reachable[i]).collect();
    let mut work=0usize;
    while let Some(block)=pending.pop_front() {
        queued[block]=false;let mut wrote=incoming[block];let b=&plan.blocks[block];
        for pc in b.start..b.end {
            work+=1;if work>1_000_000 {return Err("entry_effect_work");}
            for &id in &plan.computations[pc] {
                if !plan.live[id] {continue;}
                if wrote && failing_node(&plan.nodes[id]) {return Err("entry_division_after_write");}
                if matches!(plan.nodes[id].value,Value::Write{..}) {wrote=true;}
            }
            if wrote && matches!(plan.effects[pc],Effect::Assert{..}|Effect::Trap(_)) {return Err("entry_fault_after_write");}
        }
        if wrote && !outgoing[block] {
            outgoing[block]=true;
            for &to in &b.successors {
                if !incoming[to] {incoming[to]=true;if !queued[to] {queued[to]=true;pending.push_back(to);}}
            }
        }
    }
    Ok(())
}

fn classify(plan:&Plan)->Result<EntryPlan,&'static str> {
    if plan.nodes.len()>16384 || plan.effects.len()>512 || plan.blocks.len()>512 {return Err("entry_shape_limit");}
    let identities=addresses(plan)?;let mut ranges=BTreeMap::<(Address,u8),bool>::new();let (mut reads,mut writes)=(0,0);
    for (id,node) in plan.nodes.iter().enumerate() {
        if !plan.live[id] {continue;}
        let (address,size,write)=match node.value {
            Value::Read{address,size}=>(address,size,false),Value::Write{address,size,..}=>(address,size,true),_=>continue,
        };
        if size==0 || size>16 {return Err("entry_range_width");}
        let address=entry_address(plan,&identities,address)?;
        *ranges.entry((address,size)).or_default()|=write;
        if ranges.len()>MAX_RANGES {return Err("entry_range_limit");}
        if write {writes+=1;} else {reads+=1;}
    }
    if writes==0 {return Err("entry_no_stores");}
    if writes>16 {return Err("entry_store_limit");}
    no_failure_after_write(plan)?;
    Ok(EntryPlan{ranges:ranges.into_iter().map(|((address,size),write)|Range{address,size,write}).collect(),
        reads,writes,blocks:plan.reachable.iter().filter(|r|**r).count()})
}

#[cfg(test)]
#[path="entry_guard_tests.rs"]
mod tests;

#[cfg(test)]
#[path="entry_guard_census.rs"]
mod census;

#[cfg(test)]
#[path="entry_dependencies.rs"]
mod dependencies;
