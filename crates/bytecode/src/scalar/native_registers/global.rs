//! Test-only bounded whole-CFG allocation model. The emitter still uses allocate.
use super::*;
use std::collections::VecDeque;
const MAX_CANDIDATES: usize = 4096;
const MAX_BLOCKS: usize = 512;
const MAX_EVENTS: usize = 250_000;
const MAX_WORK: usize = 8_000_000;

#[derive(Clone)]
struct Event { reads: Vec<usize>, write: Option<usize> }
struct Graph { ids: Vec<Id>, edges: Vec<Vec<u64>>, weights: Vec<u64>, work: usize }
struct Assignment { registers: Vec<Option<u32>>, global_selected: bool, work: usize,
    candidates: usize, baseline_weight: u64, global_weight: u64 }
struct Work { used: usize, limit: usize }
impl Work {
    fn charge(&mut self, n: usize) -> Result<(), &'static str> {
        self.used = self.used.checked_add(n).ok_or("global_register_work")?;
        if self.used > self.limit { Err("global_register_work") } else { Ok(()) }
    }
}
fn set(bits: &mut [u64], id: usize) { bits[id/64] |= 1 << (id%64); }
fn clear(bits: &mut [u64], id: usize) { bits[id/64] &= !(1 << (id%64)); }
fn each(bits: &[u64], mut f: impl FnMut(usize)) {
    for (word, &value) in bits.iter().enumerate() {
        let mut value=value;
        while value!=0 { f(word*64+value.trailing_zeros() as usize); value &= value-1; }
    }
}
fn reads(ids: impl IntoIterator<Item=Id>, mapping: &[Option<usize>], weights: &mut [u64],
    work: &mut Work) -> Result<Vec<usize>, &'static str> {
    let mut out=vec![];
    for id in ids {
        work.charge(1)?;
        if let Some(index)=*mapping.get(id).ok_or("global_register_input")? {
            weights[index]+=1;out.push(index);
        }
    }
    Ok(out)
}

fn graph(plan: &Plan, limit: usize) -> Result<Graph, &'static str> {
    if plan.blocks.len()>MAX_BLOCKS || plan.nodes.len()>16_384 || plan.effects.len()>512
        || plan.live.len()!=plan.nodes.len() || plan.reachable.len()!=plan.blocks.len()
        || plan.at.len()!=plan.effects.len() || plan.computations.len()!=plan.effects.len() {
        return Err("global_register_shape");
    }
    let mut work=Work{used:0,limit};let mut ids=vec![];let mut mapping=vec![None;plan.nodes.len()];
    let mut defined=vec![false;plan.nodes.len()];
    for (block,b) in plan.blocks.iter().enumerate() {
        if !plan.reachable[block] {continue;}
        if b.start>=b.end || b.end>plan.effects.len() {return Err("global_register_block");}
        for pc in b.start..b.end {
            if plan.at[pc]!=block {return Err("global_register_block_identity");}
            for &id in &plan.computations[pc] {
                work.charge(1)?;
                let node=plan.nodes.get(id).ok_or("global_register_definition")?;
                if !plan.live[id] {continue;}
                if defined[id] || node.pc!=Some(pc) {return Err("global_register_definition");}
                defined[id]=true;
                if node.width==0 || node.width>8 || matches!(node.value,Value::Phi(_)|Value::Constant(_)|Value::Input(_)|Value::Base(_)) {continue;}
                if ids.len()==MAX_CANDIDATES {return Err("global_register_candidates");}
                mapping[id]=Some(ids.len());ids.push(id);
            }
        }
    }
    let n=ids.len();let stride=n.div_ceil(64);let mut weights=vec![1u64;n];
    let mut events=vec![vec![];plan.blocks.len()];let mut edge_uses=vec![vec![];plan.blocks.len()];let mut count=0;
    for (block,b) in plan.blocks.iter().enumerate() {
        if !plan.reachable[block] {continue;}
        for pc in b.start..b.end {
            for &id in &plan.computations[pc] {
                if !plan.live[id] {continue;}
                let uses=reads(plan.nodes[id].inputs(),&mapping,&mut weights,&mut work)?;
                events[block].push(Event{reads:uses,write:mapping[id]});count+=1;
            }
            let uses=match plan.effects[pc] {
                Effect::Assert{value,..}|Effect::Switch{value,..}|Effect::Return(value)=>vec![value],_=>vec![],
            };
            events[block].push(Event{reads:reads(uses,&mapping,&mut weights,&mut work)?,write:None});count+=1;
            if count>MAX_EVENTS {return Err("global_register_events");}
        }
        for &to in &b.successors {
            let next=plan.blocks.get(to).ok_or("global_register_successor")?;
            if !plan.reachable[to] {return Err("global_register_reachability");}
            for &phi in &next.phis {
                if !*plan.live.get(phi).ok_or("global_register_phi")? {continue;}
                let Value::Phi(parts)=&plan.nodes[phi].value else {return Err("global_register_phi");};
                let (_,part)=parts.iter().find(|(from,_)|*from==block).ok_or("global_register_phi_edge")?;
                edge_uses[block].extend(reads([part.value],&mapping,&mut weights,&mut work)?);
            }
        }
    }
    let mut predecessors=vec![vec![];plan.blocks.len()];
    for (block,b) in plan.blocks.iter().enumerate() {if plan.reachable[block] {
        for &to in &b.successors {predecessors[to].push(block);}
    }}
    let mut incoming=vec![vec![0u64;stride];plan.blocks.len()];let mut outgoing=incoming.clone();
    let mut queued=plan.reachable.clone();let mut pending:VecDeque<_>=(0..plan.blocks.len()).rev().filter(|&b|plan.reachable[b]).collect();
    while let Some(block)=pending.pop_front() {
        queued[block]=false;let mut live=vec![0;stride];
        for &to in &plan.blocks[block].successors {
            work.charge(stride)?;for (out,&value) in live.iter_mut().zip(&incoming[to]) {*out|=value;}
        }
        for &id in &edge_uses[block] {work.charge(1)?;set(&mut live,id);}
        outgoing[block].clone_from(&live);
        for event in events[block].iter().rev() {
            work.charge(event.reads.len()+1)?;
            if let Some(id)=event.write {clear(&mut live,id);}
            for &id in &event.reads {set(&mut live,id);}
        }
        if incoming[block]!=live {
            incoming[block]=live;
            for &previous in &predecessors[block] {work.charge(1)?;if !queued[previous] {queued[previous]=true;pending.push_back(previous);}}
        }
    }
    let mut edges=vec![vec![0;stride];n];
    for (block,events) in events.iter().enumerate() {
        if !plan.reachable[block] {continue;}
        let mut live=outgoing[block].clone();
        for event in events.iter().rev() {
            if let Some(id)=event.write {
                work.charge(stride)?;let mut neighbors=vec![];each(&live,|other|if other!=id {neighbors.push(other)});
                work.charge(neighbors.len())?;
                for other in neighbors {set(&mut edges[id],other);set(&mut edges[other],id);}
                clear(&mut live,id);
            }
            work.charge(event.reads.len())?;for &id in &event.reads {set(&mut live,id);}
        }
    }
    Ok(Graph{ids,edges,weights,work:work.used})
}

