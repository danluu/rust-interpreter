use super::*;
use crate::{Binary, Slot, VERSION};

fn slot_function() -> Function {
    let mut f=function(vec![local(0,0),store(0,8),local(1,16),
        Op::Store{address:1,src:0,size:8},Op::Load{dst:2,address:1,size:8},
        load(2,8),Op::Return]);
    f.frame_size=64;f
}

#[test]
fn local_pointer_slots_prove_reads_without_assuming_initial_contents() {
    let f=slot_function();let p=program(vec![f.clone()]);
    assert!(check(&p).0[0]);assert!(check(&p).1[0].eligible);
    assert!(!crate::previous::analyze(&p,0,&[false],crate::previous::Mode::Initialized).eligible);
    let mut bad=f;bad.code.remove(1);
    assert!(!check(&program(vec![bad])).1[0].eligible);
}

#[test]
fn partial_unknown_and_confined_call_writes_kill_overlapping_slots() {
    for offset in 9..24 {
        let mut f=slot_function();f.code.splice(4..4,[local(3,offset),store(3,8)]);
        assert!(!check(&program(vec![f])).1[0].eligible,"overlap at {offset}");
    }
    let mut f=slot_function();f.code.splice(4..4,[store(4,1)]);
    assert!(!check(&program(vec![f])).1[0].eligible);
    let mut f=slot_function();f.code.insert(4,Op::Call{function:1,args:vec![1],destination:1});
    let mut leaf=identity();leaf.args[0].size=8;leaf.frame_size=16;leaf.result=Slot{offset:8,size:8};
    leaf.code=vec![local(0,0),local(1,8),Op::Copy{dst:1,src:0,size:8},Op::Return];
    assert!(!check(&program(vec![f,leaf])).1[0].eligible);
}

#[test]
fn slot_load_widths_and_output_aliases_preserve_only_exact_values() {
    for size in [1,2,4,8,16] {
        let mut f=slot_function();f.code[4]=Op::Load{dst:1,address:1,size};f.code[5]=load(1,8);
        assert_eq!(check(&program(vec![f])).1[0].eligible,size==8);
    }
    let mut f=slot_function();f.code[3]=Op::Store{address:1,src:0,size:4};
    assert!(!check(&program(vec![f])).1[0].eligible);
}

#[test]
fn joins_and_backedges_cannot_invent_slot_values() {
    for other in [0,8] {
        let mut f=slot_function();f.code=vec![local(0,0),store(0,8),local(1,16),
            Op::Switch{value:4,cases:vec![(0,4)],otherwise:6},
            Op::Store{address:1,src:0,size:8},Op::Jump{target:9},
            local(3,other),Op::Store{address:1,src:3,size:8},Op::Jump{target:9},
            Op::Load{dst:2,address:1,size:8},load(2,8),Op::Return];
        assert_eq!(check(&program(vec![f])).1[0].eligible,other==0);
    }
    let mut f=slot_function();f.code.insert(6,Op::Switch{value:4,cases:vec![(0,4)],otherwise:7});
    assert!(check(&program(vec![f])).1[0].eligible);
    let mut f=slot_function();f.code=vec![local(0,0),store(0,8),local(1,16),
        Op::Load{dst:2,address:1,size:8},Op::Store{address:1,src:0,size:8},
        Op::Jump{target:3}];
    assert!(!check(&program(vec![f])).1[0].eligible);
}

#[test]
fn memmove_snapshots_slot_values_before_overlap_invalidation() {
    for (src,dst) in [(16,20),(20,16),(16,16)] {
        let mut f=slot_function();f.code=vec![local(0,0),store(0,8),local(1,src),
            Op::Store{address:1,src:0,size:8},local(3,dst),
            Op::Copy{dst:3,src:1,size:8},Op::Load{dst:2,address:3,size:8},load(2,8),Op::Return];
        assert!(check(&program(vec![f.clone()])).1[0].eligible);
        f.code[5]=Op::Copy{dst:3,src:1,size:7};
        if src!=dst {assert!(!check(&program(vec![f])).1[0].eligible);}
    }
}

