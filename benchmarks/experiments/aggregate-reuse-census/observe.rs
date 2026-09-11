//! Diagnostic child of scalar_frame; reuses its actual bounded planner.
use super::*;

fn primitive(ty: Ty<'_>) -> bool {
    matches!(ty.kind(), ty::Int(_) | ty::Uint(_) | ty::Float(_) | ty::Bool | ty::Char)
}

struct ArrayUses<'a> {
    arrays: &'a [bool],
    reasons: &'a mut [Option<&'static str>],
    event: Event,
}
impl ArrayUses<'_> {
    fn reject(&mut self, i: usize, reason: &'static str) {
        if self.arrays[i] { self.reasons[i].get_or_insert(reason); self.event.reads.insert(i); }
    }
    fn access(&mut self, i: usize, context: PlaceContext, projected: bool) {
        if !self.arrays[i] { return; }
        match context {
            PlaceContext::NonUse(..) => {},
            PlaceContext::NonMutatingUse(NonMutatingUseContext::Copy | NonMutatingUseContext::Move) => {
                self.event.reads.insert(i);
            }
            PlaceContext::MutatingUse(MutatingUseContext::Store) => {
                self.event.writes.insert(i);
                // A field/element write preserves all other bytes. Keep the
                // incoming whole range, including its initial zero bytes.
                if projected { self.event.reads.insert(i); }
            }
            PlaceContext::MutatingUse(MutatingUseContext::Call) => self.reject(i, "call_destination"),
            _ => self.reject(i, "address_or_unsupported_context"),
        }
    }
}
impl<'tcx> Visitor<'tcx> for ArrayUses<'_> {
    fn visit_place(&mut self, place: &mir::Place<'tcx>, context: PlaceContext, location: mir::Location) {
        let i = place.local.as_usize();
        if self.arrays[i] {
            if place.projection.iter().any(|p| !matches!(p,
                mir::ProjectionElem::Index(_) | mir::ProjectionElem::ConstantIndex { .. })) {
                self.reject(i, "unsupported_projection");
            }
            self.access(i, context, !place.projection.is_empty());
            // The original visitor still walks every projection and records
            // index-local uses. Only array-local events are replaced below.
        } else { self.super_place(place, context, location); }
    }
    fn visit_local(&mut self, local: mir::Local, context: PlaceContext, _: mir::Location) {
        self.access(local.as_usize(), context, false);
    }
}

fn merge(mut old: Event, arrays: &[bool], new: Event) -> Event {
    old.reads.retain(|&i| !arrays[i]); old.writes.retain(|&i| !arrays[i]);
    old.reads.extend(new.reads); old.writes.extend(new.writes); old
}

