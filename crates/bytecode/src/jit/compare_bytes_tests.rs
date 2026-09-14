use super::*;
use crate::{Engine, Limits, Memory, Slot, VERSION, execute_profiled, execute_with_engine};
const LIVE: u128 = 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef;

fn program(heap: bool, dst: Reg, inputs: [Reg;3]) -> Program {
    Program {version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,
        data:vec![],statics:if heap {vec![0;16]} else {vec![]},thread_locals:vec![],
        functions:vec![Function {name:"dynamic_byte_comparison".into(),frame_size:64,frame_align:16,
            registers:9,args:vec![],result:Slot {offset:0,size:16},code:vec![
                Op::Binary {dst:4,overflow:7,op:Binary::Sub,a:4,b:6,bits:128,signed:false},
                Op::CompareBytes {dst,left:inputs[0],right:inputs[1],size:inputs[2]},
                Op::Imm {dst:5,value:19},
                Op::Unary {dst:5,src:dst,bits:128,op:Unary::CountOnes},
                Op::Unary {dst:5,src:4,bits:128,op:Unary::CountOnes},Op::Return,
            ]}]
    }
}
fn memory() -> Memory {
    let mut heap=crate::heap::Heap::default();heap.bytes=vec![0x55;2048];
    Memory {bytes:vec![0x55;2048].into(),heap,limit:8192,readonly_end:128,peak:4096,auxiliary_bytes:0}
}
fn ordering(m: &Memory, left: usize, right: usize, size: usize) -> Result<u128,String> {
    let a=m.read(left,size)?;let b=m.read(right,size)?;
    Ok(match a.cmp(b) {std::cmp::Ordering::Less=>u32::MAX as u128,std::cmp::Ordering::Equal=>0,std::cmp::Ordering::Greater=>1})
}
fn probe(jit:&Jit<'_>,m:&mut Memory,values:[u128;3],dst:Reg,profiled:bool)->Result<u128,String> {
    let mut r=[values[0],values[1],values[2],LIVE,LIVE,0,0,0,LIVE];let mut hits=[0;6];
    let outcome=unsafe {jit.run(jit.blocks[0][0].unwrap(),6,3,
        if profiled {hits.as_mut_ptr()} else {std::ptr::null_mut()},r.as_mut_ptr(),128,
        m.bytes.as_mut_ptr(),m.bytes.len(),m.readonly_end,m.heap.bytes.as_mut_ptr(),m.heap.bytes.len())};
    let (next,steps)=outcome?;assert_eq!((next,steps),(3,3));
    assert_eq!(r[4],LIVE,"native cache survives byte comparison");assert_eq!(r[8],LIVE);
    assert_eq!(hits,[u64::from(profiled),0,0,0,0,0]);Ok(r[dst as usize])
}
#[test]
fn native_byte_comparison_matches_ordering_across_lengths_alignments_arenas_and_dest_aliases() {
    let lengths:Vec<usize>=(0..=17).chain([23,31,32,33,63,64,65,127,128,129,255,256,257,512]).collect();
    for heap in [false,true] {for dst in 0..=3 {for profiled in [false,true] {
        let p=program(heap,dst,[0,1,2]);crate::validate(&p).unwrap();
        let mut jit=Jit::new(&p,profiled,MAX_CODE_BYTES).unwrap();jit.ensure_function(0).unwrap();
        assert_eq!(jit.blocks[0][0].unwrap().end,3);
        for &length in &lengths {for align in 0..16 {
            for left_heap in [false,true].into_iter().filter(|h|heap||!*h) {
                for right_heap in [false,true].into_iter().filter(|h|heap||!*h) {
                    let left=256+align+if left_heap {crate::heap::TAG} else {0};
                    let right=1024+(align*7)%16+if right_heap {crate::heap::TAG} else {0};
                    let mut positions=vec![None];
                    if length<=17 {positions.extend((0..length).map(Some));}
                    else {positions.extend([0,7,8,15,length-1].into_iter().map(Some));}
                    for position in positions {for byte in [0u8,255] {
                        let mut m=memory();
                        if let Some(pos)=position {
                            let offset=left%crate::heap::TAG+pos;
                            let bytes=if left_heap {&mut m.heap.bytes[..]} else {&mut m.bytes[..]};bytes[offset]=byte;
                            // Opposite later difference catches little-endian integer ordering.
                            if pos+1<length {bytes[offset+1]=255-byte;}
                        }
                        let expected=ordering(&m,left,right,length).unwrap();
                        let original=(m.bytes.to_vec(),m.heap.bytes.clone());
                        assert_eq!(probe(&jit,&mut m,[left as u128,right as u128,length as u128],dst,profiled).unwrap(),expected,
                            "len={length},align={align},position={position:?},dst={dst}");
                        assert_eq!((m.bytes.to_vec(),m.heap.bytes.clone()),original);
                    }}
                }
            }
        }}
    }}}
}
#[test]
fn native_byte_comparison_checks_full_ranges_and_accepts_empty_dangling_ranges() {
    for heap in [false,true] {for profiled in [false,true] {
        let p=program(heap,3,[0,1,2]);let mut jit=Jit::new(&p,profiled,MAX_CODE_BYTES).unwrap();jit.ensure_function(0).unwrap();
        for length in [1,7,8,9,15,16,17,129,512,2048,usize::MAX] {
            let mut addresses=vec![0,1,127,128,2047,2048,2049,usize::MAX,crate::heap::TAG,crate::heap::TAG+1,crate::heap::TAG+2047,crate::heap::TAG+2048];
            if length<=2048 {addresses.extend([2048-length,2049-length]);}
            for address in addresses {for (left,right) in [(address,256),(256,address)] {
                let mut m=memory();m.bytes[256]=0;m.bytes[257]=255;
                // With no guest heap in the program, tagged addresses must fault.
                let expected=if !heap && (left>=crate::heap::TAG||right>=crate::heap::TAG) {Err("no heap".into())} else {ordering(&m,left,right,length)};
                let original=(m.bytes.to_vec(),m.heap.bytes.clone());
                let result=probe(&jit,&mut m,[left as u128,right as u128,length as u128],3,profiled);
                if let Ok(value)=expected {assert_eq!(result.unwrap(),value);} else {assert_eq!(result.unwrap_err(),"JIT guest memory access failed");}
                assert_eq!((m.bytes.to_vec(),m.heap.bytes.clone()),original);
            }}
        }
        for left in [0,1,usize::MAX,crate::heap::TAG] {for right in [0,17,usize::MAX,crate::heap::TAG] {
            let mut m=memory();assert_eq!(probe(&jit,&mut m,[left as u128,right as u128,0],3,profiled).unwrap(),0);
        }}
        // High halves are truncated exactly as the interpreter's usize casts.
        let mut m=memory();m.bytes[256]=1;
        assert_eq!(probe(&jit,&mut m,[(1u128<<100)|256,(1u128<<90)|512,(1u128<<80)|1],3,profiled).unwrap(),u32::MAX as u128);
    }}
}
#[test]
fn native_byte_comparison_accepts_aliased_inputs_and_overlapping_read_ranges() {
    for inputs in [[0,0,2],[0,1,0],[0,1,1],[0,0,0]] {for dst in 0..=3 {
        let p=program(true,dst,inputs);let mut jit=Jit::new(&p,false,MAX_CODE_BYTES).unwrap();jit.ensure_function(0).unwrap();
        for values in [[16u128,32,7],[32,16,0],[0,0,0],[256,257,129]] {
            let mut m=memory();for (i,b) in m.bytes.iter_mut().enumerate() {*b=(i*71) as u8;}
            let expected=ordering(&m,values[inputs[0] as usize] as usize,values[inputs[1] as usize] as usize,values[inputs[2] as usize] as usize);
            let result=probe(&jit,&mut m,values,dst,false);
            assert_eq!(result.unwrap(),expected.unwrap());
        }
    }}
}
#[test]
fn native_byte_comparison_preserves_budgets_profiles_and_code_limit_fallback() {
    for length in [0,1,7,8,9,16,17,32,33] {for sign in [-1i32,0,1] {
        let mut p=program(false,3,[0,1,2]);p.functions[0].frame_size=160;
        let f=&mut p.functions[0];f.code=vec![
            Op::Local {dst:0,offset:32},Op::Local {dst:1,offset:80},Op::Imm {dst:2,value:length as u128},
            Op::Imm {dst:4,value:if sign<0 {1} else {2}},Op::Store {address:0,src:4,size:1},
            Op::Imm {dst:4,value:if sign>0 {1} else {2}},Op::Store {address:1,src:4,size:1},
            Op::CompareBytes {dst:0,left:0,right:1,size:2},Op::Local {dst:1,offset:0},
            Op::Store {address:1,src:0,size:16},Op::Return,
        ];
        for budget in 0..=12 {for code_budget in [0,MAX_CODE_BYTES] {
            let limits=||Limits {instructions:budget,jit_code_bytes:code_budget,..Limits::default()};
            let native=execute_with_engine(&p,&[],limits(),Engine::Jit);
            let interpreted=execute_with_engine(&p,&[],limits(),Engine::Interpreter);
            let observed=execute_profiled(&p,&[],limits(),Engine::Jit);
            if budget<11 {
                assert_eq!(native.unwrap_err(),"interpreter instruction limit exceeded");
                assert_eq!(interpreted.unwrap_err(),"interpreter instruction limit exceeded");
                assert_eq!(observed.unwrap_err(),"interpreter instruction limit exceeded");
            } else {
                let native=native.unwrap();let interpreted=interpreted.unwrap();let (observed,profile)=observed.unwrap();
                let expected=if length==0||sign==0 {0} else if sign<0 {u32::MAX as u128} else {1};
                assert_eq!(native.value,expected);assert_eq!(interpreted.value,expected);assert_eq!(observed.value,expected);
                assert_eq!(native.instructions,11);assert_eq!(interpreted.instructions,11);assert_eq!(observed.instructions,11);
                assert_eq!(profile.functions[0].interpreted[7],u64::from(code_budget==0));
                if code_budget>0 {assert_eq!(native.jit_instructions,10);assert_eq!(native.jit_entries,1);}
            }
        }}
    }}
}
