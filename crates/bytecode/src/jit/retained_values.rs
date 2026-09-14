//! Bounded complete-value origins. Every original frame write remains immediate.
use super::*;

#[derive(Clone,Copy)]
enum Fact { Local(usize), Imm(u128) }
#[derive(Clone,Copy)]
struct Byte { origin:usize, byte:usize }
#[derive(Clone,Copy,Debug)]
#[cfg_attr(test,derive(serde::Serialize))]
pub(super) struct Capture {pub slot:usize,pub size:usize}
#[derive(Clone,Copy,Debug)]
#[cfg_attr(test,derive(serde::Serialize))]
pub(super) struct Reuse {pub slot:usize,pub size:usize,pub origin_pc:usize}
#[derive(Default,Debug)]
#[cfg_attr(test,derive(serde::Serialize))]
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

#[derive(Default)]
pub(super) struct State { plan:Option<Plan>, active:[Option<usize>;15] }
impl State {
    pub fn new(plan:Option<Plan>)->Self {Self{plan:plan.filter(|p|!p.captures.is_empty()),active:[None;15]}}
    pub fn word(&mut self,word:u32) {
        if self.plan.is_none(){return;}
        let kill=|active:&mut [Option<usize>;15],reg:u32| {
            if reg>=17 {active[(reg-17)as usize]=None;}
        };
        if word&0x3b000000==0x39000000 && word&0x04000000!=0 {
            if word&(1<<22)!=0 {kill(&mut self.active,word&31);}
            return;
        }
        if matches!(word&0xfffffc00,0x1e260000|0x9e660000|0x4e183c00) {return;}
        if matches!(word&0xfffffc00,0x1e270000|0x9e670000|0x4e181c00) {
            kill(&mut self.active,word&31);return;
        }
        // Every other SIMD/FP instruction, unaudited SIMD memory class, or
        // host call conservatively destroys availability. Future emitters
        // cannot silently start borrowing retained temporaries.
        if word&0x0e000000==0x0e000000
            || (word&0x0a000000==0x08000000 && word&0x04000000!=0)
            || word&0xfc000000==0x94000000 || word&0xfffffc1f==0xd63f0000 {
            self.active.fill(None);
        }
    }
    fn register(&self,pc:usize,size:usize)->Option<u32> {
        let r=self.plan.as_ref()?.uses.get(&pc)?;
        (r.size==size && self.active[r.slot]==Some(r.origin_pc)).then_some(17+r.slot as u32)
    }
}

#[path="retained_values_native.rs"]
mod native;
#[cfg(test)]
#[path="retained_values_tests.rs"]
mod tests;
