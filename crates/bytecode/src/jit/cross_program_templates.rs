//! Test-only, trusted in-memory staging reuse. No persistence or publication.
use super::*;
use serde::Serialize;
use sha2::{Digest,Sha256};
use std::io::Write;

const MAX_KEY_BYTES:usize=4*1024*1024;
const MAX_CALL_SITES:usize=16_384;
const MAX_RETAINED:usize=64*1024*1024;

struct Checked<'p>(&'p Program);
impl<'p> Checked<'p> {
    fn new(p:&'p Program)->Option<Self> {
        if p.version & crate::PARTIAL_VALIDATION!=0 {return None;}
        crate::validate(p).ok()?;Some(Self(p))
    }
}
struct BoundedHash {hash:Sha256,bytes:usize,limit:usize}
impl Write for BoundedHash {
    fn write(&mut self,bytes:&[u8])->std::io::Result<usize> {
        let next=self.bytes.checked_add(bytes.len()).filter(|&n|n<=self.limit)
            .ok_or_else(||std::io::Error::other("template identity exceeds bound"))?;
        self.hash.update(bytes);self.bytes=next;Ok(bytes.len())
    }
    fn flush(&mut self)->std::io::Result<()> {Ok(())}
}
#[derive(Serialize)]
struct CallInput<'a> {
    id:usize,frame_size:usize,frame_align:usize,registers:usize,
    args:&'a [crate::Slot],result:&'a crate::Slot,
    scalar:Option<(usize,usize,Option<usize>,usize)>,
}
fn identity(checked:&Checked<'_>,jit:&Jit<'_>,id:usize,emitter:&[u8;32],limit:usize)->Option<[u8;32]> {
    if !std::ptr::eq(checked.0,jit.program) || jit.profiled || jit.native_call_stubs
        || jit.trees.is_some() || jit.resumable.is_none() || limit>MAX_KEY_BYTES {return None;}
    let f=jit.program.functions.get(id)?;
    if f.code.len()>500_000 || f.registers>65_536 {return None;}
    let mut ids=vec![];
    for op in &f.code {
        if let Op::Call{function,..}=op {
            if ids.len()==MAX_CALL_SITES {return None;}
            ids.try_reserve(1).ok()?;ids.push(*function);
        }
    }
    ids.sort_unstable();ids.dedup();
    let mut calls=vec![];calls.try_reserve_exact(ids.len()).ok()?;
    for id in ids {
        let c=jit.program.functions.get(id)?;
        calls.push(CallInput{id,frame_size:c.frame_size,frame_align:c.frame_align,registers:c.registers,
            args:&c.args,result:&c.result,scalar:jit.scalar_entry(id).map(|e|e.template_model_identity())});
    }
    let assertion_base=f.code.iter().any(|op|matches!(op,Op::Assert{..})).then_some(jit.assertions.len());
    let test_flags=[jit.disable_call_slot_hints,jit.observe_guarded_local_retention,jit.observe_static_local_facts,
        jit.observe_scalar_copy,jit.observe_scratch_locals,jit.scratch_values_enabled,jit.observe_flush,jit.observe_memory_parts];
    let context=(jit.program.version,&jit.program.target,jit.program.functions.len(),jit.uses_heap,
        jit.persistent_registers,jit.scalar.is_some(),test_flags,assertion_base);
    let mut sink=BoundedHash{hash:Sha256::new(),bytes:0,limit};
    bincode::serialize_into(&mut sink,&("cross-program-staging-model-v1",emitter,context,id,f,calls)).ok()?;
    Some(sink.hash.finalize().into())
}

