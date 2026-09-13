//! Offline, basic-block argument-byte facts. No compiler or VM uses this analysis.
use crate::{Function, Op, Program, Reg};
use serde::Serialize;
use std::collections::BTreeMap;

const MAX_SHAPE: usize = 65_536;
const MAX_ACCESSES: usize = 262_144;
const MAX_BYTES: usize = 256;
const MAX_SITES: usize = 131_072;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
enum Fact { #[default] Unknown, Scalar(u128), Local(usize) }
impl Fact {
    fn scalar(self) -> Option<u128> { if let Self::Scalar(v) = self { Some(v) } else { None } }
}

struct Facts<'a> {
    registers: Vec<Fact>,
    epochs: Vec<u32>,
    epoch: u32,
    bytes: BTreeMap<usize, u8>,
    frame_size: usize,
    data: &'a [u8],
    evictions: usize,
}
impl<'a> Facts<'a> {
    fn new(f: &Function, data: &'a [u8]) -> Self {
        Self { registers:vec![Fact::Unknown;f.registers], epochs:vec![0;f.registers], epoch:1,
            bytes:BTreeMap::new(), frame_size:f.frame_size, data, evictions:0 }
    }
    fn reset(&mut self) { self.epoch += 1; self.bytes.clear(); }
    fn get(&self, r: Reg) -> Fact {
        if self.epochs[r as usize] == self.epoch { self.registers[r as usize] } else { Fact::Unknown }
    }
    fn set(&mut self, r: Reg, value: Fact) {
        self.registers[r as usize] = value; self.epochs[r as usize] = self.epoch;
    }
    fn read(&self, address: Fact, size: usize) -> Option<u128> {
        if size == 0 || size > 16 { return None; }
        let mut out = [0u8;16];
        match address {
            Fact::Local(start) => {
                if start.checked_add(size)? > self.frame_size { return None; }
                for (i, byte) in out[..size].iter_mut().enumerate() { *byte = *self.bytes.get(&(start+i))?; }
            }
            Fact::Scalar(value) => {
                // Be stricter than the VM's host-usize truncation. Only the
                // immutable data range supplies facts, never heap/static bytes.
                let start = usize::try_from(value).ok()?;
                // Null padding is not readable guest data (Memory::range).
                if start == 0 { return None; }
                let end = start.checked_add(size)?;
                out[..size].copy_from_slice(self.data.get(start..end)?);
            }
            Fact::Unknown => return None,
        }
        Some(u128::from_le_bytes(out))
    }
    fn write(&mut self, address: Fact, size: usize, value: Option<u128>) {
        if size == 0 { return; }
        let Fact::Local(start) = address else { self.bytes.clear(); return; };
        let Some(end) = start.checked_add(size).filter(|&end|end <= self.frame_size) else {
            self.bytes.clear(); return;
        };
        // Remove every overlapping byte even for untracked/large copies.
        self.bytes.retain(|&offset,_|offset < start || offset >= end);
        if let Some(value) = value.filter(|_|size <= 16) {
            if self.bytes.len()+size > MAX_BYTES { self.bytes.clear(); self.evictions += 1; }
            for (i, byte) in value.to_le_bytes()[..size].iter().enumerate() { self.bytes.insert(start+i,*byte); }
        }
    }
    fn step(&mut self, op: &Op) {
        // Compute results before invalidating writes: inputs may alias outputs.
        let mut outputs = [(0,Fact::Unknown);2];
        let mut count = 0;
        let mut output = |r,value| { outputs[count]=(r,value); count+=1; };
        match op {
            Op::Imm {dst,value} => output(*dst,Fact::Scalar(*value)),
            Op::Local {dst,offset} => output(*dst,Fact::Local(*offset)),
            Op::Load {dst,address,size} => output(*dst,self.read(self.get(*address),*size as usize).map_or(Fact::Unknown,Fact::Scalar)),
            Op::Store {address,src,size} => self.write(self.get(*address),*size as usize,self.get(*src).scalar()),
            Op::Copy {dst,src,size} => {
                let value=self.read(self.get(*src),*size); self.write(self.get(*dst),*size,value);
            }
            Op::Binary {dst,overflow,op,a,b,bits,signed} => {
                if let (Some(a),Some(b)) = (self.get(*a).scalar(),self.get(*b).scalar()) {
                    if let Ok((v,over))=crate::binary(*op,a,b,*bits,*signed) {
                        output(*dst,Fact::Scalar(v));output(*overflow,Fact::Scalar(u128::from(over)));
                    }
                }
                // Arithmetic on symbolic Local addresses is intentionally unknown.
                // An error leaves both outputs unknown; it is never evaluated as
                // a guest fault or used to suppress a runtime check.
            }
            Op::Cast {dst,src,from,to,signed} => {
                if let Some(value)=self.get(*src).scalar() {
                    let value=if *signed {crate::signed(value,*from) as u128} else {value & crate::mask(*from)};
                    output(*dst,Fact::Scalar(value & crate::mask(*to)));
                }
            }
            Op::Select {dst,condition,yes,no} => {
                let a=self.get(*yes);let b=self.get(*no);
                let value=match self.get(*condition).scalar() {Some(v)=>if v!=0 {a} else {b},None=>if a==b {a} else {Fact::Unknown}};
                output(*dst,value);
            }
            Op::CopyDynamic {..}|Op::FillBytes {..}|Op::Call {..}|Op::CallIndirect {..}
            |Op::Allocate {..}|Op::Deallocate {..}|Op::Reallocate {..}|Op::ResetThreadLocals
            |Op::DescriptorOpen {..}|Op::DescriptorWrite {..}|Op::DescriptorClose {..}|Op::DescriptorGetFd {..}
            |Op::RandomBytes {..}|Op::CpuFeatureQuery {..}|Op::EnvironmentGet {..}|Op::CAllocate {..}|Op::CDeallocate {..}
            |Op::CReallocate {..}|Op::CAlignedAllocate {..}|Op::RegisterTlsDestructor {..} => self.bytes.clear(),
            Op::Unary {..}|Op::FloatBinary {..}|Op::FloatUnary {..}|Op::FloatConvert {..}
            |Op::CompareBytes {..}|Op::Jump {..}|Op::Switch {..}|Op::Assert {..}|Op::Return|Op::Trap {..} => {},
        }
        crate::registers::visit_registers(op, |_|{}, |r|self.set(r,Fact::Unknown));
        // In Binary, overflow is the last write even when dst == overflow.
        for &(r,value) in &outputs[..count] { self.set(r,value); }
    }
}

