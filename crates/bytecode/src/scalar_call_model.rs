//! Test-only scalar leaf transaction at the ordinary VM's Call-body boundary.
//! The caller's original Call PC/profile/budget charge has already happened.
use crate::{Memory,Program,Reg,Limits,ExecutionProfile,PARTIAL_VALIDATION};
use crate::scalar_ir::{self,native_leaf::Native};
use std::cell::{Cell,RefCell};

#[derive(Clone,Copy,Debug,Default)]
struct Statistics {attempts:usize,commits:usize,declines:usize}
thread_local! {
    static ENABLED:Cell<bool>=const {Cell::new(false)};
    static STATISTICS:Cell<Statistics>=Cell::new(Statistics::default());
    static NATIVE_STORES:Cell<bool>=const {Cell::new(false)};
    static STORE_MODEL:Cell<bool>=const {Cell::new(false)};
    static SNAPSHOT_ENABLED:Cell<bool>=const {Cell::new(false)};
    static SNAPSHOT:RefCell<Option<(Vec<u8>,Vec<u8>)>>=const {RefCell::new(None)};
}
pub(crate) fn native_stores_enabled()->bool {NATIVE_STORES.with(Cell::get)}
struct NativeEnabled;
impl NativeEnabled {fn new()->Self {NATIVE_STORES.with(|s|assert!(!s.replace(true)));Self}}
impl Drop for NativeEnabled {fn drop(&mut self) {NATIVE_STORES.with(|s|s.set(false));}}
struct Enabled;
impl Enabled {
    fn new()->Self {ENABLED.with(|v|assert!(!v.replace(true)));STATISTICS.with(|v|v.set(Statistics::default()));Self}
    fn transaction()->Self {let enabled=Self::new();STORE_MODEL.with(|v|assert!(!v.replace(true)));enabled}
}
impl Drop for Enabled {fn drop(&mut self) {ENABLED.with(|v|v.set(false));STORE_MODEL.with(|v|v.set(false));}}
fn record(commit:bool) {STATISTICS.with(|v|{let mut s=v.get();s.attempts+=1;if commit {s.commits+=1;} else {s.declines+=1;}v.set(s);});}
struct Compiled {native:Option<Native>,transaction:Option<scalar_ir::Plan>,maximum_steps:usize}
pub(crate) struct Context<'a> {program:&'a Program,profiled:bool,transactional:bool,tried:Vec<bool>,compiled:Vec<Option<Compiled>>,proof_work:usize,scalar_work:usize,mappings:usize}

// Test-only snapshot captures both success and error exits of the actual VM.
impl Drop for Memory {
    fn drop(&mut self) {
        if SNAPSHOT_ENABLED.with(Cell::get) {SNAPSHOT.with(|slot|*slot.borrow_mut()=Some((self.bytes.to_vec(),self.heap.bytes.to_vec())));}
    }
}
#[derive(Clone)]
struct Store {address:usize,size:usize,value:u128}
struct PrivateMemory<'a> {memory:&'a Memory,stores:Vec<Store>}
impl PrivateMemory<'_> {
    fn read(&self,address:u128,size:u8)->Result<u128,String> {
        let address=address as usize;let size=size as usize;
        if size>16 {return Err("private read width".into());}
        let source=self.memory.read(address,size)?;let mut bytes=[0u8;16];bytes[..size].copy_from_slice(source);
        // Every write and this complete read range were checked independently.
        // Overlay in original order; later bytes replace earlier writes.
        for store in &self.stores {
            let start=address.max(store.address);
            let end=address.checked_add(size).ok_or("private address overflow")?
                .min(store.address.checked_add(store.size).ok_or("private store overflow")?);
            if start<end {bytes[start-address..end-address].copy_from_slice(&store.value.to_le_bytes()[start-store.address..end-store.address]);}
        }
        Ok(u128::from_le_bytes(bytes))
    }
    fn write(&mut self,address:u128,value:u128,size:u8)->Result<(),String> {
        let address=address as usize;let size=size as usize;
        if size>16 {return Err("private store width".into());}
        let (heap,_)=self.memory.range(address,size)?;
        if !heap && size!=0 && address<self.memory.readonly_end {return Err("write to read-only guest memory".into());}
        if size!=0 {
            if self.stores.len()>=16 {return Err("private store limit".into());}
            self.stores.push(Store{address,size,value});
        }
        Ok(())
    }
}

