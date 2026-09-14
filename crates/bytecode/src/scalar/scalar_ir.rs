//! Experimental scalar value graph for an already proved, bounded pure leaf.
//! No executable code is published. Original PCs remain the accounting unit.
use crate::{Binary, Function, Op, Unary};
use crate::proof::{Access, MemoryPlan};
use serde::Serialize;
use std::collections::{BTreeSet, HashMap, VecDeque};

type Id = usize;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Byte { value: Id, byte: u8 }
#[derive(Clone, Copy, Debug)]
struct Slice { value: Id, byte: u8, size: u8 }
#[derive(Clone, Debug)]
enum Value {
    Constant(u128), Input(usize), Base(usize),
    Pack(Vec<Slice>), Phi(Vec<(usize, Slice)>),
    Binary { a:Id, b:Id, op:Binary, bits:u8, signed:bool, overflow:bool },
    Unary { src:Id, op:Unary, bits:u8 },
    Cast { src:Id, from:u8, to:u8, signed:bool },
    Select { condition:Id, yes:Id, no:Id },
}
#[derive(Clone, Debug)]
struct Node { value:Value, width:u8, pc:Option<usize> }
impl Node {
    fn inputs(&self) -> Vec<Id> {
        match &self.value {
            Value::Constant(_) | Value::Input(_) | Value::Base(_) => vec![],
            Value::Pack(parts) => parts.iter().map(|p|p.value).collect(),
            Value::Phi(parts) => parts.iter().map(|(_,p)|p.value).collect(),
            Value::Binary{a,b,..} => vec![*a,*b],
            Value::Unary{src,..} | Value::Cast{src,..} => vec![*src],
            Value::Select{condition,yes,no} => vec![*condition,*yes,*no],
        }
    }
}
#[derive(Clone)]
struct State { registers:Vec<Id>, bytes:Vec<Byte> }
#[derive(Clone, Debug)]
enum Effect {
    None, Assert {value:Id,expected:bool,message:String},
    Jump(usize), Switch {value:Id,cases:Vec<(u128,usize)>,otherwise:usize},
    Return(Id), Trap(String),
}
#[derive(Clone, Debug)]
struct Block {start:usize,end:usize,successors:Vec<usize>,predecessors:Vec<usize>,phis:Vec<Id>}
#[derive(Clone, Debug)]
pub struct Plan {
    nodes:Vec<Node>, blocks:Vec<Block>, at:Vec<usize>, computations:Vec<Vec<Id>>,
    effects:Vec<Effect>, live:Vec<bool>, reachable:Vec<bool>,
    pub maximum_steps:usize, pub success_steps:Option<usize>, pub result_size:usize, pub work:usize,
}
#[derive(Debug, Serialize)]
pub struct Summary {
    pub eligible:bool, pub decline:Option<&'static str>, pub nodes:usize, pub live_nodes:usize,
    pub live_phis:usize, pub maximum_steps:usize, pub reachable_operations:usize,
    pub live_computations_per_pc:Vec<usize>, pub work:usize,
}
pub fn summary(result:&Result<Plan,&'static str>) -> Summary {
    match result {
        Err(reason) => Summary {eligible:false,decline:Some(reason),nodes:0,live_nodes:0,live_phis:0,
            maximum_steps:0,reachable_operations:0,live_computations_per_pc:vec![],work:0},
        Ok(p) => Summary {eligible:true,decline:None,nodes:p.nodes.len(),live_nodes:p.live.iter().filter(|v|**v).count(),
            live_phis:p.nodes.iter().zip(&p.live).filter(|(n,l)|**l && matches!(n.value,Value::Phi(_))).count(),
            maximum_steps:p.maximum_steps,reachable_operations:p.blocks.iter().zip(&p.reachable)
                .filter(|(_,r)|**r).map(|(b,_)|b.end-b.start).sum(),
            live_computations_per_pc:p.computations.iter().map(|ids|ids.iter().filter(|id|p.live[**id]).count()).collect(),work:p.work},
    }
}

