//! Prototype: bounded dense register facts with sparse fallback and touched resets.
//! No runtime emitter uses this model yet.
use crate::Reg;
use std::collections::BTreeMap;

pub(super) const MAX_REGISTERS: usize = 65_536;
pub(super) const MAX_DENSE_BYTES: usize = 4 * 1024 * 1024;

struct Dense<V> {
    slots: Vec<Option<V>>,
    seen: Vec<u8>,
    touched: Vec<Reg>,
}
enum Storage<V> { Sparse(BTreeMap<Reg, V>), Dense(Dense<V>) }
pub(super) struct Map<V>(Storage<V>);
impl<V> Default for Map<V> {
    fn default() -> Self { Self(Storage::Sparse(BTreeMap::new())) }
}
impl<V: Copy> Map<V> {
    pub(super) fn dense(registers: usize, byte_limit: usize) -> Self {
        fn allocate<V: Copy>(registers: usize, limit: usize) -> Option<Dense<V>> {
            if registers == 0 || registers > MAX_REGISTERS || limit > MAX_DENSE_BYTES { return None; }
            let per_register = std::mem::size_of::<Option<V>>().checked_add(1 + std::mem::size_of::<Reg>())?;
            if registers.checked_mul(per_register)? > limit { return None; }
            let mut slots = Vec::new(); let mut seen = Vec::new(); let mut touched = Vec::new();
            slots.try_reserve_exact(registers).ok()?;
            seen.try_reserve_exact(registers).ok()?;
            touched.try_reserve_exact(registers).ok()?;
            let actual = slots.capacity().checked_mul(std::mem::size_of::<Option<V>>())?
                .checked_add(seen.capacity())?.checked_add(touched.capacity().checked_mul(std::mem::size_of::<Reg>())?)?;
            if actual > limit { return None; }
            slots.resize(registers, None); seen.resize(registers, 0);
            Some(Dense { slots, seen, touched })
        }
        Self(allocate(registers, byte_limit).map_or_else(|| Storage::Sparse(BTreeMap::new()), Storage::Dense))
    }
    pub(super) fn get(&self, reg: &Reg) -> Option<&V> {
        match &self.0 { Storage::Sparse(map) => map.get(reg), Storage::Dense(d) => d.slots.get(*reg as usize)?.as_ref() }
    }
    pub(super) fn contains_key(&self, reg: &Reg) -> bool { self.get(reg).is_some() }
    pub(super) fn insert(&mut self, reg: Reg, value: V) -> Option<V> {
        if let Storage::Dense(d) = &mut self.0 {
            if let Some(slot) = d.slots.get_mut(reg as usize) {
                if d.seen[reg as usize] == 0 { d.seen[reg as usize] = 1; d.touched.push(reg); }
                return slot.replace(value);
            }
            // Validated ordinary regions should never need this. Preserve map
            // semantics for all callers rather than indexing an invalid slot.
            let Storage::Dense(d) = std::mem::replace(&mut self.0, Storage::Sparse(BTreeMap::new())) else { unreachable!() };
            let Storage::Sparse(map) = &mut self.0 else { unreachable!() };
            for key in d.touched { if let Some(value) = d.slots[key as usize] { map.insert(key, value); } }
        }
        let Storage::Sparse(map) = &mut self.0 else { unreachable!() };
        map.insert(reg, value)
    }
    pub(super) fn remove(&mut self, reg: &Reg) -> Option<V> {
        match &mut self.0 { Storage::Sparse(map) => map.remove(reg), Storage::Dense(d) => d.slots.get_mut(*reg as usize)?.take() }
    }
    pub(super) fn clear(&mut self) {
        match &mut self.0 {
            Storage::Sparse(map) => map.clear(),
            Storage::Dense(d) => for reg in d.touched.drain(..) { d.slots[reg as usize] = None; d.seen[reg as usize] = 0; },
        }
    }
    /// Preserve ascending flush order, independent of insertion/removal order.
    pub(super) fn filter_sorted(&self, mut keep: impl FnMut(Reg, V) -> bool) -> Vec<(Reg, V)> {
        match &self.0 {
            Storage::Sparse(map) => map.iter().filter_map(|(&r, &v)| keep(r,v).then_some((r,v))).collect(),
            Storage::Dense(d) => {
                let mut values: Vec<_> = d.touched.iter().filter_map(|&r| d.slots[r as usize].map(|v| (r,v))).collect();
                values.sort_unstable_by_key(|&(reg, _)| reg);
                values.retain(|&(reg, value)| keep(reg, value)); values
            }
        }
    }
}

