//! Only for private, non-address-exposed primitive MIR slots. The caller must
//! prove that other pointers cannot alias these ranges. This is not a general
//! optimizer for externally supplied bytecode.
use rust_interp_bytecode::{Op,Reg,Slot};
use std::collections::BTreeMap;

#[derive(Default,Debug)]
pub(super) struct Report { pub slots:usize, pub removed_addresses:usize, pub rewritten:usize, pub removed_moves:usize }

// Explicit matches force review when the bytecode gains a register operand.
fn registers(op:&Op,mut read:impl FnMut(Reg),mut write:impl FnMut(Reg)) {
    match op {
        Op::Imm{..}|Op::Local{..}|Op::Jump{..}|Op::Return|Op::Trap{..}|Op::ResetThreadLocals=>{},
        Op::Load{address,..}=>read(*address),
        Op::Store{address,src,..}=>{read(*address);read(*src);},
        Op::Copy{dst,src,..}=>{read(*dst);read(*src);},
        Op::CopyDynamic{dst,src,size}=>{read(*dst);read(*src);read(*size);},
        Op::Binary{a,b,..}|Op::FloatBinary{a,b,..}=>{read(*a);read(*b);},
        Op::Unary{src,..}|Op::Cast{src,..}|Op::FloatUnary{src,..}|Op::FloatConvert{src,..}=>read(*src),
        Op::Select{condition,yes,no,..}=>{read(*condition);read(*yes);read(*no);},
        Op::Switch{value,..}|Op::Assert{value,..}=>read(*value),
        Op::Call{args,destination,..}=>{read(*destination);for &r in args {read(r);}},
        Op::CallIndirect{callee,args,destination,..}=>{read(*callee);read(*destination);for &r in args {read(r);}},
        Op::CompareBytes{left,right,size,..}=>{read(*left);read(*right);read(*size);},
        Op::Allocate{size,align,..}=>{read(*size);read(*align);},
        Op::Deallocate{pointer,size,align}=>{read(*pointer);read(*size);read(*align);},
        Op::Reallocate{pointer,old_size,align,new_size,..}=>{read(*pointer);read(*old_size);read(*align);read(*new_size);},
        Op::FillBytes{address,value,size}=>{read(*address);read(*value);read(*size);},
        Op::RandomBytes{address,size,..}=>{read(*address);read(*size);},
        Op::DescriptorOpen{path,flags,mode,errno,..}=>{for r in [path,flags,errno] {read(*r);} if let Some(r)=mode {read(*r);}},
        Op::DescriptorWrite{descriptor,address,size,errno,..}=>{for r in [descriptor,address,size,errno] {read(*r);}},
        Op::DescriptorClose{descriptor,errno,..}|Op::DescriptorGetFd{descriptor,errno,..}=>{read(*descriptor);read(*errno);},
        Op::DescriptorStat{descriptor,address,errno,..}=>{for r in [descriptor,address,errno] {read(*r);}},
        Op::CurrentDirectory{address,size,errno,..}=>{for r in [address,size,errno] {read(*r);}},
        Op::EnvironmentGet{name,..}=>read(*name),
        Op::CpuFeatureQuery{name,output,output_len,new_data,new_len,..}=>{for r in [name,output,output_len,new_data,new_len] {read(*r);}},
        Op::CAllocate{count,size,errno,..}=>{for r in [count,size,errno] {read(*r);}},
        Op::CDeallocate{pointer}=>read(*pointer),
        Op::RegisterTlsDestructor{callback,argument}=>{read(*callback);read(*argument);},
        Op::CReallocate{pointer,size,errno,..}=>{for r in [pointer,size,errno] {read(*r);}},
        Op::CAlignedAllocate{output,align,size,..}=>{for r in [output,align,size] {read(*r);}},
    }
    match op {
        Op::Binary{dst,overflow,..}=>{write(*dst);write(*overflow);},
        Op::Imm{dst,..}|Op::Local{dst,..}|Op::Load{dst,..}|Op::Unary{dst,..}|Op::Cast{dst,..}|Op::Select{dst,..}
        |Op::CompareBytes{dst,..}|Op::Allocate{dst,..}|Op::Reallocate{dst,..}|Op::RandomBytes{dst,..}|Op::CpuFeatureQuery{dst,..}|Op::EnvironmentGet{dst,..}
        |Op::DescriptorOpen{dst,..}|Op::DescriptorWrite{dst,..}|Op::DescriptorClose{dst,..}|Op::DescriptorGetFd{dst,..}|Op::CurrentDirectory{dst,..}|Op::DescriptorStat{dst,..}
        |Op::CAllocate{dst,..}|Op::CReallocate{dst,..}|Op::CAlignedAllocate{dst,..}
        |Op::FloatBinary{dst,..}|Op::FloatUnary{dst,..}|Op::FloatConvert{dst,..}=>write(*dst),
        Op::Store{..}|Op::Copy{..}|Op::CopyDynamic{..}|Op::Jump{..}|Op::Switch{..}|Op::Assert{..}
        |Op::Call{..}|Op::CallIndirect{..}|Op::Return|Op::Trap{..}|Op::Deallocate{..}|Op::CDeallocate{..}
        |Op::RegisterTlsDestructor{..}|Op::FillBytes{..}|Op::ResetThreadLocals=>{},
    }
}

