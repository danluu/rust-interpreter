//! Bounded exact-value aliases for this emitter's scalar graph.
//! Preserve PCs, CFG, fault roots and all nonaliased live computations.
use super::*;

const MAX_WORK:usize=250_000;

fn bit_bound(node:&Node,bounds:&[u16]) -> u16 {
    let get=|id:Id|bounds[id];
    let part=|p:Slice|get(p.value).saturating_sub(u16::from(p.byte)*8).min(u16::from(p.size)*8);
    match &node.value {
        Value::Constant(v)=>(128-v.leading_zeros()) as u16,
        Value::Input(_)=>u16::from(node.width)*8,Value::Base(_)=>64,
        Value::Phi(parts)=>parts.iter().map(|(_,p)|part(*p)).max().unwrap_or(0),
        Value::Pack(parts)=>{
            let mut bits=0;let mut shift=0;
            for p in parts {let n=part(*p);if n!=0 {bits=bits.max(shift+n);}shift+=u16::from(p.size)*8;}
            bits
        },
        Value::Binary{overflow:true,..}=>1,
        Value::Binary{a,b,op,bits,signed,..}=>{
            let limit=u16::from(*bits);let left=get(*a).min(limit);let right=get(*b).min(limit);
            match op {
                Binary::Eq|Binary::Ne|Binary::Lt|Binary::Le|Binary::Gt|Binary::Ge=>1,
                Binary::Cmp=>8,
                Binary::And=>left.min(right),Binary::Or|Binary::Xor=>left.max(right),
                Binary::Add=>(left.max(right)+1).min(limit),Binary::Mul=>(left+right).min(limit),
                Binary::Div|Binary::Rem|Binary::Shr if !signed=>left,
                _=>limit,
            }
        },
        Value::Unary{op,bits,..}=>match op {
            Unary::CountOnes|Unary::LeadingZeros|Unary::TrailingZeros=>8,
            _=>u16::from(*bits),
        },
        Value::Cast{src,from,to,signed}=>{
            let bound=get(*src);let from=u16::from(*from);let to=u16::from(*to);
            if !signed || bound<from {bound.min(from).min(to)} else {to}
        },
        Value::Select{yes,no,..}=>get(*yes).max(get(*no)),
    }
}

pub(super) fn simplify(plan:&Plan)->Result<Option<Plan>,&'static str> {
    if plan.nodes.len()>16384 || plan.live.len()!=plan.nodes.len() {return Err("native_width_node_limit");}
    let mut work=plan.nodes.len()+plan.effects.len();
    let mut bounds=Vec::with_capacity(plan.nodes.len());
    let mut canonical:Vec<Id>=Vec::with_capacity(plan.nodes.len());
    let mut changed=false;
    for (id,node) in plan.nodes.iter().enumerate() {
        let inputs=node.inputs();
        work=work.checked_add(inputs.len().checked_mul(4).ok_or("native_width_work_limit")?).ok_or("native_width_work_limit")?;
        if work>MAX_WORK {return Err("native_width_work_limit");}
        if inputs.iter().any(|&input|input>=id) {return Err("native_width_order");}
        let bound=bit_bound(node,&bounds);if bound>128 {return Err("native_width_bits");}bounds.push(bound);
        let alias=match &node.value {
            Value::Pack(parts) if parts.len()==1 && parts[0].byte==0 && bounds[parts[0].value]<=u16::from(parts[0].size)*8=>Some(parts[0].value),
            Value::Cast{src,from,to,signed} if bounds[*src]<=u16::from((*from).min(*to)) && (!signed || from==to || bounds[*src]<u16::from(*from))=>Some(*src),
            _=>None,
        };
        canonical.push(alias.map_or(id,|source|canonical[source]));
        changed |= plan.live[id] && canonical[id]!=id;
    }
    if !changed {return Ok(None);}
    let mut result=plan.clone();
    for (id,node) in result.nodes.iter_mut().enumerate() {
        if canonical[id]!=id {result.live[id]=false;}
        let replace=|value:&mut Id|*value=canonical[*value];
        match &mut node.value {
            Value::Pack(parts)=>for p in parts {replace(&mut p.value);},
            Value::Phi(parts)=>for (_,p) in parts {replace(&mut p.value);},
            Value::Binary{a,b,..}=>{replace(a);replace(b);},
            Value::Unary{src,..}|Value::Cast{src,..}=>replace(src),
            Value::Select{condition,yes,no}=>{replace(condition);replace(yes);replace(no);},
            Value::Constant(_)|Value::Input(_)|Value::Base(_)=>{},
        }
    }
    for effect in &mut result.effects {
        match effect {
            Effect::Assert{value,..}|Effect::Switch{value,..}|Effect::Return(value)=>*value=canonical[*value],
            Effect::None|Effect::Jump(_)|Effect::Trap(_)=>{},
        }
    }
    // No general dead-code elimination: in particular, original live Div/Rem
    // nodes remain live even when no result is needed, preserving private faults.
    Ok(Some(result))
}

#[cfg(test)]
#[path="native_width_tests.rs"]
mod tests;
