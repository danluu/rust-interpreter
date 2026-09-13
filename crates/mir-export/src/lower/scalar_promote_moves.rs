//! Forward width-preserving scalar captures inside a block, then remove only
//! captures with no remaining register reads anywhere in the function.
use rust_interp_bytecode::{Op,Reg};

fn rewrite_reads(op:&mut Op,mut map:impl FnMut(&mut Reg)) {
    match op {
        Op::Imm{..}|Op::Local{..}|Op::Jump{..}|Op::Return|Op::Trap{..}|Op::ResetThreadLocals=>{},
        Op::Load{address,..}=>map(address),
        Op::Store{address,src,..}=>{map(address);map(src);},
        Op::Copy{dst,src,..}=>{map(dst);map(src);},
        Op::CopyDynamic{dst,src,size}=>{map(dst);map(src);map(size);},
        Op::Binary{a,b,..}|Op::FloatBinary{a,b,..}=>{map(a);map(b);},
        Op::Unary{src,..}|Op::Cast{src,..}|Op::FloatUnary{src,..}|Op::FloatConvert{src,..}=>map(src),
        Op::Select{condition,yes,no,..}=>{map(condition);map(yes);map(no);},
        Op::Switch{value,..}|Op::Assert{value,..}=>map(value),
        Op::Call{args,destination,..}=>{map(destination);for r in args {map(r);}},
        Op::CallIndirect{callee,args,destination,..}=>{map(callee);map(destination);for r in args {map(r);}},
        Op::CompareBytes{left,right,size,..}=>{map(left);map(right);map(size);},
        Op::Allocate{size,align,..}=>{map(size);map(align);},
        Op::Deallocate{pointer,size,align}=>{map(pointer);map(size);map(align);},
        Op::Reallocate{pointer,old_size,align,new_size,..}=>{map(pointer);map(old_size);map(align);map(new_size);},
        Op::FillBytes{address,value,size}=>{map(address);map(value);map(size);},
        Op::RandomBytes{address,size,..}=>{map(address);map(size);},
        Op::DescriptorOpen{path,flags,mode,errno,..}=>{for r in [path,flags,errno] {map(r);} if let Some(r)=mode {map(r);}},
        Op::DescriptorWrite{descriptor,address,size,errno,..}=>{for r in [descriptor,address,size,errno] {map(r);}},
        Op::DescriptorClose{descriptor,errno,..}|Op::DescriptorGetFd{descriptor,errno,..}=>{map(descriptor);map(errno);},
        Op::EnvironmentGet{name,..}=>map(name),
        Op::CpuFeatureQuery{name,output,output_len,new_data,new_len,..}=>{for r in [name,output,output_len,new_data,new_len] {map(r);}},
        Op::CAllocate{count,size,errno,..}=>{for r in [count,size,errno] {map(r);}},
        Op::CDeallocate{pointer}=>map(pointer),
        Op::RegisterTlsDestructor{callback,argument}=>{map(callback);map(argument);},
        Op::CReallocate{pointer,size,errno,..}=>{for r in [pointer,size,errno] {map(r);}},
        Op::CAlignedAllocate{output,align,size,..}=>{for r in [output,align,size] {map(r);}},
    }
}

pub(super) fn eliminate(code:&mut Vec<Op>,register_count:u32,scalars:&[(Reg,u8)])->usize {
    let mut widths=vec![None;register_count as usize];
    for &(r,bits) in scalars {assert!([8,16,32,64,128].contains(&bits));widths[r as usize]=Some(bits);}
    let starts=super::starts(code);let mut versions=vec![0u32;register_count as usize];
    let mut aliases=vec![None;register_count as usize];let mut captures=vec![None;code.len()];
    for (pc,op) in code.iter_mut().enumerate() {
        if starts[pc] {aliases.fill(None);}
        rewrite_reads(op,|r| {
            if let Some((source,version))=aliases[*r as usize] {
                if versions[source as usize]==version {*r=source;}
            }
        });
        // Calls preserve the caller's registers. Every explicit writer expires
        // captures of its previous value, even if the new bits might be equal.
        super::registers(op,|_|{},|r| {versions[r as usize]+=1;aliases[r as usize]=None;});
        if let Op::Cast{dst,src,from,to,signed:false}=op {
            if widths[*dst as usize].is_none() && widths[*src as usize]==Some(*from) && from==to {
                aliases[*dst as usize]=Some((*src,versions[*src as usize]));captures[pc]=Some(*dst);
            }
        }
    }
    let mut read=vec![false;register_count as usize];
    for op in code.iter() {super::registers(op,|r|read[r as usize]=true,|_|{});}
    let dead:Vec<_>=captures.iter().map(|r|r.is_some_and(|r|!read[r as usize])).collect();
    let removed=dead.iter().filter(|&&d|d).count();if removed==0 {return 0;}
    let mut mapped=vec![0usize;code.len()];let mut out=Vec::with_capacity(code.len()-removed);
    for (pc,op) in code.iter().enumerate() {mapped[pc]=out.len();if !dead[pc] {out.push(op.clone());}}
    for op in &mut out {match op {
        Op::Jump{target}=>*target=mapped[*target],
        Op::Switch{cases,otherwise,..}=>{*otherwise=mapped[*otherwise];for (_,target) in cases {*target=mapped[*target];}},
        _=>{},
    }}
    *code=out;removed
}

#[cfg(test)]
#[path="scalar_promote_moves_tests.rs"]
mod tests;
