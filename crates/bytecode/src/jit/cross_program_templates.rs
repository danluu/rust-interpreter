//! Test-only, trusted in-memory staging reuse. No persistence or publication.
use super::*;
use serde::Serialize;
use sha2::{Digest,Sha256};
use std::io::Write;

const MAX_KEY_BYTES:usize=4*1024*1024;
const MAX_CALL_SITES:usize=16_384;
const MAX_RETAINED:usize=64*1024*1024;

#[path="cross_program_template_replay.rs"]
mod replay;

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(super) enum Kind { Assertion(usize), Scalar{function:usize,pc:usize} }
#[derive(Clone,Debug,PartialEq,Eq)]
pub(super) struct Relocation {pub word:usize,pub words:usize,pub value:u64,pub kind:Kind}
pub(super) fn append(out:&mut Vec<Relocation>,relocations:Vec<Relocation>,base:usize) {
    out.extend(relocations.into_iter().map(|mut r|{r.word+=base;r}));
}
fn immediate(kind:Kind,value:u64)->Vec<u32> {
    let mut a=Assembler::default();
    a.imm(match kind {Kind::Assertion(_)=>0,Kind::Scalar{..}=>16},value);a.words
}

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
// A private request computes identity once and keeps the exact current owner
// immutably borrowed through lookup, restore and emission/capture. Callers cannot
// supply a free-standing digest for a different owner/function/options tuple.
struct Request<'j,'p> {jit:&'j Jit<'p>,id:usize,emitter:[u8;32],key:[u8;32],rebind:bool}
struct Emission<'r,'j,'p> {request:&'r Request<'j,'p>,compiled:CompiledFunction<'p>}
impl<'j,'p> Request<'j,'p> {
    fn new(checked:&Checked<'p>,jit:&'j Jit<'p>,id:usize,emitter:[u8;32],rebind:bool)->Option<Self> {
        let key=identity_mode(checked,jit,id,&emitter,MAX_KEY_BYTES,rebind)?;
        Some(Self{jit,id,emitter,key,rebind})
    }
    fn emit(&self,word_budget:usize)->Result<Option<Emission<'_,'j,'p>>,EmitError> {
        Ok(self.jit.emit_function(&self.jit.program.functions[self.id],word_budget)?
            .map(|compiled|Emission{request:self,compiled}))
    }
}
fn identity(checked:&Checked<'_>,jit:&Jit<'_>,id:usize,emitter:&[u8;32],limit:usize)->Option<[u8;32]> {
    identity_mode(checked,jit,id,emitter,limit,false)
}
fn identity_mode(checked:&Checked<'_>,jit:&Jit<'_>,id:usize,emitter:&[u8;32],limit:usize,rebind:bool)->Option<[u8;32]> {
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
            args:&c.args,result:&c.result,scalar:jit.scalar_entry(id).map(|e|{
                let (bytes,maximum,success,target)=e.template_model_identity();
                (bytes,maximum,success,if rebind {0} else {target})
            })});
    }
    let assertion_base=(!rebind && f.code.iter().any(|op|matches!(op,Op::Assert{..}))).then_some(jit.assertions.len());
    let test_flags=[jit.disable_call_slot_hints,jit.observe_guarded_local_retention,jit.observe_static_local_facts,
        jit.observe_scalar_copy,jit.observe_scratch_locals,jit.scratch_values_enabled,jit.observe_flush,jit.observe_memory_parts];
    let context=(jit.program.version,&jit.program.target,jit.program.functions.len(),jit.uses_heap,
        jit.persistent_registers,jit.scalar.is_some(),test_flags,assertion_base);
    let mut sink=BoundedHash{hash:Sha256::new(),bytes:0,limit};
    bincode::serialize_into(&mut sink,&("cross-program-staging-model-v2",rebind,emitter,context,id,f,calls)).ok()?;
    Some(sink.hash.finalize().into())
}

struct Template {
    key:[u8;32],emitter:[u8;32],words:Vec<u32>,entries:Vec<Option<Block>>,resumes:Vec<Option<usize>>,
    assertion_pcs:Vec<usize>,operations:usize,register_pairs:usize,liveness_declined:bool,
    relocations:Vec<Relocation>,assertion_base:usize,rebind:bool,
}

