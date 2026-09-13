use super::*;
use crate::Slot;

fn function(code:Vec<Op>)->Function {
    Function {name:"local overwrite proof".into(),frame_size:32,frame_align:16,registers:16,
        args:vec![],result:Slot {offset:0,size:0},code}
}
fn candidates(code:Vec<Op>)->Vec<usize> {
    let f=function(code);let report=analyze(&f,0,f.code.len(),&mut MAX_GLOBAL_WORK.clone());
    assert!(report.decline.is_none());report.candidates.iter().map(|c|c.pc).collect()
}
fn local(r:Reg,offset:usize)->Op {Op::Local {dst:r,offset}}
fn store(r:Reg,size:u8)->Op {Op::Store {address:r,src:15,size}}
fn read(r:Reg,size:u8)->Op {Op::Load {dst:14,address:r,size}}

#[test]
fn exact_partial_bytes_and_reads_preserve_only_fully_overwritten_writes() {
    let prefix=vec![local(0,0),local(1,4),local(2,8),store(0,8)];
    assert!(candidates([prefix.clone(),vec![store(0,4)]].concat()).is_empty());
    assert_eq!(candidates([prefix.clone(),vec![store(0,4),store(1,4)]].concat()),vec![3]);
    assert!(candidates([prefix.clone(),vec![read(1,1),store(0,8)]].concat()).is_empty());
    assert_eq!(candidates([prefix.clone(),vec![read(2,8),store(0,8)]].concat()),vec![3]);
    // Reading already overwritten bytes observes the newer write only.
    assert_eq!(candidates([prefix,vec![store(0,4),read(0,4),store(1,4)]].concat()),vec![3]);
    assert_eq!(candidates(vec![local(0,0),store(0,8),store(0,8),store(0,8)]),vec![1,2]);
}

#[test]
fn copies_observe_sources_before_destination_overwrites() {
    assert!(candidates(vec![local(0,0),store(0,8),Op::Copy {src:0,dst:0,size:8}]).is_empty());
    assert!(!candidates(vec![local(0,0),local(1,4),store(0,8),Op::Copy {src:0,dst:1,size:8},store(0,8)]).contains(&2));
    assert_eq!(candidates(vec![local(0,0),local(1,16),store(0,8),Op::Copy {src:1,dst:0,size:8}]),vec![2]);
    assert_eq!(candidates(vec![local(0,0),local(1,16),Op::Copy {src:1,dst:0,size:8},store(0,8)]),vec![2]);
}

#[test]
fn errors_unknown_accesses_and_region_entries_are_observation_barriers() {
    let barriers=vec![read(7,8),store(7,8),Op::Copy {src:7,dst:0,size:8},
        Op::Copy {src:0,dst:7,size:8},Op::Return,Op::Jump {target:0},
        Op::Trap {message:"stop".into()},
        Op::Assert {value:7,expected:true,message:"check".into()},
        Op::Call {function:0,args:vec![0],destination:0},
        Op::Binary {dst:3,overflow:4,op:Binary::Div,a:5,b:6,bits:64,signed:false},
        Op::Binary {dst:3,overflow:4,op:Binary::Rem,a:5,b:6,bits:64,signed:true}];
    for barrier in barriers {
        assert!(candidates(vec![local(0,0),store(0,8),barrier,store(0,8)]).is_empty());
    }
    assert!(candidates(vec![local(0,31),store(0,8),store(0,8)]).is_empty());
    let f=function(vec![local(0,0),store(0,8),store(0,8)]);
    assert!(analyze(&f,1,3,&mut MAX_GLOBAL_WORK.clone()).candidates.is_empty());
    assert!(analyze(&f,0,2,&mut MAX_GLOBAL_WORK.clone()).candidates.is_empty());
}

