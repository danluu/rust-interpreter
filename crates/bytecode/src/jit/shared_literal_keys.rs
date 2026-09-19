//! Share only normalized Function hashing within one immutable checked request.
use super::*;
use std::sync::OnceLock;

const MAX_FUNCTIONS:usize=65_536;
const MAX_BYTES:usize=4*1024*1024;

#[derive(Clone,Copy,Debug,PartialEq,Eq,Serialize)]
pub(super) struct BodyKey {digest:[u8;32],pub(super) bytes:usize}

pub(super) fn body(f:&Function)->Option<BodyKey> {
    if f.code.len()>500_000 || f.registers>65_536 {return None;}
    let selected=parameterized_literals::selected(f);
    let input=parameterized_literals::FunctionInput::new(f,&selected);
    let mut sink=BoundedHash::new(MAX_KEY_BYTES);
    bincode::serialize_into(&mut sink,&("normalized-function-literals-v1",&selected,input)).ok()?;
    let bytes=sink.bytes;Some(BodyKey{digest:sink.finish()?,bytes})
}

pub(crate) struct FunctionKeys {
    slots:Vec<OnceLock<Option<BodyKey>>>,
    #[cfg(test)] computations:std::sync::atomic::AtomicUsize,
}
impl FunctionKeys {
    pub(crate) fn new(count:usize)->Option<Self> {
        if count>MAX_FUNCTIONS {return None;}
        let overhead=std::mem::size_of::<Self>()+64;
        let unit=std::mem::size_of::<OnceLock<Option<BodyKey>>>();
        if count.checked_mul(unit)?.checked_add(overhead)?>MAX_BYTES {return None;}
        let mut slots=Vec::new();slots.try_reserve_exact(count).ok()?;
        if slots.capacity().checked_mul(unit)?.checked_add(overhead)?>MAX_BYTES {return None;}
        slots.resize_with(count,OnceLock::new);
        Some(Self{slots,#[cfg(test)] computations:std::sync::atomic::AtomicUsize::new(0)})
    }
    pub(super) fn get(&self,id:usize,f:&Function)->Option<BodyKey> {
        *self.slots.get(id)?.get_or_init(|| {
            #[cfg(test)] self.computations.fetch_add(1,std::sync::atomic::Ordering::Relaxed);
            body(f)
        })
    }
    #[cfg(test)]
    pub(super) fn computations(&self)->usize {self.computations.load(std::sync::atomic::Ordering::Relaxed)}
}