struct Template {
    key:[u8;32],emitter:[u8;32],words:Vec<u32>,entries:Vec<Option<Block>>,resumes:Vec<Option<usize>>,
    assertion_pcs:Vec<usize>,operations:usize,register_pairs:usize,liveness_declined:bool,
}
impl Template {
    fn valid(&self,f:&Function)->bool {
        if self.words.is_empty() || self.words.len()>MAX_CODE_BYTES/4 || self.entries.len()!=f.code.len()
            || self.resumes.len()!=f.code.len()+1 {return false;}
        if self.entries.iter().enumerate().any(|(pc,b)|b.is_some_and(|b|
            b.offset%4!=0 || b.offset/4>=self.words.len() || !(pc<b.end && b.end<=f.code.len()))) {return false;}
        if self.resumes.iter().flatten().any(|&pc|pc>=self.words.len()) {return false;}
        self.assertion_pcs.iter().copied().eq(f.code.iter().enumerate().filter_map(|(pc,op)|matches!(op,Op::Assert{..}).then_some(pc)))
    }
    fn charge(&self)->Option<usize> {
        [self.words.capacity().checked_mul(4)?,self.entries.capacity().checked_mul(std::mem::size_of::<Option<Block>>())?,
            self.resumes.capacity().checked_mul(std::mem::size_of::<Option<usize>>())?,
            self.assertion_pcs.capacity().checked_mul(std::mem::size_of::<usize>())?]
            .into_iter().try_fold(std::mem::size_of::<Self>()+4*64,usize::checked_add)
    }
    fn capture(checked:&Checked<'_>,jit:&Jit<'_>,id:usize,emitter:[u8;32],staged:&CompiledFunction<'_>,limit:usize)->Option<Self> {
        if limit>MAX_RETAINED {return None;}
        let key=identity(checked,jit,id,&emitter,MAX_KEY_BYTES)?;
        let f=jit.program.functions.get(id)?;
        let minimum=staged.words.len().checked_mul(4)?
            .checked_add(staged.entries.len().checked_mul(std::mem::size_of::<Option<Block>>())?)?
            .checked_add(staged.resumes.len().checked_mul(std::mem::size_of::<Option<usize>>())?)?
            .checked_add(staged.assertions.len().checked_mul(std::mem::size_of::<usize>())?)?
            .checked_add(std::mem::size_of::<Self>()+4*64)?;
        if minimum>limit {return None;}
        let mut pcs=vec![];pcs.try_reserve_exact(staged.assertions.len()).ok()?;
        for (pc,op) in f.code.iter().enumerate() {
            if let Op::Assert{message,..}=op {
                let assertion=staged.assertions.get(pcs.len())?;
                if assertion.message!=message || assertion.function!=f.name || assertion.kind!=FaultKind::Assertion {return None;}
                pcs.push(pc);
            }
        }
        if pcs.len()!=staged.assertions.len() {return None;}
        fn copy<T:Clone>(items:&[T])->Option<Vec<T>> {
            let mut out=vec![];out.try_reserve_exact(items.len()).ok()?;out.extend_from_slice(items);Some(out)
        }
        let result=Self{key,emitter,words:copy(&staged.words)?,entries:copy(&staged.entries)?,resumes:copy(&staged.resumes)?,
            assertion_pcs:pcs,operations:staged.operations,register_pairs:staged.register_pairs,liveness_declined:staged.liveness_declined};
        (result.valid(f) && result.charge()?<=limit).then_some(result)
    }
    fn restore<'p>(&self,checked:&Checked<'p>,jit:&Jit<'p>,id:usize,emitter:&[u8;32],word_budget:usize)->Option<CompiledFunction<'p>> {
        if *emitter!=self.emitter || identity(checked,jit,id,emitter,MAX_KEY_BYTES)?!=self.key {return None;}
        let f=jit.program.functions.get(id)?;
        if !self.valid(f) || self.words.len()>word_budget || self.words.len()>jit.capacity.checked_sub(jit.bytes)?/4
            || !jit.resumable.as_ref()?.fits(f.code.len()) {return None;}
        let mut assertions=vec![];assertions.try_reserve_exact(self.assertion_pcs.len()).ok()?;
        for &pc in &self.assertion_pcs {
            let Op::Assert{message,..}=&f.code[pc] else {return None;};
            assertions.push(Assertion{message,function:&f.name,kind:FaultKind::Assertion});
        }
        fn copy<T:Clone>(items:&[T])->Option<Vec<T>> {
            let mut out=vec![];out.try_reserve_exact(items.len()).ok()?;out.extend_from_slice(items);Some(out)
        }
        Some(CompiledFunction{words:copy(&self.words)?,entries:copy(&self.entries)?,resumes:copy(&self.resumes)?,assertions,
            operations:self.operations,register_pairs:self.register_pairs,liveness_declined:self.liveness_declined,
            local_forwarding:vec![],local_fact_events:vec![],scratch_hits:vec![],scratch_copy_hits:vec![],
            flush_spans:vec![],memory_spans:vec![],retained_local_writes:vec![]})
    }
}