struct Builder { plan:Plan, constants:HashMap<u128,Id>, bases:HashMap<usize,Id>, roots:Vec<Id>, pc:usize, limit:usize }
impl Builder {
    fn charge(&mut self,n:usize) -> Result<(),&'static str> {
        self.plan.work=self.plan.work.checked_add(n).ok_or("scalar_work_limit")?;
        if self.plan.work>self.limit {Err("scalar_work_limit")} else {Ok(())}
    }
    fn node(&mut self,value:Value,width:u8,global:bool) -> Result<Id,&'static str> {
        self.charge(1)?;if self.plan.nodes.len()>=16384 {return Err("scalar_node_limit");}
        let id=self.plan.nodes.len();self.plan.nodes.push(Node{value,width,pc:(!global).then_some(self.pc)});
        if !global {self.plan.computations[self.pc].push(id);} Ok(id)
    }
    fn constant(&mut self,value:u128) -> Result<Id,&'static str> {
        if let Some(id)=self.constants.get(&value) {return Ok(*id);}
        let width=((128-value.leading_zeros()).div_ceil(8).max(1)) as u8;
        let id=self.node(Value::Constant(value),width,true)?;self.constants.insert(value,id);Ok(id)
    }
    fn base(&mut self,offset:usize) -> Result<Id,&'static str> {
        if let Some(id)=self.bases.get(&offset) {return Ok(*id);}
        let id=self.node(Value::Base(offset),8,true)?;self.bases.insert(offset,id);Ok(id)
    }
    fn phi(&mut self,parts:Vec<(usize,Slice)>,width:u8,block:usize) -> Result<Id,&'static str> {
        self.charge(parts.len())?;
        let id=self.node(Value::Phi(parts),width,true)?;self.plan.blocks[block].phis.push(id);Ok(id)
    }
    fn merge(&mut self,states:&[(usize,&State)],block:usize) -> Result<State,&'static str> {
        self.charge(states.len()*(states[0].1.registers.len()+states[0].1.bytes.len()))?;
        let mut result=states[0].1.clone();
        for (reg,value) in result.registers.iter_mut().enumerate() {
            if states.iter().all(|(_,s)|s.registers[reg]==*value) {continue;}
            let width=states.iter().map(|(_,s)|self.plan.nodes[s.registers[reg]].width).max().unwrap();
            *value=self.phi(states.iter().map(|(b,s)|(*b,Slice{value:s.registers[reg],byte:0,size:16})).collect(),width,block)?;
        }
        for (offset,byte) in result.bytes.iter_mut().enumerate() {
            if states.iter().all(|(_,s)|s.bytes[offset]==*byte) {continue;}
            let id=self.phi(states.iter().map(|(b,s)|{let v=s.bytes[offset];(*b,Slice{value:v.value,byte:v.byte,size:1})}).collect(),1,block)?;
            *byte=Byte{value:id,byte:0};
        }
        Ok(result)
    }
    fn read<'a>(&mut self,state:&'a State,access:Access) -> Result<&'a [Byte],&'static str> {
        self.charge(access.size)?;
        if access.size==0 {return Ok(&[]);}
        let offset=access.offset.ok_or("scalar_missing_offset")?;
        state.bytes.get(offset..offset.checked_add(access.size).ok_or("scalar_range")?).ok_or("scalar_range")
    }
    fn write(&mut self,state:&mut State,access:Access,bytes:&[Byte]) -> Result<(),&'static str> {
        self.charge(access.size)?;if access.size!=bytes.len() {return Err("scalar_extent_mismatch");}
        if access.size==0 {return Ok(());}
        let offset=access.offset.ok_or("scalar_missing_offset")?;
        let target=state.bytes.get_mut(offset..offset.checked_add(access.size).ok_or("scalar_range")?).ok_or("scalar_range")?;
        target.copy_from_slice(bytes);Ok(())
    }
    fn pack(&mut self,bytes:&[Byte]) -> Result<Id,&'static str> {
        self.charge(bytes.len())?;if bytes.len()>16 {return Err("scalar_pack_width");}
        if bytes.is_empty() {return self.constant(0);}
        let mut parts:Vec<Slice>=vec![];
        for b in bytes {
            match parts.last_mut() {
                Some(p) if p.value==b.value && p.byte+p.size==b.byte => p.size+=1,
                _ => parts.push(Slice{value:b.value,byte:b.byte,size:1}),
            }
        }
        if parts.len()==1 && parts[0].byte==0 && self.plan.nodes[parts[0].value].width<=parts[0].size {
            return Ok(parts[0].value);
        }
        if parts.iter().all(|p|matches!(self.plan.nodes[p.value].value,Value::Constant(_))) {
            let mut value=0u128;let mut shift=0;
            for p in parts {let Value::Constant(v)=self.plan.nodes[p.value].value else {unreachable!()};
                value|=slice(v,p)<<shift;shift+=p.size as u32*8;}
            return self.constant(value);
        }
        self.node(Value::Pack(parts),bytes.len() as u8,false)
    }
}
fn bytes(value:Id,size:usize) -> Vec<Byte> {(0..size).map(|byte|Byte{value,byte:byte as u8}).collect()}
fn mask(bits:u8) -> u128 {if bits==128 {u128::MAX} else {(1u128<<bits)-1}}
fn slice(value:u128,p:Slice) -> u128 {(value>>(p.byte as u32*8))&mask(p.size*8)}

