//! Direct AArch64 emission for the experimental scalar IR, with private output.
//! Original guest state is committed only by the separately checked Call bridge.
use super::*;
#[path="native_registers.rs"]
mod registers;
#[path="native_dead.rs"]
mod dead;
// Fixed offsets from the caller's SP at private native Call entry. Leaf
// spills grow below that SP; inputs and Output remain in caller-owned scratch.
pub(crate) const CALL_OUTPUT:usize=64;
pub(crate) const CALL_ARGUMENTS:usize=160;
const MAX_WORDS:usize=65536;
const MAX_CODE_BYTES:usize=MAX_WORDS*4;
#[repr(C)]
struct Cursor { remaining:u64, profile_hits:*mut u64 }
#[path="native_memory.rs"]
mod publisher;
#[cfg(all(target_arch="aarch64",target_os="macos"))]
use publisher::memory;

#[repr(C)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Output {pub value:u128,pub steps:u64,pub visited:[u64;8]}
const _:()={assert!(std::mem::offset_of!(Output,value)==0);assert!(std::mem::offset_of!(Output,steps)==16);assert!(std::mem::offset_of!(Output,visited)==24);};
pub struct Emitted {pub words:Vec<u32>,pub stack_bytes:usize,pub profiled:bool,pub register_values:usize,pub success_steps:Option<usize>}
struct Emitter<'a> {
    plan:&'a Plan, words:Vec<u32>, slots:Vec<Option<usize>>, stack_bytes:usize,
    registers:Vec<Option<u32>>,
    labels:Vec<Option<usize>>, jumps:Vec<(usize,usize)>, failures:Vec<usize>,
    exhausted:bool, profiled:bool, call_frame:bool, heap:bool, fixed_steps:Option<usize>,
}
impl Emitter<'_> {
    fn emit(&mut self,word:u32) {if self.words.len()<MAX_WORDS {self.words.push(word);} else {self.exhausted=true;}}
    fn imm(&mut self,rd:u32,value:u64) {
        self.emit(0xd2800000|((value as u32&0xffff)<<5)|rd);
        for shift in 1..4 {let part=(value>>(shift*16)) as u32&0xffff;if part!=0 {self.emit(0xf2800000|(shift<<21)|(part<<5)|rd);}}
    }
    fn three(&mut self,op:u32,rd:u32,rn:u32,rm:u32) {self.emit(op|(rm<<16)|(rn<<5)|rd);}
    fn mov(&mut self,rd:u32,rn:u32) {self.three(0xaa000000,rd,31,rn);}
    fn cmp(&mut self,a:u32,b:u32) {self.three(0xeb000000,31,a,b);}
    fn cset(&mut self,rd:u32,condition:u32) {self.emit(0x9a9f07e0|((condition^1)<<12)|rd);}
    fn csel(&mut self,rd:u32,yes:u32,no:u32,condition:u32) {self.emit(0x9a800000|(no<<16)|(condition<<12)|(yes<<5)|rd);}
    fn mask(&mut self,rd:u32,bits:u8) {if bits==0 {self.mov(rd,31);} else if bits<64 {self.emit(0xd3400000|((bits as u32-1)<<10)|(rd<<5)|rd);}}
    fn sign(&mut self,rd:u32,bits:u8) {if bits<64 {self.emit(0x93400000|((bits as u32-1)<<10)|(rd<<5)|rd);}}
    fn lsr(&mut self,rd:u32,rn:u32,shift:u8) {assert!(shift<64);self.emit(0xd340fc00|((shift as u32)<<16)|(rn<<5)|rd);}
    fn lsl(&mut self,rd:u32,rn:u32,shift:u8) {assert!(shift<64);if shift==0 {self.mov(rd,rn);} else {self.emit(0xd3400000|((64-shift as u32)<<16)|((63-shift as u32)<<10)|(rn<<5)|rd);}}
    fn load(&mut self,rd:u32,base:u32,offset:usize) {assert!(offset%8==0 && offset/8<4096);self.emit(0xf9400000|((offset as u32/8)<<10)|(base<<5)|rd);}
    fn store(&mut self,rd:u32,base:u32,offset:usize) {assert!(offset%8==0 && offset/8<4096);self.emit(0xf9000000|((offset as u32/8)<<10)|(base<<5)|rd);}
    fn output_address(&self,offset:usize)->(u32,usize) {
        if self.call_frame {(31,self.stack_bytes+CALL_OUTPUT+offset)} else {(2,offset)}
    }
    fn output_load(&mut self,rd:u32,offset:usize) {
        let (base,offset)=self.output_address(offset);self.load(rd,base,offset);
    }
    fn output_store(&mut self,rd:u32,offset:usize) {
        let (base,offset)=self.output_address(offset);self.store(rd,base,offset);
    }
    fn stack(&mut self,restore:bool) {
        let opcode=if restore {0x91000000} else {0xd1000000};
        if self.stack_bytes/4096!=0 {self.emit(opcode|(1<<22)|((self.stack_bytes as u32/4096)<<10)|(31<<5)|31);}
        if self.stack_bytes%4096!=0 {self.emit(opcode|((self.stack_bytes as u32%4096)<<10)|(31<<5)|31);}
    }
    fn patch(&mut self,at:usize,target:usize,conditional:bool)->Result<(),&'static str> {
        if self.exhausted {return Err("native_word_limit");}
        let bits=if conditional {19} else {26};let delta=target as i64-at as i64;
        if delta < -(1i64<<(bits-1)) || delta >= (1i64<<(bits-1)) {return Err("native_branch_limit");}
        self.words[at]|=((delta as u32)&((1u32<<bits)-1))<<if conditional {5} else {0};Ok(())
    }
    fn fail(&mut self,condition:u32) {self.failures.push(self.words.len());self.emit(0x54000000|condition);}
    fn get(&mut self,rd:u32,id:Id,high:bool) {
        let node=&self.plan.nodes[id];
        if high && node.width<=8 {self.mov(rd,31);return;}
        match node.value {
            Value::Constant(v)=>self.imm(rd,(if high {v>>64} else {v}) as u64),
            Value::Input(index)=>{if node.width==0 {self.mov(rd,31);} else {
                let offset=index*16+usize::from(high)*8;
                if self.call_frame {self.load(rd,31,self.stack_bytes+CALL_ARGUMENTS+offset);} else {self.load(rd,0,offset);}
                self.mask(rd,if high {(node.width-8)*8} else {node.width.min(8)*8});}},
            Value::Base(offset)=>{if high {self.mov(rd,31);} else {self.imm(rd,offset as u64);self.three(0x8b000000,rd,if self.call_frame {21} else {1},rd);}},
            _=>if let Some(register)=self.registers[id] {self.mov(rd,register);} else {
                self.load(rd,31,self.slots[id].expect("live scalar storage")+usize::from(high)*8)
            },
        }
    }
    fn put(&mut self,id:Id) {
        if let Some(register)=self.registers[id] {self.mov(register,9);return;}
        let offset=self.slots[id].unwrap();self.store(9,31,offset);if self.plan.nodes[id].width>8 {self.store(10,31,offset+8);}
    }
    /// Private Call only. x2/x7/x8 retain the stable linear/heap backing and
    /// heap length. The caller saved its PRE-Call linear length at SP+24.
    /// Limiting linear reads to that prefix excludes all fresh payload/padding,
    /// whose logical bytes may differ from our private virtual frame. Any failed
    /// check returns private failure; the bridge replays the ordinary Call.
    /// Use only x9-x14: x3 and x15-x17 may contain allocated live scalar values.
    fn read_external(&mut self,address:Id,size:u8)->Result<(),&'static str> {
        if !self.call_frame {return Err("native_external_read_call_only");}
        if size==0 || size>16 {return Err("native_external_read_width");}
        self.get(9,address,false); // exactly the VM's low-usize address bits
        self.imm(10,crate::heap::TAG as u64);self.cmp(9,10);
        if self.heap {
            self.three(0xcb000000,11,9,10);
            self.csel(9,9,11,3);self.csel(12,2,7,3);
            self.load(13,31,self.stack_bytes+24);self.csel(13,13,8,3);
        } else {
            // Heap-free external prologues leave x7/x8 outside the guest ABI.
            // Reject tagged reads before consulting either register.
            self.fail(2);self.mov(12,2);self.load(13,31,self.stack_bytes+24);
        }
        self.cmp(9,31);self.fail(0);
        self.cmp(9,13);self.fail(8);
        self.three(0xcb000000,13,13,9);self.imm(14,size as u64);
        self.cmp(13,14);self.fail(3);
        self.three(0x8b000000,11,12,9);
        match size {
            1|2|4|8=>{
                let opcode=match size {1=>0x39400000,2=>0x79400000,4=>0xb9400000,_=>0xf9400000};
                self.emit(opcode|(11<<5)|9);self.mov(10,31);
            },
            16=>{self.load(9,11,0);self.load(10,11,8);},
            _=>{
                self.mov(9,31);self.mov(10,31);
                for byte in 0..size {
                    self.emit(0x39400000|((byte as u32)<<10)|(11<<5)|12);
                    self.lsl(12,12,(byte%8)*8);
                    let output=if byte<8 {9} else {10};self.three(0xaa000000,output,output,12);
                }
            },
        }
        Ok(())
    }
    fn extract(&mut self,p:Slice) {
        self.get(9,p.value,false);self.get(10,p.value,true);
        let shift=p.byte*8;
        if shift>=64 {self.lsr(9,10,shift-64);self.mov(10,31);} else if shift!=0 {
            self.emit(0x93c00000|(9<<16)|((shift as u32)<<10)|(10<<5)|9); // EXTR low from high:low
            self.lsr(10,10,shift);
        }
        if p.size<=8 {self.mask(9,p.size*8);self.mov(10,31);} else {self.mask(10,(p.size-8)*8);}
    }
    fn pack(&mut self,parts:&[Slice]) {
        self.mov(13,31);self.mov(14,31);let mut shift=0u8;
        for &part in parts {
            self.extract(part);
            if shift==0 {self.three(0xaa000000,13,13,9);self.three(0xaa000000,14,14,10);}
            else if shift<64 {
                self.lsl(11,9,shift);self.three(0xaa000000,13,13,11);
                self.lsr(11,9,64-shift);self.lsl(12,10,shift);self.three(0xaa000000,11,11,12);self.three(0xaa000000,14,14,11);
            } else {self.lsl(11,9,shift-64);self.three(0xaa000000,14,14,11);}
            shift+=part.size*8;
        }
        self.mov(9,13);self.mov(10,14);
    }
    fn arithmetic(&mut self,op:Binary,bits:u8,signed:bool,observed:bool) {
        let plain=match op {Binary::Add=>0x8b000000,Binary::Sub=>0xcb000000,Binary::Mul=>0x9b007c00,_=>unreachable!()};
        if !observed {self.three(plain,9,9,10);return;}
        if bits<64 {
            if signed {self.sign(9,bits);self.sign(10,bits);}
            self.three(plain,9,9,10);self.mov(11,9);
            if signed {self.sign(11,bits);} else {self.mask(11,bits);}
            self.cmp(9,11);self.cset(13,1);
        } else if matches!(op,Binary::Mul) {
            self.three(if signed {0x9b407c00} else {0x9bc07c00},11,9,10);self.three(plain,9,9,10);
            if signed {self.emit(0x9340fc00|(63<<16)|(9<<5)|12);self.cmp(11,12);} else {self.cmp(11,31);}
            self.cset(13,1);
        } else {
            let add=matches!(op,Binary::Add);self.three(if add {0xab000000} else {0xeb000000},9,9,10);
            self.cset(13,if signed {6} else if add {2} else {3});
        }
    }
    fn division(&mut self,op:Binary,bits:u8,signed:bool) {
        self.cmp(10,31);self.fail(0);
        if signed {
            self.sign(9,bits);self.sign(10,bits);self.imm(11,1u64<<(bits-1));self.sign(11,bits);
            self.three(0xca000000,11,9,11);self.three(0xaa200000,12,31,10);self.three(0xaa000000,11,11,12);self.cmp(11,31);self.fail(0);
        }
        let opcode=if signed {0x9ac00c00} else {0x9ac00800};
        if matches!(op,Binary::Rem) {self.three(opcode,11,9,10);self.emit(0x9b008000|(10<<16)|(9<<10)|(11<<5)|9);} else {self.three(opcode,9,9,10);}
    }
    fn binary(&mut self,a:Id,b:Id,op:Binary,bits:u8,signed:bool,overflow:bool) {
        let arithmetic=matches!(op,Binary::Add|Binary::Sub|Binary::Mul);
        if overflow && !arithmetic && !matches!(op,Binary::Div|Binary::Rem) {self.mov(9,31);self.mov(10,31);return;}
        self.get(9,a,false);self.get(10,b,false);self.mask(9,bits);
        if !matches!(op,Binary::Shl|Binary::Shr|Binary::RotateLeft|Binary::RotateRight) {self.mask(10,bits);}
        match op {
            Binary::Add|Binary::Sub|Binary::Mul=>self.arithmetic(op,bits,signed,overflow),
            Binary::Div|Binary::Rem=>self.division(op,bits,signed),
            Binary::And=>self.three(0x8a000000,9,9,10),Binary::Or=>self.three(0xaa000000,9,9,10),Binary::Xor=>self.three(0xca000000,9,9,10),
            Binary::Shl|Binary::Shr|Binary::RotateLeft|Binary::RotateRight=>{
                self.imm(11,bits as u64-1);self.three(0x8a000000,10,10,11);
                if matches!(op,Binary::Shr) && signed {self.sign(9,bits);}
                match op {
                    Binary::Shl=>self.three(0x9ac02000,9,9,10),
                    Binary::Shr=>self.three(if signed {0x9ac02800} else {0x9ac02400},9,9,10),
                    _=>{
                        if matches!(op,Binary::RotateLeft) {self.three(0xcb000000,10,31,10);}
                        if bits==64 || bits==32 {self.three(if bits==64 {0x9ac02c00} else {0x1ac02c00},9,9,10);}
                        else {self.three(0x8a000000,10,10,11);self.three(0x9ac02400,12,9,10);self.imm(11,bits as u64);
                            self.three(0xcb000000,10,11,10);self.three(0x9ac02000,9,9,10);self.three(0xaa000000,9,9,12);}
                    },
                }
            },
            _=>{
                if signed {self.sign(9,bits);self.sign(10,bits);}self.cmp(9,10);
                let condition=match op {Binary::Eq=>0,Binary::Ne=>1,Binary::Lt=>if signed {11} else {3},
                    Binary::Le=>if signed {13} else {9},Binary::Gt|Binary::Cmp=>if signed {12} else {8},
                    Binary::Ge=>if signed {10} else {2},_=>unreachable!()};
                self.cset(9,condition);
                if matches!(op,Binary::Cmp) {self.cset(10,if signed {11} else {3});self.three(0xcb000000,9,9,10);self.mask(9,8);}
            },
        }
        self.mask(9,bits);
        if overflow {self.mov(9,if arithmetic {13} else {31});}self.mov(10,31);
    }
    fn node(&mut self,id:Id)->Result<(),&'static str> {
        match &self.plan.nodes[id].value {
            Value::Read{address,size}=>self.read_external(*address,*size)?,
            Value::Pack(parts)=>self.pack(parts),
            Value::Binary{a,b,op,bits,signed,overflow}=>self.binary(*a,*b,*op,*bits,*signed,*overflow),
            Value::Unary{src,op,bits}=>{
                self.get(9,*src,false);self.mask(9,*bits);
                match op {
                    Unary::Not=>self.three(0xaa200000,9,31,9),Unary::Neg=>self.three(0xcb000000,9,31,9),
                    Unary::SwapBytes=>{self.emit(0xdac00c00|(9<<5)|9);if *bits<64 {self.lsr(9,9,64-*bits);}},
                    Unary::CountOnes=>{for word in [0x9e670120,0x0e205800,0x0e31b800,0x0e013c09] {self.emit(word);}},
                    Unary::LeadingZeros=>{self.emit(0xdac01000|(9<<5)|9);if *bits<64 {self.imm(10,(64-*bits) as u64);self.three(0xcb000000,9,9,10);}},
                    Unary::TrailingZeros=>{self.emit(0xdac00000|(9<<5)|9);self.emit(0xdac01000|(9<<5)|9);
                        if *bits<64 {self.imm(10,*bits as u64);self.cmp(9,10);self.csel(9,9,10,3);}},
                }self.mask(9,*bits);self.mov(10,31);
            },
            Value::Cast{src,from,to,signed}=>{
                self.get(9,*src,false);self.get(10,*src,true);
                if *from<128 {self.mask(9,*from);if *signed {self.sign(9,*from);self.emit(0x9340fc00|(63<<16)|(9<<5)|10);} else {self.mov(10,31);}}
                if *to<128 {self.mask(9,*to);self.mov(10,31);}
            },
            Value::Select{condition,yes,no}=>{
                self.get(9,*condition,false);self.get(10,*condition,true);self.three(0xaa000000,9,9,10);self.cmp(9,31);
                self.get(9,*yes,false);self.get(10,*no,false);self.csel(9,9,10,1);
                self.get(11,*yes,true);self.get(12,*no,true);self.csel(10,11,12,1);
            },
            _=>return Err("native_misplaced_node"),
        }
        self.put(id);Ok(())
    }
    fn edge(&mut self,from:usize,to:usize)->Result<(),&'static str> {
        for &id in &self.plan.blocks[to].phis {
            if !self.plan.live[id] {continue;}
            let Value::Phi(parts)=&self.plan.nodes[id].value else {return Err("native_phi_shape");};
            let (_,part)=parts.iter().find(|(p,_)|*p==from).ok_or("native_phi_predecessor")?;
            self.extract(*part);self.put(id);
        }
        self.jumps.push((self.words.len(),to));self.emit(0x14000000);Ok(())
    }
    fn charge_block(&mut self,block:usize) {
        let b=&self.plan.blocks[block];let (start,end)=(b.start,b.end);
        if self.fixed_steps.is_none() {self.output_load(9,16);self.emit(0x91000000|(((end-start) as u32)<<10)|(9<<5)|9);self.output_store(9,16);}
        if self.profiled {
            for word in start/64..=(end-1)/64 {
                let left=start.max(word*64)-word*64;let right=end.min((word+1)*64)-word*64;
                let bits=if right-left==64 {u64::MAX} else {((1u64<<(right-left))-1)<<left};
                self.output_load(9,24+word*8);self.imm(10,bits);self.three(0xaa000000,9,9,10);self.output_store(9,24+word*8);
            }
        }
    }
}

