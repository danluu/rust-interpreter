use super::*;

fn fixture(code:Vec<Op>)->Function {
    Function{name:"retained value model".into(),frame_size:128,frame_align:16,registers:16,
        args:vec![],result:crate::Slot{offset:0,size:0},code}
}
fn narrow(v:u128,size:usize)->u128 {if size==16 {v}else{v&((1u128<<(size*8))-1)}}

#[derive(Debug,PartialEq,Eq)]
struct Snapshot {bytes:Vec<u8>,registers:Vec<u128>,steps:usize,error:Option<String>}

fn execute(f:&Function,p:Option<&Plan>,seed:u128,unknown:usize,budget:usize)->(Snapshot,usize) {
    let mut memory=crate::Memory{bytes:(0..192).map(|i|((seed.rotate_left((i%128)as u32))as u8).wrapping_add(i as u8)).collect::<Vec<_>>().into(),
        heap:crate::heap::Heap::default(),limit:4096,readonly_end:32,peak:192,auxiliary_bytes:0};
    let mut registers:Vec<_>=(0..16).map(|i|seed.rotate_left(i)).collect();registers[7]=unknown as u128;
    let mut slots=[None;15];let(mut steps,mut error,mut reuses)=(0,None,0);
    for(pc,op)in f.code.iter().enumerate() {
        if steps==budget {error=Some("instruction limit".into());break;}
        steps+=1;
        let mut captured=None;
        let mut load=|value:u128,size:usize|->u128 {
            if let Some(reuse)=p.and_then(|p|p.uses.get(&pc)) {
                assert_eq!(reuse.size,size);
                let (origin,bits)=slots[reuse.slot].expect("live capture");
                assert_eq!(origin,reuse.origin_pc);
                assert_eq!(bits,value,"pc={pc}, origin={origin}, seed={seed:x}");
                reuses+=1;bits
            }else{value}
        };
        let step=(||->Result<(),String> {
            match *op {
                Op::Imm{dst,value}=>registers[dst as usize]=value,
                Op::Local{dst,offset}=>registers[dst as usize]=(64+offset)as u128,
                Op::Load{dst,address,size}=>{
                    let value=memory.load(registers[address as usize]as usize,size.into())?;
                    let value=load(value,size.into());captured=Some(value);registers[dst as usize]=value;
                },
                Op::Store{address,src,size}=>{
                    let value=registers[src as usize];memory.store(registers[address as usize]as usize,size.into(),value)?;
                    captured=Some(narrow(value,size.into()));
                },
                Op::Copy{src,dst,size}=>{
                    let value=memory.load(registers[src as usize]as usize,size)?;
                    let value=load(value,size);captured=Some(value);
                    if p.and_then(|p|p.uses.get(&pc)).is_some() {memory.store(registers[dst as usize]as usize,size,value)?;}
                    else{memory.copy(registers[src as usize]as usize,registers[dst as usize]as usize,size)?;}
                },
                Op::Binary{dst,overflow,op,a,b,bits,signed}=>{
                    let(v,o)=crate::binary(op,registers[a as usize],registers[b as usize],bits,signed)?;
                    registers[dst as usize]=v;registers[overflow as usize]=o as u128;
                },
                Op::Assert{value,expected,..}=>if(registers[value as usize]!=0)!=expected{return Err("assertion".into());},
                Op::Return=>{},
                _=>panic!("unreviewed model fixture operation"),
            }
            Ok(())
        })();
        if let Err(e)=step {error=Some(e);break;}
        if let Some(c)=p.and_then(|p|p.captures.get(&pc)) {
            slots[c.slot]=Some((pc,narrow(captured.expect("capture has original materialized bits"),c.size)));
        }
    }
    (Snapshot{bytes:memory.bytes.to_vec(),registers,steps,error},reuses)
}

fn compare(f:&Function)->usize {
    let mut hits=0;
    for capacity in [0,1,2,15] {
        let p=plan(f,0,f.code.len(),capacity,&mut 100_000).unwrap();
        for seed in [0,1,u128::MAX,0xfedc_ba98_7654_3210_0123_4567_89ab_cdef] {
            for address in [16,48,64,68,72,80,184,192,usize::MAX] {
                for budget in 0..=f.code.len() {
                    let expected=execute(f,None,seed,address,budget);
                    let actual=execute(f,Some(&p),seed,address,budget);
                    assert_eq!(actual.0,expected.0,"capacity={capacity} address={address} budget={budget}");
                    hits+=actual.1;
                }
            }
        }
    }
    hits
}

