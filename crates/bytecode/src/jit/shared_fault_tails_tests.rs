use crate::jit::*;
use crate::{Engine, Limits, Slot, VERSION, execute_profiled};

fn fixture(last: Op) -> Program {
    let mut code=vec![
        Op::Local{dst:0,offset:0}, Op::Load{dst:1,address:0,size:8},
        Op::Local{dst:2,offset:16}, Op::Imm{dst:3,value:1},
        Op::Imm{dst:4,value:15}, Op::Store{address:2,src:4,size:8},
        Op::Binary{dst:5,overflow:6,op:Binary::Div,a:4,b:3,bits:64,signed:true},
        Op::Jump{target:8},
        Op::Load{dst:4,address:2,size:8},
        Op::Binary{dst:5,overflow:6,op:Binary::Div,a:4,b:3,bits:64,signed:true},
        Op::Store{address:2,src:5,size:8},Op::Jump{target:12},last,
        Op::Local{dst:2,offset:16}, Op::Store{address:2,src:5,size:8},Op::Return];
    // Distinct assertion identities remain outside the shared fault path.
    code.insert(12,Op::Assert{value:3,expected:true,message:"first assertion".into()});
    Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![0;64],
        statics:vec![],thread_locals:vec![],functions:vec![Function{name:"shared fault fixture".into(),
            frame_size:64,frame_align:16,registers:8,args:vec![Slot{offset:0,size:8}],
            result:Slot{offset:16,size:8},code}]}
}

fn counts(p:&crate::ExecutionProfile)->Vec<u64> {
    let f=&p.functions[0];let mut result=f.interpreted.clone();
    for (pc,&hits) in f.jit_blocks.iter().enumerate() {
        if hits!=0 { for x in &mut result[pc..f.jit_block_ends[pc]] {*x+=hits;} }
    }
    result
}

#[test]
fn shared_fault_native_status_assertions_and_all_budget_prefixes_match() {
    let cases=[
        Op::Load{dst:5,address:1,size:8},
        Op::Binary{dst:5,overflow:6,op:Binary::Div,a:4,b:1,bits:64,signed:true},
        Op::Assert{value:1,expected:true,message:"second assertion".into()},
    ];
    for last in cases {
        let division=matches!(last,Op::Binary{op:Binary::Div,..});
        let mut p=fixture(last);
        if division { p.functions[0].code[4]=Op::Imm{dst:4,value:1<<63}; }
        crate::validate(&p).unwrap();
        for argument in [0,1,64,u64::MAX as u128] {
            for budget in 0..=p.functions[0].code.len() as u64+1 {
                let reference=execute_profiled(&p,&[argument],Limits{instructions:budget,..Limits::default()},Engine::Interpreter);
                for persistent in [false,true] {for capacity in [0,MAX_CODE_BYTES] {
                    let actual=execute_profiled(&p,&[argument],Limits{instructions:budget,
                        jit_resumable_calls:true,jit_persistent_registers:persistent,jit_code_bytes:capacity,
                        ..Limits::default()},Engine::Jit);
                    match (&reference,actual) {
                        (Ok((a,ap)),Ok((b,bp)))=>{
                            assert_eq!((a.value,a.instructions,a.peak_memory),(b.value,b.instructions,b.peak_memory));
                            assert_eq!(counts(ap),counts(&bp));
                        },
                        (Err(a),Err(b))=>assert_eq!(*a,b),
                        (a,b)=>panic!("shared tail budget={budget},arg={argument}: {a:?} {b:?}"),
                    }
                }}
            }
        }
    }
}

#[test]
fn shared_fault_maps_reconstruct_real_backward_tail_branches() {
    let p=fixture(Op::Load{dst:5,address:1,size:8});
    for persistent in [false,true] {for profiled in [false,true] {
        let mut actual=Jit::new_resumable(&p,profiled,MAX_CODE_BYTES,persistent).unwrap();
        let mut reference=Jit::new_resumable(&p,profiled,MAX_CODE_BYTES,persistent).unwrap();
        reference.share_fault_tails=false;
        actual.ensure_function(0).unwrap();reference.ensure_function(0).unwrap();
        assert!(actual.bytes<reference.bytes);
        let mut bytes=vec![];actual.operation_map().unwrap().write(&mut bytes).unwrap();
        let map:serde_json::Value=serde_json::from_slice(&bytes).unwrap();
        let native=actual.code.as_ref().unwrap().published().1;
        let rows=map["functions"][0]["spans"].as_array().unwrap();
        let tails:Vec<_>=rows.iter().filter(|r|r["kind"]=="fault_tail").collect();
        let mut shared=0;
        for tail in &tails {
            let offset=tail["offset"].as_u64().unwrap() as usize;
            let end=tail["end"].as_u64().unwrap() as usize;
            if end-offset!=4 {continue;}
            let word=u32::from_le_bytes(native[offset..end].try_into().unwrap());
            assert_eq!(word&0xfc000000,0x14000000);
            let displacement=((word<<6) as i32)>>6;
            let target=(offset as i64+displacement as i64*4) as usize;
            assert!(target<offset);
            assert!(tails.iter().any(|r|r["offset"].as_u64()==Some(target as u64)
                &&r["end"].as_u64().unwrap()-target as u64>4));
            shared+=1;
        }
        assert!(shared>=3);
        assert_eq!(actual.operations,reference.operations);
        assert_eq!(actual.assertions,reference.assertions);
    }}
}
