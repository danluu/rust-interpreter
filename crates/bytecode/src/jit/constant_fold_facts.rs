//! Abstract transfer for the experimental function-body constant folder.
use crate::{Binary, Function, Op, Program, Reg, Unary};
use std::collections::BTreeMap;

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(super) enum Fact { Scalar(u128), Local(usize) }
impl Fact { fn scalar(self)->Option<u128> {if let Self::Scalar(x)=self {Some(x)} else {None}} }

#[derive(Clone,Debug,Default,PartialEq,Eq)]
pub(super) struct State {
    pub registers:BTreeMap<Reg,Fact>,
    pub bytes:BTreeMap<usize,u8>,
}
impl State {
    pub fn cost(&self)->usize {1+self.registers.len()+self.bytes.len()}
    pub fn get(&self,r:Reg)->Option<Fact> {self.registers.get(&r).copied()}
    pub fn scalar(&self,r:Reg)->Option<u128> {self.get(r)?.scalar()}
    fn set(&mut self,r:Reg,fact:Fact) {
        if !self.registers.contains_key(&r) && self.registers.len()==512 {self.registers.clear();}
        self.registers.insert(r,fact);
    }
    pub fn intersect(&mut self, other:&Self)->bool {
        let before=(self.registers.len(),self.bytes.len());
        self.registers.retain(|r,v|other.registers.get(r)==Some(v));
        self.bytes.retain(|offset,v|other.bytes.get(offset)==Some(v));
        before!=(self.registers.len(),self.bytes.len())
    }
    pub fn covered_by(&self,other:&Self)->bool {
        self.registers.iter().all(|(r,v)|other.registers.get(r)==Some(v)) && self.bytes.iter().all(|(p,v)|other.bytes.get(p)==Some(v))
    }
    pub fn read(&self,address:Option<Fact>,size:usize,p:&Program,f:&Function)->Option<u128> {
        if size==0 || size>16 {return None;}
        let mut bytes=[0u8;16];
        match address? {
            Fact::Local(start)=>{
                if start.checked_add(size)?>f.frame_size {return None;}
                for (i,b) in bytes[..size].iter_mut().enumerate() {*b=*self.bytes.get(&(start+i))?;}
            }
            Fact::Scalar(v)=>{let start=usize::try_from(v).ok()?;bytes[..size].copy_from_slice(p.data.get(start..start.checked_add(size)?)?);}
        }
        Some(u128::from_le_bytes(bytes))
    }
    fn write(&mut self,address:Option<Fact>,size:usize,value:Option<u128>,frame:usize) {
        if size==0 {return;}
        let Some(Fact::Local(start))=address else {self.bytes.clear();return;};
        let Some(end)=start.checked_add(size).filter(|&end|end<=frame) else {self.bytes.clear();return;};
        self.bytes.retain(|&offset,_|offset<start || offset>=end);
        if let Some(value)=value.filter(|_|size<=16) {
            if self.bytes.len()+size>256 {self.bytes.clear();}
            for (i,&byte) in value.to_le_bytes()[..size].iter().enumerate() {self.bytes.insert(start+i,byte);}
        }
    }
    pub fn step(&mut self,op:&Op,p:&Program,f:&Function) {
        let mut out=Vec::with_capacity(2);
        match op {
            Op::Imm{dst,value}=>out.push((*dst,Fact::Scalar(*value))),
            Op::Local{dst,offset}=>out.push((*dst,Fact::Local(*offset))),
            Op::Load{dst,address,size}=>{if let Some(value)=self.read(self.get(*address),*size as usize,p,f) {out.push((*dst,Fact::Scalar(value)));}},
            Op::Store{address,src,size}=>self.write(self.get(*address),*size as usize,self.scalar(*src),f.frame_size),
            Op::Copy{dst,src,size}=>{let value=self.read(self.get(*src),*size,p,f);self.write(self.get(*dst),*size,value,f.frame_size);},
            Op::CopyDynamic{dst,src,size}=>{
                if let Some(size)=self.scalar(*size).and_then(|v|usize::try_from(v).ok()) {
                    let value=self.read(self.get(*src),size,p,f);self.write(self.get(*dst),size,value,f.frame_size);
                } else {self.bytes.clear();}
            }
            Op::FillBytes{address,value,size}=>{
                let address=self.get(*address);let byte=self.scalar(*value).map(|v|v as u8);
                if let Some(size)=self.scalar(*size).and_then(|v|usize::try_from(v).ok()) {
                    self.write(address,size,None,f.frame_size);
                    if let (Some(Fact::Local(start)),Some(byte))=(address,byte) {
                        if size<=256 && start.checked_add(size).is_some_and(|end|end<=f.frame_size) {
                            if self.bytes.len()+size>256 {self.bytes.clear();}
                            for offset in start..start+size {self.bytes.insert(offset,byte);}
                        }
                    }
                } else {self.bytes.clear();}
            }
            Op::Binary{dst,overflow,op,a,b,bits,signed}=>{
                let av=self.get(*a);let bv=self.get(*b);
                let scalar=match (av.and_then(Fact::scalar),bv.and_then(Fact::scalar)) {
                    (Some(a),Some(b))=>crate::binary(*op,a,b,*bits,*signed).ok(),
                    (a,b)=>match op {
                        Binary::And if a.is_some_and(|v|v & crate::mask(*bits)==0)||b.is_some_and(|v|v & crate::mask(*bits)==0)=>Some((0,false)),
                        Binary::Or if a.is_some_and(|v|v & crate::mask(*bits)==crate::mask(*bits))||b.is_some_and(|v|v & crate::mask(*bits)==crate::mask(*bits))=>Some((crate::mask(*bits),false)),
                        Binary::Mul if a.is_some_and(|v|v & crate::mask(*bits)==0)||b.is_some_and(|v|v & crate::mask(*bits)==0)=>Some((0,false)),
                        _=>None,
                    },
                };
                if let Some((v,over))=scalar {out.push((*dst,Fact::Scalar(v)));out.push((*overflow,Fact::Scalar(u128::from(over))));}
                else if matches!(op,Binary::Add) && *bits==64 && !signed {
                    let parts=match (av,bv) {(Some(Fact::Local(offset)),Some(Fact::Scalar(v)))|(Some(Fact::Scalar(v)),Some(Fact::Local(offset)))=>Some((offset,v)),_=>None};
                    if let Some((offset,v))=parts {
                        if let Some(end)=usize::try_from(v).ok().and_then(|v|offset.checked_add(v)).filter(|&end|end<=f.frame_size) {
                            out.push((*dst,Fact::Local(end)));out.push((*overflow,Fact::Scalar(0)));
                        }
                    }
                }
            }
            Op::Unary{dst,op,src,bits}=>{if let Some(v)=self.scalar(*src) {
                let v=v & crate::mask(*bits);
                let result=match op {
                    Unary::Not=>!v & crate::mask(*bits),Unary::Neg=>v.wrapping_neg() & crate::mask(*bits),
                    Unary::CountOnes=>v.count_ones() as u128,Unary::LeadingZeros=>(v.leading_zeros()-(128-u32::from(*bits))) as u128,
                    Unary::TrailingZeros=>v.trailing_zeros().min(u32::from(*bits)) as u128,Unary::SwapBytes=>v.swap_bytes()>>(128-*bits),
                };out.push((*dst,Fact::Scalar(result)));
            }},
            Op::Cast{dst,src,from,to,signed}=>{if let Some(v)=self.scalar(*src) {
                let v=if *signed {crate::signed(v,*from) as u128} else {v & crate::mask(*from)};
                out.push((*dst,Fact::Scalar(v & crate::mask(*to))));
            }},
            Op::Select{dst,condition,yes,no}=>{
                let chosen=match self.scalar(*condition) {Some(v)=>self.get(if v!=0 {*yes} else {*no}),None=>if self.get(*yes)==self.get(*no) {self.get(*yes)} else {None}};
                if let Some(value)=chosen {out.push((*dst,value));}
            }
            Op::Call{..}|Op::CallIndirect{..}|Op::Allocate{..}|Op::Deallocate{..}|Op::Reallocate{..}
            |Op::ResetThreadLocals|Op::RandomBytes{..}|Op::CpuFeatureQuery{..}|Op::CAllocate{..}
            |Op::CDeallocate{..}|Op::CReallocate{..}|Op::CAlignedAllocate{..}|Op::RegisterTlsDestructor{..}=>self.bytes.clear(),
            Op::FloatBinary{..}|Op::FloatUnary{..}|Op::FloatConvert{..}|Op::CompareBytes{..}
            |Op::Jump{..}|Op::Switch{..}|Op::Assert{..}|Op::Return|Op::Trap{..}=>{},
        }
        crate::registers::visit_registers(op, |_|{}, |r|{self.registers.remove(&r);});
        for (r,value) in out {self.set(r,value);}
    }
}