impl<'a> Context<'a> {
    pub fn new(program:&'a Program,profiled:bool,use_jit:bool)->Result<Option<Self>,String> {
        if !ENABLED.with(Cell::get) {return Ok(None);}
        if use_jit {return Err("scalar transaction model requires ordinary interpreter dispatch".into());}
        if program.version & PARTIAL_VALIDATION != 0 {return Err("scalar transaction model requires full validation".into());}
        Ok(Some(Self{program,profiled,transactional:STORE_MODEL.with(Cell::get),tried:vec![false;program.functions.len()],compiled:(0..program.functions.len()).map(|_|None).collect(),
            proof_work:crate::proof::MAX_GLOBAL_WORK,scalar_work:128_000_000,mappings:0}))
    }
    fn ensure(&mut self,id:usize) {
        if self.tried[id] {return;}self.tried[id]=true;
        // The prototype reserves 256 KiB per publisher; cap all reservations
        // at 16 MiB. The production bridge will use its shared code arena.
        if self.mappings>=64 {return;}
        let memory=if self.transactional {crate::proof::memory_plan_transaction(self.program,id,&mut self.proof_work)}
            else {crate::proof::memory_plan(self.program,id,&mut self.proof_work)};
        let limit=self.scalar_work.min(250_000);
        let scalar=scalar_ir::lower(&self.program.functions[id],&memory,limit);
        self.scalar_work=self.scalar_work.saturating_sub(match &scalar {Ok(p)=>p.work,Err("no_memory_plan")=>0,Err(_)=>limit});
        if let Ok(plan)=scalar {
            if self.transactional {
                let maximum_steps=plan.maximum_steps;
                self.compiled[id]=Some(Compiled{native:None,transaction:Some(plan),maximum_steps});return;
            }
            if let Ok(native)=Native::compile(&plan,&self.program.functions[id],self.profiled) {
                self.mappings+=1;
                self.compiled[id]=Some(Compiled{native:Some(native),transaction:None,maximum_steps:plan.maximum_steps});
            }
        }
    }
    #[allow(clippy::too_many_arguments)]
    pub fn try_call(&mut self,id:usize,args:&[Reg],registers:&[u128],destination:usize,memory:&mut Memory,
        register_bytes:usize,frame_count:usize,limits:&Limits,budget:u64,profile:Option<&mut ExecutionProfile>)->Result<Option<u64>,String> {
        if self.profiled && profile.is_none() {return Err("missing scalar transaction profile".into());}
        self.ensure(id);
        let Some(compiled)=&self.compiled[id] else {record(false);return Ok(None);};
        let f=&self.program.functions[id];let old_len=memory.bytes.len();
        // Guards establish only success eligibility. Their failure exposes no
        // error: ordinary Call performs every original check in its own order.
        let preflight=(|| {
            if frame_count>=limits.frames || budget<compiled.maximum_steps as u64 {return None;}
            let base=old_len.checked_add(f.frame_align-1)? & !(f.frame_align-1);
            let end=base.checked_add(f.frame_size.max(1))?;
            let total=end.checked_add(memory.heap.bytes.len())?.checked_add(memory.auxiliary_bytes)?;
            if total>memory.limit {return None;}
            let working=register_bytes.checked_add(f.registers.checked_mul(16)?)?.checked_add(total)?;
            if working>limits.memory {return None;}
            let (heap,_)=memory.range(destination,f.result.size).ok()?;
            if !heap && f.result.size!=0 && destination<memory.readonly_end {return None;}
            let inputs:Option<Vec<_>>=args.iter().zip(&f.args).map(|(reg,slot)|memory.load(registers[*reg as usize] as usize,slot.size).ok()).collect();
            Some((base,end,total,inputs?))
        })();
        let Some((base,end,total,inputs))=preflight else {record(false);return Ok(None);};
        // Preparation can move private backing but cannot change active bytes,
        // guest bounds, registers, frames, peak memory or logical counters.
        // The additional backing is bounded by one <=512-byte leaf plus <=4095
        // alignment bytes. No guest reference spans preparation/native entry.
        if memory.bytes.prepare(end).is_err() {record(false);return Ok(None);}
        let (output,stores)=if let Some(plan)=&compiled.transaction {
            let shadow=RefCell::new(PrivateMemory{memory,stores:vec![]});
            let outcome=plan.evaluate_effects(&inputs,base,budget as usize,&f.name,
                &mut |a,n|shadow.borrow().read(a,n),&mut |a,v,n|shadow.borrow_mut().write(a,v,n));
            let Ok(outcome)=outcome else {record(false);return Ok(None);};
            let mut output=scalar_ir::native_leaf::Output{value:outcome.value,steps:outcome.pcs.len() as u64,visited:[0;8]};
            for pc in outcome.pcs {assert_eq!(output.visited[pc/64]&(1u64<<(pc%64)),0);output.visited[pc/64]|=1u64<<(pc%64);}
            (output,shadow.into_inner().stores)
        } else {
            let Some(output)=compiled.native.as_ref().unwrap().attempt(&inputs,base,budget as usize)? else {record(false);return Ok(None);};
            (output,vec![])
        };
        if output.steps==0 || output.steps>compiled.maximum_steps as u64 || output.steps>budget {
            return Err("invalid scalar transaction instruction count".into());
        }
        if self.profiled {
            if output.visited.iter().map(|w|w.count_ones() as u64).sum::<u64>()!=output.steps
                || (f.code.len()..512).any(|pc|output.visited[pc/64]&(1u64<<(pc%64))!=0) {
                return Err("invalid scalar transaction profile".into());
            }
        }
        // Only successful private execution reaches publication. Preserve the
        // original Return's retained alignment padding and peak payload extent.
        // Callee frame/register backing is dead after Return; future frame
        // reservations reinitialize it before exposing it to guest addresses.
        memory.bytes.resize(base,0);
        for store in stores {memory.store(store.address,store.size,store.value)?;}
        memory.store(destination,f.result.size,output.value)?;
        memory.peak=memory.peak.max(total);
        if self.profiled {
            let row=&mut profile.ok_or("missing scalar transaction profile")?.functions[id];
            for pc in 0..f.code.len() {
                if output.visited[pc/64]&(1u64<<(pc%64))!=0 {
                    row.jit_blocks[pc]+=1;row.jit_block_ends[pc]=pc+1;
                }
            }
        }
        record(true);Ok(Some(output.steps))
    }
}

#[path="scalar_call_model_tests.rs"]
mod tests;

#[path="scalar_call_model_transaction_tests.rs"]
mod transaction_tests;

#[path="scalar_call_native_transaction_tests.rs"]
mod native_transaction_tests;
