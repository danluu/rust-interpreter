//! Bounded byte liveness for removing provably valid, unobserved frame writes.
use crate::{Function,Op,Program};
use super::constant_fold_facts::{Fact,State};
use std::collections::VecDeque;
type Range=(usize,usize);

#[derive(Clone,Default)]
struct Effect {reads:Vec<Range>,read_all:bool,write:Option<Range>,removable:bool}
impl Effect {
    fn opaque()->Self {Self{read_all:true,..Self::default()}}
    fn read(&mut self,address:Option<Fact>,size:usize,p:&Program,f:&Function)->bool {
        if size==0 {return true;}
        if let Some(range)=local(address,size,f) {self.reads.push(range);true}
        else if let Some(Fact::Scalar(value))=address {
            let valid=usize::try_from(value).ok().filter(|&v|v!=0)
                .and_then(|v|v.checked_add(size)).is_some_and(|end|end<=p.data.len());
            if !valid {self.read_all=true;}valid
        } else {self.read_all=true;false}
    }
}
fn local(address:Option<Fact>,size:usize,f:&Function)->Option<Range> {
    let Fact::Local(start)=address? else {return None;};let end=start.checked_add(size)?;
    (end<=f.frame_size).then_some((start,end))
}
fn effect(op:&Op,state:&State,p:&Program,f:&Function)->Effect {
    let mut e=Effect::default();
    match op {
        Op::Load{address,size,..}=>{e.read(state.get(*address),*size as usize,p,f);},
        Op::Store{address,size,..}=>{
            e.write=local(state.get(*address),*size as usize,f);e.removable=e.write.is_some();
        }
        Op::Copy{dst,src,size}=>{
            e.write=local(state.get(*dst),*size,f);
            e.removable=e.read(state.get(*src),*size,p,f) && e.write.is_some();
        }
        Op::CopyDynamic{dst,src,size}=>{
            let Some(size)=state.scalar(*size).and_then(|v|usize::try_from(v).ok()) else {return Effect::opaque();};
            e.write=local(state.get(*dst),size,f);
            e.removable=e.read(state.get(*src),size,p,f) && e.write.is_some();
        }
        Op::FillBytes{address,size,..}=>{
            let Some(size)=state.scalar(*size).and_then(|v|usize::try_from(v).ok()) else {return Effect::opaque();};
            e.write=local(state.get(*address),size,f);e.removable=e.write.is_some();
        }
        Op::CompareBytes{left,right,size,..}=>{
            let Some(size)=state.scalar(*size).and_then(|v|usize::try_from(v).ok()) else {return Effect::opaque();};
            e.read(state.get(*left),size,p,f);e.read(state.get(*right),size,p,f);
        }
        Op::Return=>{e.reads.push((f.result.offset,f.result.offset+f.result.size));},
        Op::Call{..}|Op::CallIndirect{..}|Op::Allocate{..}|Op::Deallocate{..}|Op::Reallocate{..}
        |Op::ResetThreadLocals|Op::RandomBytes{..}|Op::CpuFeatureQuery{..}|Op::CAllocate{..}
        |Op::CDeallocate{..}|Op::CReallocate{..}|Op::CAlignedAllocate{..}|Op::RegisterTlsDestructor{..}=>return Effect::opaque(),
        Op::Imm{..}|Op::Local{..}|Op::Binary{..}|Op::Unary{..}|Op::Cast{..}|Op::Select{..}
        |Op::FloatBinary{..}|Op::FloatUnary{..}|Op::FloatConvert{..}|Op::Jump{..}|Op::Switch{..}
        |Op::Assert{..}|Op::Trap{..}=>{},
    }
    e
}
struct Meter<'a>{used:usize,global:&'a mut usize}
impl Meter<'_>{fn spend(&mut self,n:usize)->Option<()> {
    if n>*self.global || n>2_000_000-self.used {return None;}self.used+=n;*self.global-=n;Some(())
}}
fn bit_set(bits:&mut [u64],(start,end):Range,set:bool) {
    for byte in start..end {let mask=1u64<<(byte%64);if set {bits[byte/64]|=mask;} else {bits[byte/64]&=!mask;}}
}
fn transfer(e:&Effect,mut live:Vec<u64>,meter:&mut Meter)->Option<(Vec<u64>,bool)> {
    let write_bytes=e.write.map_or(0,|(a,b)|b-a);
    meter.spend(live.len()+2*write_bytes+e.reads.iter().map(|&(a,b)|b-a).sum::<usize>()+1)?;
    if e.removable && e.write.is_some_and(|(a,b)|(a..b).all(|byte|live[byte/64]&(1u64<<(byte%64))==0)) {
        // A removed copy has a valid source and need not read it at all.
        return Some((live,true));
    }
    if let Some(range)=e.write {bit_set(&mut live,range,false);}
    if e.read_all {live.fill(u64::MAX);} else {for &range in &e.reads {bit_set(&mut live,range,true);}}
    Some((live,false))
}
fn edges(f:&Function)->Option<(Vec<Vec<usize>>,Vec<Vec<usize>>)> {
    let mut next=Vec::new();let mut previous=vec![Vec::new();f.code.len()];let mut total=0;
    for (pc,op) in f.code.iter().enumerate() {
        let mut targets=match op {
            Op::Jump{target}=>vec![*target],
            Op::Switch{cases,otherwise,..}=>{
                if cases.len()>2048 {return None;}
                cases.iter().map(|&(_,pc)|pc).chain(std::iter::once(*otherwise)).collect()
            }
            Op::Return|Op::Trap{..}=>vec![],_=>vec![pc+1],
        };
        targets.sort_unstable();targets.dedup();total+=targets.len();if total>4096 {return None;}
        for &target in &targets {previous.get_mut(target)?.push(pc);}next.push(targets);
    }
    Some((next,previous))
}
fn joined(pc:usize,next:&[Vec<usize>],live:&[Vec<u64>],words:usize,meter:&mut Meter)->Option<Vec<u64>> {
    meter.spend(1+words*(1+next[pc].len()))?;let mut out=vec![0;words];
    for &target in &next[pc] {for (a,b) in out.iter_mut().zip(&live[target]) {*a|=*b;}}
    Some(out)
}
fn solve(f:&Function,effects:&[Effect],meter:&mut Meter)->Option<Vec<bool>> {
    let (next,previous)=edges(f)?;let words=f.frame_size.div_ceil(64);
    let mut live=vec![vec![0;words];f.code.len()];let mut queue:VecDeque<_>=(0..f.code.len()).rev().collect();
    let mut queued=vec![true;f.code.len()];
    while let Some(pc)=queue.pop_front() {
        queued[pc]=false;
        let output=joined(pc,&next,&live,words,meter)?;let (input,_)=transfer(&effects[pc],output,meter)?;
        if input!=live[pc] {
            if input.iter().zip(&live[pc]).any(|(new,old)|old&!new!=0) {return None;}
            live[pc]=input;
            for &previous in &previous[pc] {if !queued[previous] {queue.push_back(previous);queued[previous]=true;}}
        }
    }
    // A separate complete pass checks every final equation before any deletion.
    let mut remove=Vec::new();
    for pc in 0..f.code.len() {
        let output=joined(pc,&next,&live,words,meter)?;let (input,dead)=transfer(&effects[pc],output,meter)?;
        if input!=live[pc] {return None;}remove.push(dead);
    }
    Some(remove)
}

