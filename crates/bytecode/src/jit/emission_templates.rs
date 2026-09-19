//! Test-only staging prototype. No cache is connected to guest execution.
use super::*;

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(super) enum Kind { Assertion(usize), Scalar(usize) }
#[derive(Clone,Debug)]
pub(super) struct Relocation {pub word:usize,pub words:usize,pub value:u64,pub kind:Kind}
pub(super) fn append(out:&mut Vec<Relocation>,relocations:Vec<Relocation>,base:usize) {
    out.extend(relocations.into_iter().map(|mut r|{r.word+=base;r}));
}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(super) struct ScalarInput {
    pub bytes:usize,pub maximum_steps:usize,pub success_steps:Option<usize>,pub target:usize,
}
impl ScalarInput {
    fn shape(self)->(usize,usize,Option<usize>) {(self.bytes,self.maximum_steps,self.success_steps)}
}

#[derive(Debug,PartialEq,Eq)]
struct Options {
    heap:bool,persistent:bool,scalar:bool,
    // Test-only emitter switches must never masquerade as default emission.
    test_flags:[bool;7],
}
impl Options {
    fn of(jit:&Jit<'_>)->Option<Self> {
        if jit.profiled || jit.native_call_stubs || jit.trees.is_some() || jit.resumable.is_none() {return None;}
        Some(Self {heap:jit.uses_heap,persistent:jit.persistent_registers,scalar:jit.scalar.is_some(),
            test_flags:[jit.disable_call_slot_hints,jit.observe_guarded_local_retention,jit.observe_static_local_facts,
                jit.observe_scalar_copy,jit.observe_scratch_locals,jit.scratch_values_enabled,jit.observe_memory_parts]})
    }
}

fn immediate(register:u32,value:u64)->Vec<u32> {
    let mut a=Assembler::default();a.imm(register,value);a.words
}
fn register(kind:Kind)->u32 {match kind {Kind::Assertion(_)=>0,Kind::Scalar(_)=>16}}

struct Template<'p> {
    program:&'p Program,function:usize,options:Options,
    words:Vec<u32>,entries:Vec<Option<Block>>,resumes:Vec<Option<usize>>,
    relocations:Vec<Relocation>,assertion_pcs:Vec<usize>,scalar_inputs:Vec<(usize,Option<ScalarInput>)>,
    operations:usize,register_pairs:usize,liveness_declined:bool,
}
impl<'p> Template<'p> {
    fn capture(jit:&Jit<'p>,id:usize,staged:&CompiledFunction<'_>)->Option<Self> {
        let options=Options::of(jit)?;let f=jit.program.functions.get(id)?;
        if staged.words.is_empty() || staged.words.len()>MAX_CODE_BYTES/4
            || staged.entries.len()!=f.code.len() || staged.resumes.len()!=f.code.len()+1
            || staged.template_assertion_pcs.len()!=staged.assertions.len() {return None;}
        for (pc,b) in staged.entries.iter().enumerate() {
            if let Some(b)=b {if b.offset%4!=0 || b.offset/4>=staged.words.len() || !(pc<b.end && b.end<=f.code.len()) {return None;}}
        }
        if staged.resumes.iter().flatten().any(|&w|w>=staged.words.len()) {return None;}
        for (&pc,assertion) in staged.template_assertion_pcs.iter().zip(&staged.assertions) {
            let Op::Assert{message,..}=f.code.get(pc)? else {return None;};
            if assertion.message!=message || assertion.function!=f.name || assertion.kind!=FaultKind::Assertion {return None;}
        }
        let mut ids=BTreeSet::new();
        for op in &f.code {if let Op::Call{function,..}=op {ids.insert(*function);}}
        let scalar_inputs=ids.into_iter().map(|id|(id,jit.template_scalar_input(id))).collect::<Vec<_>>();
        let mut assertion_ids=BTreeSet::new();let mut scalar_sites=0usize;let mut end=0;
        for r in &staged.template_relocations {
            if r.word<end || r.words==0 {return None;}
            end=r.word.checked_add(r.words)?;
            if staged.words.get(r.word..end)?!=immediate(register(r.kind),r.value) {return None;}
            match r.kind {
                Kind::Assertion(index)=>{
                    if index>=staged.assertions.len() || !assertion_ids.insert(index)
                        || assertion_code(jit.assertions.len(),index).ok()?!=r.value {return None;}
                },
                Kind::Scalar(id)=>{
                    if !scalar_inputs.iter().any(|(i,e)|*i==id && e.is_some_and(|e|e.target as u64==r.value)) {return None;}
                    if *staged.words.get(end)?!=0xd63f0200 {return None;} // the associated blr x16
                    scalar_sites+=1;
                },
            }
        }
        let expected_sites=f.code.iter().filter(|op|matches!(op,Op::Call{function,..} if jit.scalar_entry(*function).is_some())).count();
        if assertion_ids.len()!=staged.assertions.len() || scalar_sites!=expected_sites {return None;}
        Some(Self {program:jit.program,function:id,options,words:staged.words.clone(),entries:staged.entries.clone(),
            resumes:staged.resumes.clone(),relocations:staged.template_relocations.clone(),
            assertion_pcs:staged.template_assertion_pcs.clone(),scalar_inputs,
            operations:staged.operations,register_pairs:staged.register_pairs,liveness_declined:staged.liveness_declined})
    }

