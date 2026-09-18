//! Complete typed sites for execution; never consume the truncated JSON census.
use super::*;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(in crate::jit) struct Site {
    pub pc: usize,
    pub register: Reg,
    pub offset: i64,
    pub size: usize,
    pub write: bool,
}

#[derive(Debug)]
pub(in crate::jit) struct Plan {
    pub root: Root,
    pub low: i64,
    pub high: i64,
    pub writes: bool,
    pub frame_disjoint: bool,
    pub sites: Vec<Site>,
}

impl Plan {
    pub fn displacement(&self, pc: usize, register: Reg, size: usize, write: bool) -> Option<usize> {
        let first = self.sites.partition_point(|site| site.pc < pc);
        self.sites[first..].iter().take_while(|site| site.pc == pc)
            .find(|site| site.register == register && site.size == size && site.write == write)
            .map(|site| (site.offset - self.low) as usize)
    }
}

pub(in crate::jit) fn runtime_plan(f: &Function, start: usize, end: usize, budget: &mut usize) -> Option<Plan> {
    plan_with_minimum(f, start, end, budget, 8)
}

#[cfg(test)]
pub(in crate::jit) fn small_plan(f: &Function, start: usize, end: usize, budget: &mut usize) -> Option<Plan> {
    plan_with_minimum(f, start, end, budget, 4)
}

