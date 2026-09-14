//! Test-only guard obligations. This does not read memory or execute effects.
use super::*;
use std::collections::BTreeSet;

#[derive(Debug,Serialize)]
pub(super) struct DependencyPlan {
    ranges:Vec<DependencyRange>,entry_nodes:Vec<Id>,captured_reads:Vec<Id>,
    disjoint_pairs:Vec<(Id,Id)>,writes:usize,work:usize,
}
#[derive(Debug,Serialize)]
struct DependencyRange {address:Id,size:u8,write:bool}

// A write bit reaches a read only along a CFG path that places that write
// before the read. Later updates do not invalidate an already captured value.
use crate::scalar_ir::path_entry::earlier_writes;

pub(super) fn classify_dependencies(plan:&Plan)->Result<DependencyPlan,&'static str> {
    if plan.nodes.len()>16384 || plan.effects.len()>512 || plan.blocks.len()>512 {return Err("entry_shape_limit");}
    let stores:Vec<_>=plan.nodes.iter().enumerate().filter(|(id,n)|plan.live[*id] && matches!(n.value,Value::Write{..})).map(|(id,_)|id).collect();
    if stores.is_empty() {return Err("entry_no_stores");}
    if stores.len()>16 {return Err("entry_store_limit");}
    no_failure_after_write(plan)?;
    let mut ranges=BTreeMap::<(Id,u8),bool>::new();let mut pending=vec![];
    for (id,node) in plan.nodes.iter().enumerate() {
        if !plan.live[id] {continue;}
        let (address,size,write)=match node.value {
            Value::Read{address,size}=>(address,size,false),Value::Write{address,size,..}=>(address,size,true),_=>continue,
        };
        if size==0 || size>16 {return Err("entry_range_width");}
        *ranges.entry((address,size)).or_default()|=write;pending.push(address);
        if ranges.len()>128 {return Err("entry_range_limit");}
    }
    let mut nodes=BTreeSet::new();let mut captured_reads=BTreeSet::new();let mut work=0usize;
    while let Some(id)=pending.pop() {
        work+=1;if work>65536 {return Err("entry_dependency_work");}
        if !nodes.insert(id) {continue;}
        if nodes.len()>4096 {return Err("entry_dependency_nodes");}
        let node=&plan.nodes[id];
        match node.value {
            Value::Base(_)=>return Err("entry_dependency_frame"),
            Value::Phi(_)=>return Err("entry_dependency_phi"),
            Value::Write{..}=>return Err("entry_dependency_effect"),
            Value::Read{..}=>{captured_reads.insert(id);if captured_reads.len()>128 {return Err("entry_captured_read_limit");}},
            _=>{},
        }
        for input in node.inputs() {
            if input>=id {return Err("entry_dependency_order");}
            pending.push(input);
        }
    }
    // All dependency reads are live nodes already included above. Evaluating
    // this topological list must check each read's range before loading it.
    assert!(captured_reads.iter().all(|&id|plan.live[id]));
    let (before,order_work)=earlier_writes(plan,&stores)?;let mut disjoint_pairs=vec![];
    for &read in &captured_reads {for (bit,&write) in stores.iter().enumerate() {
        if before[read]&(1<<bit)!=0 {disjoint_pairs.push((read,write));}
    }}
    assert!(captured_reads.len()<=128 && disjoint_pairs.len()<=2048);
    Ok(DependencyPlan{ranges:ranges.into_iter().map(|((address,size),write)|DependencyRange{address,size,write}).collect(),
        entry_nodes:nodes.into_iter().collect(),captured_reads:captured_reads.into_iter().collect(),
        disjoint_pairs,writes:stores.len(),work:work+order_work})
}

#[cfg(test)]
#[path="entry_dependency_tests.rs"]
mod tests;