    fn restore(&self,jit:&Jit<'p>,id:usize)->Option<CompiledFunction<'p>> {
        if !std::ptr::eq(self.program,jit.program) || id!=self.function || Options::of(jit)?!=self.options {return None;}
        let f=jit.program.functions.get(id)?;
        if self.words.len()>jit.capacity.checked_sub(jit.bytes)?/4 || !jit.resumable.as_ref()?.fits(f.code.len()) {return None;}
        for &(id,old) in &self.scalar_inputs {
            if old.map(ScalarInput::shape)!=jit.template_scalar_input(id).map(ScalarInput::shape) {return None;}
        }
        let mut words=self.words.clone();let mut relocations=self.relocations.clone();
        for r in &mut relocations {
            let end=r.word.checked_add(r.words)?;
            if words.get(r.word..end)?!=immediate(register(r.kind),r.value) {return None;}
            let value=match r.kind {
                Kind::Assertion(index)=>assertion_code(jit.assertions.len(),index).ok()?,
                Kind::Scalar(id)=>jit.template_scalar_input(id)?.target as u64,
            };
            let patch=immediate(register(r.kind),value);
            // MOVK omission changes instruction count. A different shape misses
            // rather than moving branches or trying an unproved widening fixup.
            if patch.len()!=r.words {return None;}
            words.get_mut(r.word..end)?.copy_from_slice(&patch);r.value=value;
        }
        let mut assertions=vec![];
        for &pc in &self.assertion_pcs {
            let Op::Assert{message,..}=f.code.get(pc)? else {return None;};
            assertions.push(Assertion{message,function:&f.name,kind:FaultKind::Assertion});
        }
        Some(CompiledFunction {words,entries:self.entries.clone(),resumes:self.resumes.clone(),assertions,
            operations:self.operations,register_pairs:self.register_pairs,liveness_declined:self.liveness_declined,
            template_relocations:relocations,template_assertion_pcs:self.assertion_pcs.clone(),
            // These diagnostics are irrelevant to this staging-only prototype.
            local_forwarding:vec![],local_fact_events:vec![],scratch_hits:vec![],scratch_copy_hits:vec![],
            flush_spans:vec![],memory_spans:vec![],retained_local_writes:vec![]})
    }
}

fn fixture()->Program {
    use crate::Slot;
    let f=|name:&str,code:Vec<Op>|Function{name:name.into(),registers:4,frame_size:16,frame_align:8,
        args:vec![],result:Slot{offset:0,size:0},code};
    Program {version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![],statics:vec![],thread_locals:vec![],
        functions:vec![f("caller",vec![Op::Local{dst:0,offset:0},Op::Imm{dst:1,value:1},
            Op::Assert{value:1,expected:true,message:"first".into()},Op::Call{function:1,args:vec![],destination:0},
            Op::Assert{value:1,expected:true,message:"second".into()},Op::Call{function:1,args:vec![],destination:0},Op::Return]),
            f("leaf",vec![Op::Imm{dst:0,value:7},Op::Return])]}
}
fn owner(p:&Program)->Jit<'_> {
    crate::validate(p).unwrap();let mut j=Jit::new_resumable(p,false,MAX_CODE_BYTES,true).unwrap();
    j.enable_scalar_calls();j
}
fn stage<'a>(j:&Jit<'a>,id:usize)->CompiledFunction<'a> {j.emit_function(&j.program.functions[id],MAX_CODE_BYTES/4).unwrap().unwrap()}
fn scalar(j:&mut Jit<'_>,base:usize) {
    let mut work=crate::proof::MAX_GLOBAL_WORK;let memory=crate::proof::memory_plan(j.program,1,&mut work);
    let plan=crate::scalar_ir::lower(&j.program.functions[1],&memory,250_000).unwrap();
    let emitted=crate::scalar_ir::native_leaf::emit_call(&plan,false).unwrap();
    j.observe_saved_scalar_entry(1,0,emitted.words.len()*4,base);
}
fn assertions(j:&mut Jit<'_>,count:usize) {
    for _ in 0..count {j.assertions.push(Assertion{message:"preceding owner assertion",function:"other",kind:FaultKind::Assertion});}
}
fn same(a:&CompiledFunction<'_>,b:&CompiledFunction<'_>) {
    assert_eq!(a.words,b.words);assert_eq!(a.resumes,b.resumes);assert_eq!(a.assertions,b.assertions);
    assert_eq!(a.entries.iter().map(|e|e.map(|e|(e.offset,e.end))).collect::<Vec<_>>(),
        b.entries.iter().map(|e|e.map(|e|(e.offset,e.end))).collect::<Vec<_>>());
    assert_eq!((a.operations,a.register_pairs,a.liveness_declined),(b.operations,b.register_pairs,b.liveness_declined));
    assert_eq!(a.template_assertion_pcs,b.template_assertion_pcs);
}