#[derive(Default)]
pub(super) struct Set(Map<()>);
impl Set {
    pub(super) fn dense(registers: usize, bytes: usize) -> Self { Self(Map::dense(registers, bytes)) }
    pub(super) fn contains(&self, reg: &Reg) -> bool { self.0.contains_key(reg) }
    pub(super) fn insert(&mut self, reg: Reg) -> bool { self.0.insert(reg, ()).is_none() }
    pub(super) fn clear(&mut self) { self.0.clear(); }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn snapshot<V: Copy>(m: &Map<V>) -> Vec<(Reg,V)> { m.filter_sorted(|_,_| true) }
    #[test]
    fn register_workspace_matches_sparse_model_across_generated_updates_and_resets() {
        for registers in [1,9,65,127,1024] {
            let mut map = Map::dense(registers, MAX_DENSE_BYTES); let mut oracle = BTreeMap::new();
            let mut seed = 0x17a52e8d9ab362c1u64;
            for step in 0..12_000 {
                seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
                let reg = (seed as usize % registers) as Reg; let value = (seed as u128) << 64 | step;
                match seed >> 60 {
                    0 => { map.clear(); oracle.clear(); },
                    1..=5 => assert_eq!(map.remove(&reg),oracle.remove(&reg)),
                    6..=9 => assert_eq!(map.get(&reg),oracle.get(&reg)),
                    _ => assert_eq!(map.insert(reg,value),oracle.insert(reg,value)),
                }
                if step % 37 == 0 { assert_eq!(snapshot(&map),oracle.iter().map(|(&k,&v)|(k,v)).collect::<Vec<_>>()); }
            }
        }
    }
    #[test]
    fn register_workspace_bounds_and_out_of_range_fallback_preserve_existing_facts() {
        for (count,bytes) in [(0,MAX_DENSE_BYTES),(MAX_REGISTERS+1,MAX_DENSE_BYTES),(65,0),(usize::MAX,MAX_DENSE_BYTES),(1,MAX_DENSE_BYTES+1)] {
            let mut map=Map::<u128>::dense(count,bytes);assert!(matches!(map.0,Storage::Sparse(_)));
            map.insert(Reg::MAX,123);assert_eq!(map.get(&Reg::MAX),Some(&123));
        }
        let mut map=Map::<u128>::dense(MAX_REGISTERS,MAX_DENSE_BYTES);assert!(matches!(map.0,Storage::Dense(_)));
        map.insert(0,9);map.insert(65_535,17);map.insert(2,3);map.remove(&2);
        assert_eq!(map.insert(Reg::MAX,21),None);assert!(matches!(map.0,Storage::Sparse(_)));
        assert_eq!(snapshot(&map),vec![(0,9),(65_535,17),(Reg::MAX,21)]);
    }
    #[test]
    fn register_workspace_reinsertions_touch_once_and_clear_retains_only_empty_capacity() {
        let mut map=Map::dense(32,MAX_DENSE_BYTES);
        for value in 0..1000u128 {map.insert(7,value);assert_eq!(map.remove(&7),Some(value));}
        let Storage::Dense(d)=&map.0 else {panic!()};assert_eq!(d.touched,vec![7]);
        let capacities=(d.slots.capacity(),d.seen.capacity(),d.touched.capacity());
        map.insert(31,42);let old=snapshot(&map);map.clear();assert!(snapshot(&map).is_empty());
        let Storage::Dense(d)=&map.0 else {panic!()};assert_eq!(capacities,(d.slots.capacity(),d.seen.capacity(),d.touched.capacity()));
        assert!(d.touched.is_empty() && d.seen.iter().all(|&v|v==0) && d.slots.iter().all(Option::is_none));
        map.insert(7,99);assert_eq!(snapshot(&map),vec![(7,99)]);assert_eq!(old,vec![(31,42)]);
    }
    #[test]
    fn register_workspace_filtered_order_matches_tree_after_adversarial_insertions() {
        for dense in [false,true] {
            let mut map=if dense {Map::dense(128,MAX_DENSE_BYTES)} else {Map::default()};
            for reg in (0..128).rev() {map.insert(reg,reg as u128*17);}
            for reg in (0..128).step_by(3) {map.remove(&reg);map.insert(reg,0);}
            let mut visited=vec![];
            let rows=map.filter_sorted(|reg,value| {visited.push(reg);reg%2==0 && value!=0});
            assert_eq!(visited,(0..128).collect::<Vec<_>>());
            let expected:Vec<_>=(0..128).filter(|r|r%2==0 && r%3!=0).map(|r|(r,r as u128*17)).collect();
            assert_eq!(rows,expected);
        }
    }
    #[test]
    fn register_workspace_set_membership_and_reset_match_tree_semantics() {
        for dense in [false,true] {
            let mut set=if dense {Set::dense(257,MAX_DENSE_BYTES)} else {Set::default()};
            let mut oracle=std::collections::BTreeSet::new();
            for pass in 0..5 {
                for i in 0..1024 {let r=((i*73+pass*13)%257) as Reg;assert_eq!(set.insert(r),oracle.insert(r));assert_eq!(set.contains(&r),oracle.contains(&r));}
                set.clear();oracle.clear();assert!((0..257).all(|r|!set.contains(&r)));
            }
        }
    }
}