#[test]
fn byte_oracle_checks_every_claimed_copy_fact_and_partial_overlaps() {
    // Concrete bytes, independent of the abstract transfer/meet implementation.
    // Nonzero frame bases make a relative Local distinguishable from a literal.
    for base in [0x1000u64,0x1234_0000] { for src in 0..24 { for dst in 0..24 { for size in 0..=16 {
        let mut state=State{bytes:vec![true;48],facts:vec![None;2],slots:BTreeMap::new()};
        let mut memory=vec![0xabu8;48];
        for (offset,fact,value) in [(0,Fact::Local(32),base+32),(8,Fact::Constant(0xabcdef),0xabcdef),
                (16,Fact::Local(40),base+40)] {
            state.slots.insert(offset,fact);memory[offset..offset+8].copy_from_slice(&value.to_le_bytes());
        }
        state.facts[0]=Some(Fact::Local(dst));state.facts[1]=Some(Fact::Local(src));
        let observed=copied_slots(&state,0,1,size);
        memory.copy_within(src..src+size,dst);
        for (offset,fact) in observed {
            let expected=match fact {Fact::Local(relative)=>base+relative as u64,Fact::Constant(v)=>v as u64};
            assert_eq!(u64::from_le_bytes(memory[offset..offset+8].try_into().unwrap()),expected);
        }
    }}}}
}

#[test]
fn stored_constants_truncate_and_feed_only_exact_extent_loads() {
    let mut f=slot_function();f.code=vec![local(0,0),local(1,16),Op::Imm{dst:3,value:(1u128<<80)+8},
        Op::Store{address:1,src:3,size:8},Op::Load{dst:2,address:1,size:8},
        Op::FillBytes{address:0,value:5,size:2},Op::Return];
    f.result=Slot{offset:0,size:8};assert!(check(&program(vec![f])).1[0].eligible);
}

#[test]
fn slot_capacity_copy_extent_and_unknown_effects_are_conservative() {
    let mut f=slot_function();f.code=vec![local(0,0),store(0,8)];f.frame_size=1024;
    for n in 0..=MAX_SLOTS {f.code.extend([local(1,16+n*8),Op::Store{address:1,src:0,size:8}]);}
    f.code.extend([Op::Load{dst:2,address:1,size:8},load(2,8),Op::Return]);
    assert!(!check(&program(vec![f])).1[0].eligible);
    let state=State{bytes:vec![true;512],facts:vec![Some(Fact::Local(256)),Some(Fact::Local(0))],
        slots:BTreeMap::from([(0,Fact::Local(0))])};
    assert!(copied_slots(&state,0,1,MAX_COPY_FACT_BYTES+1).is_empty());
    let p=program(vec![slot_function()]);
    let mut analysis=Analysis{program:&p,confined:&[false],mode:Mode::Initialized,work:0,max_work:MAX_WORK,pc:0};
    let mut state=state;state.facts.resize(6,None);
    // An unknown Call is allowed after full initialization, but its effects
    // invalidate pointer cells before any later load can use stale provenance.
    analysis.transfer(&mut state,&Op::Call{function:0,args:vec![],destination:0},&p.functions[0]).unwrap();
    assert!(state.slots.is_empty());
}

fn local(dst: u32, offset: usize) -> Op { Op::Local {dst, offset} }
fn store(address: u32, size: u8) -> Op { Op::Store {address, src:5, size} }
fn load(address: u32, size: u8) -> Op { Op::Load {dst:5, address, size} }
fn function(code: Vec<Op>) -> Function {
    Function {name:"proof".into(),frame_size:8,frame_align:8,registers:6,args:vec![],result:Slot{offset:0,size:0},code}
}
fn program(functions: Vec<Function>) -> Program {
    Program {version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,functions,data:vec![],statics:vec![],thread_locals:vec![]}
}
fn check(p: &Program) -> (Vec<bool>, Vec<Proof>) {
    crate::validate(p).unwrap();
    let effects: Vec<_> = effects(p).into_iter().map(|p| p.eligible).collect();
    let initialized = (0..p.functions.len()).map(|id| analyze(p,id,&effects,Mode::Initialized)).collect();
    (effects, initialized)
}

#[test]
fn cfg_retains_only_definite_locals_and_initialization() {
    let mut f = function(vec![local(0,0),store(0,8),Op::Jump{target:3},load(0,8),Op::Return]);f.frame_size=16;
    assert!(check(&program(vec![f.clone()])).1[0].eligible);
    let mut changed = f.clone(); changed.code[1] = Op::Imm{dst:0,value:0};
    assert!(!check(&program(vec![changed])).1[0].eligible);
    for (dst, overflow) in [(0,1),(1,0)] {
        let mut changed=f.clone(); changed.code.insert(3,Op::Binary{dst,overflow,op:Binary::Add,a:2,b:3,bits:64,signed:false});
        assert!(!check(&program(vec![changed])).1[0].eligible, "unknown reads cannot use a dead Local fact");
    }
}