pub(super) fn observe(lower: &Lower<'_, '_>) {
    let started = std::time::Instant::now();
    let id = *lower.exporter.ids.get(&lower.instance).expect("registered compiler instance");
    let name = format!("{}{:?}", lower.tcx().def_path_str(lower.instance.def_id()), lower.instance.args);
    let identity = format!("{:?}", lower.instance);
    let n = lower.locals.len();
    let event_count = lower.body.basic_blocks.iter().try_fold(0usize, |n, b| n.checked_add(b.statements.len() + 1));
    let decline = |reason| eprintln!("rust-interp-aggregate-reuse: {}", serde_json::json!({
        "id":id,"name":name,"instance":identity,"old_local_extent":lower.frame_size,
        "decline":reason,"additional_bytes_saved":0,"production_change":false
    }));
    if n > MAX_LOCALS || event_count.is_none_or(|n| n > MAX_EVENTS) { decline("input_bound"); return; }
    let mut shapes = vec![]; let mut kinds = vec![]; let mut primitive_eligible = vec![];
    let mut arrays = vec![]; let mut reasons = vec![];
    for (id, local) in lower.body.local_decls.iter_enumerated() {
        let ty = lower.mono(local.ty);
        let layout = lower.layout(ty).expect("previously laid out local");
        let shape = (layout.size.bytes_usize(), layout.align.abi.bytes() as usize);
        let array = matches!(ty.kind(), ty::Array(element, _) if primitive(*element));
        let scalar = primitive(ty);
        let abi = id.as_usize() <= lower.body.arg_count;
        shapes.push(shape); primitive_eligible.push(!abi && scalar);
        arrays.push(array && shape.0 != 0);
        kinds.push(if scalar { "primitive" } else if array { "primitive_array" } else { "other_layout" });
        reasons.push(if abi { Some("abi") } else if shape.0 == 0 { Some("zero_size") } else { None });
    }
    let mut old_events = vec![]; let mut events = vec![]; let mut successors = vec![];
    for (bb, block) in lower.body.basic_blocks.iter_enumerated() {
        let mut old = vec![]; let mut new = vec![];
        for (statement_index, statement) in block.statements.iter().enumerate() {
            let location = mir::Location { block: bb, statement_index };
            let mut a = Uses { eligible: &mut primitive_eligible, event: Event::default() };
            a.visit_statement(statement, location);
            let mut b = ArrayUses { arrays: &arrays, reasons: &mut reasons, event: Event::default() };
            b.visit_statement(statement, location);
            if let StatementKind::Assign(assignment) = &statement.kind {
                let i = assignment.0.local.as_usize();
                if arrays[i] && assignment.0.projection.is_empty() {
                    let complete = matches!(&assignment.1, Rvalue::Use(..) | Rvalue::Repeat(..)) ||
                        matches!(&assignment.1, Rvalue::Aggregate(kind, _) if matches!(**kind, mir::AggregateKind::Array(_)));
                    if !complete { b.reject(i, "unproven_complete_assignment"); }
                }
            }
            new.push(merge(a.event.clone(), &arrays, b.event)); old.push(a.event);
        }
        let location = mir::Location { block: bb, statement_index: block.statements.len() };
        let mut a = Uses { eligible: &mut primitive_eligible, event: Event::default() };
        a.visit_terminator(block.terminator(), location);
        let mut b = ArrayUses { arrays: &arrays, reasons: &mut reasons, event: Event::default() };
        b.visit_terminator(block.terminator(), location);
        new.push(merge(a.event.clone(), &arrays, b.event)); old.push(a.event);
        old_events.push(old); events.push(new);
        successors.push(block.terminator().successors().map(|b| b.as_usize()).collect());
    }
    let mut original_end = 0;
    let original_slots: Vec<_> = shapes.iter().map(|&(size, align)| allocate(&mut original_end, size, align).unwrap()).collect();
    let baseline = plan(&shapes, primitive_eligible.clone(), old_events, &successors);
    let baseline = baseline.filter(|(_, end)| *end < original_end).unwrap_or((original_slots, original_end));
    assert_eq!(baseline.1, lower.frame_size, "observer reconstructed wrong baseline extent");
    assert!(baseline.0.iter().zip(&lower.locals).all(|(a,b)| a.offset == b.offset && a.size == b.size),
        "observer reconstructed wrong baseline slots");
    let eligible: Vec<_> = primitive_eligible.iter().enumerate().map(|(i, &yes)|
        yes || (arrays[i] && reasons[i].is_none())).collect();
    let mut final_eligible = vec![];
    let Some((slots, proposed_end)) = plan_with_eligibility(&shapes, eligible, events, &successors, Some(&mut final_eligible)) else {
        decline("planner_bound"); return;
    };
    let mut rows = vec![];
    for i in 0..n {
        if !arrays[i] { continue; }
        let reason = reasons[i].or_else(|| (!final_eligible[i]).then_some("entry_zero_read"));
        rows.push(serde_json::json!({"local":i,"size":shapes[i].0,"align":shapes[i].1,
            "original_offset":lower.locals[i].offset,"hypothetical_offset":slots[i].offset,
            "exclusion":reason,"eligible":final_eligible[i]}));
    }
    let mut classes = BTreeMap::<&str, (usize, usize)>::new();
    let mut physical = BTreeSet::new();
    for (i, slot) in lower.locals.iter().enumerate() {
        // Existing scalar coloring can share ranges: count each range once.
        if physical.insert((slot.offset, slot.size)) {
            let count = classes.entry(kinds[i]).or_default(); count.0 += 1; count.1 += slot.size;
        }
    }
    eprintln!("rust-interp-aggregate-reuse: {}", serde_json::json!({
        "id":id,"name":name,"instance":identity,"old_local_extent":lower.frame_size,
        "hypothetical_local_extent":proposed_end,"additional_bytes_saved":lower.frame_size.saturating_sub(proposed_end),
        "arrays":rows,"physical_classes":classes,"decline":null,"events":event_count,
        "analysis_nanos":started.elapsed().as_nanos(),"production_change":false,
        "baseline_slots_reconstructed":true
    }));
}

