//! Diagnostic-only MIR allocation inventory. Does not alter slots or bytecode.
use super::*;
use rustc_middle::mir::visit::{PlaceContext, Visitor};

struct Uses { referenced: Vec<bool> }
impl<'tcx> Visitor<'tcx> for Uses {
    fn visit_local(&mut self, local: mir::Local, context: PlaceContext, _: mir::Location) {
        if !matches!(context, PlaceContext::NonUse(..)) {
            self.referenced[local.as_usize()] = true;
        }
    }
}

pub(super) fn observe(lower: &Lower<'_, '_>) {
    let mut uses = Uses { referenced: vec![false; lower.locals.len()] };
    for (bb, block) in lower.body.basic_blocks.iter_enumerated() {
        for (statement_index, statement) in block.statements.iter().enumerate() {
            uses.visit_statement(statement, mir::Location { block: bb, statement_index });
        }
        uses.visit_terminator(block.terminator(), mir::Location { block: bb, statement_index: block.statements.len() });
    }
    // Return and formal argument storage remains part of the ABI even when
    // the MIR body never refers to it explicitly.
    for i in 0..=lower.body.arg_count { uses.referenced[i] = true; }
    let addresses: BTreeSet<_> = lower.code.iter().filter_map(|op| {
        if let Op::Local { offset, .. } = op { Some(*offset) } else { None }
    }).collect();
    // Coloring can assign multiple declarations to the same range. Count
    // distinct physical ranges, keeping a range if any declaration uses it.
    let mut groups = BTreeMap::<(usize, usize), (usize, bool, bool)>::new();
    for (i, slot) in lower.locals.iter().enumerate() {
        if slot.size == 0 { continue; }
        let group = groups.entry((slot.offset, slot.size)).or_default();
        group.0 += 1;
        group.1 |= uses.referenced[i];
        group.2 |= i <= lower.body.arg_count;
    }
    let mut last_end = 0;
    let mut unused_bytes = 0;
    let mut unnamed_bytes = 0;
    let mut rows = Vec::new();
    for ((offset, size), (declarations, referenced, abi)) in groups {
        assert!(offset >= last_end, "distinct colored local ranges overlap");
        last_end = offset.checked_add(size).expect("validated local size");
        assert!(last_end <= lower.frame_size);
        // Include one-past addresses conservatively; this is an inventory,
        // not a proof that unreferenced storage may be removed.
        let named = addresses.range(offset..=last_end).next().is_some();
        if !referenced { unused_bytes += size; }
        if !named && !abi { unnamed_bytes += size; }
        rows.push(serde_json::json!({"offset":offset,"size":size,"declarations":declarations,
            "mir_referenced":referenced,"abi":abi,"named_by_local_opcode":named}));
    }
    eprintln!("rust-interp-frame-census: {}", serde_json::json!({
        "name":format!("{}{:?}", lower.tcx().def_path_str(lower.instance.def_id()), lower.instance.args),
        "frame_size_before_bytecode_inlining":lower.frame_size,"frame_align":lower.frame_align,
        "mir_declarations":lower.locals.len(),"unique_mir_ranges":rows,
        "semantically_unreferenced_mir_bytes":unused_bytes,
        "non_abi_mir_bytes_without_named_local_address":unnamed_bytes,
        "declared_range_end":last_end,
        "caller_location":lower.caller_location.map(|slot|(slot.offset,slot.size)),
        "distinct_emitted_local_offsets":addresses,
        "performance_measurement":false,"removability_proven":false
    }));
}
