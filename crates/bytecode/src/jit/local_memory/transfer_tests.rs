use super::*;

fn assembler(recent: usize) -> Assembler<'static> {
    let mut a = Assembler { observe_local_transfer:true, reads:&[Some((0,9));32],
        frame_size:512, region_end:10, current_pc:5, cached:[Some(1),Some(2)],
        cache_recent:recent, ..Default::default() };
    a.facts.insert(1,Fact::Cached {lo:5,high_zero:true});
    a.facts.insert(2,Fact::Cached {lo:6,high_zero:true});
    a.local_values=vec![Value {offset:0,size:8,source:1}, Value {offset:8,size:4,source:1},
        Value {offset:16,size:4,source:3}, Value {offset:24,size:8,source:2}];
    a
}

fn load(a: &mut Assembler<'_>, dst: Reg, width: usize) {
    let value=a.facts[&1];
    let snapshot=a.capture_local_transfer(1,dst,width,value);
    a.forward_local_value(value,width,"Load");
    a.put(dst,9,31);
    a.finish_local_transfer(snapshot);
}

#[test]
fn transfer_only_when_the_actual_source_is_evicted() {
    let mut a=assembler(1);
    load(&mut a,3,8);
    assert!(!a.facts.contains_key(&1));
    assert_eq!(a.cached,[Some(3),Some(2)]);
    assert_eq!(a.local_values,vec![Value {offset:0,size:8,source:3},
        Value {offset:8,size:4,source:3},Value {offset:24,size:8,source:2}]);
    assert_eq!(a.local_transfer_events[0].transferred,2);
    let mut a=assembler(0);
    load(&mut a,3,8);
    assert!(a.facts.contains_key(&1));
    assert_eq!(a.local_values,vec![Value {offset:0,size:8,source:1},Value {offset:8,size:4,source:1}]);
    assert_eq!(a.local_transfer_events[0].outcome,"source-survived");
}

#[test]
fn narrow_result_cannot_restore_wider_aliases_or_old_destination_values() {
    let mut a=assembler(1);
    load(&mut a,3,4);
    assert_eq!(a.local_values,vec![Value {offset:8,size:4,source:3},Value {offset:24,size:8,source:2}]);
    assert_eq!(a.local_transfer_events[0].too_wide,1);
    assert_eq!(a.local_transfer_events[0].transferred,1);
    a.remember_local_memory(Some(8),4,3);
    assert_eq!(a.local_values.last().unwrap().source,3);
}

#[test]
fn full_bounded_list_keeps_survivor_and_transfer_order() {
    let mut a=assembler(1);
    a.local_values=(0..MAX_VALUES).map(|i|Value {offset:i*8,size:8,
        source:if i==7 {3} else if i%2==0 {1} else {2}}).collect();
    let expected:Vec<_>=a.local_values.iter().copied().filter(|v|v.source!=3)
        .map(|mut v|{if v.source==1 {v.source=3;} v}).collect();
    load(&mut a,3,8);
    assert_eq!(a.local_values,expected);
    a.remember_local_memory(Some(0),8,3);
    assert_eq!(a.local_values.len(),15);
    assert_eq!(a.local_values.last().unwrap().offset,0);
}

#[test]
fn wide_cached_owner_becomes_an_independent_zero_extended_result() {
    let mut a=assembler(0);
    a.cached=[Some(1),Some(1)];
    a.facts.remove(&2);
    a.facts.insert(1,Fact::Cached {lo:5,high_zero:false});
    a.local_values.retain(|v|v.source==1);
    load(&mut a,3,4);
    assert!(!a.facts.contains_key(&1));
    assert!(matches!(a.facts[&3],Fact::Cached {lo:6,high_zero:true}));
    assert_eq!(a.local_values,vec![Value {offset:8,size:4,source:3}]);
    assert_eq!(a.cached,[None,Some(3)]);
}

#[test]
fn exclusions_do_not_create_extra_register_owners() {
    let mut a=assembler(1);
    load(&mut a,1,8);
    assert!(!a.local_values.iter().any(|v|v.source==1));
    assert_eq!(a.local_transfer_events[0].outcome,"same-register");
    let mut a=assembler(1);
    a.reads=&[Some((0,9)),Some((0,9)),Some((0,9)),None];
    load(&mut a,3,8);
    assert!(!a.facts.contains_key(&3));
    assert_eq!(a.local_transfer_events[0].outcome,"dead-destination");
    for fact in [Fact::Imm(7),Fact::Local(64),Fact::Physical {lo:20}] {
        let mut a=assembler(1);
        assert!(a.capture_local_transfer(1,3,8,fact).is_none());
        assert_eq!(a.cached,[Some(1),Some(2)]);
        assert_eq!(a.local_transfer_events[0].transferred,0);
    }
}

#[test]
fn normal_redefinitions_and_writes_invalidate_transferred_values() {
    let mut a=assembler(1);
    load(&mut a,3,8);
    a.invalidate_local_memory(Some(2),1);
    assert!(!a.local_values.iter().any(|v|v.offset==0));
    assert!(a.local_values.iter().any(|v|v.offset==8));
    a.remember(3,Fact::Imm(99));
    assert!(!a.local_values.iter().any(|v|v.source==3));
    assert!(a.local_values.iter().any(|v|v.source==2));
    a.invalidate_local_memory(None,1);
    assert!(a.local_values.is_empty());
}

#[test]
fn disabled_observer_leaves_metadata_and_machine_words_exact() {
    let mut a=assembler(1);
    a.observe_local_transfer=false;
    let mut reference=assembler(1);
    reference.forward_local_value(reference.facts[&1],8,"Load");
    reference.put(3,9,31);
    load(&mut a,3,8);
    assert_eq!(a.local_values,reference.local_values);
    assert_eq!(a.words,reference.words);
    assert!(a.local_transfer_events.is_empty());
}

#[test]
#[should_panic]
fn future_metadata_insertion_during_put_is_refused() {
    let mut a=assembler(1);
    let snapshot=a.capture_local_transfer(1,3,8,a.facts[&1]);
    a.local_values.push(Value {offset:48,size:8,source:1});
    a.finish_local_transfer(snapshot);
}