#[test]
fn constant_offsets_extents_and_output_aliases_remain_conservative() {
    let prefix=vec![local(0,0),store(0,8),Op::Imm {dst:1,value:(1u128<<100)+0},
        Op::Binary {dst:2,overflow:3,op:Binary::Add,a:0,b:1,bits:64,signed:false}];
    assert_eq!(candidates([prefix.clone(),vec![store(2,8)]].concat()),vec![1]);
    for (bits,signed,overflow,value) in [(128,false,3,0),(64,true,3,0),(64,false,2,0),(64,false,3,33)] {
        let mut code=prefix.clone();code[2]=Op::Imm {dst:1,value};
        code[3]=Op::Binary {dst:2,overflow,op:Binary::Add,a:0,b:1,bits,signed};code.push(store(2,8));
        assert!(candidates(code).is_empty());
    }
    let prefix=vec![local(0,0),store(0,8),Op::Imm {dst:1,value:8}];
    assert_eq!(candidates([prefix.clone(),vec![Op::FillBytes {address:0,size:1,value:15}]].concat()),vec![1]);
    assert!(candidates([prefix.clone(),vec![Op::FillBytes {address:0,size:7,value:15}]].concat()).is_empty());
    assert!(candidates([prefix,vec![Op::Imm {dst:1,value:1u128<<100},Op::FillBytes {address:0,size:1,value:15}]].concat()).is_empty());
}

#[test]
fn exhausted_budgets_and_shape_limits_publish_no_partial_candidates() {
    let f=function(vec![local(0,0),store(0,8),store(0,8)]);
    for n in 0..80 {
        let mut budget=n;let r=analyze(&f,0,f.code.len(),&mut budget);
        if r.decline.is_some() {assert!(r.candidates.is_empty());}
        assert_eq!(budget+r.work,n);
    }
    let mut huge=f.clone();huge.frame_size=MAX_FRAME+1;
    let r=analyze(&huge,0,3,&mut MAX_GLOBAL_WORK.clone());assert_eq!(r.decline,Some("shape_limit"));
    let mut huge=f.clone();huge.registers=MAX_REGISTERS+1;
    assert!(analyze(&huge,0,3,&mut MAX_GLOBAL_WORK.clone()).candidates.is_empty());
    assert!(analyze(&f,2,1,&mut MAX_GLOBAL_WORK.clone()).candidates.is_empty());
}

#[derive(Clone,Copy)]
enum Event { Write(usize,usize,u8), Read(usize,usize), Copy(usize,usize,usize), Barrier }

fn observations(events:&[Event],skip:&[usize],seed:u8)->Vec<Vec<u8>> {
    let mut bytes:Vec<_>=(0..32).map(|n|seed.wrapping_add(n)).collect();let mut out=vec![];
    for (index,event) in events.iter().enumerate() {
        if skip.contains(&index) { continue; }
        match *event {
            Event::Write(start,size,value)=>bytes[start..start+size].fill(value),
            Event::Read(start,size)=>out.push(bytes[start..start+size].to_vec()),
            Event::Copy(dst,src,size)=>{let v=bytes[src..src+size].to_vec();bytes[dst..dst+size].copy_from_slice(&v);},
            Event::Barrier=>out.push(bytes.clone()),
        }
    }
    out.push(bytes);out
}

#[test]
fn independent_byte_oracle_checks_10000_four_event_histories() {
    use Event::*;
    let alphabet=[Write(0,8,1),Write(0,4,2),Write(4,4,3),Write(2,2,4),
        Read(0,8),Read(0,4),Copy(0,8,8),Copy(4,0,8),Copy(0,4,8),Barrier];
    for encoded in 0..10000usize {
        let mut value=encoded;let mut events=vec![];let mut code=vec![];let mut event_pcs=vec![];
        for _ in 0..4 {
            let event=alphabet[value%10];value/=10;
            match event {
                Write(start,size,byte)=>{code.push(local(0,start));code.push(Op::Imm {dst:15,value:byte as u128});event_pcs.push(code.len());code.push(store(0,size as u8));},
                Read(start,size)=>{code.push(local(0,start));event_pcs.push(code.len());code.push(read(0,size as u8));},
                Copy(dst,src,size)=>{code.push(local(0,dst));code.push(local(1,src));event_pcs.push(code.len());code.push(Op::Copy {dst:0,src:1,size});},
                Barrier=>{event_pcs.push(code.len());code.push(Op::Trap {message:"observation".into()});},
            }
            events.push(event);
        }
        let deleted=candidates(code);let skip:Vec<_>=deleted.iter().map(|pc|event_pcs.iter().position(|p|p==pc).unwrap()).collect();
        for &index in &skip {assert!(matches!(events[index],Write(..)|Copy(..)));}
        for seed in [0,165] {
            assert_eq!(observations(&events,&[],seed),observations(&events,&skip,seed),"history {encoded}");
            for &index in &skip {assert_eq!(observations(&events,&[],seed),observations(&events,&[index],seed),"history {encoded}, event {index}");}
        }
    }
}
