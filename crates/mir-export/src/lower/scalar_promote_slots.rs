//! Choose disjoint colored ranges without displacing legacy scalar candidates.
use rust_interp_bytecode::Slot;
use std::collections::BTreeMap;

pub(super) fn select(locals:&[Slot],eligible:&[bool],legacy:&[bool]) -> (Vec<Slot>,Vec<usize>) {
    assert_eq!(locals.len(),eligible.len());assert_eq!(locals.len(),legacy.len());
    // Exact coloring aliases must all be eligible. Any partial overlap with
    // another live range declines, including ineligible arguments/results.
    let mut ranges=BTreeMap::<(usize,usize),(bool,bool)>::new();
    for (i,slot) in locals.iter().enumerate() {
        if slot.size==0 {continue;}
        let flags=ranges.entry((slot.offset,slot.size)).or_insert((true,true));
        flags.0 &= eligible[i];flags.1 &= eligible[i] && legacy[i];
    }
    let ranges:Vec<_>=ranges.into_iter().collect();let mut prefix_end=0;let mut old=vec![];let mut added=vec![];
    for (i,&((offset,size),(yes,legacy))) in ranges.iter().enumerate() {
        let Some(end)=offset.checked_add(size) else {return (vec![],vec![]);};
        if yes && prefix_end<=offset && ranges.get(i+1).is_none_or(|&((next,_),_)|next>=end) {
            if legacy {old.push(Slot{offset,size});} else {added.push(Slot{offset,size});}
        }
        prefix_end=prefix_end.max(end);
    }
    // The original transform declines above 256 slots. Retain that decision
    // when legacy candidates alone exceed the bound, and otherwise reserve
    // their capacity before admitting any new pointer ranges.
    if old.len()>256 {return (vec![],vec![]);}
    added.truncate(256-old.len());
    let new_offsets=added.iter().map(|s|s.offset).collect();
    old.extend(added);(old,new_offsets)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn pointer_candidates_never_displace_legacy_capacity() {
        let locals:Vec<_>=(0..300).map(|i|Slot{offset:i*8,size:8}).collect();
        let eligible=vec![true;300];let legacy:Vec<_>=(0..300).map(|i|i>=50).collect();
        let (slots,added)=select(&locals,&eligible,&legacy);
        assert_eq!(slots.len(),256);assert_eq!(added,vec![0,8,16,24,32,40]);
        assert_eq!(slots[..250].iter().map(|s|s.offset).collect::<Vec<_>>(),(50..300).map(|i|i*8).collect::<Vec<_>>());
        assert!(select(&locals,&eligible,&vec![true;300]).0.is_empty());
    }
    #[test]
    fn exact_coloring_aliases_partial_overlap_and_exposed_slots_are_conservative() {
        let locals=[Slot{offset:0,size:8},Slot{offset:0,size:8},Slot{offset:16,size:16},
            Slot{offset:24,size:8},Slot{offset:40,size:8},Slot{offset:56,size:8}];
        let (slots,added)=select(&locals,&[true,false,true,true,true,true],&[true,false,true,false,true,false]);
        assert_eq!(slots.iter().map(|s|s.offset).collect::<Vec<_>>(),[40,56]);assert_eq!(added,[56]);
        let (slots,added)=select(&locals[..2],&[true,true],&[true,false]);
        assert_eq!(slots.len(),1);assert_eq!(added,[0]);
    }
}