// Private bounded in-memory history for the diagnostic model. The two ordered
// maps retain at most one recency record per template; repeated hits cannot
// grow an append-only eviction queue. Charges bound declared retained payload
// and node slack, not allocator RSS. No file or process interface exists.
const HISTORY_BASE:usize=512;
const HISTORY_NODE:usize=256;
struct History {
    entries:BTreeMap<[u8;32],(Template,u64,usize)>,order:BTreeMap<u64,[u8;32]>,
    charge:usize,limit:usize,clock:u64,evictions:usize,
}
impl History {
    fn new(limit:usize)->Option<Self> {
        (HISTORY_BASE..=MAX_RETAINED).contains(&limit).then(||Self{
            entries:BTreeMap::new(),order:BTreeMap::new(),charge:HISTORY_BASE,limit,clock:0,evictions:0})
    }
    fn get(&mut self,key:&[u8;32])->Option<&Template> {
        let next=self.clock.checked_add(1)?;let entry=self.entries.get_mut(key)?;
        assert_eq!(self.order.remove(&entry.1),Some(*key));entry.1=next;self.clock=next;
        assert!(self.order.insert(next,*key).is_none());Some(&entry.0)
    }
    fn insert(&mut self,template:Template)->Option<()> {
        let charge=template.charge()?.checked_add(HISTORY_NODE)?;
        if charge>self.limit-HISTORY_BASE {return None;}
        let next=self.clock.checked_add(1)?;let key=template.key;
        if let Some((_,stamp,old_charge))=self.entries.remove(&key) {
            assert_eq!(self.order.remove(&stamp),Some(key));self.charge-=old_charge;
        }
        while self.charge.checked_add(charge)?>self.limit || self.entries.len()>=16_384 {
            let (stamp,old)=self.order.pop_first()?;let (_,recorded,removed)=self.entries.remove(&old)?;
            assert_eq!(recorded,stamp);self.charge-=removed;self.evictions+=1;
        }
        self.clock=next;self.charge+=charge;
        assert!(self.order.insert(next,key).is_none());assert!(self.entries.insert(key,(template,next,charge)).is_none());
        Some(())
    }
}
impl Template {
    fn valid_relocations(&self,f:&Function,jit:&Jit<'_>,capture:bool)->Option<()> {
        // Expected sites come from the complete checked caller and current scalar
        // admission. Per-call PCs reject missing/duplicated/misassociated sites.
        let mut expected=f.code.iter().enumerate().filter_map(|(pc,op)|match op {
            Op::Call{function,..} if jit.scalar_entry(*function).is_some()=>Some((pc,*function)),_=>None,
        });
        let mut assertion=0;let mut end=0;
        for r in &self.relocations {
            if r.word<end || !(1..=4).contains(&r.words) {return None;}
            end=r.word.checked_add(r.words)?;
            if self.words.get(r.word..end)?!=immediate(r.kind,r.value) {return None;}
            match r.kind {
                Kind::Assertion(index)=>{
                    if index!=assertion || index>=self.assertion_pcs.len()
                        || assertion_code(self.assertion_base,index).ok()?!=r.value {return None;}
                    assertion+=1;
                },
                Kind::Scalar{function,pc}=>{
                    if expected.next()!=Some((pc,function)) || *self.words.get(end)?!=0xd63f0200 {return None;}
                    if capture && jit.scalar_entry(function)?.template_model_identity().3 as u64!=r.value {return None;}
                },
            }
        }
        (assertion==self.assertion_pcs.len() && expected.next().is_none()).then_some(())
    }
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
            self.assertion_pcs.capacity().checked_mul(std::mem::size_of::<usize>())?,
            self.relocations.capacity().checked_mul(std::mem::size_of::<Relocation>())?]
            .into_iter().try_fold(std::mem::size_of::<Self>()+5*64,usize::checked_add)
    }
    fn capture(checked:&Checked<'_>,jit:&Jit<'_>,id:usize,emitter:[u8;32],staged:&CompiledFunction<'_>,limit:usize)->Option<Self> {
        Self::capture_mode(checked,jit,id,emitter,staged,limit,false)
    }
    fn capture_mode(checked:&Checked<'_>,jit:&Jit<'_>,id:usize,emitter:[u8;32],staged:&CompiledFunction<'_>,limit:usize,rebind:bool)->Option<Self> {
        let request=Request::new(checked,jit,id,emitter,rebind)?;
        Self::capture_request(&request,staged,limit)
    }
    fn capture_emission(emission:&Emission<'_,'_,'_>,limit:usize)->Option<Self> {
        Self::capture_request(emission.request,&emission.compiled,limit)
    }
    fn capture_request(request:&Request<'_,'_>,staged:&CompiledFunction<'_>,limit:usize)->Option<Self> {
        if limit>MAX_RETAINED {return None;}
        let Request{jit,id,emitter,key,rebind}=*request;
        let f=jit.program.functions.get(id)?;
        let minimum=staged.words.len().checked_mul(4)?
            .checked_add(staged.entries.len().checked_mul(std::mem::size_of::<Option<Block>>())?)?
            .checked_add(staged.resumes.len().checked_mul(std::mem::size_of::<Option<usize>>())?)?
            .checked_add(staged.assertions.len().checked_mul(std::mem::size_of::<usize>())?)?
            .checked_add(staged.model_relocations.len().checked_mul(std::mem::size_of::<Relocation>())?)?
            .checked_add(std::mem::size_of::<Self>()+5*64)?;
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
            assertion_pcs:pcs,operations:staged.operations,register_pairs:staged.register_pairs,liveness_declined:staged.liveness_declined,
            relocations:copy(&staged.model_relocations)?,assertion_base:jit.assertions.len(),rebind};
        result.valid_relocations(f,jit,true)?;
        (result.valid(f) && result.charge()?<=limit).then_some(result)
    }
    fn restore<'p>(&self,checked:&Checked<'p>,jit:&Jit<'p>,id:usize,emitter:&[u8;32],word_budget:usize)->Option<CompiledFunction<'p>> {
        let request=Request::new(checked,jit,id,*emitter,self.rebind)?;
        self.restore_request(&request,word_budget)
    }
    fn restore_request<'p>(&self,request:&Request<'_,'p>,word_budget:usize)->Option<CompiledFunction<'p>> {
        let Request{jit,id,emitter,key,rebind}=*request;
        if emitter!=self.emitter || key!=self.key || rebind!=self.rebind {return None;}
        let f=jit.program.functions.get(id)?;
        if !self.valid(f) || self.words.len()>word_budget || self.words.len()>jit.capacity.checked_sub(jit.bytes)?/4
            || !jit.resumable.as_ref()?.fits(f.code.len()) {return None;}
        self.valid_relocations(f,jit,false)?;
        let mut assertions=vec![];assertions.try_reserve_exact(self.assertion_pcs.len()).ok()?;
        for &pc in &self.assertion_pcs {
            let Op::Assert{message,..}=&f.code[pc] else {return None;};
            assertions.push(Assertion{message,function:&f.name,kind:FaultKind::Assertion});
        }
        fn copy<T:Clone>(items:&[T])->Option<Vec<T>> {
            let mut out=vec![];out.try_reserve_exact(items.len()).ok()?;out.extend_from_slice(items);Some(out)
        }
        let mut words=copy(&self.words)?;let mut model_relocations=copy(&self.relocations)?;
        for r in &mut model_relocations {
            let value=match r.kind {
                Kind::Assertion(index)=>assertion_code(jit.assertions.len(),index).ok()?,
                Kind::Scalar{function,..}=>jit.scalar_entry(function)?.template_model_identity().3 as u64,
            };
            if !self.rebind && value!=r.value {return None;}
            let replacement=immediate(r.kind,value);
            if replacement.len()!=r.words {return None;}
            words[r.word..r.word+r.words].copy_from_slice(&replacement);r.value=value;
        }
        Some(CompiledFunction{words,model_relocations,entries:copy(&self.entries)?,resumes:copy(&self.resumes)?,assertions,
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
pub(super) fn same(a:&CompiledFunction<'_>,b:&CompiledFunction<'_>) {
    assert_eq!(a.words,b.words);assert_eq!(a.resumes,b.resumes);assert_eq!(a.assertions,b.assertions);
    assert_eq!(a.model_relocations,b.model_relocations);
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
    j.enable_scalar_calls();scalar_at(j,1,base);
}
fn scalar_at(j:&mut Jit<'_>,id:usize,base:usize) {
    let mut work=crate::proof::MAX_GLOBAL_WORK;
    let memory=crate::proof::memory_plan(j.program,id,&mut work);
    let plan=crate::scalar_ir::lower(&j.program.functions[id],&memory,250_000).unwrap();
    let emitted=crate::scalar_ir::native_leaf::emit_call(&plan,false).unwrap();
    j.observe_saved_scalar_entry(id,0,emitted.words.len()*4,base);
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

fn relocatable(c:&Checked<'_>,j:&Jit<'_>)->Template {
    Template::capture_mode(c,j,0,EMITTER,&stage(j,0),MAX_RETAINED,true).unwrap()
}
fn prior_assertions(j:&mut Jit<'_>,count:usize) {
    for _ in 0..count {j.assertions.push(Assertion{message:"prior",function:"other",kind:FaultKind::Assertion});}
}
#[test]
fn cross_program_template_rebinding_records_every_site_and_matches_fresh_staging() {
    let mut p=fixture();p.functions.push(p.functions[1].clone());p.functions[2].name="second leaf".into();
    p.functions[0].code.pop();
    p.functions[0].code.extend([Op::Assert{value:0,expected:false,message:"second assertion".into()},
        Op::Call{function:2,args:vec![],destination:1},Op::Call{function:1,args:vec![],destination:1},Op::Return]);
    let mut a=owner(&p);scalar(&mut a,0x123456780000);scalar_at(&mut a,2,0x123456780000);prior_assertions(&mut a,2);
    let c=Checked::new(&p).unwrap();let t=relocatable(&c,&a);assert_eq!(t.relocations.len(),5);
    let mut q=p.clone();q.data[0]=8;q.statics[0]=9;q.functions[1].code[0]=Op::Imm{dst:0,value:8};
    let mut b=owner(&q);scalar(&mut b,0x234567890000);scalar_at(&mut b,2,0x3456789a0000);prior_assertions(&mut b,7);
    let d=Checked::new(&q).unwrap();let fresh=stage(&b,0);
    let restored=t.restore(&d,&b,0,&EMITTER,MAX_CODE_BYTES/4).unwrap();same(&fresh,&restored);
    assert_ne!(t.words,restored.words);
    for (i,(&old,&new)) in t.words.iter().zip(&restored.words).enumerate() {
        if old!=new {assert!(t.relocations.iter().any(|r|r.word<=i && i<r.word+r.words));}
    }
    for (&pc,assertion) in t.assertion_pcs.iter().zip(&restored.assertions) {
        let Op::Assert{message,..}=&q.functions[0].code[pc] else {panic!()};
        assert!(std::ptr::eq(message.as_ptr(),assertion.message.as_ptr()));
    }
    let recaptured=Template::capture_mode(&d,&b,0,EMITTER,&restored,MAX_RETAINED,true).unwrap();
    same(&stage(&a,0),&recaptured.restore(&c,&a,0,&EMITTER,MAX_CODE_BYTES/4).unwrap());
    assert!(a.code.is_none() && b.code.is_none());assert_eq!(a.bytes+b.bytes,0);
}
#[test]
fn cross_program_template_rebinding_width_changes_decline_without_mutating_template() {
    let p=fixture();let mut a=owner(&p);scalar(&mut a,0x10000000);
    let t=relocatable(&Checked::new(&p).unwrap(),&a);let before=t.words.clone();
    let q=p.clone();let mut b=owner(&q);scalar(&mut b,0x123456780000);let c=Checked::new(&q).unwrap();
    assert_eq!(identity_mode(&c,&b,0,&EMITTER,MAX_KEY_BYTES,true).unwrap(),t.key);
    assert!(t.restore(&c,&b,0,&EMITTER,MAX_CODE_BYTES/4).is_none());assert_eq!(t.words,before);
    assert!(a.code.is_none() && b.code.is_none());assert_eq!(b.bytes,0);
}
#[test]
fn cross_program_template_rebinding_rejects_incomplete_overlapping_and_wrong_ledgers() {
    let mut p=fixture();p.functions.push(p.functions[1].clone());
    let mut a=owner(&p);scalar(&mut a,0x123456780000);scalar_at(&mut a,2,0x123456780000);
    let c=Checked::new(&p).unwrap();let original=stage(&a,0);assert_eq!(original.model_relocations.len(),2);
    for which in 0..9 {
        let mut t=relocatable(&c,&a);
        match which {
            0=>{t.relocations.pop();},1=>{t.relocations.remove(0);},
            2=>t.relocations[1].word=t.relocations[0].word,
            3=>t.relocations[1].value^=0x10000,
            4=>{let end=t.relocations[1].word+t.relocations[1].words;t.words[end]=0;},
            5=>t.relocations[1].kind=Kind::Scalar{function:2,pc:4},
            6=>t.relocations[1].kind=Kind::Scalar{function:1,pc:5},
            7=>t.relocations[0].kind=Kind::Assertion(1),
            _=>t.relocations[1].words=usize::MAX,
        }
        assert!(t.restore(&c,&a,0,&EMITTER,MAX_CODE_BYTES/4).is_none(),"case {which}");
        let mut staged=stage(&a,0);staged.model_relocations=t.relocations;staged.words=t.words;
        assert!(Template::capture_mode(&c,&a,0,EMITTER,&staged,MAX_RETAINED,true).is_none(),"capture {which}");
    }
    // A self-consistent immediate for a different target is still not an
    // admissible capture from this owner, even if the instruction width agrees.
    let mut staged=stage(&a,0);let r=&mut staged.model_relocations[1];r.value=0x234567890000;
    staged.words[r.word..r.word+r.words].copy_from_slice(&immediate(r.kind,r.value));
    assert!(Template::capture_mode(&c,&a,0,EMITTER,&staged,MAX_RETAINED,true).is_none());
    assert!(a.code.is_none());
}
#[test]
fn cross_program_template_rebinding_keeps_body_layout_admission_and_budget_dependencies() {
    let p=fixture();let mut a=owner(&p);scalar(&mut a,0x123456780000);
    let c=Checked::new(&p).unwrap();let t=relocatable(&c,&a);
    assert_ne!(t.key,identity(&c,&a,0,&EMITTER,MAX_KEY_BYTES).unwrap());
    for which in 0..5 {
        let mut q=p.clone();match which {
            0=>q.functions[0].code[0]=Op::Imm{dst:0,value:2},
            1=>q.functions[1].frame_size=32,2=>q.functions[1].registers=5,
            3=>q.functions[1].code.insert(0,Op::Imm{dst:1,value:2}),_=>(),
        }
        let mut b=owner(&q);if which==4 {b.enable_scalar_calls();} else {scalar(&mut b,0x234567890000);}
        let d=Checked::new(&q).unwrap();assert!(t.restore(&d,&b,0,&EMITTER,MAX_CODE_BYTES/4).is_none());
    }
    let q=p.clone();let mut b=owner(&q);scalar(&mut b,0x234567890000);let d=Checked::new(&q).unwrap();
    assert!(t.restore(&d,&b,0,&EMITTER,t.words.len()-1).is_none());
    same(&stage(&b,0),&t.restore(&d,&b,0,&EMITTER,t.words.len()).unwrap());
    b.bytes=b.capacity;assert!(t.restore(&d,&b,0,&EMITTER,MAX_CODE_BYTES/4).is_none());assert!(b.code.is_none());
}

#[test]
fn cross_program_template_history_bounds_recency_replacement_and_declines() {
    let p=fixture();let a=owner(&p);let c=Checked::new(&p).unwrap();
    let item=template(&c,&a,0).charge().unwrap()+HISTORY_NODE;
    let make=|key|{let mut t=template(&c,&a,0);t.key=[key;32];t};
    let mut h=History::new(HISTORY_BASE+2*item).unwrap();
    h.insert(make(1)).unwrap();h.insert(make(2)).unwrap();
    for _ in 0..1000 {assert!(h.get(&[1;32]).is_some());}
    assert_eq!(h.order.len(),2);assert_eq!(h.charge,HISTORY_BASE+2*item);
    h.insert(make(3)).unwrap();assert_eq!(h.evictions,1);
    assert!(h.get(&[2;32]).is_none());assert!(h.get(&[1;32]).is_some());
    h.insert(make(1)).unwrap();assert_eq!(h.entries.len(),2);assert_eq!(h.order.len(),2);
    assert_eq!(h.charge,HISTORY_BASE+2*item);assert_eq!(h.evictions,1);
    let mut small=History::new(HISTORY_BASE+item-1).unwrap();assert!(small.insert(make(4)).is_none());
    assert_eq!(small.charge,HISTORY_BASE);assert!(small.entries.is_empty() && small.order.is_empty());
    h.clock=u64::MAX;assert!(h.get(&[1;32]).is_none());assert!(h.insert(make(4)).is_none());
    assert_eq!(h.entries.len(),2);assert_eq!(h.order.len(),2);
    assert!(History::new(0).is_none() && History::new(MAX_RETAINED+1).is_none());
}
#[test]
fn cross_program_template_history_reuses_checked_body_variants_with_fresh_owner_values() {
    let mut history=History::new(MAX_RETAINED).unwrap();let mut hits=0;
    for (iteration,value) in [1,2,1,2].into_iter().enumerate() {
        let mut p=fixture();p.functions[0].code[0]=Op::Imm{dst:0,value};
        let c=Checked::new(&p).unwrap();let mut j=owner(&p);
        scalar(&mut j,0x123456780000+iteration*4096);prior_assertions(&mut j,iteration);
        let key=identity_mode(&c,&j,0,&EMITTER,MAX_KEY_BYTES,true).unwrap();let fresh=stage(&j,0);
        if let Some(t)=history.get(&key) {
            same(&fresh,&t.restore(&c,&j,0,&EMITTER,MAX_CODE_BYTES/4).unwrap());hits+=1;
        } else {history.insert(relocatable(&c,&j)).unwrap();}
        assert!(j.code.is_none());assert_eq!(j.bytes,0);
    }
    assert_eq!(hits,2);assert_eq!(history.entries.len(),2);assert_eq!(history.order.len(),2);
}

#[test]
fn cross_program_template_bound_request_emission_and_restore_keep_exact_current_identity() {
    let p=fixture();let mut a=owner(&p);scalar(&mut a,0x123456780000);let c=Checked::new(&p).unwrap();
    let request=Request::new(&c,&a,0,EMITTER,true).unwrap();let emitted=request.emit(MAX_CODE_BYTES/4).unwrap().unwrap();
    let t=Template::capture_emission(&emitted,MAX_RETAINED).unwrap();assert_eq!(t.key,request.key);
    let mut q=p.clone();q.data[0]=7;let d=Checked::new(&q).unwrap();let mut b=owner(&q);
    scalar(&mut b,0x234567890000);prior_assertions(&mut b,3);
    let current=Request::new(&d,&b,0,EMITTER,true).unwrap();
    let fresh=current.emit(MAX_CODE_BYTES/4).unwrap().unwrap();
    same(&fresh.compiled,&t.restore_request(&current,MAX_CODE_BYTES/4).unwrap());
    let recaptured=Template::capture_emission(&fresh,MAX_RETAINED).unwrap();
    same(&emitted.compiled,&recaptured.restore_request(&request,MAX_CODE_BYTES/4).unwrap());
    assert!(a.code.is_none() && b.code.is_none());
}
#[test]
fn cross_program_template_bound_request_rejects_foreign_checks_functions_modes_and_budgets() {
    let p=fixture();let a=owner(&p);let c=Checked::new(&p).unwrap();let request=Request::new(&c,&a,0,EMITTER,true).unwrap();
    let emitted=request.emit(MAX_CODE_BYTES/4).unwrap().unwrap();let t=Template::capture_emission(&emitted,MAX_RETAINED).unwrap();
    let mut q=p.clone();q.functions[0].code[0]=Op::Imm{dst:0,value:2};let b=owner(&q);let d=Checked::new(&q).unwrap();
    assert!(Request::new(&d,&a,0,EMITTER,true).is_none());
    for invalid in [Request::new(&d,&b,0,EMITTER,true).unwrap(),Request::new(&c,&a,1,EMITTER,true).unwrap(),
        Request::new(&c,&a,0,[18;32],true).unwrap(),Request::new(&c,&a,0,EMITTER,false).unwrap()] {
        assert!(t.restore_request(&invalid,MAX_CODE_BYTES/4).is_none());
    }
    assert!(t.restore_request(&request,t.words.len()-1).is_none());
    assert!(Template::capture_emission(&emitted,0).is_none());assert!(request.emit(0).unwrap().is_none());
    same(&emitted.compiled,&t.restore_request(&request,t.words.len()).unwrap());assert!(a.code.is_none() && b.code.is_none());
}
}
