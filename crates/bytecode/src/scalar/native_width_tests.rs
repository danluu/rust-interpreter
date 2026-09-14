use super::*;
use crate::{Program,Slot,VERSION};

fn mask_bits(bits:u16)->u128 {if bits==128 {u128::MAX} else {(1u128<<bits)-1}}
fn node(value:Value)->Node {Node{value,width:16,pc:Some(0)}}

#[test]
fn native_scalar_width_bounds_cover_signed_arithmetic_and_full_width_values() {
    let ops=[Binary::Add,Binary::Sub,Binary::Mul,Binary::Div,Binary::Rem,Binary::And,Binary::Or,Binary::Xor,
        Binary::Shl,Binary::Shr,Binary::RotateLeft,Binary::RotateRight,Binary::Eq,Binary::Ne,Binary::Lt,
        Binary::Le,Binary::Gt,Binary::Ge,Binary::Cmp];
    let mut seed=0x123456789abcdef0u128;
    for bits in [8,16,32,64,128] {for bound in [0,1,7,8,15,31,32,63,64,127,128] {
        for signed in [false,true] {for op in ops {for _ in 0..8 {
            seed^=seed<<13;seed^=seed>>7;seed^=seed<<17;
            let a=seed&mask_bits(bound);let b=(seed.rotate_left(53))&mask_bits(bound);
            if let Ok((value,over))=crate::binary(op,a,b,bits,signed) {
                for (overflow,value) in [(false,value),(true,u128::from(over))] {
                    let n=node(Value::Binary{a:0,b:1,op,bits,signed,overflow});
                    let result=bit_bound(&n,&[bound,bound]);
                    assert_eq!(value&!mask_bits(result),0,"{op:?} bits={bits} signed={signed} overflow={overflow}");
                }
            }
        }}}
    }}
    for from in [8,16,32,64,128] {for to in [8,16,32,64,128] {for signed in [false,true] {
        for bound in [0,1,7,8,15,31,32,63,64,127,128] {
            for value in [0,1,mask_bits(bound),mask_bits(bound)>>1] {
                let value=value&mask_bits(bound);
                let n=node(Value::Cast{src:0,from,to,signed});let result=bit_bound(&n,&[bound]);
                let cast=if signed {(((value<<(128-from)) as i128)>>(128-from)) as u128} else {value&mask(from)};
                assert_eq!((cast&mask(to))&!mask_bits(result),0);
            }
        }
    }}}
    assert_eq!(bit_bound(&node(Value::Cast{src:0,from:8,to:64,signed:true}),&[8]),64);
    assert_eq!(bit_bound(&node(Value::Cast{src:0,from:8,to:64,signed:true}),&[7]),7);
}

#[test]
fn native_scalar_width_aliases_preserve_fault_roots_high_results_and_budget_tails() {
    let p=Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![],statics:vec![],thread_locals:vec![],
        functions:vec![Function{name:"width aliases".into(),frame_size:16,frame_align:8,registers:8,
            args:vec![Slot{offset:0,size:8}],result:Slot{offset:0,size:16},code:vec![
                Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},Op::Imm{dst:2,value:127},
                Op::Binary{dst:3,overflow:4,op:Binary::Eq,a:1,b:2,bits:64,signed:false},
                Op::Local{dst:0,offset:8},Op::Store{address:0,src:3,size:1},Op::Load{dst:3,address:0,size:1},
                Op::Cast{dst:3,src:3,from:8,to:64,signed:true},Op::Cast{dst:3,src:3,from:64,to:128,signed:false},
                Op::Cast{dst:5,src:1,from:8,to:128,signed:true},
                Op::Select{dst:5,condition:3,yes:3,no:5},
                // Its unused quotient still has to fault for a zero divisor.
                Op::Binary{dst:6,overflow:7,op:Binary::Div,a:2,b:1,bits:64,signed:false},
                Op::Local{dst:0,offset:0},Op::Store{address:0,src:5,size:16},Op::Return,
            ]}]};
    crate::validate(&p).unwrap();
    let memory=crate::proof::memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());
    let plan=lower(&p.functions[0],&memory,250_000).unwrap();let simplified=simplify(&plan).unwrap().unwrap();
    assert_eq!(simplified.maximum_steps,plan.maximum_steps);
    assert!(simplified.live.iter().filter(|&&l|l).count()<plan.live.iter().filter(|&&l|l).count());
    for (id,n) in plan.nodes.iter().enumerate() {if plan.live[id] && matches!(n.value,Value::Binary{op:Binary::Div|Binary::Rem,..}) {assert!(simplified.live[id]);}}
    for profiled in [false,true] {
        let old=emit_inner(&plan,profiled,true,true,true,false).unwrap();let new=emit(&plan,profiled).unwrap();
        assert!(new.words.len()<old.words.len());
        let make=|emitted:Emitted| {
            let mut code=memory::Code::reserve(MAX_CODE_BYTES).unwrap();assert_eq!(code.append(&emitted.words).unwrap(),0);
            Native{code,emitted,argument_widths:vec![8],frame_size:16}
        };
        let old=make(old);let new=make(new);
        for input in [0,1,127,128,255,256,1<<63,u64::MAX as u128] {for budget in 0..=plan.maximum_steps+1 {
            let expected=plan.evaluate(&[input],16,budget,"width aliases");
            let simplified_result=simplified.evaluate(&[input],16,budget,"width aliases");
            assert_eq!(expected,simplified_result);
            let actual=new.attempt(&[input],16,budget).unwrap();assert_eq!(actual,old.attempt(&[input],16,budget).unwrap());
            if let Some(actual)=actual {
                let expected=expected.unwrap();assert_eq!(actual.value,expected.value);assert_eq!(actual.steps as usize,expected.pcs.len());
                if profiled {let mut visited=[0;8];for pc in expected.pcs {visited[pc/64]|=1u64<<(pc%64);}assert_eq!(actual.visited,visited);}
            } else {assert!(budget<plan.maximum_steps || expected.is_err());}
        }}
    }
    let mut excessive=plan.clone();excessive.nodes.push(node(Value::Pack(vec![Slice{value:0,byte:0,size:1};MAX_WORK/4+1])));excessive.live.push(true);
    assert!(matches!(simplify(&excessive),Err("native_width_work_limit")));
    let mut forward=plan.clone();forward.nodes.push(node(Value::Cast{src:forward.nodes.len()+1,from:8,to:64,signed:false}));forward.live.push(true);
    assert!(matches!(simplify(&forward),Err("native_width_order")));
}
