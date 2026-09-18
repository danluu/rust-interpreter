//! Disabled observer of available values in an existing frame-disjoint range.
use super::*;
use std::cell::RefCell;
use serde::Serialize;
const MAX_VALUES:usize=16;
#[derive(Clone,Debug)]
struct Value { offset:usize,size:usize,source:Reg,origin:usize }
#[derive(Serialize)]
pub(super) struct Hit { pub pc:usize,pub operation:&'static str,pub offset:usize,pub size:usize,pub source:Reg,pub origin_pc:usize }
thread_local! {static ACTIVE:RefCell<Option<Vec<Hit>>>=const {RefCell::new(None)};}
#[derive(Clone,Copy)]
enum Write {None,Local,External(usize,usize),Unknown}
#[derive(Default)]
struct Model {values:Vec<Value>}
impl Model {
    fn find(&self,offset:usize,size:usize,available:impl Fn(Reg)->bool)->Option<Value> {
        self.values.iter().find(|v|v.offset==offset && v.size==size && available(v.source)).cloned()
    }
    fn write(&mut self,write:Write) {
        match write {
            Write::None|Write::Local=>{},
            Write::Unknown=>self.values.clear(),
            Write::External(offset,size)=> {let end=offset.checked_add(size).unwrap();
                if size!=0 {self.values.retain(|v|v.offset>=end || offset>=v.offset+v.size);}
            }
        }
    }
    fn forget(&mut self,r:Reg) {self.values.retain(|v|v.source!=r);}
    fn remember(&mut self,offset:usize,size:usize,source:Reg,origin:usize) {
        if ![1,2,4,8].contains(&size) {return;}
        self.values.retain(|v|v.offset!=offset || v.size!=size);
        if self.values.len()==MAX_VALUES {self.values.remove(0);}
        self.values.push(Value{offset,size,source,origin});
    }
}
pub(super) struct State {enabled:bool,model:Model}
impl State {
    pub(super) fn new()->Self {Self{enabled:ACTIVE.with(|s|s.borrow().is_some()),model:Model::default()}}
    pub(super) fn observe(&mut self,a:&Assembler<'_>,op:&Op) {
        if !self.enabled {return;}
        let Some(plan)=a.guarded_range.as_ref().filter(|p|p.frame_disjoint) else {self.model.values.clear();return;};
        // Use immutable plan queries, never guarded_displacement(), which would
        // add synthetic register live-ins to the ordinary emitter.
        let offset=|r,size,write|plan.displacement(a.current_pc,r,size,write);
        let write_to=|r,size|if size==0 {Write::None} else if a.local_range(r,size).is_some() {Write::Local}
            else {offset(r,size,true).map_or(Write::Unknown,|o|Write::External(o,size))};
        let mut read=None;let mut producer=None;let mut effect=Write::None;
        match *op {
            Op::Load{dst,address,size}=>if let Some(o)=offset(address,size as usize,false) {
                if [1,2,4,8].contains(&(size as usize)) {read=Some((o,size as usize,"Load"));producer=Some((o,size as usize,dst));}
            },
            Op::Store{address,src,size}=> {
                effect=write_to(address,size as usize);
                if let Some(o)=offset(address,size as usize,true) {
                    if a.facts.contains_key(&src) {producer=Some((o,size as usize,src));}
                }
            },
            Op::Copy{dst,src,size}=> {
                if [1,2,4,8].contains(&size) {read=offset(src,size,false).map(|o|(o,size,"Copy"));}
                effect=write_to(dst,size);
                if let Some(o)=offset(dst,size,true) {
                    let available=read.and_then(|(o,s,_)|self.model.find(o,s,|r|a.facts.contains_key(&r)))
                        .map(|v|v.source).or_else(||a.local_value(a.local_range(src,size),size).map(|(r,_)|r));
                    producer=available.map(|r|(o,size,r));
                }
            },
            Op::Imm{..}|Op::Local{..}|Op::Binary{..}|Op::Unary{..}|Op::Cast{..}|Op::Select{..}|Op::Assert{..}
            |Op::CompareBytes{..}|Op::FloatBinary{..}|Op::FloatUnary{..}|Op::FloatConvert{..}=>{},
            _=>effect=Write::Unknown,
        }
        if let Some((offset,size,operation))=read {
            if let Some(v)=self.model.find(offset,size,|r|a.facts.contains_key(&r)) {
                ACTIVE.with(|s| {let mut s=s.borrow_mut();let rows=s.as_mut().unwrap();assert!(rows.len()<1_000_000);
                    rows.push(Hit{pc:a.current_pc,operation,offset,size,source:v.source,origin_pc:v.origin});});
            }
        }
        self.model.write(effect);
        crate::registers::visit_registers(op,|_|{},|r|self.model.forget(r));
        if let Some((offset,size,r))=producer {self.model.remember(offset,size,r,a.current_pc);}
    }
}
struct Reset;
impl Drop for Reset {fn drop(&mut self){ACTIVE.with(|s|*s.borrow_mut()=None);}}
pub(super) fn capture<T>(f:impl FnOnce()->T)->(T,Vec<Hit>) {
    ACTIVE.with(|s|{let mut s=s.borrow_mut();assert!(s.is_none());*s=Some(vec![]);});
    let reset=Reset;let result=f();let rows=ACTIVE.with(|s|s.borrow_mut().take().unwrap());drop(reset);(result,rows)
}
#[test]
fn overlap_unknown_writes_and_unavailable_registers_remove_reuse() {
    let mut m=Model::default();m.remember(8,8,1,0);m.remember(24,8,2,1);
    assert!(m.find(8,8,|_|false).is_none());assert!(m.find(8,4,|_|true).is_none());
    m.write(Write::Local);m.write(Write::External(16,8));assert!(m.find(8,8,|_|true).is_some());
    m.write(Write::External(12,4));assert!(m.find(8,8,|_|true).is_none());assert!(m.find(24,8,|_|true).is_some());
    m.write(Write::External(25,0));assert!(m.find(24,8,|_|true).is_some());
    m.write(Write::Unknown);assert!(m.values.is_empty());
}
#[test]
fn register_writes_capacity_and_region_boundaries_invalidate_old_values() {
    let mut m=Model::default();m.remember(8,8,1,0);m.remember(24,8,1,1);m.forget(1);assert!(m.values.is_empty());
    for r in 0..17 {m.remember(r as usize*8,8,r,r as usize);}
    assert_eq!(m.values.len(),16);assert!(m.find(0,8,|_|true).is_none());assert!(m.find(8,8,|_|true).is_some());
    m.remember(128,8,99,20);assert_eq!(m.values.len(),16);assert_eq!(m.find(128,8,|_|true).unwrap().source,99);
    assert!(State::new().model.values.is_empty());assert!(!State::new().enabled);
    assert!(std::panic::catch_unwind(||capture(||panic!("cleanup"))).is_err());assert!(capture(||()).1.is_empty());
}

#[test]
fn only_active_disjoint_plans_record_hits_without_emitter_side_effects() {
    let mut a=Assembler{frame_size:64,..Assembler::default()};
    let op=Op::Load{dst:1,address:0,size:8};
    let f=Function{name:"observer plan control".into(),frame_size:64,frame_align:8,registers:2,
        args:vec![],result:crate::Slot{offset:0,size:0},code:vec![op.clone();8]};
    let mut plan=range_groups::runtime_plan(&f,0,8,&mut 4_000_000).unwrap();
    // Exercise the observer's disjointness gate; this unit control publishes or
    // executes no plan. Runtime reconstruction uses only the actual plan flag.
    plan.frame_disjoint=true;a.guarded_range=Some(plan);
    let (_,hits)=capture(|| {
        let mut state=State::new();state.observe(&a,&op);
        a.facts.insert(1,Fact::Imm(99));a.current_pc=1;state.observe(&a,&op);
        a.guarded_range.as_mut().unwrap().frame_disjoint=false;a.current_pc=2;state.observe(&a,&op);
        assert!(state.model.values.is_empty());assert!(a.live_in.is_empty());assert!(matches!(a.facts[&1],Fact::Imm(99)));
    });
    assert_eq!(hits.len(),1);assert_eq!((hits[0].pc,hits[0].origin_pc,hits[0].source,hits[0].offset),(1,0,1,0));
}
