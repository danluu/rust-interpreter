//! Exact test-only instruction ownership for small memory operations.
use super::*;

#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize)]
pub(super) struct Span {
    pub offset: usize,
    pub end: usize,
    pub region_start: usize,
    pub region_end: usize,
    pub pc: usize,
    pub operation: &'static str,
    pub size: usize,
    pub heap_enabled: bool,
    pub access: &'static str,
    pub part: &'static str,
}

pub(super) fn selected(op: &Op) -> Option<(&'static str, usize)> {
    match *op {
        Op::Load {size, ..} => Some(("Load", size as usize)),
        Op::Store {size, ..} => Some(("Store", size as usize)),
        Op::Copy {size, ..} if size <= 16 => Some(("Copy", size)),
        _ => None,
    }
}

pub(super) struct State {
    enabled: bool,
    active: Option<Span>,
    pub part: &'static str,
    pub access: &'static str,
    pub spans: Vec<Span>,
}

impl Default for State { fn default() -> Self { Self::new(false) } }

impl State {
    pub fn new(enabled: bool) -> Self {
        Self {enabled, active:None, part:"unclassified", access:"none", spans:vec![]}
    }
    pub fn begin(&mut self, op: &Op, pc: usize, start: usize, end: usize, heap: bool) {
        assert!(self.active.is_none());
        self.part="unclassified"; self.access="none";
        if !self.enabled { return; }
        if let Some((operation,size))=selected(op) {
            self.active=Some(Span {offset:0,end:0,region_start:start,region_end:end,pc,
                operation,size,heap_enabled:heap,access:self.access,part:self.part});
        }
    }
    pub fn finish(&mut self) { self.active=None; }
    pub fn word(&mut self, offset: usize) {
        let Some(context)=&self.active else { return; };
        if let Some(last)=self.spans.last_mut() {
            if last.end==offset && last.pc==context.pc && last.region_start==context.region_start
                && last.part==self.part && last.access==self.access {
                last.end+=4;
                return;
            }
        }
        assert!(self.spans.len()<2_000_000, "bounded diagnostic spans");
        let mut row=context.clone();row.offset=offset;row.end=offset+4;
        row.part=self.part;row.access=self.access;self.spans.push(row);
    }
}