#[derive(Default,serde::Serialize)]
pub(super) struct Report {old_operations:usize,new_operations:usize,removed_writes:usize,removed_write_bytes:usize,
    removed_definitions:usize,fact_work:usize,liveness_work:usize,applied:bool,decline:Option<&'static str>}

pub(super) fn optimize(p:&Program,f:&mut Function,known:&[(usize,usize,u128)],facts_budget:&mut usize,live_budget:&mut usize)->Report {
    let mut r=Report{old_operations:f.code.len(),new_operations:f.code.len(),..Report::default()};
    if f.code.is_empty() || f.code.len()>512 || f.frame_size>4096 || f.registers>8192 {
        r.decline=Some("shape bound");return r;
    }
    let Some(initial)=State::argument_entry(f,known) else {r.decline=Some("argument facts");return r;};
    let mut effects=vec![Effect::opaque();f.code.len()];let before=*facts_budget;
    let solved=super::constant_fold::visit_facts(p,f,&initial,facts_budget,|pc,state|effects[pc]=effect(&f.code[pc],state,p,f));
    r.fact_work=before-*facts_budget;
    if solved.is_none() {r.decline=Some("forward facts or work bound");return r;}
    let mut meter=Meter{used:0,global:live_budget};let removal=solve(f,&effects,&mut meter);r.liveness_work=meter.used;
    let Some(removal)=removal else {r.decline=Some("liveness certificate or work bound");return r;};
    if !removal.iter().any(|&b|b) {return r;}
    let mut body=f.clone();let mut mapping=vec![0;f.code.len()];body.code.clear();
    for (pc,op) in f.code.iter().enumerate() {
        mapping[pc]=body.code.len();
        if removal[pc] {r.removed_writes+=1;r.removed_write_bytes+=effects[pc].write.map_or(0,|(a,b)|b-a);} else {body.code.push(op.clone());}
    }
    for op in &mut body.code {match op {
        Op::Jump{target}=>*target=mapping[*target],
        Op::Switch{cases,otherwise,..}=>{*otherwise=mapping[*otherwise];for (_,target) in cases {*target=mapping[*target];}},_=>{},
    }}
    let Some(definitions)=super::constant_fold::cleanup_definitions(&mut body) else {r.decline=Some("definition cleanup bound");return r;};
    r.removed_definitions=definitions;
    if crate::control_flow::optimize_function(&mut body,true).is_err() {
        r.decline=Some("CFG cleanup");return r;
    }
    if !crate::registers::needs_initial_zeroes(f) && crate::registers::needs_initial_zeroes(&body) {
        r.decline=Some("register initialization");return r;
    }
    r.new_operations=body.code.len();r.applied=true;*f=body;r
}

#[cfg(all(test,target_arch="aarch64",target_os="macos"))]
#[path="dead_frame_writes_tests.rs"]
mod tests;