#[cfg(test)]
mod tests {
use super::*;
const EMITTER:[u8;32]=[17;32];
fn fixture()->Program {
    let f=|name:&str,code:Vec<Op>|Function{name:name.into(),frame_size:16,frame_align:8,registers:4,
        args:vec![],result:crate::Slot{offset:0,size:0},code};
    Program{version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![0;16],statics:vec![0;16],thread_locals:vec![],
        functions:vec![f("caller",vec![Op::Imm{dst:0,value:1},Op::Local{dst:1,offset:0},
            Op::Store{address:1,src:0,size:8},Op::Assert{value:0,expected:true,message:"current program assertion".into()},
            Op::Call{function:1,args:vec![],destination:1},Op::Load{dst:2,address:1,size:8},Op::Return]),
            f("leaf",vec![Op::Imm{dst:0,value:7},Op::Return])]}
}
fn owner(p:&Program)->Jit<'_> {Checked::new(p).unwrap();Jit::new_resumable(p,false,MAX_CODE_BYTES,true).unwrap()}
fn stage<'p>(j:&Jit<'p>,id:usize)->CompiledFunction<'p> {j.emit_function(&j.program.functions[id],MAX_CODE_BYTES/4).unwrap().unwrap()}
fn template(c:&Checked<'_>,j:&Jit<'_>,id:usize)->Template {Template::capture(c,j,id,EMITTER,&stage(j,id),MAX_RETAINED).unwrap()}
fn same(a:&CompiledFunction<'_>,b:&CompiledFunction<'_>) {
    assert_eq!(a.words,b.words);assert_eq!(a.resumes,b.resumes);assert_eq!(a.assertions,b.assertions);
    assert_eq!((a.operations,a.register_pairs,a.liveness_declined),(b.operations,b.register_pairs,b.liveness_declined));
    let entries=|e:&[Option<Block>]|e.iter().map(|b|b.map(|b|(b.offset,b.end))).collect::<Vec<_>>();
    assert_eq!(entries(&a.entries),entries(&b.entries));
}
#[test]
fn cross_program_template_new_initializers_and_callee_body_preserve_exact_caller_staging() {
    let p=fixture();let a=owner(&p);let c=Checked::new(&p).unwrap();let t=template(&c,&a,0);
    let mut q=p.clone();q.data[0]=99;q.statics[3]=17;q.functions[1].code[0]=Op::Imm{dst:0,value:9};
    let b=owner(&q);let d=Checked::new(&q).unwrap();let restored=t.restore(&d,&b,0,&EMITTER,MAX_CODE_BYTES/4).unwrap();
    same(&stage(&b,0),&restored);
    let Op::Assert{message,..}=&q.functions[0].code[3] else {panic!()};
    assert!(std::ptr::eq(restored.assertions[0].message.as_ptr(),message.as_ptr()));
    assert!(std::ptr::eq(restored.assertions[0].function.as_ptr(),q.functions[0].name.as_ptr()));
    assert!(a.code.is_none() && b.code.is_none());assert_eq!(a.bytes+b.bytes,0);
}
#[test]
fn cross_program_template_changed_body_layout_heap_options_and_emitter_miss() {
    let p=fixture();let a=owner(&p);let t=template(&Checked::new(&p).unwrap(),&a,0);
    for which in 0..6 {
        let mut q=p.clone();match which {
            0=>q.functions[0].code[0]=Op::Imm{dst:0,value:2},1=>q.functions[1].frame_size=32,
            2=>q.functions[1].registers=5,3=>q.statics.clear(),4=>q.functions[0].name.push('!'),_=>q.target.push('!')}
        let b=owner(&q);assert!(t.restore(&Checked::new(&q).unwrap(),&b,0,&EMITTER,MAX_CODE_BYTES/4).is_none());
    }
    let c=Checked::new(&p).unwrap();let mut b=owner(&p);b.disable_call_slot_hints=true;
    assert!(t.restore(&c,&b,0,&EMITTER,MAX_CODE_BYTES/4).is_none());
    b=Jit::new_resumable(&p,false,MAX_CODE_BYTES,false).unwrap();
    assert!(t.restore(&c,&b,0,&EMITTER,MAX_CODE_BYTES/4).is_none());
    assert!(t.restore(&c,&a,0,&[18;32],MAX_CODE_BYTES/4).is_none());
}
#[test]
fn cross_program_template_assertion_bases_are_explicit_and_assertion_free_bodies_ignore_them() {
    let p=fixture();let a=owner(&p);let c=Checked::new(&p).unwrap();let t=template(&c,&a,0);let leaf=template(&c,&a,1);
    let mut b=owner(&p);b.assertions.push(Assertion{message:"earlier",function:"other",kind:FaultKind::Assertion});
    assert!(t.restore(&c,&b,0,&EMITTER,MAX_CODE_BYTES/4).is_none());
    same(&stage(&b,1),&leaf.restore(&c,&b,1,&EMITTER,MAX_CODE_BYTES/4).unwrap());
}
#[test]
fn cross_program_template_key_storage_and_code_budgets_decline_before_publication() {
    let p=fixture();let mut a=owner(&p);let c=Checked::new(&p).unwrap();let staged=stage(&a,0);
    assert!(identity(&c,&a,0,&EMITTER,0).is_none());assert!(identity(&c,&a,0,&EMITTER,MAX_KEY_BYTES+1).is_none());
    assert!(Template::capture(&c,&a,0,EMITTER,&staged,0).is_none());
    assert!(Template::capture(&c,&a,0,EMITTER,&staged,MAX_RETAINED+1).is_none());
    let t=template(&c,&a,0);assert!(t.charge().unwrap()<=MAX_RETAINED);
    assert!(t.restore(&c,&a,0,&EMITTER,t.words.len()-1).is_none());
    same(&staged,&t.restore(&c,&a,0,&EMITTER,t.words.len()).unwrap());
    a.bytes=a.capacity;assert!(t.restore(&c,&a,0,&EMITTER,MAX_CODE_BYTES/4).is_none());assert!(a.code.is_none());
    let mut many=fixture();many.functions[0].code=vec![Op::Call{function:1,args:vec![],destination:0};MAX_CALL_SITES+1];
    many.functions[0].code.push(Op::Return);let b=owner(&many);
    assert!(identity(&Checked::new(&many).unwrap(),&b,0,&EMITTER,MAX_KEY_BYTES).is_none());
    many=fixture();many.functions[0].registers=65_537;let b=owner(&many);
    assert!(identity(&Checked::new(&many).unwrap(),&b,0,&EMITTER,MAX_KEY_BYTES).is_none());
}
fn scalar(j:&mut Jit<'_>,base:usize) {
    j.enable_scalar_calls();let mut work=crate::proof::MAX_GLOBAL_WORK;
    let memory=crate::proof::memory_plan(j.program,1,&mut work);
    let plan=crate::scalar_ir::lower(&j.program.functions[1],&memory,250_000).unwrap();
    let emitted=crate::scalar_ir::native_leaf::emit_call(&plan,false).unwrap();
    j.observe_saved_scalar_entry(1,0,emitted.words.len()*4,base);
}
#[test]
fn cross_program_template_scalar_target_admission_and_step_shape_are_identity_inputs() {
    let p=fixture();let mut a=owner(&p);scalar(&mut a,0x10000000);let c=Checked::new(&p).unwrap();let t=template(&c,&a,0);
    let mut q=p.clone();q.functions[1].code[0]=Op::Imm{dst:0,value:8};
    let mut b=owner(&q);scalar(&mut b,0x10000000);let d=Checked::new(&q).unwrap();
    same(&stage(&b,0),&t.restore(&d,&b,0,&EMITTER,MAX_CODE_BYTES/4).unwrap());
    let mut b=owner(&q);scalar(&mut b,0x20000000);assert!(t.restore(&d,&b,0,&EMITTER,MAX_CODE_BYTES/4).is_none());
    let mut b=owner(&q);b.enable_scalar_calls();assert!(t.restore(&d,&b,0,&EMITTER,MAX_CODE_BYTES/4).is_none());
    q.functions[1].code.insert(0,Op::Imm{dst:1,value:2});let mut b=owner(&q);scalar(&mut b,0x10000000);
    assert!(t.restore(&Checked::new(&q).unwrap(),&b,0,&EMITTER,MAX_CODE_BYTES/4).is_none());
    assert!(a.code.is_none() && b.code.is_none());
}
#[test]
fn cross_program_template_requires_the_checked_owner_and_supported_emission_mode() {
    let p=fixture();let q=p.clone();let a=owner(&p);let wrong=Checked::new(&q).unwrap();
    assert!(identity(&wrong,&a,0,&EMITTER,MAX_KEY_BYTES).is_none());
    let mut bad=p.clone();bad.version|=crate::PARTIAL_VALIDATION;assert!(Checked::new(&bad).is_none());
    bad=p.clone();bad.functions[0].code=vec![Op::Jump{target:999}];assert!(Checked::new(&bad).is_none());
    let c=Checked::new(&p).unwrap();let a=Jit::new_resumable(&p,true,MAX_CODE_BYTES,true).unwrap();
    assert!(identity(&c,&a,0,&EMITTER,MAX_KEY_BYTES).is_none());
    let a=Jit::new(&p,false,MAX_CODE_BYTES).unwrap();assert!(identity(&c,&a,0,&EMITTER,MAX_KEY_BYTES).is_none());
}
#[test]
fn cross_program_template_invalid_entry_resume_and_assertion_metadata_are_rejected() {
    let p=fixture();let a=owner(&p);let c=Checked::new(&p).unwrap();
    for which in 0..3 {
        let mut t=template(&c,&a,0);match which {
            0=>t.entries[0]=Some(Block{offset:t.words.len()*4,end:1}),
            1=>t.resumes[0]=Some(t.words.len()),_=>t.assertion_pcs[0]=usize::MAX}
        assert!(t.restore(&c,&a,0,&EMITTER,MAX_CODE_BYTES/4).is_none());
    }
    assert!(a.code.is_none());
}
#[test]
fn cross_program_template_branches_loops_and_persistent_options_match_fresh_staging() {
    for persistent in [false,true] {for heap in [false,true] {
        let mut p=fixture();if !heap {p.statics.clear();}
        p.functions[0].code=vec![Op::Imm{dst:0,value:1<<95},Op::Local{dst:1,offset:0},
            Op::Store{address:1,src:0,size:16},Op::Jump{target:4},Op::Load{dst:2,address:1,size:16},
            Op::Switch{value:2,cases:vec![(1,7)],otherwise:6},Op::Jump{target:4},
            Op::Assert{value:2,expected:true,message:"branch".into()},Op::Return];
        let a=Jit::new_resumable(&p,false,MAX_CODE_BYTES,persistent).unwrap();let c=Checked::new(&p).unwrap();let t=template(&c,&a,0);
        let mut q=p.clone();q.data[0]=7;let b=Jit::new_resumable(&q,false,MAX_CODE_BYTES,persistent).unwrap();let d=Checked::new(&q).unwrap();
        same(&stage(&b,0),&t.restore(&d,&b,0,&EMITTER,MAX_CODE_BYTES/4).unwrap());assert!(a.code.is_none() && b.code.is_none());
    }}
}
}