#[test]
fn loops_cannot_borrow_initialization_from_a_later_iteration() {
    let good=function(vec![local(0,0),store(0,8),load(0,8),Op::Switch{value:4,cases:vec![(0,2)],otherwise:4},Op::Return]);
    assert!(check(&program(vec![good])).1[0].eligible);
    let bad=function(vec![local(0,0),load(0,8),store(0,8),Op::Switch{value:4,cases:vec![(0,1)],otherwise:4},Op::Return]);
    assert!(!check(&program(vec![bad])).1[0].eligible);
    let unreachable=function(vec![Op::Return,load(0,8)]);
    assert!(check(&program(vec![unreachable])).1[0].eligible);
}

#[test]
fn path_byte_oracle_checks_both_sides_of_cfg_joins() {
    // Independent oracle: enumerate the two abstract paths as byte masks.
    // No dataflow state or meet/transfer helper is shared with the analyzer.
    for arguments in 0..=4 { for left in 0u8..16 { for right in 0u8..16 { for read in 0..=4 {
        let mut code=vec![Op::Switch{value:4,cases:vec![(0,1)],otherwise:0}];
        for byte in 0..4 { if left & (1<<byte) != 0 {code.extend([local(0,byte),store(0,1)]);} }
        let jump=code.len();code.push(Op::Jump{target:0});let second=code.len();
        for byte in 0..4 { if right & (1<<byte) != 0 {code.extend([local(0,byte),store(0,1)]);} }
        let join=code.len();code.extend([local(0,0),load(0,read),Op::Return]);
        code[0]=Op::Switch{value:4,cases:vec![(0,1)],otherwise:second};code[jump]=Op::Jump{target:join};
        let mut f=function(code);f.frame_size=4;f.args=vec![Slot{offset:0,size:arguments}];
        let expected=[left,right].into_iter().all(|writes| (0..usize::from(read)).all(|b| b<arguments || writes&(1<<b)!=0));
        assert_eq!(check(&program(vec![f])).1[0].eligible,expected,"{arguments} {left} {right} {read}");
    }}}}
}

fn identity() -> Function {
    let mut f=function(vec![local(0,0),local(1,4),Op::Copy{dst:1,src:0,size:4},Op::Return]);
    f.args=vec![Slot{offset:0,size:4}];f.result=Slot{offset:4,size:4};f
}

#[test]
fn confined_calls_read_arguments_before_initializing_results() {
    let mut caller=function(vec![local(0,0),local(1,4),Op::Call{function:1,args:vec![0],destination:1},Op::Return]);
    caller.args=vec![Slot{offset:0,size:4}];caller.result=Slot{offset:4,size:4};
    let p=program(vec![caller.clone(),identity()]);let (effects,proofs)=check(&p);
    assert_eq!(effects,vec![true,true]);assert!(proofs.iter().all(|p|p.eligible));
    assert!(!analyze(&p,0,&[false,false],Mode::Initialized).eligible);
    caller.args.clear();caller.code[2]=Op::Call{function:1,args:vec![1],destination:1};
    assert!(!check(&program(vec![caller,identity()])).1[0].eligible);
}

#[test]
fn effects_do_not_imply_initialization_or_allow_external_accesses() {
    let mut leaf=function(vec![Op::Return]);leaf.result=Slot{offset:0,size:8};
    let (effects,proofs)=check(&program(vec![leaf]));assert_eq!(effects,vec![true]);assert!(!proofs[0].eligible);
    for body in [vec![load(0,1),Op::Return],vec![store(0,1),Op::Return]] {
        let p=program(vec![function(body)]);assert!(!check(&p).0[0]);
    }
    let recursive=function(vec![Op::Call{function:0,args:vec![],destination:0},Op::Return]);
    let (effects,proofs)=check(&program(vec![recursive]));assert_eq!(effects,vec![false]);assert!(!proofs[0].eligible);
    let mut caller=function(vec![local(0,0),store(0,8),Op::Call{function:1,args:vec![],destination:0},Op::Return]);
    let external=function(vec![load(0,1),Op::Return]);
    assert!(check(&program(vec![caller.clone(),external.clone()])).1[0].eligible);
    caller.code[1]=store(0,4);assert!(!check(&program(vec![caller,external])).1[0].eligible);
}

#[test]
fn copies_zero_frames_and_result_padding_keep_exact_extents() {
    for written in 0..=8 { for read in 0..=8 {
        let mut f=function(vec![local(0,0),store(0,written),Op::Return]);f.result=Slot{offset:0,size:read};
        assert_eq!(check(&program(vec![f])).1[0].eligible,read<=usize::from(written));
    }}
    let f=function(vec![local(0,0),Op::Copy{dst:0,src:0,size:4},Op::Return]);
    assert!(!check(&program(vec![f])).1[0].eligible);
    let mut f=function(vec![local(0,0),load(0,1),Op::Return]);f.frame_size=0;
    assert!(!check(&program(vec![f.clone()])).1[0].eligible);
    f.code.insert(1,store(0,1));assert!(check(&program(vec![f])).1[0].eligible);
}