fn starts(code:&[Op])->Vec<bool> {
    let mut start=vec![false;code.len()];start[0]=true;
    for (pc,op) in code.iter().enumerate() {
        match op {
            Op::Jump{target}=>start[*target]=true,
            Op::Switch{cases,otherwise,..}=>{start[*otherwise]=true;for (_,target) in cases {start[*target]=true;}},
            _=>{},
        }
        if matches!(op,Op::Jump{..}|Op::Switch{..}|Op::Return|Op::Trap{..})&&pc+1<start.len() {start[pc+1]=true;}
    }
    start
}

pub(super) fn promote(code:&mut Vec<Op>,count:&mut u32,slots:&[Slot])->Report {
    if slots.is_empty() || slots.len()>256 || code.is_empty() || code.len()>100_000 || *count>100_000 {return Report::default();}
    let by_offset:BTreeMap<_,_>=slots.iter().enumerate().map(|(i,s)|(s.offset,i)).collect();
    assert_eq!(slots.len(),by_offset.len());
    for slot in slots {assert!([1,2,4,8,16].contains(&slot.size));}
    let mut writer_counts=vec![0u32;*count as usize];let mut addresses=vec![None;*count as usize];
    let mut candidate=vec![true;slots.len()];let mut uses=vec![0usize;slots.len()];
    for op in code.iter() {
        registers(op,|_|{},|r|writer_counts[r as usize]+=1);
        if let Op::Local{dst,offset}=op {if let Some(&slot)=by_offset.get(offset) {addresses[*dst as usize]=Some(slot);}}
    }
    for (r,&slot) in addresses.iter().enumerate() {if let Some(slot)=slot {if writer_counts[r]!=1 {candidate[slot]=false;}}}
    let start=starts(code);let mut defined=vec![0usize;*count as usize];let mut epoch=0;
    for (pc,op) in code.iter().enumerate() {
        if start[pc] {epoch=pc+1;}
        registers(op,|r| {
            if let Some(slot)=addresses[r as usize] {
                let size=slots[slot].size;
                let allowed=match op {
                    Op::Load{address,size:n,..}=>*address==r&&usize::from(*n)==size,
                    Op::Store{address,src,size:n}=>*address==r&&*src!=r&&usize::from(*n)==size,
                    Op::Copy{src,dst,size:n}=>(*src==r||*dst==r)&&*n==size,
                    _=>false,
                };
                if !allowed || defined[r as usize]!=epoch {candidate[slot]=false;}
                uses[slot]+=1;
            }
        },|_|{});
        if let Op::Local{dst,..}=op {defined[*dst as usize]=epoch;}
    }
    for (yes,uses) in candidate.iter_mut().zip(uses) {*yes &= uses>0;}
    let mut canonical=vec![None;slots.len()];let mut output=Vec::with_capacity(code.len()+slots.len());let mut report=Report::default();
    for (slot,&yes) in candidate.iter().enumerate() {
        if yes {let dst=*count;*count+=1;canonical[slot]=Some(dst);output.push(Op::Imm{dst,value:0});report.slots+=1;}
    }
    if report.slots==0 {return report;}
    let promoted=|r:Reg|addresses[r as usize].and_then(|slot|canonical[slot]);
    let mov=|dst,src,size:usize|Op::Cast{dst,src,from:(size*8) as u8,to:(size*8) as u8,signed:false};
    let mut mapped=vec![0usize;code.len()];
    for (pc,op) in code.iter().enumerate() {
        mapped[pc]=output.len();
        match op {
            Op::Local{dst,..} if promoted(*dst).is_some()=>{report.removed_addresses+=1;},
            Op::Load{dst,address,size} if promoted(*address).is_some()=>{
                output.push(mov(*dst,promoted(*address).unwrap(),*size as usize));report.rewritten+=1;
            },
            Op::Store{address,src,size} if promoted(*address).is_some()=>{
                output.push(mov(promoted(*address).unwrap(),*src,*size as usize));report.rewritten+=1;
            },
            Op::Copy{dst,src,size} if promoted(*dst).is_some()||promoted(*src).is_some()=>{
                match (promoted(*dst),promoted(*src)) {
                    (Some(dst),Some(src))=>output.push(mov(dst,src,*size)),
                    (Some(dst),None)=>output.push(Op::Load{dst,address:*src,size:*size as u8}),
                    (None,Some(src))=>output.push(Op::Store{address:*dst,src,size:*size as u8}),
                    _=>unreachable!(),
                }
                report.rewritten+=1;
            },
            _=>output.push(op.clone()),
        }
    }
    for op in &mut output {
        match op {
            Op::Jump{target}=>*target=mapped[*target],
            Op::Switch{cases,otherwise,..}=>{*otherwise=mapped[*otherwise];for (_,target) in cases {*target=mapped[*target];}},
            _=>{},
        }
    }
    *code=output;
    let scalars:Vec<_>=canonical.iter().enumerate().filter_map(|(i,r)|r.map(|r|(r,(slots[i].size*8) as u8))).collect();
    report.removed_moves=scalar_moves::eliminate(code,*count,&scalars);
    report
}

#[cfg(test)]
#[path="scalar_promote_tests.rs"]
mod tests;

#[path="scalar_promote_moves.rs"]
mod scalar_moves;