pub fn lower(f:&Function,memory:&MemoryPlan,limit:usize) -> Result<Plan,&'static str> {
    lower_bounded::<512>(f,memory,limit)
}

fn lower_bounded<const FRAME:usize>(f:&Function,memory:&MemoryPlan,limit:usize) -> Result<Plan,&'static str> {
    if !memory.eligible {return Err("no_memory_plan");}
    if f.code.is_empty() || f.code.len()>512 || f.frame_size>FRAME || f.registers>512 {return Err("scalar_shape_limit");}
    // A new opcode must be reviewed explicitly. Floating point and byte
    // comparison are deliberately outside this first internal representation.
    if f.code.iter().any(|op|!matches!(op,Op::Imm{..}|Op::Local{..}|Op::Load{..}|Op::Store{..}|Op::Copy{..}
        |Op::Binary{..}|Op::Unary{..}|Op::Cast{..}|Op::Select{..}|Op::Jump{..}|Op::Switch{..}
        |Op::Assert{..}|Op::Return|Op::Trap{..}|Op::FillBytes{..}|Op::CopyDynamic{..})) {return Err("scalar_unsupported");}
    let mut starts=BTreeSet::from([0]);let mut edges=0usize;
    for (pc,op) in f.code.iter().enumerate() {
        match op {
            Op::Jump{target} => {starts.insert(*target);edges+=1;},
            Op::Switch{cases,otherwise,..} => {starts.insert(*otherwise);for (_,t) in cases {starts.insert(*t);}edges+=cases.len()+1;},
            _=>{},
        }
        if edges>8192 {return Err("scalar_edge_limit");}
        if matches!(op,Op::Jump{..}|Op::Switch{..}|Op::Return|Op::Trap{..}) && pc+1<f.code.len() {starts.insert(pc+1);}
    }
    let starts:Vec<_>=starts.into_iter().collect();let mut at=vec![0;f.code.len()];let mut blocks=vec![];
    for (id,&start) in starts.iter().enumerate() {
        let end=starts.get(id+1).copied().unwrap_or(f.code.len());if start>=end {return Err("scalar_invalid_cfg");}
        at[start..end].fill(id);blocks.push(Block{start,end,successors:vec![],predecessors:vec![],phis:vec![]});
    }
    for b in 0..blocks.len() {
        let end=blocks[b].end;
        let mut next=match &f.code[end-1] {
            Op::Jump{target}=>vec![at[*target]],
            Op::Switch{cases,otherwise,..}=>cases.iter().map(|(_,t)|at[*t]).chain([at[*otherwise]]).collect(),
            Op::Return|Op::Trap{..}=>vec![],
            _ if end<f.code.len()=>vec![at[end]],
            _=>return Err("scalar_falloff"),
        };
        next.sort_unstable();next.dedup();
        for &n in &next {blocks[n].predecessors.push(b);}blocks[b].successors=next;
    }
    let mut reachable=vec![false;blocks.len()];reachable[0]=true;let mut queue=VecDeque::from([0]);
    while let Some(b)=queue.pop_front() {for &n in &blocks[b].successors {if !reachable[n] {reachable[n]=true;queue.push_back(n);}}}
    let mut pending:Vec<_>=blocks.iter().map(|b|b.predecessors.iter().filter(|p|reachable[**p]).count()).collect();
    for b in 0..blocks.len() {if reachable[b] && pending[b]==0 {queue.push_back(b);}}
    let mut order=vec![];let mut longest=vec![0;blocks.len()];
    // Reuse the existing bounded topological traversal. A single successful
    // length is valid only when every structural Return path has that length.
    // Fault-only paths still participate in maximum_steps for entry admission.
    let mut shortest=vec![usize::MAX;blocks.len()];shortest[0]=0;
    let (mut return_min,mut return_max)=(usize::MAX,0);
    while let Some(b)=queue.pop_front() {
        order.push(b);let length=blocks[b].end-blocks[b].start;longest[b]+=length;shortest[b]+=length;
        if matches!(f.code[blocks[b].end-1],Op::Return) {return_min=return_min.min(shortest[b]);return_max=return_max.max(longest[b]);}
        for &n in &blocks[b].successors {longest[n]=longest[n].max(longest[b]);shortest[n]=shortest[n].min(shortest[b]);
            pending[n]-=1;if pending[n]==0 {queue.push_back(n);}}
    }
    if order.len()!=reachable.iter().filter(|v|**v).count() {return Err("scalar_cycle");}
    let maximum_steps=longest.into_iter().max().unwrap();
    let success_steps=(return_min==return_max).then_some(return_max);
    let mut b=Builder {plan:Plan{nodes:vec![],blocks,at,computations:vec![vec![];f.code.len()],effects:vec![Effect::None;f.code.len()],
        live:vec![],reachable,maximum_steps,success_steps,result_size:f.result.size,work:0},constants:HashMap::new(),bases:HashMap::new(),roots:vec![],pc:0,limit};
    b.charge(f.code.len()+edges+f.registers+f.frame_size.max(1))?;
    let zero=b.constant(0)?;let mut entry=State{registers:vec![zero;f.registers],bytes:vec![Byte{value:zero,byte:0};f.frame_size.max(1)]};
    for (index,slot) in f.args.iter().enumerate() {
        if slot.size>16 {return Err("scalar_input_width");}
        let value=b.node(Value::Input(index),slot.size as u8,true)?;
        b.write(&mut entry,Access{offset:Some(slot.offset),size:slot.size},&bytes(value,slot.size))?;
    }
    let accesses:HashMap<_,_>=memory.accesses.iter().map(|a|(a.pc,a)).collect();
    if accesses.len()!=memory.accesses.len() {return Err("scalar_duplicate_access");}
    let mut outputs:Vec<Option<State>>=vec![None;b.plan.blocks.len()];
    for block in order {
        let mut state=if block==0 {entry.clone()} else {
            let predecessors:Vec<_>=b.plan.blocks[block].predecessors.iter().filter(|p|b.plan.reachable[**p])
                .map(|p|(*p,outputs[*p].as_ref().unwrap())).collect();b.merge(&predecessors,block)?
        };
        for pc in b.plan.blocks[block].start..b.plan.blocks[block].end {
            b.pc=pc;b.charge(1)?;
            let access=accesses.get(&pc);
            let read=|n:usize| access.and_then(|a|a.reads.get(n)).copied().ok_or("scalar_missing_read");
            let write=|n:usize| access.and_then(|a|a.writes.get(n)).copied().ok_or("scalar_missing_write");
            let effect=match &f.code[pc] {
                Op::Imm{dst,value}=>{state.registers[*dst as usize]=b.constant(*value)?;Effect::None},
                Op::Local{dst,offset}=>{state.registers[*dst as usize]=b.base(*offset)?;Effect::None},
                Op::Load{dst,..}=>{let data=b.read(&state,read(0)?)?.to_vec();state.registers[*dst as usize]=b.pack(&data)?;Effect::None},
                Op::Store{src,..}=>{let a=write(0)?;let value=state.registers[*src as usize];b.write(&mut state,a,&bytes(value,a.size))?;Effect::None},
                Op::Copy{..}|Op::CopyDynamic{..}=>{let data=b.read(&state,read(0)?)?.to_vec();b.write(&mut state,write(0)?,&data)?;Effect::None},
                Op::FillBytes{value,..}=>{let a=write(0)?;let byte=Byte{value:state.registers[*value as usize],byte:0};
                    b.write(&mut state,a,&vec![byte;a.size])?;Effect::None},
                Op::Binary{dst,overflow,op,a,b:other,bits,signed}=>{
                    let (left,right)=(state.registers[*a as usize],state.registers[*other as usize]);
                    let value=b.node(Value::Binary{a:left,b:right,op:*op,bits:*bits,signed:*signed,overflow:false},bits/8,false)?;
                    let over=b.node(Value::Binary{a:left,b:right,op:*op,bits:*bits,signed:*signed,overflow:true},1,false)?;
                    state.registers[*dst as usize]=value;state.registers[*overflow as usize]=over;
                    if matches!(op,Binary::Div|Binary::Rem) {b.roots.push(value);}Effect::None
                },
                Op::Unary{dst,op,src,bits}=>{let value=b.node(Value::Unary{src:state.registers[*src as usize],op:*op,bits:*bits},bits/8,false)?;
                    state.registers[*dst as usize]=value;Effect::None},
                Op::Cast{dst,src,from,to,signed}=>{let value=b.node(Value::Cast{src:state.registers[*src as usize],from:*from,to:*to,signed:*signed},to/8,false)?;
                    state.registers[*dst as usize]=value;Effect::None},
                Op::Select{dst,condition,yes,no}=>{let (condition,yes,no)=(state.registers[*condition as usize],state.registers[*yes as usize],state.registers[*no as usize]);
                    let width=b.plan.nodes[yes].width.max(b.plan.nodes[no].width);
                    let value=b.node(Value::Select{condition,yes,no},width,false)?;state.registers[*dst as usize]=value;Effect::None},
                Op::Jump{target}=>Effect::Jump(*target),
                Op::Switch{value,cases,otherwise}=>{let value=state.registers[*value as usize];b.roots.push(value);
                    Effect::Switch{value,cases:cases.clone(),otherwise:*otherwise}},
                Op::Assert{value,expected,message}=>{let value=state.registers[*value as usize];b.roots.push(value);
                    Effect::Assert{value,expected:*expected,message:message.clone()}},
                Op::Trap{message}=>Effect::Trap(message.clone()),
                Op::Return=>{let data=b.read(&state,read(0)?)?.to_vec();let value=b.pack(&data)?;b.roots.push(value);Effect::Return(value)},
                _=>return Err("scalar_unsupported"),
            };
            b.plan.effects[pc]=effect;
        }
        outputs[block]=Some(state);
    }
    b.plan.live=vec![false;b.plan.nodes.len()];
    while let Some(id)=b.roots.pop() {if b.plan.live[id] {continue;}b.plan.live[id]=true;
        let inputs=b.plan.nodes[id].inputs();b.charge(inputs.len()+1)?;b.roots.extend(inputs);}
    Ok(b.plan)
}