pub fn emit(plan:&Plan,profiled:bool)->Result<Emitted,&'static str> {
    emit_inner(plan,profiled,true,true,true,false,false,false)
}
#[cfg(test)]
fn emit_with_registers(plan:&Plan,profiled:bool,use_registers:bool)->Result<Emitted,&'static str> {
    // Preserve exact pre-elimination reference bytes for the archived census.
    emit_inner(plan,profiled,use_registers,true,false,false,false,false)
}
/// Historical pointer-argument entry retained as an independent test reference.
#[cfg(test)]
#[allow(dead_code)]
pub(crate) fn emit_prechecked(plan:&Plan,profiled:bool)->Result<Emitted,&'static str> {
    emit_inner(plan,profiled,true,false,true,false,false,false)
}
/// Private Call entry: captured inputs/Output use fixed caller-SP offsets,
/// logical base is x21, status is x9, and x0–x2 remain live. Its caller must
/// preflight maximum_steps + Call. Standalone emission retains its budget guard.
pub(crate) fn emit_call(plan:&Plan,profiled:bool)->Result<Emitted,&'static str> {
    emit_call_with_heap(plan,profiled,false)
}
pub(crate) fn emit_call_with_heap(plan:&Plan,profiled:bool,heap:bool)->Result<Emitted,&'static str> {
    emit_inner(plan,profiled,true,false,true,true,true,heap)
}
#[cfg(test)]
fn emit_call_reference(plan:&Plan,profiled:bool)->Result<Emitted,&'static str> {
    emit_inner(plan,profiled,true,false,true,true,false,false)
}
fn emit_inner(plan:&Plan,profiled:bool,use_registers:bool,check_budget:bool,eliminate_dead:bool,call_frame:bool,optimize_commit:bool,heap:bool)->Result<Emitted,&'static str> {
    if !call_frame && plan.nodes.iter().any(|n|matches!(n.value,Value::Read{..})) {
        return Err("native_external_read_call_only");
    }
    let registers=if use_registers {registers::allocate(plan)?} else {vec![None;plan.nodes.len()]};
    let register_values=registers.iter().filter(|r|r.is_some()).count();
    let mut slots=vec![None;plan.nodes.len()];let mut bytes=0;
    for (id,node) in plan.nodes.iter().enumerate() {
        if !plan.live[id] {continue;}
        if matches!(node.value,Value::Binary{bits:128,..}|Value::Unary{bits:128,..}) {return Err("native_integer_128");}
        if let Value::Input(index)=node.value {if index>=if call_frame {64} else {2048} {return Err("native_argument_limit");}}
        if registers[id].is_none() && !matches!(node.value,Value::Constant(_)|Value::Input(_)|Value::Base(_)) {slots[id]=Some(bytes);bytes+=if node.width>8 {16} else {8};}
    }
    let stack_bytes=(bytes+15)&!15;if stack_bytes>32752 {return Err("native_stack_limit");}
    if call_frame {
        // Scaled LDR/STR offsets must fit even after allocating private spills.
        let mut end=CALL_OUTPUT+std::mem::size_of::<Output>();
        for (id,node) in plan.nodes.iter().enumerate() {
            if plan.live[id] {if let Value::Input(index)=node.value {end=end.max(CALL_ARGUMENTS+(index+1)*16);}}
        }
        if stack_bytes+end>32768 {return Err("native_call_stack_limit");}
    }
    let status=if call_frame {9} else {0};
    let success_steps=if optimize_commit {plan.success_steps} else {None};
    let mut a=Emitter{plan,words:vec![],slots,stack_bytes,registers,labels:vec![None;plan.blocks.len()],jumps:vec![],failures:vec![],exhausted:false,profiled,call_frame,heap,fixed_steps:success_steps};
    // This function owns only its private scratch/output. The standalone
    // guard returns before touching either; other failures discard private work.
    let short=if check_budget {
        a.imm(9,plan.maximum_steps as u64);a.cmp(3,9);let at=a.words.len();a.emit(0x54000003);Some(at)
    } else {None};
    a.stack(false);if success_steps.is_none() {a.output_store(31,16);}if profiled {for i in 0..8 {a.output_store(31,24+i*8);}}
    for block in 0..plan.blocks.len() {
        if !plan.reachable[block] {continue;}a.labels[block]=Some(a.words.len());a.charge_block(block);
        for pc in plan.blocks[block].start..plan.blocks[block].end {
            for &id in &plan.computations[pc] {if plan.live[id] {a.node(id)?;}}
            match &plan.effects[pc] {
                Effect::None=>{},
                Effect::Assert{value,expected,..}=>{a.get(9,*value,false);a.get(10,*value,true);a.three(0xaa000000,9,9,10);a.cmp(9,31);a.fail(if *expected {0} else {1});},
                Effect::Trap(_)=>{a.cmp(31,31);a.fail(0);},
                Effect::Return(value)=>{
                    // A zero-byte result has no destination or readable lane.
                    if !optimize_commit || plan.result_size!=0 {
                        a.get(9,*value,false);a.get(10,*value,true);a.output_store(9,0);a.output_store(10,8);
                    }
                    a.stack(true);a.mov(status,31);a.emit(0xd65f03c0);
                },
                Effect::Jump(pc)=>a.edge(block,plan.at[*pc])?,
                Effect::Switch{value,cases,otherwise}=>{
                    a.get(9,*value,false);a.get(10,*value,true);let mut targets=vec![];
                    for (value,target) in cases {
                        a.imm(11,*value as u64);a.imm(12,(*value>>64) as u64);
                        a.three(0xca000000,13,9,11);a.three(0xca000000,14,10,12);a.three(0xaa000000,13,13,14);a.cmp(13,31);
                        targets.push((a.words.len(),plan.at[*target]));a.emit(0x54000000);
                    }
                    a.edge(block,plan.at[*otherwise])?;
                    for (at,target) in targets {a.patch(at,a.words.len(),true)?;a.edge(block,target)?;}
                },
            }
        }
        let end=plan.blocks[block].end;
        if !matches!(plan.effects[end-1],Effect::Return(_)|Effect::Trap(_)|Effect::Jump(_)|Effect::Switch{..}) {a.edge(block,plan.at[end])?;}
    }
    let failed=a.words.len();a.stack(true);let declined=a.words.len();a.imm(status,1);a.emit(0xd65f03c0);
    if let Some(short)=short {a.patch(short,declined,true)?;}
    for at in std::mem::take(&mut a.failures) {a.patch(at,failed,true)?;}
    for (at,block) in std::mem::take(&mut a.jumps) {a.patch(at,a.labels[block].ok_or("native_missing_block")?,false)?;}
    if a.exhausted {return Err("native_word_limit");}
    if eliminate_dead {
        // Unknown future encodings or nonconforming CFGs keep their original
        // qualified emission. All branch relocations finish before publication.
        let compact=if call_frame {dead::eliminate_call(&a.words)} else {dead::eliminate(&a.words)};
        if let Ok(compact)=compact {a.words=compact;}
    }
    Ok(Emitted{words:a.words,stack_bytes,profiled,register_values,success_steps})
}

