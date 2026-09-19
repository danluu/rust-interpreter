//! Bounded hints change only execution order, never current entries or results.
use serde_json::Value;

const MAX_ENTRIES:usize=16_384;
const MAX_NAME_BYTES:usize=4096;
const MAX_BYTES:usize=4*1024*1024;
struct Hint {name:String,nanos:u64}
#[derive(Default)]
pub(super) struct Durations {hints:Vec<Hint>}
impl Durations {
    pub(super) fn order(&self,entries:&[(String,usize)])->Option<Vec<usize>> {
        if self.hints.is_empty() || entries.len()>MAX_ENTRIES {return None;}
        let mut ranked=vec![];ranked.try_reserve_exact(entries.len()).ok()?;
        for (index,(name,_)) in entries.iter().enumerate() {
            let cost=self.hints.binary_search_by(|hint|hint.name.as_str().cmp(name))
                .ok().map_or(0,|i|self.hints[i].nanos);
            ranked.push((index,cost));
        }
        ranked.sort_unstable_by_key(|&(index,cost)|(std::cmp::Reverse(cost),index));
        let mut order=vec![];order.try_reserve_exact(ranked.len()).ok()?;
        order.extend(ranked.into_iter().map(|(index,_)|index));Some(order)
    }
    pub(super) fn observe(&mut self,entries:&[(String,usize)],rows:&[Value]) {
        // Retain only a complete latest request. Refused or malformed hints
        // revert to catalog order, without affecting the already computed result.
        self.hints=Self::collect(entries,rows).unwrap_or_default();
    }
    fn collect(entries:&[(String,usize)],rows:&[Value])->Option<Vec<Hint>> {
        if entries.is_empty() || entries.len()>MAX_ENTRIES || rows.len()!=2 {return None;}
        let mut charge=std::mem::size_of::<Self>()+64;
        charge=charge.checked_add(entries.len().checked_mul(std::mem::size_of::<Hint>())?)?;
        for (name,_) in entries {
            if name.len()>MAX_NAME_BYTES {return None;}
            charge=charge.checked_add(name.len().checked_add(64)?)?;
            if charge>MAX_BYTES {return None;}
        }
        let mut seen=vec![false;entries.len()];let mut workers=[false;2];
        let mut hints=vec![];hints.try_reserve_exact(entries.len()).ok()?;
        charge=(std::mem::size_of::<Self>()+64).checked_add(hints.capacity().checked_mul(std::mem::size_of::<Hint>())?)?;
        if charge>MAX_BYTES {return None;}
        for row in rows {
            let worker=usize::try_from(row["worker"].as_u64()?).ok()?;
            if worker>=2 || workers[worker] || row["status"]!="completed" || row["poisoned"]!=false {return None;}
            workers[worker]=true;
            for test in row["tests"].as_array()? {
                let index=usize::try_from(test["index"].as_u64()?).ok()?;
                let (name,_)=entries.get(index)?;
                if seen[index] || test["name"].as_str()?!=name
                    || !matches!(test["status"].as_str()?,"passed"|"failed") {return None;}
                let seconds=test["seconds"].as_f64()?;let nanos=seconds*1e9;
                if !nanos.is_finite() || seconds<0.0 || nanos>=u64::MAX as f64 {return None;}
                let mut owned=String::new();owned.try_reserve_exact(name.len()).ok()?;owned.push_str(name);
                charge=charge.checked_add(owned.capacity().checked_add(64)?)?;
                if charge>MAX_BYTES {return None;}
                hints.push(Hint{name:owned,nanos:nanos as u64});seen[index]=true;
            }
        }
        if !seen.into_iter().all(|v|v) {return None;}
        hints.sort_unstable_by(|a,b|a.name.cmp(&b.name));
        if hints.windows(2).any(|pair|pair[0].name==pair[1].name) {return None;}
        Some(hints)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    fn entries()->Vec<(String,usize)> {
        ["short","long","medium","equal"].into_iter().enumerate().map(|(i,n)|(n.into(),i+10)).collect()
    }
    fn rows(entries:&[(String,usize)],times:&[f64])->Vec<Value> {
        (0..2).map(|worker|json!({"worker":worker,"status":"completed","poisoned":false,
            "tests":entries.iter().enumerate().filter(|(i,_)|i%2==worker).map(|(i,(name,_))|
                json!({"index":i,"name":name,"seconds":times[i],"status":"passed"})).collect::<Vec<_>>()})).collect()
    }
    #[test]
    fn duration_order_uses_latest_costs_and_stable_original_index_ties() {
        let e=entries();let mut d=Durations::default();assert!(d.order(&e).is_none());
        d.observe(&e,&rows(&e,&[1.0,8.0,4.0,4.0]));assert_eq!(d.order(&e).unwrap(),vec![1,2,3,0]);
        let mut r=rows(&e,&[9.0,1.0,2.0,2.0]);r[0]["tests"][0]["status"]="failed".into();
        d.observe(&e,&r);assert_eq!(d.order(&e).unwrap(),vec![0,2,3,1]);
    }
    #[test]
    fn duration_order_maps_names_to_current_indices_without_dropping_unknown_entries() {
        let e=entries();let mut d=Durations::default();d.observe(&e,&rows(&e,&[1.0,8.0,4.0,4.0]));
        let current=vec![("new".into(),900),("medium".into(),901),("long".into(),902),("missing".into(),903)];
        let order=d.order(&current).unwrap();assert_eq!(order,vec![2,1,0,3]);
        let mut coverage=order;coverage.sort_unstable();assert_eq!(coverage,(0..current.len()).collect::<Vec<_>>());
    }
    #[test]
    fn duration_order_clears_hints_for_incomplete_or_malformed_worker_results() {
        let e=entries();let original=rows(&e,&[1.0,8.0,4.0,4.0]);
        for case in 0..10 {
            let mut r=original.clone();match case {
                0=>{r.pop();},1=>r[0]["poisoned"]=true.into(),2=>r[0]["status"]="setup-failed".into(),
                3=>{r[0]["tests"].as_array_mut().unwrap().pop();},4=>r[1]["worker"]=0.into(),
                5=>r[0]["tests"][1]=r[0]["tests"][0].clone(),6=>r[0]["tests"][0]["index"]=99.into(),
                7=>r[0]["tests"][0]["name"]="different".into(),8=>r[0]["tests"][0]["seconds"]=(-1.0).into(),
                _=>r[0]["tests"][0]["seconds"]=json!(1e300),
            }
            let mut d=Durations::default();d.observe(&e,&original);assert!(d.order(&e).is_some());
            d.observe(&e,&r);assert!(d.order(&e).is_none(),"case {case}");
        }
    }
    #[test]
    fn duration_order_refuses_oversized_hint_storage_and_duplicate_names() {
        let e=entries();let r=rows(&e,&[1.0,8.0,4.0,4.0]);let mut d=Durations::default();
        for oversized in [vec![(String::new(),0);MAX_ENTRIES+1],vec![("x".repeat(MAX_NAME_BYTES+1),0)],
            vec![("x".repeat(MAX_NAME_BYTES),0);1024]] {
            d.observe(&e,&r);d.observe(&oversized,&r);assert!(d.order(&e).is_none());
        }
        let repeated=vec![("same".into(),0),("same".into(),1)];d.observe(&repeated,&rows(&repeated,&[1.0,2.0]));
        assert!(d.order(&e).is_none());
    }
    #[test]
    fn duration_order_empty_or_unusable_hints_cannot_change_current_coverage() {
        let e=entries();let mut d=Durations::default();let mut r=rows(&e,&[1.0,8.0,4.0,4.0]);
        r[0]["tests"][0]["seconds"]=Value::Null;d.observe(&e,&r);assert!(d.order(&e).is_none());
        d.observe(&e,&rows(&e,&[0.0;4]));assert_eq!(d.order(&e).unwrap(),vec![0,1,2,3]);
        d.observe(&[],&rows(&[],&[]));assert!(d.order(&e).is_none());
    }
}
