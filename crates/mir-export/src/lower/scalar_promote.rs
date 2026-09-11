//! Select private primitive MIR slots; lower their scalar accesses to registers.
use super::*;
use rustc_middle::mir::visit::{MutatingUseContext,NonMutatingUseContext,PlaceContext,Visitor};
use std::sync::atomic::{AtomicU64,Ordering};
#[path="scalar_promote_transform.rs"]
mod transform;
static NANOS:AtomicU64=AtomicU64::new(0);
static SLOTS:AtomicU64=AtomicU64::new(0);
static ADDRESSES:AtomicU64=AtomicU64::new(0);
static REWRITTEN:AtomicU64=AtomicU64::new(0);
static MOVES:AtomicU64=AtomicU64::new(0);
struct Uses<'a> { eligible:&'a mut [bool] }
impl<'tcx> Visitor<'tcx> for Uses<'_> {
    fn visit_local(&mut self,local:mir::Local,context:PlaceContext,_:mir::Location) {
        match context {
            PlaceContext::NonUse(..)|PlaceContext::MutatingUse(MutatingUseContext::Store)
            |PlaceContext::NonMutatingUse(NonMutatingUseContext::Copy|NonMutatingUseContext::Move)=>{},
            _=>self.eligible[local.as_usize()]=false,
        }
    }
}
fn exclude_operand(eligible:&mut [bool],op:&Operand<'_>) {
    if let Operand::Copy(p)|Operand::Move(p)=op {if p.projection.is_empty() {eligible[p.local.as_usize()]=false;}}
}
pub(super) fn apply(lower:&mut Lower<'_, '_>)->Result<()> {
    let start=std::time::Instant::now();
    if lower.locals.len()>4096 || lower.code.len()>100_000 {return Ok(());}
    let mut eligible=vec![false;lower.locals.len()];
    for (id,decl) in lower.body.local_decls.iter_enumerated() {
        let id=id.as_usize();let ty=lower.mono(decl.ty);
        eligible[id]=id>lower.body.arg_count&&matches!(ty.kind(),ty::Int(_)|ty::Uint(_)|ty::Float(_)|ty::Bool|ty::Char);
    }
    for (bb,block) in lower.body.basic_blocks.iter_enumerated() {
        for (statement_index,statement) in block.statements.iter().enumerate() {
            Uses{eligible:&mut eligible}.visit_statement(statement,mir::Location{block:bb,statement_index});
            if let StatementKind::Assign(assignment)=&statement.kind {
                if let Rvalue::Aggregate(_,ops)=&assignment.1 {for op in ops {exclude_operand(&mut eligible,op);}}
            }
        }
        Uses{eligible:&mut eligible}.visit_terminator(block.terminator(),mir::Location{block:bb,statement_index:block.statements.len()});
        if let TerminatorKind::Call{args,..}=&block.terminator().kind {for arg in args {exclude_operand(&mut eligible,&arg.node);}}
    }
    // Merge exact colored ranges, then reject overlaps with any other range.
    // A prefix maximum avoids a quadratic scan in large MIR functions.
    let mut ranges=BTreeMap::<(usize,usize),bool>::new();
    for (i,slot) in lower.locals.iter().enumerate() {
        if slot.size==0 {continue;}
        *ranges.entry((slot.offset,slot.size)).or_insert(true)&=eligible[i];
    }
    let ranges:Vec<_>=ranges.into_iter().collect();let mut prefix_end=0;let mut slots=vec![];
    for (i,&((offset,size),yes)) in ranges.iter().enumerate() {
        let end=offset.checked_add(size).ok_or("scalar promotion slot overflow")?;
        if yes && prefix_end<=offset && ranges.get(i+1).is_none_or(|&((next,_),_)|next>=end) {
            slots.push(Slot{offset,size});
        }
        prefix_end=prefix_end.max(end);
    }
    let r=transform::promote(&mut lower.code,&mut lower.registers,&slots);
    SLOTS.fetch_add(r.slots as u64,Ordering::Relaxed);ADDRESSES.fetch_add(r.removed_addresses as u64,Ordering::Relaxed);
    MOVES.fetch_add(r.removed_moves as u64,Ordering::Relaxed);
    REWRITTEN.fetch_add(r.rewritten as u64,Ordering::Relaxed);NANOS.fetch_add(start.elapsed().as_nanos() as u64,Ordering::Relaxed);
    Ok(())
}
pub(super) fn report() {
    eprintln!("rust-interp-scalar-promotion: slots={} removed_addresses={} rewritten={} seconds={:.6} removed_moves={}",
        SLOTS.load(Ordering::Relaxed),ADDRESSES.load(Ordering::Relaxed),REWRITTEN.load(Ordering::Relaxed),NANOS.load(Ordering::Relaxed) as f64/1e9,MOVES.load(Ordering::Relaxed));
}
