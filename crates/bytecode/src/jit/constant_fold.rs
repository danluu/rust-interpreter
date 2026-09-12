//! Experimental bounded forward must-analysis and pure-definition cleanup.
use crate::{Binary, Function, Op, Program};
use super::constant_fold_facts::{Fact,State};
use std::collections::{BTreeSet,VecDeque};
use serde::Serialize;

struct Block {start:usize,end:usize,next:Vec<usize>}
struct Meter<'a> {used:usize,global:&'a mut usize}
impl Meter<'_> {fn spend(&mut self,n:usize)->Option<()> {
    if n>*self.global || n>2_000_000-self.used {return None;}self.used+=n;*self.global-=n;Some(())
}}
fn blocks(f:&Function)->Option<Vec<Block>> {
    if f.code.len()>4096 || f.registers>8192 || !matches!(f.code.last()?,Op::Return|Op::Trap{..}|Op::Jump{..}|Op::Switch{..}) {return None;}
    let mut starts=BTreeSet::from([0usize]);let mut accesses=0;
    for (pc,op) in f.code.iter().enumerate() {
        crate::registers::visit_registers(op, |_|accesses+=1, |_|{});
        crate::registers::visit_registers(op, |_|{}, |_|accesses+=1);
        match op {
            Op::Jump{target}=>{starts.insert(*target);accesses+=1;},
            Op::Switch{cases,otherwise,..}=>{starts.insert(*otherwise);accesses+=1;for &(_,target) in cases {starts.insert(target);accesses+=1;}},
            _=>{},
        }
        if matches!(op,Op::Jump{..}|Op::Switch{..}|Op::Return|Op::Trap{..}) && pc+1<f.code.len() {starts.insert(pc+1);}
        if starts.len()>256 || accesses>16384 {return None;}
    }
    let starts:Vec<_>=starts.into_iter().collect();let mut out=Vec::new();
    for (i,&start) in starts.iter().enumerate() {
        let end=starts.get(i+1).copied().unwrap_or(f.code.len());
        let pcs:Vec<_>=match &f.code[end-1] {
            Op::Jump{target}=>vec![*target],
            Op::Switch{cases,otherwise,..}=>cases.iter().map(|&(_,pc)|pc).chain(std::iter::once(*otherwise)).collect(),
            Op::Return|Op::Trap{..}=>vec![],_=>vec![end],
        };
        let mut next:Vec<_>=pcs.into_iter().map(|pc|starts.binary_search(&pc).ok()).collect::<Option<_>>()?;
        next.sort_unstable();next.dedup();out.push(Block{start,end,next});
    }
    Some(out)
}
fn trace(mut state:State,b:&Block,p:&Program,f:&Function,meter:&mut Meter)->Option<State> {
    for op in &f.code[b.start..b.end] {
        // Register maps are capped at 512, so each scalar access has bounded
        // lookup cost. Memory updates may visit every tracked byte.
        let extra=if matches!(op,Op::Store{..}|Op::Copy{..}|Op::CopyDynamic{..}|Op::FillBytes{..}|Op::Call{..}|Op::CallIndirect{..}) {state.bytes.len()} else {0};
        meter.spend(1+extra)?;state.step(op,p,f);
    }
    Some(state)
}
fn solve(p:&Program,f:&Function,blocks:&[Block],initial:&State,meter:&mut Meter)->Option<Vec<Option<State>>> {
    let mut incoming=vec![None;blocks.len()];incoming[0]=Some(initial.clone());
    let mut queue=VecDeque::from([0]);let mut queued=vec![false;blocks.len()];queued[0]=true;
    while let Some(id)=queue.pop_front() {
        queued[id]=false;let state=incoming[id].as_ref()?;meter.spend(state.cost())?;
        let output=trace(state.clone(),&blocks[id],p,f,meter)?;
        for &next in &blocks[id].next {
            meter.spend(output.cost()+incoming[next].as_ref().map_or(0,State::cost))?;
            let changed=if let Some(state)=&mut incoming[next] {state.intersect(&output)} else {incoming[next]=Some(output.clone());true};
            if changed && !queued[next] {queue.push_back(next);queued[next]=true;}
        }
    }
    // Independently verify the post-fixpoint. Every claimed entry fact must
    // hold on every reachable predecessor, including the unknown root state.
    if !incoming[0].as_ref()?.covered_by(initial) {return None;}
    for (id,b) in blocks.iter().enumerate() {
        let Some(state)=&incoming[id] else {continue;};meter.spend(state.cost())?;
        let output=trace(state.clone(),b,p,f,meter)?;
        for &next in &b.next {
            meter.spend(output.cost()+incoming[next].as_ref()?.cost())?;
            if !incoming[next].as_ref()?.covered_by(&output) {return None;}
        }
    }
    Some(incoming)
}