#[derive(Debug, Serialize)]
struct Argument { index: usize, bytes: usize, value: String }
#[derive(Debug, Serialize)]
struct Site { pc: usize, callee: usize, executions: Option<u64>, arguments: Vec<Argument> }

fn block_starts(f: &Function) -> Option<Vec<bool>> {
    if f.registers > MAX_SHAPE || f.code.len() > MAX_SHAPE { return None; }
    let mut starts=vec![false;f.code.len()];starts[0]=true;
    let mut accesses=0usize;
    for (pc,op) in f.code.iter().enumerate() {
        crate::registers::visit_registers(op, |_|accesses+=1, |_|{});
        crate::registers::visit_registers(op, |_|{}, |_|accesses+=1);
        match op {
            Op::Jump {target} => {starts[*target]=true;accesses+=1;},
            Op::Switch {cases,otherwise,..} => {
                starts[*otherwise]=true;accesses+=1;
                for &(_,target) in cases {starts[target]=true;accesses+=1;}
            }
            _=>{},
        }
        if matches!(op,Op::Jump{..}|Op::Switch{..}|Op::Return|Op::Trap{..}) && pc+1<f.code.len() { starts[pc+1]=true; }
        if accesses > MAX_ACCESSES {return None;}
    }
    Some(starts)
}