fn valid(graph: &Graph, assigned: &[Option<u32>]) -> bool {
    graph.ids.iter().enumerate().all(|(i,&id)| {
        let Some(reg)=assigned[id] else {return true;};
        let mut okay=REGISTERS.contains(&reg);
        each(&graph.edges[i],|j|okay &= assigned[graph.ids[j]]!=Some(reg));okay
    })
}

fn allocate_global(plan: &Plan) -> Result<Assignment, &'static str> {
    let baseline=allocate(plan)?;let graph=graph(plan,MAX_WORK)?;
    if !valid(&graph,&baseline) {return Err("global_register_baseline_conflict");}
    let degrees:Vec<_>=graph.edges.iter().map(|row|row.iter().map(|w|w.count_ones() as u64).sum::<u64>()).collect();
    let mut order:Vec<_>=(0..graph.ids.len()).collect();
    order.sort_unstable_by(|&a,&b| (graph.weights[b]*(degrees[a]+1)).cmp(&(graph.weights[a]*(degrees[b]+1)))
        .then_with(||graph.weights[b].cmp(&graph.weights[a])).then_with(||graph.ids[a].cmp(&graph.ids[b])));
    let mut assigned=vec![None;plan.nodes.len()];
    for index in order {
        let mut used=[false;4];
        each(&graph.edges[index],|j|if let Some(reg)=assigned[graph.ids[j]] {
            used[REGISTERS.iter().position(|r|*r==reg).unwrap()]=true;
        });
        if let Some(color)=used.iter().position(|v|!*v) {assigned[graph.ids[index]]=Some(REGISTERS[color]);}
    }
    if !valid(&graph,&assigned) {return Err("global_register_coloring_conflict");}
    let score=|assignment:&[Option<u32>]|graph.ids.iter().enumerate().filter(|(_,id)|assignment[**id].is_some()).map(|(i,_)|graph.weights[i]).sum::<u64>();
    let baseline_weight=score(&baseline);let global_weight=score(&assigned);let global_selected=global_weight>baseline_weight;
    Ok(Assignment{registers:if global_selected {assigned} else {baseline},global_selected,work:graph.work,
        candidates:graph.ids.len(),baseline_weight,global_weight})
}

#[cfg(test)]
mod tests;
#[cfg(test)]
mod census;
