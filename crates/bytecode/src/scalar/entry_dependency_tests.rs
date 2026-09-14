use super::*;
use super::super::tests::{lower_code,prefix,abstract_diamond};

#[test]
fn pointer_load_before_updates_needs_no_alias_obligation() {
    let mut code=prefix();code.extend([Op::Load{dst:5,address:1,size:8},
        Op::Store{address:5,src:4,size:8},Op::Store{address:1,src:4,size:8},Op::Return]);
    let plan=lower_code(code);let d=classify_dependencies(&plan).unwrap();
    assert_eq!(d.captured_reads.len(),1);assert_eq!(d.writes,2);assert!(d.disjoint_pairs.is_empty());
}
#[test]
fn pointer_load_after_update_requires_exact_read_write_pair() {
    let mut code=prefix();code.extend([Op::Store{address:3,src:4,size:8},
        Op::Load{dst:5,address:1,size:8},Op::Store{address:5,src:4,size:8},Op::Return]);
    let plan=lower_code(code);let d=classify_dependencies(&plan).unwrap();
    let first_write=plan.nodes.iter().position(|n|matches!(n.value,Value::Write{..})).unwrap();
    assert_eq!(d.disjoint_pairs,[(d.captured_reads[0],first_write)]);
}
#[test]
fn earlier_write_sets_match_independent_forward_diamond_paths() {
    for stores in 0..16u8 {for reverse in [false,true] {
        let mut p=abstract_diamond(stores,0,reverse);let ids=if reverse {[0,3,2,1]} else {[0,1,2,3]};
        let mut reads=[0;4];let mut write_ids=[None;4];
        for logical in 0..4 {
            let pc=ids[logical];write_ids[logical]=p.computations[pc].first().copied();
            reads[logical]=p.nodes.len();p.nodes.push(Node{value:Value::Read{address:0,size:8},width:8,pc:Some(pc)});
            p.live.push(true);p.computations[pc].push(reads[logical]);
        }
        let all:Vec<_>=p.nodes.iter().enumerate().filter(|(_,n)|matches!(n.value,Value::Write{..})).map(|(id,_)|id).collect();
        let (before,_)=earlier_writes(&p,&all).unwrap();let mut expected=vec![BTreeSet::new();4];
        for path in [[0,1,3],[0,2,3]] {
            let mut occurred=BTreeSet::new();
            for block in path {if let Some(id)=write_ids[block] {occurred.insert(id);}
                expected[block].extend(occurred.iter().copied());}
        }
        for logical in 0..4 {
            let actual:BTreeSet<_>=all.iter().enumerate().filter(|(bit,_)|before[reads[logical]]&(1<<bit)!=0).map(|(_,id)|*id).collect();
            assert_eq!(actual,expected[logical],"stores={stores}, reverse={reverse}, read={logical}");
        }
    }}
}
#[test]
fn arithmetic_and_narrow_cast_addresses_keep_complete_dependencies() {
    let mut code=prefix();code.extend([Op::Cast{dst:5,src:3,from:64,to:32,signed:false},
        Op::Binary{dst:6,overflow:7,op:Binary::Add,a:1,b:5,bits:64,signed:false},
        Op::Store{address:6,src:4,size:8},Op::Return]);
    let p=lower_code(code);assert!(classify(&p).is_err());let d=classify_dependencies(&p).unwrap();
    assert!(d.captured_reads.is_empty());assert!(d.disjoint_pairs.is_empty());
    assert!(d.entry_nodes.iter().any(|&id|matches!(p.nodes[id].value,Value::Cast{to:32,..})));
    for &id in &d.entry_nodes {assert!(p.nodes[id].inputs().iter().all(|i|d.entry_nodes.contains(i)));}
}
#[test]
fn frame_phi_and_forward_dependency_roots_decline() {
    for (value,reason) in [(Value::Base(0),"entry_dependency_frame"),(Value::Phi(vec![]),"entry_dependency_phi"),
        (Value::Cast{src:3,from:64,to:64,signed:false},"entry_dependency_order")] {
        let mut p=abstract_diamond(1,0,false);p.nodes[0].value=value;
        assert_eq!(classify_dependencies(&p).err(),Some(reason));
    }
}
#[test]
fn dependency_node_limit_and_post_store_faults_remain_closed() {
    let mut p=abstract_diamond(1,0,false);let mut last=0;
    for _ in 0..4096 {let id=p.nodes.len();p.nodes.push(Node{value:Value::Cast{src:last,from:64,to:64,signed:false},width:8,pc:None});p.live.push(true);last=id;}
    let write=p.computations[0][0];p.nodes[write].value=Value::Write{address:last,value:1,size:8};
    assert_eq!(classify_dependencies(&p).err(),Some("entry_dependency_nodes"));
    let p=abstract_diamond(1,8,false);assert_eq!(classify_dependencies(&p).err(),Some("entry_fault_after_write"));
}