fn plan_with_minimum(f: &Function, start: usize, end: usize, budget: &mut usize, minimum: usize) -> Option<Plan> {
    if f.registers > MAX_ITEMS || f.code.len() > MAX_ITEMS || start >= end
        || end > f.code.len() || end-start > 1024 { return None; }
    // No helpers, transitions or unbounded transfers may clobber the cache.
    // Restrict this first candidate to the audited ordinary region opcodes.
    if f.code[start..end].iter().any(|op| !super::super::supported(op)) { return None; }
    let mut state=State {disjoint_mode:true,..State::default()};
    let mut groups=BTreeMap::<Root,Vec<Site>>::new();
    for pc in start..end {
        let op=&f.code[pc];let mut operands=1usize;
        crate::registers::visit_registers(op, |_| operands+=1, |_| {});
        *budget=budget.checked_sub(operands+state.dirty.len()+state.slots.len()+1)?;
        let accesses=match *op {
            Op::Load {address,size,..} if size != 0 => vec![(address,size as usize,false)],
            Op::Store {address,size,..} if size != 0 => vec![(address,size as usize,true)],
            Op::Copy {dst,src,size} if size != 0 && size <= 128 => vec![(src,size,false),(dst,size,true)],
            _ => vec![],
        };
        for (register,size,write) in accesses {
            if state.local(register,size,f.frame_size).is_some() { continue; }
            if let Value::Pointer(root,offset)=state.get(register) {
                groups.entry(root).or_default().push(Site {pc,register,offset,size,write});
            }
        }
        state.transfer(op,f.frame_size);
    }
    let mut plans:Vec<_>=groups.into_iter().filter_map(|(root,sites)| {
        if sites.len()<minimum { return None; }
        let low=sites.iter().map(|s|s.offset).min()?;
        let high=sites.iter().map(|s|s.offset+s.size as i64).max()?;
        if high-low>MAX_SPAN { return None; }
        Some(Plan {root,low,high,writes:sites.iter().any(|s|s.write),
            frame_disjoint:state.protected_root==Some(root),sites})
    }).collect();
    plans.sort_by_key(|p|(std::cmp::Reverse(p.sites.len()),p.high-p.low,p.root));
    plans.into_iter().next()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Slot;
    fn input(code:Vec<Op>)->Function {
        Function {name:"typed range".into(),frame_size:64,frame_align:16,registers:8,
            args:vec![],result:Slot {offset:0,size:0},code}
    }
    #[test]
    fn complete_sites_preserve_large_groups_and_copy_operand_roles() {
        let mut code=vec![Op::Load {dst:7,address:0,size:8};108];
        code.push(Op::Copy {dst:0,src:0,size:8});
        let f=input(code);let p=runtime_plan(&f,0,f.code.len(),&mut MAX_FUNCTION_WORK.clone()).unwrap();
        assert_eq!(p.sites.len(),110);assert_eq!(p.root,Root::Register(0));
        assert_eq!(p.displacement(108,0,8,false),Some(0));
        assert_eq!(p.displacement(108,0,8,true),Some(0));
        assert_eq!(p.displacement(108,0,4,true),None);
        assert_eq!(p.displacement(109,0,8,false),None);
    }
    #[test]
    fn runtime_plan_threshold_bounds_and_unaudited_operations_decline() {
        let op=Op::Load {dst:7,address:0,size:8};
        for n in [7,1025] {let f=input(vec![op.clone();n]);
            assert!(runtime_plan(&f,0,n,&mut MAX_FUNCTION_WORK.clone()).is_none());}
        let mut f=input(vec![op;8]);
        assert!(runtime_plan(&f,0,8,&mut 1).is_none());
        for op in [Op::Return,Op::Copy {dst:1,src:0,size:129}] {
            f.code.push(op);assert!(runtime_plan(&f,0,f.code.len(),&mut MAX_FUNCTION_WORK.clone()).is_none());
            f.code.pop();
        }
    }
    #[test]
    fn smaller_admission_preserves_proof_and_work_for_existing_groups() {
        for n in 1..=12 {
            let f=input(vec![Op::Load {dst:7,address:0,size:8};n]);
            let (mut old_work,mut new_work)=(MAX_FUNCTION_WORK,MAX_FUNCTION_WORK);
            let old=runtime_plan(&f,0,n,&mut old_work);
            let new=small_plan(&f,0,n,&mut new_work);
            assert_eq!(old_work,new_work);
            assert_eq!(old.is_some(),n>=8);assert_eq!(new.is_some(),n>=4);
            if let Some(old)=old {
                let new=new.unwrap();assert_eq!(old.sites,new.sites);
                assert_eq!((old.root,old.low,old.high,old.writes,old.frame_disjoint),
                    (new.root,new.low,new.high,new.writes,new.frame_disjoint));
            }
        }
    }
    #[test]
    fn smaller_admission_keeps_write_disjointness_and_bounded_declines() {
        let mut code=vec![Op::Local {dst:0,offset:0}];
        for _ in 0..4 {code.extend([Op::Load {dst:1,address:0,size:8},Op::Store {address:1,src:7,size:8}]);}
        let mut f=input(code);let p=small_plan(&f,0,f.code.len(),&mut MAX_FUNCTION_WORK.clone()).unwrap();
        assert_eq!(p.root,Root::FrameSlot(0));assert!(p.frame_disjoint && p.writes);
        assert_eq!(p.sites.len(),4);assert!(runtime_plan(&f,0,f.code.len(),&mut MAX_FUNCTION_WORK.clone()).is_none());
        assert!(small_plan(&f,0,f.code.len(),&mut 1).is_none());
        f.code.push(Op::Call {function:0,args:vec![],destination:0});
        assert!(small_plan(&f,0,f.code.len(),&mut MAX_FUNCTION_WORK.clone()).is_none());
    }
    #[test]
    fn slot_proof_includes_every_conditional_write_and_rejects_crossing_calls() {
        let mut code=vec![Op::Local {dst:0,offset:0}];
        for _ in 0..8 {code.extend([Op::Load {dst:1,address:0,size:8},Op::Store {address:1,src:7,size:8}]);}
        let f=input(code);let p=runtime_plan(&f,0,f.code.len(),&mut MAX_FUNCTION_WORK.clone()).unwrap();
        assert_eq!(p.root,Root::FrameSlot(0));assert!(p.frame_disjoint && p.writes);
        assert_eq!(p.sites.len(),8);assert!(p.sites.iter().all(|s|s.write));
        let mut f=f;f.code.insert(8,Op::Call {function:0,args:vec![],destination:0});
        assert!(runtime_plan(&f,0,f.code.len(),&mut MAX_FUNCTION_WORK.clone()).is_none());
    }
}