fn analyze(program: &Program, id: usize, counts: Option<&[u64]>) -> Option<(Vec<Site>,usize)> {
    let f=&program.functions[id];let starts=block_starts(f)?;
    let mut facts=Facts::new(f,&program.data);let mut sites=Vec::new();
    for (pc,op) in f.code.iter().enumerate() {
        if starts[pc] {facts.reset();}
        if let Op::Call {function,args,..}=op {
            let callee=&program.functions[*function];let mut arguments=Vec::new();
            for (index,(&address,slot)) in args.iter().zip(&callee.args).enumerate() {
                if ![1,2,4,8].contains(&slot.size) {continue;}
                if let Some(value)=facts.read(facts.get(address),slot.size) {
                    arguments.push(Argument {index,bytes:slot.size,value:format!("0x{value:x}")});
                }
            }
            sites.push(Site {pc,callee:*function,executions:counts.map(|c|c[pc]),arguments});
        }
        facts.step(op);
    }
    Some((sites,facts.evictions))
}

pub(super) fn census(program: &Program, profile: Option<&[u8]>) -> Result<serde_json::Value,String> {
    crate::validate(program)?;
    let profile=profile.map(|bytes|super::register_width_profile::parse(program,bytes)).transpose()?;
    let mut rows=Vec::new();let mut all_sites=0usize;let mut constant_sites=0usize;
    let mut executions=0u64;let mut constant_executions=0u64;let mut declined_executions=0u64;
    let mut declined_functions=0usize;
    let add=|a:&mut u64,b:u64|->Result<(),String>{*a=a.checked_add(b).ok_or("call census count overflow")?;Ok(())};
    for (id,f) in program.functions.iter().enumerate() {
        let counts=profile.as_ref().map(|profile| {
            let p=&profile.functions[id];let mut counts=p.native_counts(f)?;
            for (count,interpreted) in counts.iter_mut().zip(&p.interpreted) {add(count,*interpreted)?;}
            Ok::<_,String>(counts)
        }).transpose()?;
        let static_sites=f.code.iter().filter(|op|matches!(op,Op::Call{..})).count();
        all_sites=all_sites.checked_add(static_sites).ok_or("call site count overflow")?;
        if all_sites > MAX_SITES {return Err("call census exceeds 131072 sites".into());}
        let mut hits=0u64;
        if let Some(counts)=&counts {for (op,count) in f.code.iter().zip(counts) {if matches!(op,Op::Call{..}) {add(&mut hits,*count)?;}}}
        add(&mut executions,hits)?;
        match analyze(program,id,counts.as_deref()) {
            Some((sites,evictions)) => {
                for site in &sites {if !site.arguments.is_empty() {constant_sites+=1;add(&mut constant_executions,site.executions.unwrap_or(0))?;}}
                rows.push(serde_json::json!({"function":id,"declined":false,"direct_call_sites":static_sites,"direct_call_executions":counts.as_ref().map(|_|hits),"byte_fact_evictions":evictions,"sites":sites}));
            }
            None => {declined_functions+=1;add(&mut declined_executions,hits)?;
                rows.push(serde_json::json!({"function":id,"declined":true,"direct_call_sites":static_sites,"direct_call_executions":counts.as_ref().map(|_|hits)}));}
        }
    }
    Ok(serde_json::json!({"schema_version":1,"performance_measurement":false,
        "scope":"Basic-block constant argument bytes, widths 1/2/4/8. Exact direct-call counts; indirect calls and builtins excluded. No specialization, guest execution, type/pointee inference or predicted savings.",
        "bounds":{"operations_and_registers_per_function":MAX_SHAPE,"accesses_and_edges_per_function":MAX_ACCESSES,"tracked_local_bytes":MAX_BYTES,"total_direct_call_sites":MAX_SITES},
        "direct_call_sites":all_sites,"sites_with_constant_arguments":constant_sites,"declined_functions":declined_functions,
        "direct_call_executions":profile.as_ref().map(|_|executions),"executions_with_constant_arguments":profile.as_ref().map(|_|constant_executions),
        "declined_direct_call_executions":profile.as_ref().map(|_|declined_executions),"functions":rows}))
}

#[cfg(test)]
#[path="constant_arguments_tests.rs"]
mod tests;
