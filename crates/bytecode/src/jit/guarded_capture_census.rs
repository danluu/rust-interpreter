//! Disabled scope model: retain complete external payloads in four private slots.
use super::*;
use std::cell::RefCell;
use serde::Serialize;
const CAPACITY:usize=4;
#[derive(Clone,Debug)]
struct Cell {offset:usize,size:usize,origin:usize}
#[derive(Serialize)]
pub(super) struct Hit {pc:usize,region:usize,operation:&'static str,offset:usize,size:usize,origin:usize}
#[derive(Serialize)]
pub(super) struct Capture {pc:usize,region:usize,operation:&'static str,access:&'static str,offset:usize,size:usize}
#[derive(Default,Serialize)]
pub(super) struct Report {pub(super) reads:Vec<Hit>,pub(super) captures:Vec<Capture>}
thread_local! {static ACTIVE:RefCell<Option<Report>>=const {RefCell::new(None)};}
#[derive(Default)]
struct Model {cells:Vec<Cell>}
impl Model {
    fn find(&self,offset:usize,size:usize)->Option<usize> {
        self.cells.iter().find(|c|c.offset==offset && c.size==size).map(|c|c.origin)
    }
    fn write(&mut self,offset:usize,size:usize) {
        if size==0 {return;}
        let Some(end)=offset.checked_add(size) else {self.cells.clear();return;};
        self.cells.retain(|c|c.offset>=end || offset>=c.offset+c.size);
    }
    fn remember(&mut self,offset:usize,size:usize,origin:usize) {
        assert!([1,2,4,8].contains(&size));
        self.cells.retain(|c|c.offset!=offset || c.size!=size);
        if self.cells.len()==CAPACITY {self.cells.remove(0);}
        self.cells.push(Cell{offset,size,origin});
    }
}
pub(super) struct State {enabled:bool,model:Model}
impl State {
    pub(super) fn new()->Self {Self{enabled:ACTIVE.with(|s|s.borrow().is_some()),model:Model::default()}}
    fn remember(&mut self,a:&Assembler<'_>,operation:&'static str,access:&'static str,offset:usize,size:usize) {
        let origin=ACTIVE.with(|s| {let mut s=s.borrow_mut();let r=s.as_mut().unwrap();assert!(r.captures.len()<1_000_000);
            let id=r.captures.len();r.captures.push(Capture{pc:a.current_pc,region:a.region_start,operation,access,offset,size});id});
        self.model.remember(offset,size,origin);
    }
    pub(super) fn observe(&mut self,a:&Assembler<'_>,op:&Op) {
        if !self.enabled {return;}
        let Some(plan)=a.guarded_range.as_ref().filter(|p|p.frame_disjoint) else {self.model.cells.clear();return;};
        let offset=|r,size,write|plan.displacement(a.current_pc,r,size,write);
        let read=match *op {
            Op::Load{address,size,..} if [1,2,4,8].contains(&(size as usize))=>offset(address,size as usize,false).map(|o|(o,size as usize,"Load")),
            Op::Copy{src,size,..} if [1,2,4,8].contains(&size)=>offset(src,size,false).map(|o|(o,size,"Copy")),
            _=>None,
        };
        if let Some((off,size,operation))=read {
            if let Some(origin)=self.model.find(off,size) {
                ACTIVE.with(|s| {let mut s=s.borrow_mut();let r=s.as_mut().unwrap();assert!(r.reads.len()<1_000_000);
                    r.reads.push(Hit{pc:a.current_pc,region:a.region_start,operation,offset:off,size,origin});});
            } else {self.remember(a,operation,"source",off,size);}
        }
        let write=match *op {
            Op::Store{address,size,..}=>Some((address,size as usize,"Store")),
            Op::Copy{dst,size,..}=>Some((dst,size,"Copy")),
            Op::Imm{..}|Op::Local{..}|Op::Load{..}|Op::Binary{..}|Op::Unary{..}|Op::Cast{..}|Op::Select{..}
            |Op::Assert{..}|Op::CompareBytes{..}|Op::FloatBinary{..}|Op::FloatUnary{..}|Op::FloatConvert{..}=>None,
            _=>{self.model.cells.clear();None},
        };
        if let Some((reg,size,operation))=write {
            if size==0 || a.local_range(reg,size).is_some() {return;}
            if let Some(off)=offset(reg,size,true) {
                self.model.write(off,size);
                if [1,2,4,8].contains(&size) {self.remember(a,operation,"destination",off,size);}
            } else {self.model.cells.clear();}
        }
    }
}
struct Reset;
impl Drop for Reset {fn drop(&mut self){ACTIVE.with(|s|*s.borrow_mut()=None);}}
pub(super) fn capture<T>(f:impl FnOnce()->T)->(T,Report) {
    ACTIVE.with(|s|{let mut s=s.borrow_mut();assert!(s.is_none());*s=Some(Report::default());});
    let reset=Reset;let value=f();let r=ACTIVE.with(|s|s.borrow_mut().take().unwrap());drop(reset);(value,r)
}
#[test]
fn complete_payload_cache_matches_independent_byte_writes() {
    for width in [1,2,4,8] {for at in 0..24 {for size in [0,1,2,4,8] {
        let mut bytes:Vec<u8>=(0..40).collect();let captured=bytes[8..8+width].to_vec();
        let mut m=Model::default();m.remember(8,width,7);
        bytes[at..at+size].fill(255);m.write(at,size);
        if m.find(8,width).is_some() {assert_eq!(&bytes[8..8+width],captured.as_slice());}
        let overlap=size!=0 && at<8+width && 8<at+size;
        assert_eq!(m.find(8,width).is_none(),overlap);
    }}}
}
#[test]
fn four_slots_replacement_widths_and_capture_ownership_are_bounded() {
    let mut m=Model::default();for id in 0..5 {m.remember(id*8,8,id);}
    assert_eq!(m.cells.len(),4);assert_eq!(m.find(0,8),None);assert_eq!(m.find(8,8),Some(1));assert_eq!(m.find(8,4),None);
    m.remember(8,8,10);assert_eq!(m.cells.len(),4);assert_eq!(m.find(8,8),Some(10));
    m.write(usize::MAX,8);assert!(m.cells.is_empty());
    assert!(!State::new().enabled);assert!(State::new().model.cells.is_empty());
    assert!(std::panic::catch_unwind(||capture(||panic!("cleanup"))).is_err());assert!(capture(||()).1.reads.is_empty());
}
#[test]
fn register_eviction_keeps_captured_values_but_unknown_writes_and_regions_do_not() {
    let op=Op::Load{dst:1,address:0,size:8};
    let f=Function{name:"captured payload control".into(),frame_size:64,frame_align:8,registers:3,args:vec![],
        result:crate::Slot{offset:0,size:0},code:vec![op.clone();8]};
    let mut plan=range_groups::runtime_plan(&f,0,8,&mut 4_000_000).unwrap();plan.frame_disjoint=true;
    let mut a=Assembler{frame_size:64,guarded_range:Some(plan),..Assembler::default()};
    let (_,r)=capture(||{
        let mut s=State::new();s.observe(&a,&op);a.current_pc=1;s.observe(&a,&op);
        // No original register fact is available, yet the hypothetical capture lives.
        assert!(a.facts.is_empty());assert!(a.live_in.is_empty());assert!(a.words.is_empty());
        s.observe(&a,&Op::Store{address:2,src:1,size:8});assert!(s.model.cells.is_empty());
        a.current_pc=2;s.observe(&a,&op);a.current_pc=3;s.observe(&a,&op);
        let mut fresh=State::new();assert!(fresh.model.cells.is_empty());
        a.guarded_range.as_mut().unwrap().frame_disjoint=false;fresh.observe(&a,&op);s.observe(&a,&op);assert!(s.model.cells.is_empty());
    });
    assert_eq!(r.captures.len(),2);assert_eq!(r.reads.len(),2);
    assert_eq!((r.reads[0].origin,r.reads[1].origin),(0,1));
}
