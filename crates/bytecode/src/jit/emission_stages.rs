//! Disabled test-only host preparation timing; never samples guest execution.
use std::{cell::RefCell,time::Instant};
use serde::Serialize;
#[derive(Clone,Copy)]
#[repr(usize)]
pub(super) enum Stage { Function, Reads, Liveness, Fills, Slots, RegionsSetup, Regions, Transitions, Links }
const COUNT:usize=9;
#[derive(Clone,Default,Serialize)]
pub(super) struct Totals { pub calls:[u64;COUNT], pub nanos:[u128;COUNT] }
thread_local! { static ACTIVE:RefCell<Option<Totals>>=const { RefCell::new(None) }; }
pub(super) const LABELS:[&str;COUNT]=["function","read_registers","liveness","local_fills","call_slots","region_setup","regions","transitions","links"];
pub(super) struct Span { stage:Stage, started:Option<Instant> }
impl Span {
    pub(super) fn new(stage:Stage)->Self {
        Self {stage,started:ACTIVE.with(|s|s.borrow().is_some()).then(Instant::now)}
    }
}
impl Drop for Span {
    fn drop(&mut self) {
        if let Some(started)=self.started {
            let elapsed=started.elapsed().as_nanos();
            ACTIVE.with(|s| {let mut s=s.borrow_mut();let t=s.as_mut().expect("timing owner ended before span");
                t.calls[self.stage as usize]+=1;t.nanos[self.stage as usize]+=elapsed;});
        }
    }
}
struct Reset;
impl Drop for Reset {fn drop(&mut self){ACTIVE.with(|s|*s.borrow_mut()=None);}}
pub(super) fn capture<T>(f:impl FnOnce()->T)->(T,Totals) {
    ACTIVE.with(|s|{let mut s=s.borrow_mut();assert!(s.is_none(),"nested timing capture");*s=Some(Totals::default());});
    let reset=Reset;let result=f();let totals=ACTIVE.with(|s|s.borrow_mut().take().unwrap());drop(reset);(result,totals)
}
#[test]
fn disabled_and_scoped_accounting_restore_after_errors() {
    {let _span=Span::new(Stage::Reads);}
    let (_,totals)=capture(|| {let _all=Span::new(Stage::Function);for _ in 0..3 {let _part=Span::new(Stage::Reads);}});
    assert_eq!(totals.calls,[1,3,0,0,0,0,0,0,0]);assert!(totals.nanos[0]>=totals.nanos[1]);
    assert!(std::panic::catch_unwind(||capture(||panic!("timing control"))).is_err());
    let (value,totals)=capture(||7);assert_eq!(value,7);assert_eq!(totals.calls,[0;COUNT]);
}
#[test]
fn nested_capture_is_rejected_without_leaking_owner() {
    assert!(std::panic::catch_unwind(||capture(||capture(||()))).is_err());
    let (_,totals)=capture(|| {let _span=Span::new(Stage::Links);});assert_eq!(totals.calls[Stage::Links as usize],1);
}
