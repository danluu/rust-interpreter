//! Staged complete-value reuse model; no production integration or code emission.
use super::*;

#[derive(Clone,Copy)]
enum Fact { Local(usize), Imm(u128) }
#[derive(Clone,Copy)]
struct Byte { origin:usize, byte:usize }
#[derive(Clone,Copy,Debug)]
pub(super) struct Capture {pub slot:usize,pub size:usize}
#[derive(Clone,Copy,Debug)]
pub(super) struct Reuse {pub slot:usize,pub size:usize,pub origin_pc:usize}
#[derive(Default,Debug)]
pub(super) struct Plan {
    pub captures:BTreeMap<usize,Capture>,
    pub uses:BTreeMap<usize,Reuse>,
}
struct Origin {pc:usize,size:usize,uses:Vec<(usize,usize)>}

fn charge(work:&mut usize,n:usize)->Option<()> {*work=work.checked_sub(n)?;Some(())}
fn local(facts:&BTreeMap<Reg,Fact>,reg:Reg,size:usize,frame:usize)->Option<usize> {
    match facts.get(&reg) {
        Some(Fact::Local(offset)) if offset.checked_add(size).is_some_and(|end|end<=frame)=>Some(*offset),
        _=>None,
    }
}

pub(super) fn plan(f:&Function,start:usize,end:usize,capacity:usize,work:&mut usize)->Option<Plan> {
    if start>=end || end>f.code.len() || end-start>1024 || capacity>15 {return None;}
    let mut facts=BTreeMap::new();let mut bytes:BTreeMap<usize,Byte>=BTreeMap::new();
    let mut origins:Vec<Origin>=vec![];
    for pc in start..end {
        charge(work,1)?;
        let mut next=vec![];let mut read=None;let mut write=None;let mut invalidate=false;
        match f.code[pc] {
            Op::Local{dst,offset}=>next.push((dst,Fact::Local(offset))),
            Op::Imm{dst,value}=>next.push((dst,Fact::Imm(value))),
            Op::Binary{dst,overflow,op,a,b,bits,signed}=>{
                let folded=match(facts.get(&a).copied(),facts.get(&b).copied()) {
                    (Some(Fact::Imm(a)),Some(Fact::Imm(b)))=>crate::binary(op,a,b,bits,signed).ok().map(|(v,o)|(Fact::Imm(v),o)),
                    (Some(Fact::Local(offset)),Some(Fact::Imm(add)))|(Some(Fact::Imm(add)),Some(Fact::Local(offset)))
                        if matches!(op,Binary::Add) && bits==64 && !signed=>offset.checked_add(add as u64 as usize)
                            .filter(|&end|end<=f.frame_size).map(|end|(Fact::Local(end),false)),
                    _=>None,
                };
                if let Some((v,o))=folded {next.extend([(dst,v),(overflow,Fact::Imm(o as u128))]);}
            },
            Op::Load{address,size,..}=>read=local(&facts,address,size.into(),f.frame_size).map(|o|(o,usize::from(size))),
            Op::Store{address,size,..}=>{
                write=local(&facts,address,size.into(),f.frame_size).map(|o|(o,usize::from(size)));
                invalidate=write.is_none() && size!=0;
            },
            Op::Copy{src,dst,size} if size<=16=>{
                read=local(&facts,src,size,f.frame_size).map(|o|(o,size));
                write=local(&facts,dst,size,f.frame_size).map(|o|(o,size));
                invalidate=write.is_none() && size!=0;
                // Unknown source into a known frame range invalidates that range
                // below; the Copy remains ordinary and preserves both checks.
            },
            Op::Unary{..}|Op::Cast{..}|Op::Select{..}|Op::Assert{..}|Op::CompareBytes{..}=>{},
            _=>invalidate=true,
        }
        let mut operands=0;
        crate::registers::visit_registers(&f.code[pc], |_|operands+=1, |r|{facts.remove(&r);});
        charge(work,operands+next.len())?;
        for(r,v)in next {facts.insert(r,v);}
        if invalidate {bytes.clear();continue;}
        let mut value=None;
        if let Some((offset,size))=read.filter(|&(_,s)|s>0) {
            charge(work,size)?;
            let first=bytes.get(&offset).copied();
            if let Some(first)=first.filter(|first|first.byte==0 && origins[first.origin].size==size &&
                (0..size).all(|i|bytes.get(&(offset+i)).is_some_and(|b|b.origin==first.origin && b.byte==i))) {
                value=Some(first.origin);
                if [4,8,16].contains(&size) {
                    let credit=if matches!(f.code[pc],Op::Copy{..}) && size==16 {3} else {1};
                    origins[first.origin].uses.push((pc,credit));
                }
            } else {
                let id=origins.len();origins.push(Origin{pc,size,uses:vec![]});value=Some(id);
                for i in 0..size {bytes.insert(offset+i,Byte{origin:id,byte:i});}
            }
        }
        if let Some((offset,size))=write.filter(|&(_,s)|s>0) {
            charge(work,size)?;
            if matches!(f.code[pc],Op::Store{..}) {
                let id=origins.len();origins.push(Origin{pc,size,uses:vec![]});value=Some(id);
            }
            for i in 0..size {
                if let Some(origin)=value {bytes.insert(offset+i,Byte{origin,byte:i});}
                else {bytes.remove(&(offset+i));}
            }
        }
        if bytes.len()>16*1024 || origins.len()>1024 {return None;}
    }
    let mut result=Plan::default();let mut active:Vec<(usize,usize)>=vec![];
    for origin in origins {
        charge(work,origin.uses.len()+capacity+1)?;
        let cost=if origin.size==16 {2}else{1};
        if ![4,8,16].contains(&origin.size) || origin.uses.iter().map(|u|u.1).sum::<usize>()<=cost {continue;}
        active.retain(|&(last,_)|last>=origin.pc);
        let Some(slot)=(0..capacity).find(|s|!active.iter().any(|&(_,v)|v==*s))else{continue;};
        let last=origin.uses.last()?.0;active.push((last,slot));
        result.captures.insert(origin.pc,Capture{slot,size:origin.size});
        for(pc,_)in origin.uses {result.uses.insert(pc,Reuse{slot,size:origin.size,origin_pc:origin.pc});}
    }
    Some(result)
}

#[path="retained_values_tests.rs"]
mod tests;
