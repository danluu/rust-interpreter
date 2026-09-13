//! Exact signature identities and stable, host-owned indirect-call layouts.
use crate::Program;
use std::cmp::Ordering;

const MAX_METADATA_BYTES: usize = 16 * 1024 * 1024;
pub(super) const MAX_ARGUMENTS: usize = 64;

#[repr(C)]
pub(super) struct Layout {
    pub signature: usize,
    pub frame_size: usize,
    pub align_add: usize,
    pub align_and: usize,
    pub registers: usize,
    pub arguments: *const usize,
    pub zeroes: usize,
    pub function: usize,
}

pub(super) const SIGNATURE: usize = std::mem::offset_of!(Layout, signature);
pub(super) const FRAME_SIZE: usize = std::mem::offset_of!(Layout, frame_size);
pub(super) const ALIGN_ADD: usize = std::mem::offset_of!(Layout, align_add);
pub(super) const ALIGN_AND: usize = std::mem::offset_of!(Layout, align_and);
pub(super) const REGISTERS: usize = std::mem::offset_of!(Layout, registers);
pub(super) const ARGUMENTS: usize = std::mem::offset_of!(Layout, arguments);
pub(super) const ZEROES: usize = std::mem::offset_of!(Layout, zeroes);
pub(super) const FUNCTION: usize = std::mem::offset_of!(Layout, function);
#[cfg(target_pointer_width = "64")]
const _: () = { assert!(std::mem::size_of::<Layout>() == 64); };