#[cfg(test)]
mod tests {
    use super::*;
    fn event(reads: &[usize], writes: &[usize]) -> Event {
        Event { reads: reads.iter().copied().collect(), writes: writes.iter().copied().collect() }
    }
    fn slots(events: Vec<Event>) -> Vec<Slot> {
        plan(&[(4,1);2], vec![true;2], vec![events], &[vec![]]).unwrap().0
    }
    #[test]
    fn complete_arrays_share_but_initial_zero_reads_stay_private() {
        let s=slots(vec![event(&[],&[0]),event(&[0],&[]),event(&[],&[1]),event(&[1],&[])]);
        assert_eq!(s[0].offset,s[1].offset);
        let s=slots(vec![event(&[],&[1]),event(&[1],&[]),event(&[0],&[])]);
        assert_ne!(s[0].offset,s[1].offset);
    }
    #[test]
    fn partial_write_cannot_kill_bytes_needed_after_an_intervening_array() {
        let events=vec![event(&[],&[0]),event(&[],&[1]),event(&[1],&[]),event(&[0],&[0]),event(&[0],&[])];
        let correct=slots(events.clone());
        let mut wrong=events; wrong[3].reads.clear(); let wrong=slots(wrong);
        let execute=|s:&[Slot]| {
            let mut memory=[0u8;8];
            memory[s[0].offset..s[0].offset+4].fill(17);
            memory[s[1].offset..s[1].offset+4].fill(23);
            memory[s[0].offset..s[0].offset+2].fill(31);
            memory[s[0].offset..s[0].offset+4].to_vec()
        };
        assert_eq!(execute(&correct),[31,31,17,17]);
        assert_ne!(execute(&wrong),[31,31,17,17]);
    }
    #[test]
    fn array_contexts_preserve_partial_inputs_and_reject_call_destinations() {
        let mut reasons=[None];
        let mut v=ArrayUses {arrays:&[true],reasons:&mut reasons,event:Event::default()};
        v.access(0,PlaceContext::MutatingUse(MutatingUseContext::Store),true);
        assert!(v.event.reads.contains(&0) && v.event.writes.contains(&0));
        v.access(0,PlaceContext::MutatingUse(MutatingUseContext::Call),false);
        assert_eq!(v.reasons[0],Some("call_destination"));
        let merged=merge(event(&[0,1],&[]),&[true,false],event(&[],&[0]));
        assert_eq!(merged.reads,Set::from([1])); // keep dynamic index reads
        assert_eq!(merged.writes,Set::from([0]));
    }
    #[test]
    fn padding_example_requires_a_byte_initialization_proof() {
        let mut separate=[[0u8;4];2]; let mut shared=[0u8;4];
        separate[0].fill(0x7f); shared.fill(0x7f);
        separate[1][0]=3; shared[0]=3; // a second aggregate writes one field
        assert_eq!(separate[1],[3,0,0,0]);
        assert_ne!(shared,separate[1]); // disjoint named values are insufficient
    }
}
