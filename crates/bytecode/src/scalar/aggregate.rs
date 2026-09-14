//! Test-only aggregate projections. No projection is installed in a guest JIT.
//! Each <=16-byte lane observes the same original body and original PC sequence.
//! A future runtime must combine live values into one execution and a wider ABI.
use super::*;

struct Aggregate { lanes:Vec<(usize,Plan)>, size:usize, work:usize }
impl Aggregate {
    fn new(f:&Function,memory:&MemoryPlan,limit:usize)->Result<Self,&'static str> {
        if !memory.eligible {return Err("aggregate_memory_plan");}
        if f.result.size>64 || f.frame_size>1024 || f.registers>512 {return Err("aggregate_shape_limit");}
        let mut result=Self{lanes:vec![],size:f.result.size,work:0};
        for offset in (0..f.result.size.max(1)).step_by(16) {
            let size=(f.result.size-offset).min(16);
            let mut projection=f.clone();projection.result.offset=f.result.offset.checked_add(offset).ok_or("aggregate_offset")?;
            projection.result.size=size;
            let mut accesses=memory.accesses.clone();
            for access in &mut accesses {
                if matches!(f.code[access.pc],Op::Return) {
                    if access.reads!=[Access{offset:if f.result.size==0 {None} else {Some(f.result.offset)},size:f.result.size}] || !access.writes.is_empty() {
                        return Err("aggregate_return_contract");
                    }
                    access.reads=vec![Access{offset:if size==0 {None} else {Some(projection.result.offset)},size}];
                }
            }
            let projected=MemoryPlan{eligible:true,decline:None,work:memory.work,accesses};
            let plan=lower_bounded::<1024>(&projection,&projected,limit.saturating_sub(result.work))?;
            result.work=result.work.checked_add(plan.work).ok_or("aggregate_work_limit")?;
            if result.work>limit {return Err("aggregate_work_limit");}
            result.lanes.push((size,plan));
        }
        Ok(result)
    }
    fn evaluate(&self,args:&[u128],base:usize,budget:usize,name:&str)->Result<(Vec<u8>,Vec<usize>),String> {
        let mut bytes=Vec::with_capacity(self.size);let mut pcs=None;
        for (size,lane) in &self.lanes {
            let result=lane.evaluate(args,base,budget,name)?;
            if let Some(expected)=&pcs {assert_eq!(expected,&result.pcs,"projection changed control flow");}
            else {pcs=Some(result.pcs.clone());}
            bytes.extend_from_slice(&result.value.to_le_bytes()[..*size]);
        }
        assert_eq!(bytes.len(),self.size);Ok((bytes,pcs.unwrap()))
    }
}

#[path="aggregate_tests.rs"]
mod tests;
