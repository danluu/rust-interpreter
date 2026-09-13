//! Exact, test-only spans for stores emitted by the existing flush rule.
//! Eligibility here is diagnostic; no store is removed.
use super::*;

#[derive(Debug, serde::Serialize)]
pub(super) struct Span {
    pub offset: usize,
    pub end: usize,
    pub region_start: usize,
    pub region_end: usize,
    pub register: Reg,
    pub fact: &'static str,
    pub analysis_available: bool,
    pub live_before: bool,
    pub live_after: bool,
    pub tail_consumed: bool,
    pub eligible: bool,
}

impl Assembler<'_> {
    pub(super) fn observe_flush_fact(&mut self, start: usize, end: usize, register: Reg, fact: Fact, offset: usize) {
        let analysis_available = self.values.is_some();
        let live_before = self.values.is_some_and(|v| v.live.at(end-1, register));
        let live_after = self.values.is_some_and(|v| v.live.after(end-1, register));
        let fact = match fact {
            Fact::Imm(_) => "Imm", Fact::Local(_) => "Local",
            Fact::Cached {..} => "Cached", Fact::Physical {..} => panic!("persistent pair cannot flush here"),
        };
        let native_end = self.words.len()*4;
        assert!(offset < native_end);
        self.flush_spans.push(Span { offset, end:native_end, region_start:start, region_end:end,
            register, fact, analysis_available, live_before, live_after,
            tail_consumed:self.flush_tail_consumed,
            eligible:analysis_available && self.flush_tail_consumed && live_before && !live_after });
    }
}

fn program(code: Vec<Op>) -> Program {
    Program { version:crate::VERSION, target:"aarch64-apple-darwin".into(), entry:0,
        data:vec![0;16], statics:vec![], thread_locals:vec![],
        functions:vec![Function { name:"flush observation".into(), frame_size:128, frame_align:16,
            registers:8, args:vec![crate::Slot {offset:16,size:8}],
            result:crate::Slot {offset:0,size:8}, code }] }
}

fn observe(p: &Program, persistent: bool) -> Vec<Span> {
    crate::validate(p).unwrap();
    let mut baseline = Jit::new_resumable(p, false, MAX_CODE_BYTES, persistent).unwrap();
    let mut observer = Jit::new_resumable(p, false, MAX_CODE_BYTES, persistent).unwrap();
    baseline.use_adopted_emission();
    observer.use_adopted_emission();
    observer.observe_flush = true;
    let a = baseline.emit_function_inner(&p.functions[0],MAX_CODE_BYTES/4,0,None).unwrap().unwrap();
    let b = observer.emit_function_inner(&p.functions[0],MAX_CODE_BYTES/4,0,None).unwrap().unwrap();
    assert_eq!(a.words,b.words); assert_eq!(a.operations,b.operations); assert_eq!(a.resumes,b.resumes);
    assert_eq!(a.assertions,b.assertions); assert!(a.flush_spans.is_empty());
    assert!(baseline.code.is_none() && observer.code.is_none()); assert_eq!(baseline.bytes+observer.bytes,0);
    b.flush_spans
}

#[test]
fn consumed_flush_observer_finds_final_store_inputs_without_changing_words() {
    let p = program(vec![Op::Local {dst:0,offset:16}, Op::Load {dst:1,address:0,size:8},
        Op::Local {dst:0,offset:0}, Op::Store {address:0,src:1,size:8}, Op::Return]);
    let rows = observe(&p,true);
    let registers: BTreeSet<_> = rows.iter().filter(|s| s.eligible).map(|s|s.register).collect();
    assert_eq!(registers, BTreeSet::from([0,1]));
    assert!(rows.iter().all(|s| s.region_start == 0 && s.region_end == 4 && s.tail_consumed));
    assert!(observe(&p,false).iter().all(|s| !s.eligible && !s.analysis_available));
}

#[test]
fn consumed_flush_observer_excludes_unexecuted_branch_operands() {
    let p = program(vec![Op::Local {dst:0,offset:16}, Op::Load {dst:1,address:0,size:8},
        Op::Switch {value:1,cases:vec![(0,3)],otherwise:7},
        Op::Imm {dst:2,value:9}, Op::Local {dst:0,offset:0}, Op::Store {address:0,src:2,size:8}, Op::Return,
        Op::Imm {dst:2,value:11}, Op::Local {dst:0,offset:0}, Op::Store {address:0,src:2,size:8}, Op::Return]);
    let rows = observe(&p,true);
    let branch = rows.iter().find(|s|s.region_start==0 && s.register==1).unwrap();
    assert!(branch.live_before && !branch.live_after && !branch.tail_consumed && !branch.eligible);
}

#[test]
fn consumed_flush_observer_retains_values_read_by_the_next_call() {
    let mut code: Vec<_> = (0..5).map(|dst| Op::Local {dst,offset:16+dst as usize*16}).collect();
    code.extend([Op::Load {dst:5,address:0,size:8}, Op::Store {address:4,src:5,size:8},
        Op::Call {function:1,args:vec![0,1,2,3,4],destination:4}, Op::Return]);
    let mut p = program(code);
    p.functions.push(Function { name:"reads caller slots".into(),frame_size:96,frame_align:16,registers:0,
        args:(0..5).map(|i|crate::Slot {offset:16+i*16,size:8}).collect(),
        result:crate::Slot {offset:0,size:8},code:vec![Op::Return] });
    let rows = observe(&p,true);
    assert!(rows.iter().any(|s|s.register==5 && s.eligible));
    let live: Vec<_> = rows.iter().filter(|s|s.live_after).collect();
    assert!(live.len()>=2);
    assert!(live.iter().all(|s|!s.eligible && s.tail_consumed));
}
