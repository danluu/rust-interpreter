//! Test-only path certificate; all speculative actions are reads and checks.
use super::*;

struct SlicePlan {needed:Vec<bool>,nodes:usize,memory_sites:usize}
#[derive(Debug)]
pub(crate) struct EntryCertificate {pub pcs:Vec<usize>,values:Vec<Option<u128>>}
fn guard_slice(plan:&Plan)->Result<SlicePlan,&'static str> {
    if plan.nodes.len()>16384 || plan.effects.len()>512 || plan.blocks.len()>512 {return Err("path_shape_limit");}
    let mut pending=vec![];let mut memory_sites=0;let mut stores=0;
    for (id,node) in plan.nodes.iter().enumerate() {
        if !plan.live[id] {continue;}
        match node.value {
            Value::Read{address,..}=>{pending.push(address);memory_sites+=1;},
            Value::Write{address,..}=>{pending.push(address);memory_sites+=1;stores+=1;},
            Value::Binary{op:Binary::Div|Binary::Rem,..}=>pending.push(id),_=>{},
        }
    }
    if stores==0 || stores>16 || memory_sites>128 {return Err("path_memory_site_limit");}
    for effect in &plan.effects {if let Effect::Assert{value,..}|Effect::Switch{value,..}=effect {pending.push(*value);}}
    let mut needed=vec![false;plan.nodes.len()];let mut nodes=0;let mut work=0;
    while let Some(id)=pending.pop() {
        work+=1;if work>65536 {return Err("path_slice_work");}
        if needed[id] {continue;}needed[id]=true;nodes+=1;
        if nodes>4096 {return Err("path_slice_nodes");}
        if matches!(plan.nodes[id].value,Value::Write{..}) {return Err("path_effect_dependency");}
        pending.extend(plan.nodes[id].inputs());
    }
    Ok(SlicePlan{needed,nodes,memory_sites})
}
fn overlap(a:(bool,std::ops::Range<usize>),b:&(bool,std::ops::Range<usize>))->bool {
    a.0==b.0 && a.1.start<b.1.end && b.1.start<a.1.end
}
impl Plan {
    pub(crate) fn path_guard_shape(&self)->Result<(usize,usize),&'static str> {
        guard_slice(self).map(|s|(s.nodes,s.memory_sites))
    }
    pub(crate) fn check_path_entry(&self,args:&[u128],base:usize,memory:&crate::Memory)->Result<EntryCertificate,String> {
        let slice_plan=guard_slice(self).map_err(str::to_owned)?;let needed=slice_plan.needed;
        let mut values=vec![None;self.nodes.len()];let mut stores=vec![];let mut pcs=vec![];let mut seen=vec![false;self.effects.len()];
        let get=|v:&Vec<Option<u128>>,id:Id|v[id].ok_or_else(||format!("path value {id} unavailable"));
        for (id,node) in self.nodes.iter().enumerate() {if needed[id] {
            values[id]=match node.value {
                Value::Constant(v)=>Some(v),Value::Input(i)=>Some(*args.get(i).ok_or("path argument")?),
                Value::Base(offset)=>Some(base.checked_add(offset).ok_or("path base overflow")? as u128),_=>None,
            };
        }}
        let mut block=0;let mut previous=None;
        loop {
            for &id in &self.blocks[block].phis {
                if !needed[id] {continue;}
                let Value::Phi(parts)=&self.nodes[id].value else {return Err("path misplaced phi".into());};
                let (_,part)=parts.iter().find(|(p,_)|Some(*p)==previous).ok_or("path predecessor")?;
                values[id]=Some(slice(get(&values,part.value)?,*part));
            }
            let mut next=None;
            for pc in self.blocks[block].start..self.blocks[block].end {
                if pcs.len()>=512 || seen[pc] {return Err("path step limit".into());}seen[pc]=true;pcs.push(pc);
                for &id in &self.computations[pc] {
                    if !self.live[id] {continue;}
                    let value=match &self.nodes[id].value {
                        Value::Read{address,size}=>{
                            if *size==0 || *size>16 {return Err("path read width".into());}
                            let address=get(&values,*address)? as usize;let range=memory.range(address,*size as usize)?;
                            if !needed[id] {continue;}
                            if stores.iter().any(|s|overlap(range.clone(),s)) {return Err("path read follows overlapping write".into());}
                            memory.load(address,*size as usize)?
                        },
                        Value::Write{address,size,..}=>{
                            if *size==0 || *size>16 || stores.len()>=16 {return Err("path write width/count".into());}
                            let address=get(&values,*address)? as usize;let range=memory.range(address,*size as usize)?;
                            if !range.0 && address<memory.readonly_end {return Err("path readonly write".into());}
                            stores.push(range);continue;
                        },
                        _ if !needed[id]=>continue,
                        Value::Pack(parts)=>{let mut v=0;let mut shift=0;for p in parts {v|=slice(get(&values,p.value)?,*p)<<shift;shift+=u32::from(p.size)*8;}v},
                        Value::Binary{a,b,op,bits,signed,overflow}=>{let (v,o)=crate::binary(*op,get(&values,*a)?,get(&values,*b)?,*bits,*signed)?;if *overflow {u128::from(o)} else {v}},
                        Value::Unary{src,op,bits}=>{let v=get(&values,*src)?&mask(*bits);match op {
                            Unary::Not=>!v&mask(*bits),Unary::Neg=>v.wrapping_neg()&mask(*bits),Unary::CountOnes=>v.count_ones() as u128,
                            Unary::LeadingZeros=>(v.leading_zeros()-(128-u32::from(*bits))) as u128,
                            Unary::TrailingZeros=>v.trailing_zeros().min(u32::from(*bits)) as u128,Unary::SwapBytes=>v.swap_bytes()>>(128-*bits)}},
                        Value::Cast{src,from,to,signed}=>{let v=get(&values,*src)?;let n=if *signed {(((v<<(128-*from)) as i128)>>(128-*from)) as u128} else {v&mask(*from)};n&mask(*to)},
                        Value::Select{condition,yes,no}=>get(&values,if get(&values,*condition)?!=0 {*yes} else {*no})?,
                        _=>return Err("path misplaced computation".into()),
                    };values[id]=Some(value);
                }
                match &self.effects[pc] {
                    Effect::None=>{},Effect::Assert{value,expected,..}=>if (get(&values,*value)?!=0)!=*expected {return Err("path assertion".into());},
                    Effect::Trap(_)=>return Err("path trap".into()),Effect::Return(_)=>return Ok(EntryCertificate{pcs,values}),
                    Effect::Jump(target)=>next=Some(*target),
                    Effect::Switch{value,cases,otherwise}=>{let v=get(&values,*value)?;next=Some(cases.iter().find(|(n,_)|*n==v).map_or(*otherwise,|(_,t)|*t));},
                }
            }
            let pc=next.unwrap_or(self.blocks[block].end);previous=Some(block);block=*self.at.get(pc).ok_or("path falloff")?;
        }
    }
}