/// Visit facts from the certified solution without retaining per-op maps.
pub(super) fn visit_facts(p:&Program,f:&Function,initial:&State,global:&mut usize,mut visit:impl FnMut(usize,&State))->Option<()> {
    let mut meter=Meter{used:0,global};let blocks=blocks(f)?;
    let states=solve(p,f,&blocks,initial,&mut meter)?;
    for (id,block) in blocks.iter().enumerate() {
        let Some(mut state)=states[id].clone() else {continue;};
        for pc in block.start..block.end {
            meter.spend(1+state.bytes.len())?;visit(pc,&state);state.step(&f.code[pc],p,f);
        }
    }
    Some(())
}

#[derive(Default,Debug,Serialize)]
pub(super) struct Report {pub function:usize,pub old_operations:usize,pub new_operations:usize,
    pub folded_values:usize,pub folded_switches:usize,pub dead_definitions:usize,pub solver_work:usize,pub declined:bool}

fn replacement(op:&Op,condition:Option<u128>,after:&State)->Option<Vec<Op>> {
    let constant=|r|after.get(r).map(|value|match value {Fact::Scalar(value)=>Op::Imm{dst:r,value},Fact::Local(offset)=>Op::Local{dst:r,offset}});
    match op {
        Op::Load{dst,..}|Op::Unary{dst,..}|Op::Cast{dst,..}|Op::Select{dst,..}=>Some(vec![constant(*dst)?]),
        Op::Binary{dst,overflow,..}=>{
            if dst==overflow {Some(vec![constant(*dst)?])} else {Some(vec![constant(*dst)?,constant(*overflow)?])}
        }
        Op::Switch{cases,otherwise,..}=>{
            let value=condition?;Some(vec![Op::Jump{target:cases.iter().find(|&&(v,_)|v==value).map_or(*otherwise,|&(_,pc)|pc)}])
        }
        _=>None,
    }
}
fn map_branches(code:&mut [Op],mapping:&[usize]) {
    for op in code {match op {
        Op::Jump{target}=>*target=mapping[*target],
        Op::Switch{cases,otherwise,..}=>{*otherwise=mapping[*otherwise];for (_,target) in cases {*target=mapping[*target];}},_=>{},
    }}
}
fn pure(op:&Op)->bool {matches!(op,Op::Imm{..}|Op::Local{..}|Op::Unary{..}|Op::Cast{..}|Op::Select{..}) || matches!(op,Op::Binary{op,..} if !matches!(op,Binary::Div|Binary::Rem))}
fn dead_definitions(f:&mut Function)->Option<usize> {
    let (live,_)=super::values::ranked(f,32_000_000)?;
    let mut remove=vec![false;f.code.len()];
    for (pc,op) in f.code.iter().enumerate() {
        if !pure(op) {continue;}
        // Pure instructions have only fallthrough. The final operation is a
        // terminator in admitted functions and cannot be removed here.
        let next=pc+1;if next>=f.code.len() {return None;}
        let mut needed=false;
        crate::registers::visit_registers(op, |_|{}, |r|needed|=live.bits[next*live.stride+r as usize/64] & (1u64<<(r%64))!=0);
        remove[pc]=!needed;
    }
    let mut mapping=vec![0;f.code.len()];let mut code=Vec::new();let mut count=0;
    for (pc,op) in f.code.iter().enumerate() {mapping[pc]=code.len();if remove[pc] {count+=1;} else {code.push(op.clone());}}
    map_branches(&mut code,&mapping);f.code=code;Some(count)
}
pub(super) fn cleanup_definitions(f:&mut Function)->Option<usize> {dead_definitions(f)}
fn function(p:&Program,f:&Function,meter:&mut Meter)->Option<(Function,Report)> {
    let (result,report)=function_from_entry(p,f,&State::default(),meter)?;
    if !crate::registers::needs_initial_zeroes(f) && crate::registers::needs_initial_zeroes(&result) {return None;}
    Some((result,report))
}
fn function_from_entry(p:&Program,f:&Function,initial:&State,meter:&mut Meter)->Option<(Function,Report)> {
    let blocks=blocks(f)?;let states=solve(p,f,&blocks,initial,meter)?;
    let mut report=Report::default();let mut mapping=vec![0;f.code.len()];let mut code=Vec::new();
    for (id,b) in blocks.iter().enumerate() {
        let mut state=states[id].clone();
        for pc in b.start..b.end {
            mapping[pc]=code.len();let op=&f.code[pc];let mut replaced=None;
            if let Some(before)=&mut state {
                meter.spend(1+before.bytes.len())?;
                let condition=if let Op::Switch{value,..}=op {before.scalar(*value)} else {None};
                before.step(op,p,f);replaced=replacement(op,condition,before);
            }
            if let Some(ops)=replaced {
                if matches!(op,Op::Switch{..}) {report.folded_switches+=1;} else {report.folded_values+=1;}
                code.extend(ops);
            } else {code.push(op.clone());}
        }
    }
    map_branches(&mut code,&mapping);
    let mut result=f.clone();result.code=code;
    report.dead_definitions=dead_definitions(&mut result)?;
    report.new_operations=result.code.len();Some((result,report))
}

