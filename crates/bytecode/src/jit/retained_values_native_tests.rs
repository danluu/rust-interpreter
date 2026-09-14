use super::*;

// The host assembler is an independent test oracle only. Production emits
// numeric AArch64 words directly and does not call an assembler or codegen library.
std::arch::global_asm!(r#"
    .text
    .p2align 2
    .globl _retained_value_encoding_probe
_retained_value_encoding_probe:
    fmov s17, w9
    fmov d18, x9
    mov v19.d[1], x10
    fmov w9, s17
    fmov x9, d18
    mov x10, v19.d[1]
    str s17, [x11, #12]
    str d18, [x11, #24]
    str q19, [x11, #32]
    ret
"#);
unsafe extern "C" {fn retained_value_encoding_probe();}

#[test]
fn direct_words_match_host_assembler_and_preserve_only_reviewed_scratch_values() {
    let expected=[0x1e270000|(9<<5)|17,0x9e670000|(9<<5)|18,0x4e181c00|(10<<5)|19,
        0x1e260000|(17<<5)|9,0x9e660000|(18<<5)|9,0x4e183c00|(19<<5)|10,
        0xbd000000|(3<<10)|(11<<5)|17,0xfd000000|(3<<10)|(11<<5)|18,
        0x3d800000|(2<<10)|(11<<5)|19,0xd65f03c0];
    // SAFETY: this symbol names the exact ten-instruction immutable host text
    // sequence above, aligned to a u32. It is read, never called or modified.
    let actual=unsafe{std::slice::from_raw_parts(retained_value_encoding_probe as *const u32,expected.len())};
    assert_eq!(actual,expected);
    for (i,&word)in expected.iter().enumerate() {
        assert_eq!(scratch_values::preserves_x9(word),matches!(i,0|1|2|6|7|8),"word={word:x}");
    }
    for reg in 17..32 {
        for opcode in [0x1e270000,0x9e670000,0x4e181c00] {assert!(scratch_values::preserves_x9(opcode|(9<<5)|reg));}
        assert!(!scratch_values::preserves_x9(0x9e660000|(reg<<5)|9));
    }
}

#[derive(Debug,PartialEq,Eq)]
struct Snapshot {bytes:Vec<u8>,heap:Vec<u8>,peak:usize,readonly:usize,auxiliary:usize}
thread_local! {static SNAPSHOT:std::cell::RefCell<Option<Option<Snapshot>>>=const{std::cell::RefCell::new(None)};}
pub(in crate::jit) fn observe_memory(memory:&crate::Memory) {
    SNAPSHOT.with(|slot|if let Some(target)=slot.borrow_mut().as_mut(){
        *target=Some(Snapshot{bytes:memory.bytes.to_vec(),heap:memory.heap.bytes.to_vec(),peak:memory.peak,
            readonly:memory.readonly_end,auxiliary:memory.auxiliary_bytes});
    });
}
impl Drop for crate::Memory {fn drop(&mut self){observe_memory(self);}}
struct Reset;
impl Drop for Reset {fn drop(&mut self){SNAPSHOT.with(|s|{s.borrow_mut().take();});}}
fn snapshot<T>(f:impl FnOnce()->T)->(T,Snapshot) {
    SNAPSHOT.with(|s|assert!(s.replace(Some(None)).is_none()));let _reset=Reset;
    let result=f();let observed=SNAPSHOT.with(|s|s.borrow_mut().take().unwrap().expect("VM memory dropped"));
    (result,observed)
}

fn fixture(width:u8,offset:usize,effect:Op)->Program {
    let code=vec![Op::Local{dst:0,offset:16},Op::Load{dst:2,address:0,size:16},
        Op::Local{dst:0,offset:64},Op::Local{dst:1,offset},Op::Store{address:0,src:2,size:width},
        Op::Load{dst:3,address:0,size:width},Op::Load{dst:4,address:0,size:width},Op::Load{dst:5,address:0,size:width},
        Op::Copy{src:0,dst:1,size:width.into()},effect,Op::Copy{src:0,dst:1,size:width.into()},
        Op::Load{dst:6,address:1,size:width},Op::Binary{dst:6,overflow:8,op:Binary::Xor,a:6,b:3,bits:128,signed:false},
        Op::Binary{dst:6,overflow:8,op:Binary::Xor,a:6,b:4,bits:128,signed:false},
        Op::Binary{dst:6,overflow:8,op:Binary::Xor,a:6,b:5,bits:128,signed:false},
        Op::Local{dst:0,offset:0},Op::Store{address:0,src:6,size:16},Op::Return];
    Program{version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![0x57;64],
        statics:vec![],thread_locals:vec![],functions:vec![Function{name:"retained native".into(),frame_size:256,
            frame_align:16,registers:9,args:vec![crate::Slot{offset:16,size:16}],result:crate::Slot{offset:0,size:16},code}]}
}
fn compare(p:&Program) {
    crate::validate(p).unwrap();
    let mut jit=Jit::new_resumable(p,false,MAX_CODE_BYTES,true).unwrap();jit.enable_scalar_calls();
    let emitted=jit.emit_function(&p.functions[0],MAX_CODE_BYTES/4).unwrap().unwrap();
    assert!(emitted.words.iter().any(|w|matches!(w&0xfffffc00,0x1e270000|0x9e670000) && w&31>=17),"retention is exercised");
    for input in [0,u128::MAX,0xfedc_ba98_7654_3210_0123_4567_89ab_cdef] {
        for budget in 0..=p.functions[0].code.len()as u64+1 {
            let limits=||crate::Limits{instructions:budget,..crate::Limits::default()};
            let (reference,expected)=snapshot(||crate::execute_profiled(p,&[input],limits(),crate::Engine::Interpreter));
            for persistent in [false,true] {for profiled in [false,true] {
                let limits=crate::Limits{jit_persistent_registers:persistent,jit_resumable_calls:true,jit_scalar_calls:true,..limits()};
                let (actual,memory)=snapshot(||if profiled {
                    crate::execute_profiled(p,&[input],limits,crate::Engine::Jit).map(|(e,p)|(e,Some(p)))
                }else{crate::execute_with_engine(p,&[input],limits,crate::Engine::Jit).map(|e|(e,None))});
                assert_eq!(memory,expected,"budget={budget} persistent={persistent} profiled={profiled}");
                match(&reference,actual) {
                    (Ok((r,rp)),Ok((a,ap)))=>{
                        assert_eq!((a.value,a.instructions,a.peak_memory),(r.value,r.instructions,r.peak_memory));
                        if let Some(ap)=ap {for (f,r)in ap.functions.iter().zip(&rp.functions) {
                            let mut logical=f.interpreted.clone();for(start,&hits)in f.jit_blocks.iter().enumerate(){
                                if hits!=0 {for n in &mut logical[start..f.jit_block_ends[start]]{*n+=hits;}}
                            }
                            assert_eq!(logical,r.interpreted);
                        }}
                    },
                    (Err(r),Err(a))=>assert!(a==*r || (a=="JIT guest memory access failed" &&
                        matches!(r.as_str(),"invalid guest memory access"|"write to read-only guest memory")),"{a} != {r}"),
                    (r,a)=>panic!("budget={budget}: {r:?} != {a:?}"),
                }
            }}
        }
    }
}

#[test]
fn native_retention_preserves_wide_high_lanes_overlap_faults_and_all_budget_prefixes() {
    for width in [4,8,16] {for offset in [63,64,65,68,72,96,127] {
        for effect in [Op::Imm{dst:3,value:0},Op::Assert{value:2,expected:true,message:"fault".into()},
            Op::Load{dst:4,address:2,size:8},Op::Store{address:2,src:3,size:4}] {
            compare(&fixture(width,offset,effect));
        }
    }}
}

#[test]
fn missing_capture_and_slot_replacement_cannot_reuse_an_old_value() {
    let mut a=Assembler::default();a.frame_size=64;a.facts.insert(0,crate::jit::Fact::Local(0));
    a.retained=State::new(Some(Plan{captures:BTreeMap::from([(0,Capture{slot:0,size:8}),(2,Capture{slot:0,size:8})]),
        uses:BTreeMap::from([(1,Reuse{slot:0,size:8,origin_pc:0}),(3,Reuse{slot:0,size:8,origin_pc:2})])}));
    a.current_pc=1;assert!(!a.retained_load(0,8));a.current_pc=0;a.capture_retained(8);
    a.current_pc=1;assert!(a.retained_load(0,8));a.current_pc=3;assert!(!a.retained_load(0,8));
    a.current_pc=2;a.capture_retained(8);a.current_pc=3;assert!(a.retained_load(0,8));
    for word in [0x3dc00000|(11<<5)|17,0x1e602800,0x4c407000,0x94000000,0xd63f0200] {
        a.current_pc=2;a.capture_retained(8);a.emit(word);a.current_pc=3;
        assert!(!a.retained_load(0,8),"unaudited writer/call {word:x}");
    }
}