#[cfg(all(target_arch="aarch64",target_os="macos"))]
pub struct Native {code:memory::Code,pub emitted:Emitted,argument_widths:Vec<usize>,frame_size:usize}
#[cfg(all(target_arch="aarch64",target_os="macos"))]
impl Native {
    pub fn compile(plan:&Plan,f:&Function,profiled:bool)->Result<Self,String> {
        let emitted=emit(plan,profiled).map_err(str::to_string)?;
        let mut code=memory::Code::reserve(MAX_CODE_BYTES)?;assert_eq!(code.append(&emitted.words)?,0);
        Ok(Self{code,emitted,argument_widths:f.args.iter().map(|s|s.size).collect(),frame_size:f.frame_size.max(1)})
    }
    pub fn attempt(&self,args:&[u128],base:usize,budget:usize)->Result<Option<Output>,String> {
        if args.len()!=self.argument_widths.len() || base.checked_add(self.frame_size).is_none() {return Err("invalid native scalar inputs".into());}
        if args.iter().zip(&self.argument_widths).any(|(v,size)|*size<16 && *v>>(*size*8)!=0) {return Err("native scalar input width".into());}
        let mut output=Output{value:u128::MAX,steps:u64::MAX,visited:[u64::MAX;8]};
        // The generated code reads the exact argument slice and writes only
        // this private Output plus bounded stack slots. It preserves all
        // callee-saved registers, never calls host code, and never dereferences
        // base or the unused heap/cursor arguments.
        let status=unsafe {self.code.call(0,args.as_ptr().cast_mut(),base,std::ptr::from_mut(&mut output).cast(),budget,0,
            std::ptr::null_mut(),0,std::ptr::null_mut())};
        match status {0=>Ok(Some(output)),1=>Ok(None),_=>Err("invalid native scalar status".into())}
    }
}

#[cfg(all(test,target_arch="aarch64",target_os="macos"))]
#[path="native_leaf_tests.rs"]
mod tests;

#[cfg(all(test,target_arch="aarch64",target_os="macos"))]
#[path="native_register_census.rs"]
mod register_census;

#[cfg(all(test,target_arch="aarch64",target_os="macos"))]
#[path="native_commit_census.rs"]
mod commit_census;