pub(super) fn seeded_function(p:&Program,f:&Function,known:&[(usize,usize,u128)],global:&mut usize)->Option<(Function,Report)> {
    let initial=State::argument_entry(f,known)?;
    let mut meter=Meter{used:0,global};
    let (mut function,mut report)=function_from_entry(p,f,&initial,&mut meter)?;
    // Dead-definition liveness already ignores branches removed by folding.
    // Remove their bodies before the block-local initialization proof examines
    // them. The final clone must still satisfy the original no-clearing proof.
    crate::control_flow::optimize_function(&mut function,true).ok()?;
    if !crate::registers::needs_initial_zeroes(f) && crate::registers::needs_initial_zeroes(&function) {return None;}
    report.old_operations=f.code.len();report.solver_work=meter.used;
    Some((function,report))
}

pub(super) fn fold(mut program:Program)->Result<(Program,serde_json::Value),String> {
    crate::validate(&program)?;
    let mut global=32_000_000usize;
    let mut reports:Vec<Option<Report>>=(0..program.functions.len()).map(|_|None).collect();
    // Spend the fixed global budget on smaller bodies before large functions
    // can consume it. Stable IDs break ties; no names or profiles participate.
    let mut order:Vec<_>=(0..program.functions.len()).collect();
    order.sort_unstable_by_key(|&id|(program.functions[id].code.len(),id));
    for id in order {
        let f=&program.functions[id];let old=f.code.len();let mut meter=Meter{used:0,global:&mut global};
        let (result,mut report)=if let Some((result,report))=function(&program,f,&mut meter) {(Some(result),report)}
            else {(None,Report{declined:true,new_operations:old,..Report::default()})};
        report.function=id;report.old_operations=old;report.solver_work=meter.used;
        if let Some(result)=result {program.functions[id]=result;}
        reports[id]=Some(report);
    }
    crate::validate(&program)?;
    Ok((program,serde_json::json!({"functions":reports,"solver_work":32_000_000-global})))
}

#[cfg(all(test,target_arch="aarch64",target_os="macos"))]
#[path="constant_fold_tests.rs"]
mod tests;