pub(super) struct Metadata<'a> {
    pub layouts: Vec<Layout>,
    // Own the allocation referenced by Layout::arguments; never grow it after publication.
    _offsets: Vec<usize>,
    // Sorted representative function IDs. Exact signatures are read from the immutable program.
    signatures: Vec<usize>,
    program: &'a Program,
}
fn compare_signature(program: &Program, a: usize, b: usize) -> Ordering {
    let a=&program.functions[a];let b=&program.functions[b];
    a.result.size.cmp(&b.result.size).then_with(||a.args.iter().map(|s|s.size).cmp(b.args.iter().map(|s|s.size)))
}
impl<'a> Metadata<'a> {
    /// The program and register-initialization proof have already been validated.
    pub fn new(program: &'a Program, zeroes: &[bool]) -> Option<Self> {
        Self::with_limit(program, zeroes, MAX_METADATA_BYTES)
    }
    fn with_limit(program: &'a Program, zeroes: &[bool], limit: usize) -> Option<Self> {
        if program.functions.len()!=zeroes.len() { return None; }
        let args=program.functions.iter().try_fold(0usize,|n,f|n.checked_add(f.args.len()))?;
        // Bound all requested vector payloads, including the retained sorting capacity.
        let bytes=program.functions.len().checked_mul(std::mem::size_of::<Layout>()+std::mem::size_of::<usize>())?
            .checked_add(args.checked_mul(std::mem::size_of::<usize>())?)?;
        if bytes>limit { return None; }
        let mut offsets=Vec::new();offsets.try_reserve_exact(args).ok()?;
        for f in &program.functions { offsets.extend(f.args.iter().map(|s|s.offset)); }
        let mut layouts=Vec::new();layouts.try_reserve_exact(program.functions.len()).ok()?;
        let mut start=0;
        for (id,f) in program.functions.iter().enumerate() {
            // All offsets were appended above. Moving either Vec owner does not move its allocation.
            let arguments=offsets.as_ptr().wrapping_add(start);start+=f.args.len();
            layouts.push(Layout { signature:0,frame_size:f.frame_size.max(1),align_add:f.frame_align-1,
                align_and:!(f.frame_align-1),registers:f.registers,arguments,
                zeroes:usize::from(zeroes[id]),function:id });
        }
        let mut signatures=Vec::new();signatures.try_reserve_exact(program.functions.len()).ok()?;
        signatures.extend(0..program.functions.len());
        signatures.sort_unstable_by(|&a,&b|compare_signature(program,a,b));
        let mut previous=None;let mut signature=0;
        for &id in &signatures {
            if previous.is_none_or(|prev|compare_signature(program,prev,id)!=Ordering::Equal) { signature+=1; }
            layouts[id].signature=signature;previous=Some(id);
        }
        signatures.dedup_by(|a,b|compare_signature(program,*a,*b)==Ordering::Equal);
        Some(Self {layouts,_offsets:offsets,signatures,program})
    }
    pub fn signature(&self, sizes: &[usize], result: usize) -> Option<usize> {
        if sizes.len()>MAX_ARGUMENTS { return None; }
        self.signatures.binary_search_by(|&id| {
            let f=&self.program.functions[id];
            f.result.size.cmp(&result).then_with(||f.args.iter().map(|s|s.size).cmp(sizes.iter().copied()))
        }).ok().map(|index|index+1)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Function,Op,Slot,VERSION};
    fn program() -> Program {
        let f=|offset,size,align,args:Vec<Slot>|Function { name:format!("{offset}:{size}:{align}"),
            frame_size:64,frame_align:align,registers:7,args,result:Slot {offset,size},code:vec![Op::Return] };
        Program {version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![],statics:vec![],thread_locals:vec![],
            functions:vec![f(0,8,8,vec![Slot{offset:8,size:8},Slot{offset:16,size:16}]),
                f(32,8,32,vec![Slot{offset:24,size:8},Slot{offset:40,size:16}]),
                f(0,8,8,vec![Slot{offset:8,size:16},Slot{offset:24,size:8}]),
                f(0,4,8,vec![Slot{offset:8,size:8},Slot{offset:16,size:16}]),
                f(0,0,1,vec![])]}
    }
    #[test]
    fn signatures_are_exact_while_layouts_remain_distinct() {
        let p=program();let m=Metadata::new(&p,&[false,true,false,false,false]).unwrap();
        assert_eq!(m.layouts[0].signature,m.layouts[1].signature);
        assert_ne!(m.layouts[0].signature,m.layouts[2].signature);
        assert_ne!(m.layouts[0].signature,m.layouts[3].signature);
        assert_eq!(m.signature(&[8,16],8),Some(m.layouts[0].signature));
        assert_eq!(m.signature(&[8],8),None);assert_eq!(m.signature(&[8,16],16),None);
        assert_eq!(m.signature(&[],0),Some(m.layouts[4].signature));
        for (id,(layout,f)) in m.layouts.iter().zip(&p.functions).enumerate() {
            assert_eq!(layout.function,id);assert_eq!(layout.frame_size,f.frame_size.max(1));
            assert_eq!(layout.align_add,f.frame_align-1);assert_eq!(layout.align_and,!(f.frame_align-1));
            assert_eq!(layout.registers,f.registers);assert_eq!(layout.zeroes,usize::from(id==1));
            // SAFETY: metadata owns the complete immutable offset allocation for its validated layout.
            let offsets=unsafe {std::slice::from_raw_parts(layout.arguments,f.args.len())};
            assert_eq!(offsets,f.args.iter().map(|s|s.offset).collect::<Vec<_>>());
        }
    }
    #[test]
    fn moved_metadata_preserves_owned_offsets_and_empty_arguments() {
        let p=program();let m=Metadata::new(&p,&[false;5]).unwrap();
        let pointers=m.layouts.iter().map(|s|s.arguments).collect::<Vec<_>>();let moved=Box::new(m);
        assert_eq!(pointers,moved.layouts.iter().map(|s|s.arguments).collect::<Vec<_>>());
        assert_eq!(unsafe {*moved.layouts[1].arguments},24);
        let mut empty=p;empty.functions=vec![empty.functions.pop().unwrap()];
        let empty=Metadata::new(&empty,&[false]).unwrap();assert!(empty._offsets.is_empty());
        assert_eq!(empty.signature(&[],0),Some(empty.layouts[0].signature));
    }
    #[test]
    fn metadata_declines_bounded_resources_and_unsupported_arity() {
        let p=program();let estimate=p.functions.len()*(std::mem::size_of::<Layout>()+std::mem::size_of::<usize>())+p.functions.iter().map(|f|f.args.len()).sum::<usize>()*std::mem::size_of::<usize>();
        assert!(Metadata::with_limit(&p,&[false;5],estimate-1).is_none());
        assert!(Metadata::with_limit(&p,&[false;5],estimate).is_some());
        assert!(Metadata::new(&p,&[false;4]).is_none());
        let mut p=p;p.functions[0].args=vec![Slot{offset:0,size:0};MAX_ARGUMENTS+1];
        let m=Metadata::new(&p,&[false;5]).unwrap();assert!(m.signature(&vec![0;MAX_ARGUMENTS+1],8).is_none());
        assert_eq!(m.signature(&[8,16],8),Some(m.layouts[1].signature));
    }
}