#[cfg(test)]
#[path="path_entry_census.rs"]
mod census;

// Certificate values are scoped to this uninterrupted Call attempt. All reads
// and control dependencies that were hoisted were checked against prior writes.
// Keep the complete original PC sequence while executing only uncached values.
impl Plan {
    pub(crate) fn evaluate_path_effects(&self,certificate:&EntryCertificate,arguments:&[u128],base:usize,budget:usize,name:&str,
        _read:&mut impl FnMut(u128,u8)->Result<u128,String>,
        _write:&mut impl FnMut(u128,u128,u8)->Result<(),String>)->Result<Outcome,String> {
        assert_eq!(certificate.values.len(),self.nodes.len());
        let mut values=certificate.values.clone();let cached:Vec<bool>=values.iter().map(Option::is_some).collect();let mut pcs=vec![];
        let get=|values:&Vec<Option<u128>>,id:Id|values[id].ok_or_else(||format!("scalar value {id} unavailable"));
        for (id,node) in self.nodes.iter().enumerate() {
            if !self.live[id] || cached[id] {continue;}
            values[id]=match node.value {
                Value::Constant(v)=>Some(v),Value::Input(i)=>Some(arguments[i]),
                Value::Base(offset)=>Some(base.checked_add(offset).ok_or("scalar base overflow")? as u128),_=>None,
            };
        }
        let mut block=0;let mut previous=None;
        loop {
            for &id in &self.blocks[block].phis {
                if !self.live[id] || cached[id] {continue;}
                let Value::Phi(parts)=&self.nodes[id].value else {unreachable!()};
                let (_,part)=parts.iter().find(|(p,_)|Some(*p)==previous).ok_or("scalar predecessor unavailable")?;
                values[id]=Some(slice(get(&values,part.value)?,*part));
            }
            let mut next=None;
            for pc in self.blocks[block].start..self.blocks[block].end {
                if pcs.len()>=budget {return Err("interpreter instruction limit exceeded".into());}pcs.push(pc);
                for &id in &self.computations[pc] {
                    if !self.live[id] || cached[id] {continue;}
                    debug_assert_eq!(self.nodes[id].pc,Some(pc));
                    let value=match &self.nodes[id].value {
                        Value::Read{address,size}=>_read(get(&values,*address)?,*size)?&mask(*size*8),
                        Value::Write{address,value,size}=>{_write(get(&values,*address)?,get(&values,*value)?&mask(*size*8),*size)?;0},
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