#[test]
fn concrete_origins_survive_read_aliases_and_arbitrary_scratch_register_changes() {
    for width in [4,8,16] {
        let f=fixture(vec![Op::Local{dst:0,offset:0},Op::Local{dst:1,offset:32},
            Op::Store{address:0,src:2,size:width},Op::Load{dst:3,address:7,size:8},
            Op::Copy{dst:1,src:0,size:width.into()},Op::Imm{dst:2,value:0},
            Op::Copy{dst:1,src:0,size:width.into()},Op::Load{dst:4,address:0,size:width},Op::Return]);
        assert!(compare(&f)>0);
    }
}

#[test]
fn writes_and_partial_overlaps_invalidate_exact_origins_without_deferring_memory() {
    for width in [4,8,16] {for partial in [1,3,4,7,8,15,16] {
        for store in [true,false] {
            let effect=if store {Op::Store{address:7,src:2,size:partial}}
                else{Op::Copy{dst:1,src:7,size:partial.into()}};
            let f=fixture(vec![Op::Local{dst:0,offset:0},Op::Local{dst:1,offset:4},
                Op::Store{address:0,src:2,size:width},Op::Load{dst:3,address:0,size:width},
                Op::Load{dst:4,address:0,size:width},effect,
                Op::Copy{dst:1,src:0,size:width.into()},Op::Load{dst:3,address:1,size:width},
                Op::Load{dst:4,address:1,size:width},Op::Return]);
            assert!(compare(&f)>0);
        }
    }}
}

#[test]
fn fault_prefixes_and_aliased_binary_outputs_keep_exact_frame_and_register_state() {
    for alias in [false,true] {for fault in [false,true] {
        let f=fixture(vec![Op::Local{dst:0,offset:0},Op::Imm{dst:1,value:8},
            Op::Load{dst:3,address:0,size:8},
            Op::Binary{dst:0,overflow:if alias{0}else{6},op:Binary::Add,a:0,b:1,bits:64,signed:false},
            Op::Store{address:0,src:2,size:8},Op::Local{dst:0,offset:0},
            Op::Load{dst:4,address:0,size:8},
            Op::Binary{dst:5,overflow:6,op:Binary::Div,a:2,b:if fault{6}else{1},bits:64,signed:false},
            Op::Load{dst:4,address:0,size:8},Op::Assert{value:2,expected:true,message:"preserve writes".into()},
            Op::Load{dst:5,address:0,size:8},Op::Return]);
        compare(&f);
    }}
}

#[test]
fn regions_capacity_profit_filter_and_work_limits_bound_the_plan() {
    let mut code=vec![];
    for i in 0..8 {code.extend([Op::Local{dst:0,offset:i*16},Op::Load{dst:2,address:0,size:8}]);}
    for _ in 0..3 {for i in 0..8 {code.extend([Op::Local{dst:0,offset:i*16},Op::Load{dst:2,address:0,size:8}]);}}
    let f=fixture(code);
    for capacity in [0,1,2,15] {
        let p=plan(&f,0,f.code.len(),capacity,&mut 100_000).unwrap();
        assert_eq!(p.captures.len(),capacity.min(8));assert!(p.captures.values().all(|v|v.slot<capacity));
    }
    assert!(compare(&f)>0);
    for budget in [0,1,8,32] {assert!(plan(&f,0,f.code.len(),15,&mut budget.clone()).is_none());}
    assert!(plan(&f,0,1025,15,&mut 100_000).is_none());
    assert!(plan(&f,0,f.code.len(),16,&mut 100_000).is_none());
    let f=fixture(vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},Op::Load{dst:2,address:0,size:8}]);
    assert!(plan(&f,0,3,15,&mut 100_000).unwrap().captures.is_empty(),"one narrow reuse does not pay capture cost");
    assert!(plan(&f,1,3,15,&mut 100_000).unwrap().uses.is_empty(),"region entry has no old address/value facts");
}
