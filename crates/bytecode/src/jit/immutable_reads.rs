//! Observe only explicit known read addresses in immutable Program.data.
use super::*;
use std::cell::RefCell;
use serde::Serialize;
#[derive(Debug,PartialEq,Eq,Serialize)]
pub(super) struct Read { pub pc:usize, pub operation:&'static str, pub offset:usize, pub size:usize, pub value_le:[u8;16] }
thread_local! { static ACTIVE:RefCell<Option<Vec<Read>>>=const {RefCell::new(None)}; }
fn known(op:&Op,facts:&BTreeMap<Reg,Fact>,data:&[u8],pc:usize)->Option<Read> {
    let (r,size,operation)=match *op {
        Op::Load{address,size,..}=>(address,size as usize,"Load"),
        Op::Copy{src,size,..}=>(src,size,"Copy"),
        _=>return None,
    };
    if size==0 || size>16 {return None;}
    let Fact::Imm(value)=*facts.get(&r)? else {return None;};
    // Conservative full-width conversion. No numerical pointer guessing: the
    // value is already the source operand of this exact Load/Copy instruction.
    let offset=usize::try_from(value).ok()?;if offset==0 {return None;}
    let end=offset.checked_add(size)?;let bytes=data.get(offset..end)?;
    let mut value_le=[0;16];value_le[..size].copy_from_slice(bytes);
    Some(Read{pc,operation,offset,size,value_le})
}
pub(super) fn observe(op:&Op,facts:&BTreeMap<Reg,Fact>,data:&[u8],pc:usize) {
    ACTIVE.with(|s| {let mut s=s.borrow_mut();if let Some(rows)=s.as_mut() {
        if let Some(hit)=known(op,facts,data,pc) {assert!(rows.len()<1_000_000);rows.push(hit);}
    }});
}
struct Reset;
impl Drop for Reset {fn drop(&mut self){ACTIVE.with(|s|*s.borrow_mut()=None);}}
pub(super) fn capture<T>(f:impl FnOnce()->T)->(T,Vec<Read>) {
    ACTIVE.with(|s|{let mut s=s.borrow_mut();assert!(s.is_none());*s=Some(vec![]);});
    let reset=Reset;let result=f();let rows=ACTIVE.with(|s|s.borrow_mut().take().unwrap());drop(reset);(result,rows)
}
#[test]
fn exact_immutable_ranges_reject_null_heap_truncation_and_overflow() {
    let data:Vec<u8>=(0..64).collect();let mut facts=BTreeMap::new();
    for size in 1..=16 {
        facts.insert(0,Fact::Imm((64-size) as u128));
        let op=Op::Load{dst:1,address:0,size:size as u8};let hit=known(&op,&facts,&data,9).unwrap();
        assert_eq!(hit.pc,9);assert_eq!(&hit.value_le[..size],&data[64-size..]);assert!(hit.value_le[size..].iter().all(|b|*b==0));
        for offset in [0,65-size as u128,crate::heap::TAG as u128,u64::MAX as u128,(1u128<<64)+16,u128::MAX] {
            facts.insert(0,Fact::Imm(offset));assert!(known(&op,&facts,&data,9).is_none());
        }
    }
    facts.insert(0,Fact::Imm(16));
    for size in [0,17] {assert!(known(&Op::Copy{dst:1,src:0,size},&facts,&data,0).is_none());}
}
#[test]
fn only_explicit_constant_reads_are_observed_without_changing_facts() {
    let data=vec![7;64];let mut facts=BTreeMap::new();facts.insert(0,Fact::Imm(16));
    let op=Op::Copy{dst:1,src:0,size:8};observe(&op,&facts,&data,0);
    let (_,rows)=capture(|| {observe(&op,&facts,&data,7);observe(&Op::Store{address:0,src:0,size:8},&facts,&data,8);});
    assert_eq!(rows.len(),1);assert_eq!(rows[0].operation,"Copy");assert_eq!(rows[0].offset,16);
    assert!(matches!(facts[&0],Fact::Imm(16)));
    facts.insert(0,Fact::Local(16));assert!(known(&op,&facts,&data,0).is_none());facts.clear();assert!(known(&op,&facts,&data,0).is_none());
    assert!(std::panic::catch_unwind(||capture(||panic!("observer cleanup"))).is_err());
    assert!(capture(||()).1.is_empty());
}
