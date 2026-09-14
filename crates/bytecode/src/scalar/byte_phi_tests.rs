use super::*;
use crate::{Program,Slot,VERSION,Limits,Engine};

pub(super) fn fixture(width:usize,first:usize,second:usize,fragmented:bool)->(Program,Plan) {
    assert!(width>0 && first+width<=16 && second+width<=16);
    let mut code=vec![Op::Local{dst:4,offset:32},Op::Load{dst:5,address:4,size:8},
        Op::Local{dst:6,offset:48},Op::Imm{dst:1,value:0xa5a5a5a5a5a5a5a5_a5a5a5a5a5a5a5a5},
        Op::Store{address:6,src:1,size:16},Op::Switch{value:5,cases:vec![],otherwise:0}];
    let a=code.len();code.extend([Op::Local{dst:7,offset:first},Op::Copy{src:7,dst:6,size:width},Op::Jump{target:0}]);
    let jump=code.len()-1;let b=code.len();
    if fragmented && width>1 {
        code.extend([Op::Local{dst:7,offset:16+second+1},Op::Copy{src:7,dst:6,size:width-1},
            Op::Local{dst:7,offset:16+second},Op::Local{dst:0,offset:48+width-1},Op::Copy{src:7,dst:0,size:1}]);
    } else {code.extend([Op::Local{dst:7,offset:16+second},Op::Copy{src:7,dst:6,size:width}]);}
    let join=code.len();code.push(Op::Return);
    code[5]=Op::Switch{value:5,cases:vec![(0,a)],otherwise:b};code[jump]=Op::Jump{target:join};
    let p=Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![],statics:vec![],thread_locals:vec![],
        functions:vec![Function{name:"contiguous byte phis".into(),frame_size:64,frame_align:8,registers:8,
            args:vec![Slot{offset:0,size:16},Slot{offset:16,size:16},Slot{offset:32,size:8}],
            result:Slot{offset:48,size:16},code}]};
    crate::validate(&p).unwrap();let memory=crate::proof::memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());
    assert!(memory.eligible,"{:?}",memory.decline);
    let plan=lower(&p.functions[0],&memory,250_000).unwrap();(p,plan)
}
fn check(p:&Program,plan:&Plan) {
    for (a,b) in [(0,u128::MAX),(0x0123456789abcdef_fedcba9876543210,0x8877665544332211_ffeeddccbbaa0099)] {
        for choose in [0,1] {for budget in 0..=plan.maximum_steps+1 {
            let expected=crate::execute_profiled(p,&[a,b,choose],Limits{instructions:budget as u64,..Limits::default()},Engine::Interpreter);
            let actual=plan.evaluate(&[a,b,choose],16,budget,&p.functions[0].name);
            match (expected,actual) {
                (Ok((e,profile)),Ok(s))=>{
                    assert_eq!(e.value,s.value);assert_eq!(e.instructions,s.pcs.len() as u64);
                    let mut hits=vec![0;p.functions[0].code.len()];for pc in s.pcs {hits[pc]+=1;}
                    assert_eq!(hits,profile.functions[0].interpreted);
                },(Err(e),Err(s))=>assert_eq!(e,s),(e,s)=>panic!("bytecode {e:?}, scalar {s:?}"),
            }
        }}
    }
}
#[test]
fn contiguous_byte_phis_preserve_all_widths_offsets_and_budgets() {
    for width in 1..=16 {for first in 0..=16-width {
        let (p,plan)=fixture(width,first,16-width,false);
        let phis:Vec<_>=plan.nodes.iter().zip(&plan.live).filter(|(n,live)|**live && matches!(n.value,Value::Phi(_))).collect();
        assert_eq!(phis.len(),1);assert_eq!(phis[0].0.width,width as u8);
        check(&p,&plan);
    }}
}
#[test]
fn byte_phis_split_when_one_predecessor_changes_source_order() {
    for width in 2..=16 {
        let (p,plan)=fixture(width,16-width,0,true);
        let widths:Vec<_>=plan.nodes.iter().zip(&plan.live).filter(|(n,live)|**live && matches!(n.value,Value::Phi(_))).map(|(n,_)|n.width).collect();
        assert_eq!(widths,vec![(width-1) as u8,1]);check(&p,&plan);
    }
}