#[derive(Debug, PartialEq, Eq)]
pub struct Outcome {pub value:u128,pub pcs:Vec<usize>}
impl Plan {
    /// Test/reference evaluator for this experiment's own scalar IR. Guest
    /// frames, caller state and the production execution path are not modified.
    pub fn evaluate(&self,arguments:&[u128],base:usize,budget:usize,name:&str) -> Result<Outcome,String> {
        let mut values=vec![None;self.nodes.len()];let mut pcs=vec![];
        let get=|values:&Vec<Option<u128>>,id:Id|values[id].ok_or_else(||format!("scalar value {id} unavailable"));
        for (id,node) in self.nodes.iter().enumerate() {
            if !self.live[id] {continue;}
            values[id]=match node.value {
                Value::Constant(v)=>Some(v),Value::Input(i)=>Some(arguments[i]),
                Value::Base(offset)=>Some(base.checked_add(offset).ok_or("scalar base overflow")? as u128),_=>None,
            };
        }
        let mut block=0;let mut previous=None;
        loop {
            for &id in &self.blocks[block].phis {
                if !self.live[id] {continue;}
                let Value::Phi(parts)=&self.nodes[id].value else {unreachable!()};
                let (_,part)=parts.iter().find(|(p,_)|Some(*p)==previous).ok_or("scalar predecessor unavailable")?;
                values[id]=Some(slice(get(&values,part.value)?,*part));
            }
            let mut next=None;
            for pc in self.blocks[block].start..self.blocks[block].end {
                if pcs.len()>=budget {return Err("interpreter instruction limit exceeded".into());}pcs.push(pc);
                for &id in &self.computations[pc] {
                    if !self.live[id] {continue;}
                    debug_assert_eq!(self.nodes[id].pc,Some(pc));
                    let value=match &self.nodes[id].value {
                        Value::Pack(parts)=>{let mut value=0;let mut shift=0;for p in parts {value|=slice(get(&values,p.value)?,*p)<<shift;shift+=p.size as u32*8;}value},
                        Value::Binary{a,b,op,bits,signed,overflow}=>{let (value,over)=crate::binary(*op,get(&values,*a)?,get(&values,*b)?,*bits,*signed)?;
                            if *overflow {u128::from(over)} else {value}},
                        Value::Unary{src,op,bits}=>{let v=get(&values,*src)?&mask(*bits);match op {
                            Unary::Not=>!v&mask(*bits),Unary::Neg=>v.wrapping_neg()&mask(*bits),Unary::CountOnes=>v.count_ones() as u128,
                            Unary::LeadingZeros=>(v.leading_zeros()-(128-u32::from(*bits))) as u128,
                            Unary::TrailingZeros=>v.trailing_zeros().min(u32::from(*bits)) as u128,
                            Unary::SwapBytes=>v.swap_bytes()>>(128-*bits)}},
                        Value::Cast{src,from,to,signed}=>{let v=get(&values,*src)?;let n=if *signed {(((v<<(128-*from)) as i128)>>(128-*from)) as u128} else {v&mask(*from)};n&mask(*to)},
                        Value::Select{condition,yes,no}=>get(&values,if get(&values,*condition)?!=0 {*yes} else {*no})?,
                        _=>return Err("scalar misplaced node".into()),
                    };values[id]=Some(value);
                }
                match &self.effects[pc] {
                    Effect::None=>{},Effect::Assert{value,expected,message}=>if (get(&values,*value)?!=0)!=*expected {return Err(format!("guest assertion: {message} in {name}"));},
                    Effect::Jump(target)=>next=Some(*target),
                    Effect::Switch{value,cases,otherwise}=>{let v=get(&values,*value)?;next=Some(cases.iter().find(|(n,_)|*n==v).map_or(*otherwise,|(_,t)|*t));},
                    Effect::Return(value)=>return Ok(Outcome{value:get(&values,*value)?,pcs}),
                    Effect::Trap(message)=>return Err(format!("guest trap: {message} in {name}")),
                }
            }
            let pc=next.unwrap_or(self.blocks[block].end);previous=Some(block);block=*self.at.get(pc).ok_or("scalar falloff")?;
        }
    }
}

#[cfg(test)]
#[path="scalar_ir_tests.rs"]
mod tests;

#[cfg(test)]
#[path="aggregate.rs"]
mod aggregate;

#[path="native_leaf.rs"]
pub mod native_leaf;