#[test]
fn summaries_propagate_through_acyclic_callees_without_name_matching() {
    let mut middle=identity();middle.code=vec![local(0,0),local(1,4),Op::Call{function:2,args:vec![0],destination:1},Op::Return];
    let mut outer=middle.clone();outer.code[2]=Op::Call{function:1,args:vec![0],destination:1};
    let p=program(vec![outer,middle,identity()]);let (effects,proofs)=check(&p);
    assert_eq!(effects,vec![true;3]);assert!(proofs.iter().all(|p|p.eligible));
}

#[test]
fn resource_exhaustion_declines_and_does_not_publish_a_partial_proof() {
    let p=program(vec![function(vec![local(0,0),store(0,8),Op::Return])]);
    assert_eq!(analyze_with_work(&p,0,&[true],Mode::Initialized,1).decline.unwrap().reason,"work_limit");
    let mut remaining=0;assert_eq!(analyze_budgeted(&p,0,&[true],Mode::Initialized,&mut remaining).decline.unwrap().reason,"global_work_limit");
    let mut p=p;p.functions[0].frame_size=MAX_FRAME+1;
    assert_eq!(analyze(&p,0,&[true],Mode::Initialized).decline.unwrap().reason,"size_limit");
}

#[test]
fn constant_local_offsets_respect_width_bounds_aliases_and_joins() {
    for (add,bits,signed,alias,expected) in [(8,64,false,false,true),(8+(1u128<<80),64,false,false,true),
        (20,64,false,false,false),(33,64,false,false,false),(8,128,false,false,false),
        (8,64,true,false,false),(8,64,false,true,false)] {
        let mut f=function(vec![local(0,0),Op::Imm{dst:1,value:add},
            Op::Binary{dst:2,overflow:if alias {2} else {3},op:Binary::Add,a:0,b:1,bits,signed},load(2,8),Op::Return]);
        f.frame_size=32;f.args=vec![Slot{offset:0,size:16}];
        assert_eq!(check(&program(vec![f])).1[0].eligible,expected);
    }
    for right in [4,8] {
        let mut f=function(vec![local(0,0),Op::Switch{value:5,cases:vec![(0,2)],otherwise:4},
            Op::Imm{dst:1,value:4},Op::Jump{target:6},Op::Imm{dst:1,value:right},Op::Jump{target:6},
            Op::FillBytes{address:0,value:5,size:1},Op::Return]);
        f.result=Slot{offset:0,size:4};
        assert_eq!(check(&program(vec![f])).1[0].eligible,right==4);
    }
}

#[test]
fn constant_memory_extents_preserve_read_before_write_and_unknown_size_rejection() {
    for written in 0..=16 { for read in 0..=16 {
        let mut f=function(vec![local(0,0),Op::Imm{dst:1,value:written as u128},
            Op::FillBytes{address:0,value:5,size:1},Op::Return]);
        f.frame_size=32;f.result=Slot{offset:0,size:read};
        assert_eq!(check(&program(vec![f])).1[0].eligible,read<=written);
    }}
    for reverse in [false,true] {
        let mut f=function(vec![local(0,0),local(1,4),Op::Imm{dst:2,value:8},
            Op::CopyDynamic{dst:if reverse {0} else {1},src:if reverse {1} else {0},size:2},Op::Return]);
        f.frame_size=16;f.args=vec![Slot{offset:0,size:8}];f.result=Slot{offset:0,size:12};
        assert_eq!(check(&program(vec![f])).1[0].eligible,!reverse);
    }
    for initialized in [false,true] {
        let mut f=function(vec![local(0,0),local(1,4),Op::Imm{dst:2,value:4},
            Op::CompareBytes{dst:2,left:0,right:1,size:2},Op::Return]);
        f.frame_size=16;f.args=vec![Slot{offset:0,size:if initialized {8} else {4}}];
        assert_eq!(check(&program(vec![f])).1[0].eligible,initialized);
    }
    for extent in [None,Some((1u128<<80)+8),Some(9)] {
        let mut code=vec![local(0,0)];if let Some(value)=extent {code.push(Op::Imm{dst:1,value});}
        code.extend([Op::FillBytes{address:0,value:5,size:1},Op::Return]);
        assert!(!check(&program(vec![function(code)])).1[0].eligible);
    }
}