#[test]
fn template_assertion_rebinding_matches_fresh_words_and_entry_metadata() {
    let p=fixture();let first=owner(&p);let old=stage(&first,0);let t=Template::capture(&first,0,&old).unwrap();
    assert_eq!(t.assertion_pcs,[2,4]);assert_eq!(t.relocations.len(),2);
    for count in [0,1,255,65536] {
        let mut next=owner(&p);assertions(&mut next,count);
        same(&t.restore(&next,0).unwrap(),&stage(&next,0));
        assert!(next.code.is_none() && next.bytes==0);
    }
}
#[test]
fn template_scalar_targets_and_assertions_rebind_together_without_code_publication() {
    let p=fixture();let mut first=owner(&p);scalar(&mut first,0x1_2345_1000);
    let t=Template::capture(&first,0,&stage(&first,0)).unwrap();
    assert_eq!(t.relocations.len(),4);
    let mut next=owner(&p);scalar(&mut next,0x2_3456_2000);assertions(&mut next,17);
    let restored=t.restore(&next,0).unwrap();same(&restored,&stage(&next,0));
    assert!(first.code.is_none() && next.code.is_none());
    let again=Template::capture(&next,0,&restored).unwrap();same(&again.restore(&first,0).unwrap(),&stage(&first,0));
}
#[test]
fn template_scalar_admission_changes_and_immediate_shape_changes_miss() {
    let p=fixture();let mut first=owner(&p);scalar(&mut first,0x1_2345_1000);
    let t=Template::capture(&first,0,&stage(&first,0)).unwrap();let absent=owner(&p);
    assert!(t.restore(&absent,0).is_none());
    let missing=Template::capture(&absent,0,&stage(&absent,0)).unwrap();assert!(missing.restore(&first,0).is_none());
    let mut different_width=owner(&p);scalar(&mut different_width,0x1000);
    assert!(t.restore(&different_width,0).is_none());
}
#[test]
fn template_other_program_function_or_options_never_share() {
    let p=fixture();let first=owner(&p);let t=Template::capture(&first,0,&stage(&first,0)).unwrap();
    let clone=p.clone();assert!(t.restore(&owner(&clone),0).is_none());assert!(t.restore(&first,1).is_none());
    for option in 0..6 {
        let mut other=owner(&p);
        match option {0=>other.profiled=true,1=>other.persistent_registers=false,2=>other.uses_heap=true,
            3=>other.native_call_stubs=true,4=>other.observe_static_local_facts=false,_=>other.scalar=None}
        assert!(t.restore(&other,0).is_none());
    }
}
#[test]
fn template_capacity_and_resume_table_limits_decline_without_mutation() {
    let p=fixture();let first=owner(&p);let t=Template::capture(&first,0,&stage(&first,0)).unwrap();
    let mut next=owner(&p);next.capacity=t.words.len()*4-1;
    assert!(t.restore(&next,0).is_none());assert!(next.blocks[0].is_empty() && next.assertions.is_empty());
    next.capacity=MAX_CODE_BYTES;next.bytes=MAX_CODE_BYTES-t.words.len()*4;
    assert!(t.restore(&next,0).is_some());next.bytes+=1;assert!(t.restore(&next,0).is_none());
    next.bytes=0;next.resumable.as_mut().unwrap().publish(1,vec![0;16*1024*1024/8]);
    assert!(t.restore(&next,0).is_none());assert!(next.code.is_none());
}
#[test]
fn template_relocation_records_reject_overlap_corruption_and_missing_sites() {
    let p=fixture();let mut first=owner(&p);scalar(&mut first,0x1_2345_1000);
    for damage in 0..5 {
        let mut staged=stage(&first,0);
        match damage {
            0=>staged.template_relocations[1].word=staged.template_relocations[0].word,
            1=>{let w=staged.template_relocations[0].word;staged.words[w]^=1;},
            2=>{staged.template_relocations.pop();},
            3=>staged.template_relocations[0].kind=Kind::Assertion(99),
            _=>staged.entries[0].as_mut().unwrap().offset=3,
        }
        assert!(Template::capture(&first,0,&staged).is_none());
    }
    let mut t=Template::capture(&first,0,&stage(&first,0)).unwrap();let w=t.relocations[0].word;t.words[w]^=1;
    assert!(t.restore(&first,0).is_none());
}
